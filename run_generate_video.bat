@echo off
echo ============================================================
echo   PoultryGuard - Generate Annotated Video
echo ============================================================
echo.
echo Running standalone video processing script...
echo (Raw video path is configured inside generate_annotated_video.py)
echo.

.\.venv\Scripts\python.exe generate_annotated_video.py %*

echo.
pause
