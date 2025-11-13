# **QueueCTL — Background Job Queue System (CLI + Worker + Dashboard)**

### *Backend Developer Internship Assignment — Rutuja Bhagat*

QueueCTL is a **CLI-based background job queue system** built in **Python** with:

* Worker processes
* Persistent job storage (SQLite)
* Retry + exponential backoff
* Dead Letter Queue (DLQ)
* Priority + timeout + scheduled run support
* Web dashboard with live updates (WebSocket)
* Windows auto-launcher for workers + dashboard + CLI

This project demonstrates backend fundamentals such as concurrency, subprocess management, reliability, persistence, and monitoring.

---

## **🏗️ Architecture Overview**


# **Features**

### Core Requirements

| Feature                                    | Status |
| ------------------------------------------ | ------ |
| Enqueue jobs via CLI                       | ✅      |
| Multiple worker processes                  | ✅      |
| Retry with exponential backoff             | ✅      |
| Configurable retry & backoff base          | ✅      |
| Persistent job storage (SQLite)            | ✅      |
| Dead Letter Queue (DLQ)                    | ✅      |
| Job listing, filtering, status, events     | ✅      |
| Worker locking to prevent double execution | ✅      |
| Graceful shutdown (Ctrl+C safe)            | ✅      |

---

### **Bonus Features Included**

| Bonus Feature                                                    | Status |
| ---------------------------------------------------------------- | ------ |
| Job priority support                                             | ✅      |
| Job timeout support                                              | ✅      |
| Scheduled/delayed jobs (`run_at`)                                | ✅      |
| Stdout/stderr logging                                            | ✅      |
| Job event tracking (claimed, state change, failures, DLQ, retry) | ✅      |
| Minimal web dashboard (FastAPI + WebSocket live updates)         | ✅      |
| Auto-start script opening 3 terminals automatically              | ✅      |

---

# 📁 **Project Structure**

```
queuectl/
│── queuectl.py         # CLI commands (enqueue, list, dlq, config, status)
│── worker.py           # Worker process that executes jobs
│── db.py               # SQLite persistence layer
│── webapp.py           # FastAPI dashboard + WebSockets
│── templates/
│     └── index.html    # Dashboard UI
│── ps_helpers/         # PowerShell helper files for autostart
│── start_all.ps1       # Opens 3 terminals (Worker + Dashboard + CLI)
│── job*.json           # Sample job files
│── queue.db            # SQLite DB (auto-created)
│── README.md
```

---

# 🖥️ **Installation & Setup**

### 1️⃣ Clone Repository

```powershell
git clone https://github.com/<your-username>/queuectl.git
cd queuectl
```

### 2️⃣ Create & Activate Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3️⃣ Install Dependencies

```powershell
pip install -r requirements.txt
```

---

# 🚦 **Run Entire System (Auto-Start Windows Script)**

🚀 **This launches 3 windows automatically**
✔ Worker
✔ Web Dashboard
✔ Interactive CLI

### Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_all.ps1
```

Dashboard opens on:
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

# 🧪 **CLI Usage**

### ✔ Enqueue jobs

```powershell
python queuectl.py enqueue --file job3.json
python queuectl.py enqueue --file job_fail.json
```

### ✔ Enqueue with priority + timeout

```powershell
python queuectl.py enqueue --file job3.json --priority 5 --timeout 3
```

### ✔ List jobs

```powershell
python queuectl.py list
python queuectl.py list --verbose
```

### ✔ View queue summary

```powershell
python queuectl.py status
```

### ✔ Dead Letter Queue

```powershell
python queuectl.py dlq list
python queuectl.py dlq retry job_fail
```

### ✔ Change config

```powershell
python queuectl.py config set backoff_base 3
python queuectl.py config set max-retries 4
```

---

# 🌐 **Dashboard Features (FastAPI UI)**

Dashboard URL:
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Includes:

* Job table with
  ✔ id
  ✔ state
  ✔ attempts
  ✔ priority
  ✔ command
  ✔ stdout / stderr
* Live updates (WebSocket)
* Metrics box (completed, dead, avg attempts)
* Retry button for DLQ jobs
* Search + filtering
* Pagination
* Job event history modal

---

# 🔄 **Job Lifecycle**

```
pending → processing → completed
pending → processing → failed → retry...
failed (max retries reached) → dead (DLQ)
```

Backoff formula:

```
delay = backoff_base ^ attempts
```

---

# 🗄️ **Persistence**

Stored in `queue.db` (SQLite):

### `jobs` table

* id
* command
* state
* attempts
* max_retries
* priority
* timeout
* next_run_at
* stdout
* stderr
* created_at / updated_at

### `job_events` table

Tracks every job event for audit + dashboard.

---

# 🧰 **Testing Script (DB Reset + Quick Test)**

### Reset DB (optional)

```powershell
python - << 'EOF'
import sqlite3
c=sqlite3.connect("queue.db")
cur=c.cursor()
cur.execute("DELETE FROM job_events")
cur.execute("DELETE FROM jobs")
c.commit()
c.close()
print("Queue RESET!")
EOF
```

### Re-run system:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_all.ps1
```

### Enqueue sample jobs:

```powershell
python queuectl.py enqueue --file job3.json
python queuectl.py enqueue --file job_fail.json
```

---

# 🎥 **Demo Video**

```
📼 Demo Video: <>
```

# 📎 **Future Extensions**

* Multi-queue support
* Distributed workers
* Failover + heartbeats
* Docker support
* REST enqueue API

---

# 🏁 **Conclusion**

QueueCTL is a fully functional, production-style background processing system built from scratch — covering CLI design, job execution, persistence, worker orchestration, backoff, DLQ, and real-time dashboarding.

This submission satisfies **all required + bonus features**.

---