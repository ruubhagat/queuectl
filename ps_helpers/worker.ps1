Set-Location -LiteralPath "C:\Users\FCI\Desktop\queuectl"
try {
  . "C:\Users\FCI\Desktop\queuectl\.venv\Scripts\Activate.ps1"
} catch {
  Write-Host "âš ï¸ Failed to activate venv:" ($Error[0].Exception.Message) -ForegroundColor Red
}
$Host.UI.RawUI.WindowTitle = "QueueCTL Worker"
Write-Host "ðŸš€ Starting worker (foreground)..." -ForegroundColor Green
python queuectl.py worker start --foreground
Write-Host "Worker process ended. Press Enter to close." -ForegroundColor Gray
Read-Host
