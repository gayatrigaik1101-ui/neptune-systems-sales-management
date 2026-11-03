@echo off
title Push Neptune Systems to GitHub
echo ============================================================
echo   PUSH NEPTUNE SYSTEMS TO GITHUB (gayatrigaik1101-ui)
echo ============================================================
echo.

cd /d "%~dp0"

echo Configuring Git SSL Schannel...
git config --global http.sslBackend schannel

echo Pushing main branch to origin...
echo Remote: https://github.com/gayatrigaik1101-ui/neptune-systems-sales-management.git
echo.
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo   SUCCESSFULLY PUSHED TO GITHUB!
    echo   Repository: https://github.com/gayatrigaik1101-ui/neptune-systems-sales-management
    echo ============================================================
) else (
    echo.
    echo [!] Push failed or authorization was cancelled.
    echo Please make sure the private repository 'neptune-systems-sales-management'
    echo has been created at https://github.com/new under 'gayatrigaik1101-ui'.
)

pause
