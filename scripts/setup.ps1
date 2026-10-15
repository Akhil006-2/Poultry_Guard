# PoultryGuard PowerShell Setup Script
# ExecutionPolicy-safe setup: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

Write-Host "============================================================" -ForegroundColor Green
Write-Host "  PoultryGuard Setup Script (PowerShell)" -ForegroundColor Green
Write-Host "============================================================"

# 1. Detect Python
Write-Host "`n[1/4] Detecting Python installation..."
$pythonExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $ver = py -3.12 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pythonExe = "py -3.12"
        Write-Host "  Found Python 3.12 via py launcher." -ForegroundColor Cyan
    } else {
        $pythonExe = "py"
        Write-Host "  Found py launcher." -ForegroundColor Cyan
    }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
    Write-Host "  Found python in PATH." -ForegroundColor Cyan
} else {
    Write-Error "Python not found in system PATH or py launcher."
    exit 1
}

# 2. Virtual Environment
Write-Host "`n[2/4] Setting up .venv virtual environment..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Invoke-Expression "$pythonExe -m venv .venv"
    Write-Host "  Created fresh .venv" -ForegroundColor Cyan
} else {
    Write-Host "  Existing .venv detected." -ForegroundColor Cyan
}

# 3. Pip Requirements
Write-Host "`n[3/4] Installing Python dependencies..."
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  Created .env configuration." -ForegroundColor Cyan
}

# 4. Frontend Build
Write-Host "`n[4/4] Setting up and building Frontend application..."
if (Test-Path "frontend\package.json") {
    Push-Location frontend
    npm install
    npm run build
    Pop-Location
    Write-Host "  Frontend built successfully into frontend/dist." -ForegroundColor Cyan
}

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  Setup complete! Run scripts\start.ps1 to launch application." -ForegroundColor Green
Write-Host "============================================================"
