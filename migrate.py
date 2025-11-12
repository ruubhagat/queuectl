# migrate.py -- add last_stdout/last_stderr columns if missing
import sqlite3
conn = sqlite3.connect("queue.db")
cur = conn.cursor()
cols = [c[1] for c in cur.execute("PRAGMA table_info(jobs)").fetchall()]
if 'last_stdout' not in cols:
    cur.execute("ALTER TABLE jobs ADD COLUMN last_stdout TEXT")
if 'last_stderr' not in cols:
    cur.execute("ALTER TABLE jobs ADD COLUMN last_stderr TEXT")
conn.commit()
conn.close()
print("migration done")
