# demo.ps1 - enqueue sample jobs and run foreground worker for demo
Write-Host "Running demo: enqueue success + failing job"
python queuectl.py enqueue --file job3.json
python queuectl.py enqueue --file job_fail.json
Write-Host "Starting foreground worker (press Ctrl+C after you see retries/DLQ)..."
python queuectl.py worker start --foreground
Write-Host "Jobs (verbose):"
python queuectl.py list --verbose
Write-Host "DLQ:"
python queuectl.py dlq list
