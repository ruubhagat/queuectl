# migrate_events.py -- add job_events table if missing
import sqlite3
conn = sqlite3.connect("queue.db")
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
if 'job_events' not in tables:
    cur.execute("""
    CREATE TABLE job_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    print("job_events table created.")
else:
    print("job_events already present.")
conn.close()
