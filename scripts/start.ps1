# PoultryGuard PowerShell Start Script
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start.ps1

Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Starting PoultryGuard System" -ForegroundColor Green
Write-Host "============================================================"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Virtual environment .venv not found. Running setup.ps1..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File "scripts\setup.ps1"
}

Write-Host "`nServer endpoints:" -ForegroundColor Cyan
Write-Host "  - Web Dashboard:  http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "  - Swagger API:    http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "`nPress Ctrl+C to stop the server.`n"

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
