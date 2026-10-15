@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   PoultryGuard Environment Setup (Windows)
echo ============================================================

REM 1. Detect Python
echo [1/4] Detecting Python installation...
py -3.12 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PY_CMD=py -3.12
    echo   Found Python 3.12 via py launcher.
) else (
    py -3.11 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PY_CMD=py -3.11
        echo   Found Python 3.11 via py launcher.
    ) else (
        python --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set PY_CMD=python
            echo   Found default python in PATH.
        ) else (
            echo ERROR: Python 3.12 or 3.11 not found. Please install Python.
            exit /b 1
        )
    )
)

REM 2. Create Virtual Environment
echo.
echo [2/4] Setting up Python virtual environment in .venv...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
    echo   Created fresh .venv
) else (
    echo   Existing .venv detected.
)

REM 3. Install Python Dependencies
echo.
echo [3/4] Installing Python requirements...
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python dependencies.
    exit /b 1
)

if not exist ".env" (
    copy .env.example .env
    echo   Created default .env file.
)

REM 4. Build Frontend
echo.
echo [4/4] Setting up and building Frontend application...
if exist "frontend\package.json" (
    cd frontend
    call npm install
    call npm run build
    cd ..
    echo   Frontend built successfully into frontend/dist.
) else (
    echo   Notice: frontend/package.json not found; skipping frontend build.
)

echo.
echo ============================================================
echo   Setup completed successfully!
echo   To start the application: run start.bat
echo   To run automated tests:   run run_tests.bat
echo ============================================================
pause
