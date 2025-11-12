\# QueueCTL



QueueCTL is a minimal CLI-based background job queue system (Python).  

Features: enqueue jobs, multiple workers, retry with exponential backoff, Dead Letter Queue (DLQ), persistent storage (SQLite), and stdout/stderr logging.



---



\## Quick setup (Windows PowerShell)



1\. Clone / copy files to `C:\\Users\\<You>\\Desktop\\queuectl`  

2\. Open PowerShell and create \& activate a venv:

```powershell

cd $env:USERPROFILE\\Desktop\\queuectl

python -m venv .venv

.venv\\Scripts\\Activate.ps1

pip install click



