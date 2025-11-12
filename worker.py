# worker.py - job processor for QueueCTL (captures stdout/stderr)
import subprocess
import time
import multiprocessing
import signal
import sys
from db import (
    claim_one_pending,
    update_job_state,
    get_config,
    get_job,
)

shutdown_flag = multiprocessing.Event()


def handle_sigterm(signum, frame):
    print("Worker received stop signal, will exit after current job...")
    shutdown_flag.set()


signal.signal(signal.SIGINT, handle_sigterm)
try:
    signal.signal(signal.SIGTERM, handle_sigterm)
except Exception:
    pass


def process_job(job_id: str):
    job = get_job(job_id)
    if not job:
        return

    print(f"> Processing {job['id']} (cmd: {job['command']})")
    try:
        result = subprocess.run(
            job["command"], shell=True, capture_output=True, text=True
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode == 0:
            print(f"[OK] {job['id']}")
            update_job_state(job["id"], state="completed", attempts=job["attempts"], last_stdout=out, last_stderr=err)
        else:
            print(f"[FAIL] {job['id']} (exit={result.returncode})")
            handle_retry(job, err or out)
    except Exception as e:
        print(f"[EXC] {job['id']} -> {e}")
        handle_retry(job, str(e))


def handle_retry(job, err_msg):
    attempts = int(job["attempts"] or 0) + 1
    max_retries = int(job["max_retries"] or 3)
    base = int(get_config("backoff_base") or 2)
    if attempts > max_retries:
        print(f"[DLQ] Job {job['id']} moved to DLQ after {attempts-1} retries.")
        update_job_state(job["id"], state="dead", attempts=attempts, last_error=err_msg, last_stderr=err_msg)
        return

    delay = base ** attempts
    next_run_at = int(time.time()) + delay
    print(f"[RETRY] {job['id']} in {delay}s (attempt {attempts}/{max_retries})")
    update_job_state(
        job["id"],
        state="pending",
        attempts=attempts,
        next_run_at=next_run_at,
        last_error=err_msg,
        last_stderr=err_msg,
    )


def worker_loop(poll_interval: float = 2.0):
    print("Worker started. Press Ctrl+C to stop.")
    while not shutdown_flag.is_set():
        now_ts = int(time.time())
        job_id = claim_one_pending(now_ts)
        if not job_id:
            time.sleep(poll_interval)
            continue
        process_job(job_id)
        time.sleep(0.5)


def start_workers(count: int = 1, foreground: bool = False):
    if foreground:
        worker_loop()
        return

    procs = []
    for _ in range(count):
        p = multiprocessing.Process(target=worker_loop)
        p.start()
        procs.append(p)

    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        print("Main received KeyboardInterrupt, shutting down children...")
        shutdown_flag.set()
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    start_workers(1)
