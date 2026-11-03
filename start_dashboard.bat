@echo off
title Neptune Systems - Sales Management Dashboard
echo ============================================================
echo   NEPTUNE SYSTEMS - SALES MANAGEMENT DASHBOARD
echo   Google Workspace + Python Sales Automation
echo ============================================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0

:: Find Python executable
if exist "C:\Users\Gayatri\anaconda3\python.exe" (
    set "PY_EXE=C:\Users\Gayatri\anaconda3\python.exe"
) else (
    set "PY_EXE=python"
)

echo Starting Streamlit Dashboard...
echo Dashboard will open at: http://localhost:8501
echo.
"%PY_EXE%" -m streamlit run app\main.py --server.port 8501 --server.headless false

pause
