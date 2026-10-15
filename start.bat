@echo off
echo ============================================================
echo   Starting PoultryGuard Backend & Integrated Web UI
echo ============================================================

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment .venv not found. Running setup.bat first...
    call setup.bat
)

echo.
echo Launching FastAPI Server on http://127.0.0.1:8000
echo - Web Dashboard:  http://127.0.0.1:8000/
echo - Swagger Docs:   http://127.0.0.1:8000/docs
echo.
echo (For frontend development hot-reload: cd frontend && npm run dev)
echo.

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
