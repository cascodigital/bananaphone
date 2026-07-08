@echo off
REM BananaPhone - one-click Windows installer
REM Double-click this file. It runs install_windows.ps1 with the execution
REM policy bypassed for this process only (it does NOT change system settings).

cd /d "%~dp0"
echo Installing BananaPhone...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"

echo.
echo Done. You can close this window.
pause
