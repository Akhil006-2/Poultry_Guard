# PoultryGuard PowerShell Automated Tests & Smoke Test Script
# Usage: powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1

Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Running PoultryGuard Tests" -ForegroundColor Green
Write-Host "============================================================"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Virtual environment .venv not found. Run setup script first."
    exit 1
}

Write-Host "`n[1/2] Running PyTest suite..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pytest -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyTest test suite failed."
    exit 1
}

Write-Host "`n[2/2] Running End-to-End System Smoke Test..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" scripts\smoke_test.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Smoke test failed."
    exit 1
}

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  All automated tests and smoke test checks passed!" -ForegroundColor Green
Write-Host "============================================================"
