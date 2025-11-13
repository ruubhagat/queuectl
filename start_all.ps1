# start_all.ps1 - reliable launcher for QueueCTL (worker + dashboard + CLI)
# Place this file at: C:\Users\<you>\Desktop\queuectl\start_all.ps1
# Run with: powershell -ExecutionPolicy Bypass -File .\start_all.ps1

Set-StrictMode -Version Latest

$ProjectPath = "$env:USERPROFILE\Desktop\queuectl"
$VenvActivate = Join-Path $ProjectPath ".venv\Scripts\Activate.ps1"
$HelperFolder = Join-Path $ProjectPath "ps_helpers"

if (-not (Test-Path $ProjectPath)) {
    Write-Host "Project folder not found: $ProjectPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $VenvActivate)) {
    Write-Host "Virtualenv activate script not found at: $VenvActivate" -ForegroundColor Red
    exit 1
}

# recreate helper folder (overwrite broken helpers)
if (Test-Path $HelperFolder) {
    Remove-Item -Force -Recurse $HelperFolder
}
New-Item -ItemType Directory -Path $HelperFolder | Out-Null

# Templates use placeholders __PROJECT__ and __VENV__ which we replace safely
$workerTemplate = @'
Set-Location -LiteralPath "__PROJECT__"
try {
  . "__VENV__"
} catch {
  Write-Host "⚠️ Failed to activate venv:" ($Error[0].Exception.Message) -ForegroundColor Red
}
$Host.UI.RawUI.WindowTitle = "QueueCTL Worker"
Write-Host "🚀 Starting worker (foreground)..." -ForegroundColor Green
python queuectl.py worker start --foreground
Write-Host "Worker process ended. Press Enter to close." -ForegroundColor Gray
Read-Host
'@

$dashboardTemplate = @'
Set-Location -LiteralPath "__PROJECT__"
try {
  . "__VENV__"
} catch {
  Write-Host "⚠️ Failed to activate venv:" ($Error[0].Exception.Message) -ForegroundColor Red
}
$Host.UI.RawUI.WindowTitle = "QueueCTL Dashboard"
Write-Host "🌐 Starting dashboard (uvicorn) on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
python -m uvicorn webapp:app --reload --port 8000
Write-Host "Dashboard stopped. Press Enter to close." -ForegroundColor Gray
Read-Host
'@

$cliTemplate = @'
Set-Location -LiteralPath "__PROJECT__"
try {
  . "__VENV__"
} catch {
  Write-Host "⚠️ Failed to activate venv:" ($Error[0].Exception.Message) -ForegroundColor Red
}
$Host.UI.RawUI.WindowTitle = "QueueCTL CLI"
Write-Host "💡 CLI ready. Example commands:" -ForegroundColor Yellow
Write-Host "  python queuectl.py list --verbose" -ForegroundColor Yellow
Write-Host "  python queuectl.py enqueue --file job3.json" -ForegroundColor Yellow
# spawn an interactive shell that stays open
powershell -NoExit -Command "Set-Location -LiteralPath '__PROJECT__'; . '__VENV__'; Write-Host 'Interactive CLI ready' -ForegroundColor Green"
'@

# Replace placeholders with actual paths
$workerContent = $workerTemplate -replace "__PROJECT__", ($ProjectPath -replace "'","''") -replace "__VENV__", ($VenvActivate -replace "'","''")
$dashboardContent = $dashboardTemplate -replace "__PROJECT__", ($ProjectPath -replace "'","''") -replace "__VENV__", ($VenvActivate -replace "'","''")
$cliContent = $cliTemplate -replace "__PROJECT__", ($ProjectPath -replace "'","''") -replace "__VENV__", ($VenvActivate -replace "'","''")

# Write helper files
$workerFile = Join-Path $HelperFolder "worker.ps1"
$dashboardFile = Join-Path $HelperFolder "dashboard.ps1"
$cliFile = Join-Path $HelperFolder "cli.ps1"

Out-File -FilePath $workerFile -Encoding UTF8 -Force -InputObject $workerContent
Out-File -FilePath $dashboardFile -Encoding UTF8 -Force -InputObject $dashboardContent
Out-File -FilePath $cliFile -Encoding UTF8 -Force -InputObject $cliContent

# Launch helper scripts in new windows
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-File", $workerFile
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-File", $dashboardFile
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-File", $cliFile

Write-Host "✅ Launched Worker, Dashboard and CLI windows." -ForegroundColor Green
Write-Host "If 'Failed to activate venv' appears in any window, run this in THIS shell once:" -ForegroundColor Yellow
Write-Host "  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass" -ForegroundColor Cyan
