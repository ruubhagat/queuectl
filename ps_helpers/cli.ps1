Set-Location -LiteralPath "C:\Users\FCI\Desktop\queuectl"
try {
  . "C:\Users\FCI\Desktop\queuectl\.venv\Scripts\Activate.ps1"
} catch {
  Write-Host "âš ï¸ Failed to activate venv:" ($Error[0].Exception.Message) -ForegroundColor Red
}
$Host.UI.RawUI.WindowTitle = "QueueCTL CLI"
Write-Host "ðŸ’¡ CLI ready. Example commands:" -ForegroundColor Yellow
Write-Host "  python queuectl.py list --verbose" -ForegroundColor Yellow
Write-Host "  python queuectl.py enqueue --file job3.json" -ForegroundColor Yellow
# spawn an interactive shell that stays open
powershell -NoExit -Command "Set-Location -LiteralPath 'C:\Users\FCI\Desktop\queuectl'; . 'C:\Users\FCI\Desktop\queuectl\.venv\Scripts\Activate.ps1'; Write-Host 'Interactive CLI ready' -ForegroundColor Green"
