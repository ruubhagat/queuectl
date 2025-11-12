# requeue.py -- safely reset a dead job back to pending
from db import get_job, update_job_state

job_id = "job_fail"   # change if you need a different id

j = get_job(job_id)
if not j:
    print("Job not found:", job_id)
else:
    print("Before:", j["id"], j["state"], "attempts=", j["attempts"])
    update_job_state(job_id, state="pending", attempts=0, next_run_at=0, last_error=None)
    j2 = get_job(job_id)
    print("After: ", j2["id"], j2["state"], "attempts=", j2["attempts"])
    print("Requeued", job_id)
