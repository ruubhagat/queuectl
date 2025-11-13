-- schema.sql
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    command TEXT,
    state TEXT,
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    priority INTEGER DEFAULT 0,
    timeout INTEGER,
    stdout TEXT,
    stderr TEXT,
    next_run_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    event_type TEXT,
    message TEXT,
    created_at TEXT
);
