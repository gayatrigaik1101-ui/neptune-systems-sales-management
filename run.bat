@echo off
title Neptune Systems - Sales Management System
echo ============================================================
echo   NEPTUNE SYSTEMS - SALES MANAGEMENT SYSTEM
echo ============================================================
echo.
echo Select an option:
echo [1] Start Streamlit Sales Dashboard
echo [2] Run Full Automated Test Suite (Pytest)
echo [3] Generate / Update Google Apps Script
echo [4] Clean Dummy Data & Reset Database
echo [5] Exit
echo.

set /p choice="Enter choice (1-5): "

cd /d "%~dp0"
set PYTHONPATH=%~dp0

if exist "C:\Users\Gayatri\anaconda3\python.exe" (
    set "PY_EXE=C:\Users\Gayatri\anaconda3\python.exe"
) else (
    set "PY_EXE=python"
)

if "%choice%"=="1" (
    echo Launching Dashboard...
    "%PY_EXE%" -m streamlit run app\main.py --server.port 8501
) else if "%choice%"=="2" (
    echo Running Automated Tests...
    "%PY_EXE%" -m pytest tests -v
    pause
) else if "%choice%"=="3" (
    echo Generating Google Apps Script...
    "%PY_EXE%" -c "from app.google_forms import GoogleFormsManager; p = GoogleFormsManager.save_apps_script_file(); print('Generated Apps Script at:', p)"
    pause
) else if "%choice%"=="4" (
    echo Running Database Cleanup...
    "%PY_EXE%" scripts\cleanup_database.py
    pause
) else (
    echo Exiting.
)
