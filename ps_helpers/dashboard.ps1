Set-Location -LiteralPath "C:\Users\FCI\Desktop\queuectl"
try {
  . "C:\Users\FCI\Desktop\queuectl\.venv\Scripts\Activate.ps1"
} catch {
  Write-Host "âš ï¸ Failed to activate venv:" ($Error[0].Exception.Message) -ForegroundColor Red
}
$Host.UI.RawUI.WindowTitle = "QueueCTL Dashboard"
Write-Host "ðŸŒ Starting dashboard (uvicorn) on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
python -m uvicorn webapp:app --reload --port 8000
Write-Host "Dashboard stopped. Press Enter to close." -ForegroundColor Gray
Read-Host
