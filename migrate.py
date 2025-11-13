# migrate.py -- add missing columns safely
import sqlite3
conn = sqlite3.connect("queue.db")
cur = conn.cursor()
cols = [c[1] for c in cur.execute("PRAGMA table_info(jobs)").fetchall()]

# Add columns if missing
altered = False
if 'priority' not in cols:
    cur.execute("ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
    altered = True
if 'timeout' not in cols:
    cur.execute("ALTER TABLE jobs ADD COLUMN timeout INTEGER")
    altered = True
if 'last_stdout' not in cols:
    cur.execute("ALTER TABLE jobs ADD COLUMN last_stdout TEXT")
    altered = True
if 'last_stderr' not in cols:
    cur.execute("ALTER TABLE jobs ADD COLUMN last_stderr TEXT")
    altered = True

if altered:
    print("Migration applied: added missing columns.")
else:
    print("No migration needed.")
conn.commit()
conn.close()
