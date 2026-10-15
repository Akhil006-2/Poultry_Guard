@echo off
echo ============================================================
echo   Running PoultryGuard Automated Test Suite & Smoke Test
echo ============================================================

if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv not found. Run setup.bat first.
    exit /b 1
)

echo.
echo [1/2] Running PyTest test suite...
.\.venv\Scripts\python.exe -m pytest -v
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyTest suite failed.
    exit /b 1
)

echo.
echo [2/2] Running End-to-End System Smoke Test...
.\.venv\Scripts\python.exe scripts\smoke_test.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Smoke test failed.
    exit /b 1
)

echo.
echo ============================================================
echo   All tests passed successfully!
echo ============================================================
pause
