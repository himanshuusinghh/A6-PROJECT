@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_github.ps1"
if errorlevel 1 (
    echo.
    echo The upload needs attention. Read the message above, then try again.
    pause
    exit /b 1
)
echo.
pause

