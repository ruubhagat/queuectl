# webapp.py - WebSocket-backed dashboard with pagination, events, and optional token auth
import asyncio
import json
import os
import time
from typing import Dict, List, Set
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form, HTTPException, Header, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from db import list_jobs, get_jobs_paginated, stats_summary, get_job, update_job_state, get_job_events

app = FastAPI(title="QueueCTL Dashboard (WS+Auth+Events)")

# allow local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Dashboard auth token (optional)
DASH_TOKEN = os.environ.get("DASHBOARD_TOKEN", None)

clients: Set[WebSocket] = set()
_last_snapshot = {"jobs": None, "status": None}

def _serialize_jobs(rows) -> List[Dict]:
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "command": r["command"],
            "state": r["state"],
            "attempts": r["attempts"],
            "max_retries": r["max_retries"],
            "priority": r["priority"],
            "timeout": r["timeout"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "next_run_at": r["next_run_at"],
            "last_error": r["last_error"],
            "last_stdout": r["last_stdout"],
            "last_stderr": r["last_stderr"],
        })
    return out

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "token_enabled": bool(DASH_TOKEN)})

@app.get("/api/jobs")
async def api_jobs(state: str = None, page: int = 1, per_page: int = 20):
    rows, total = get_jobs_paginated(page=page, per_page=per_page, state=state)
    return JSONResponse({"jobs": _serialize_jobs(rows), "total": total, "page": page, "per_page": per_page})

@app.get("/api/status")
async def api_status():
    summary = stats_summary()
    rows = list_jobs()
    avg_attempts = round((sum([r["attempts"] for r in rows]) / len(rows)) if rows else 0, 2)
    summary["avg_attempts"] = avg_attempts
    summary["timestamp"] = int(time.time())
    return JSONResponse(summary)

@app.get("/api/jobs/{job_id}/events")
async def api_job_events(job_id: str, limit: int = 100):
    evs = get_job_events(job_id, limit=limit)
    out = []
    for e in evs:
        out.append({"event_type": e["event_type"], "message": e["message"], "created_at": e["created_at"]})
    return JSONResponse(out)

def _check_token(header_token: str = None, query_token: str = None):
    """
    Return True if allowed. If DASH_TOKEN not set, allow by default.
    """
    if not DASH_TOKEN:
        return True
    # prefer header
    if header_token and header_token == DASH_TOKEN:
        return True
    if query_token and query_token == DASH_TOKEN:
        return True
    return False

@app.post("/api/dlq/retry")
async def api_dlq_retry(job_id: str = Form(...), x_api_key: str = Header(None)):
    if not _check_token(header_token=x_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
    j = get_job(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["state"] != "dead":
        raise HTTPException(status_code=400, detail="Job not in DLQ")
    update_job_state(job_id, state="pending", attempts=0, next_run_at=0, last_error=None, last_stdout=None, last_stderr=None)
    return JSONResponse({"status": "ok", "message": f"Requeued {job_id}"})

# websocket endpoint with optional token in query param
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(None)):
    # basic token check on handshake
    if DASH_TOKEN and token != DASH_TOKEN:
        await ws.close(code=4001)
        return
    await ws.accept()
    clients.add(ws)
    try:
        await send_snapshot([ws])
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "retry" and msg.get("job_id"):
                    # only allow if no token required or token was provided on ws
                    j_id = msg["job_id"]
                    j = get_job(j_id)
                    if j and j["state"] == "dead":
                        update_job_state(j_id, state="pending", attempts=0, next_run_at=0, last_error=None, last_stdout=None, last_stderr=None)
                        await send_snapshot()
            except Exception:
                pass
    except WebSocketDisconnect:
        clients.discard(ws)
    except Exception:
        clients.discard(ws)

async def send_snapshot(target_clients: List[WebSocket] = None):
    rows = list_jobs()
    jobs = _serialize_jobs(rows)
    summary = stats_summary()
    rows_all = list_jobs()
    avg_attempts = round((sum([r["attempts"] for r in rows_all]) / len(rows_all)) if rows_all else 0, 2)
    summary["avg_attempts"] = avg_attempts
    summary["timestamp"] = int(time.time())

    global _last_snapshot
    payload = {"type": "snapshot", "jobs": jobs, "status": summary}

    if not target_clients:
        if _last_snapshot["jobs"] == jobs and _last_snapshot["status"] == summary:
            return
        _last_snapshot["jobs"] = jobs
        _last_snapshot["status"] = summary
        target = list(clients)
    else:
        target = target_clients

    text = json.dumps(payload, default=str)
    to_remove = []
    for c in target:
        try:
            await c.send_text(text)
        except Exception:
            to_remove.append(c)
    for r in to_remove:
        clients.discard(r)

async def _broadcaster():
    while True:
        try:
            await send_snapshot()
        except Exception:
            pass
        await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_broadcaster())

@app.get("/api/health")
async def health():
    return {"status": "ok", "time": int(time.time())}
