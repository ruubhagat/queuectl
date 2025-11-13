# db.py - SQLite helper for QueueCTL (with job_events and pagination)
import sqlite3
import time
from typing import Optional, List, Dict, Tuple

DB_PATH = "queue.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create tables if not exists. For new DBs, this creates the schema with
    priority, timeout, last_stdout, last_stderr and job_events.
    For existing DBs, use migrate.py to add missing columns/tables.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        command TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        priority INTEGER NOT NULL DEFAULT 0,
        timeout INTEGER,
        created_at TEXT,
        updated_at TEXT,
        next_run_at INTEGER DEFAULT 0,
        last_error TEXT,
        last_stdout TEXT,
        last_stderr TEXT
    );

    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS job_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT,
        created_at TEXT
    );
    """)
    # set defaults if not present
    cur.execute("INSERT OR IGNORE INTO config(key, value) VALUES (?, ?)", ("backoff_base", "2"))
    cur.execute("INSERT OR IGNORE INTO config(key, value) VALUES (?, ?)", ("default_max_retries", "3"))
    conn.commit()
    conn.close()


def save_job(job: Dict):
    conn = get_conn()
    cur = conn.cursor()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cur.execute("""
    INSERT INTO jobs(
      id, command, state, attempts, max_retries, priority, timeout,
      created_at, updated_at, next_run_at, last_error, last_stdout, last_stderr
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job["id"],
        job["command"],
        job.get("state", "pending"),
        job.get("attempts", 0),
        job.get("max_retries", 3),
        job.get("priority", 0),
        job.get("timeout", None),
        job.get("created_at", now),
        job.get("updated_at", now),
        job.get("next_run_at", 0),
        job.get("last_error", None),
        job.get("last_stdout", None),
        job.get("last_stderr", None),
    ))
    conn.commit()
    conn.close()


def list_jobs(state: Optional[str] = None) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    if state:
        cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY priority DESC, created_at", (state,))
    else:
        cur.execute("SELECT * FROM jobs ORDER BY priority DESC, created_at")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_jobs_paginated(page: int = 1, per_page: int = 20, state: Optional[str] = None) -> Tuple[List[sqlite3.Row], int]:
    """
    Return (rows, total_count) for given page/per_page. page is 1-based.
    """
    offset = (max(1, page) - 1) * per_page
    conn = get_conn()
    cur = conn.cursor()
    if state:
        cur.execute("SELECT COUNT(*) as cnt FROM jobs WHERE state=?", (state,))
        total = cur.fetchone()["cnt"]
        cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY priority DESC, created_at LIMIT ? OFFSET ?", (state, per_page, offset))
    else:
        cur.execute("SELECT COUNT(*) as cnt FROM jobs")
        total = cur.fetchone()["cnt"]
        cur.execute("SELECT * FROM jobs ORDER BY priority DESC, created_at LIMIT ? OFFSET ?", (per_page, offset))
    rows = cur.fetchall()
    conn.close()
    return rows, total


def get_job(job_id: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    r = cur.fetchone()
    conn.close()
    return r


def get_config(key: str) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else None


def set_config(key: str, value: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def claim_one_pending(now_ts: int) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute(
            "SELECT id FROM jobs WHERE state='pending' AND next_run_at<=? ORDER BY priority DESC, created_at LIMIT 1",
            (now_ts,),
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return None
        job_id = row["id"]
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cur.execute(
            "UPDATE jobs SET state='processing', updated_at=? WHERE id=? AND state='pending'",
            (now, job_id),
        )
        if cur.rowcount == 1:
            # record event
            cur.execute("INSERT INTO job_events(job_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
                        (job_id, "claimed", None, now))
            conn.commit()
            return job_id
        else:
            conn.rollback()
            return None
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def _record_event(conn, job_id: str, event_type: str, message: Optional[str] = None):
    cur = conn.cursor()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cur.execute("INSERT INTO job_events(job_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
                (job_id, event_type, message, now))


def update_job_state(job_id: str,
                     state: Optional[str] = None,
                     attempts: Optional[int] = None,
                     next_run_at: Optional[int] = None,
                     last_error: Optional[str] = None,
                     last_stdout: Optional[str] = None,
                     last_stderr: Optional[str] = None,
                     timeout: Optional[int] = None,
                     priority: Optional[int] = None):
    """
    Update job fields; supports event logging to job_events table.
    """
    conn = get_conn()
    cur = conn.cursor()
    parts = []
    params = []
    if state is not None:
        parts.append("state=?"); params.append(state)
    if attempts is not None:
        parts.append("attempts=?"); params.append(attempts)
    if next_run_at is not None:
        parts.append("next_run_at=?"); params.append(next_run_at)
    if last_error is not None:
        parts.append("last_error=?"); params.append(last_error)
    if last_stdout is not None:
        parts.append("last_stdout=?"); params.append(last_stdout)
    if last_stderr is not None:
        parts.append("last_stderr=?"); params.append(last_stderr)
    if timeout is not None:
        parts.append("timeout=?"); params.append(timeout)
    if priority is not None:
        parts.append("priority=?"); params.append(priority)

    # always update updated_at
    parts.append("updated_at=?")
    params.append(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    params.append(job_id)
    sql = "UPDATE jobs SET " + ", ".join(parts) + " WHERE id=?"
    cur.execute(sql, tuple(params))

    # insert an event capturing the change
    # choose event_type based on state or attempts
    try:
        if state is not None:
            ev = f"state:{state}"
        else:
            ev = "updated"
        _record_event(conn, job_id, ev, last_error or last_stderr)
    except Exception:
        pass

    conn.commit()
    conn.close()


def stats_summary() -> Dict[str, int]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT state, COUNT(*) as cnt FROM jobs GROUP BY state")
    rows = cur.fetchall()
    summary = {r["state"]: r["cnt"] for r in rows}
    cur.execute("SELECT COUNT(*) as total FROM jobs")
    total = cur.fetchone()["total"]
    conn.close()
    summary["total"] = total
    return summary


def get_job_events(job_id: str, limit: int = 100) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM job_events WHERE job_id=? ORDER BY created_at DESC LIMIT ?", (job_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows
