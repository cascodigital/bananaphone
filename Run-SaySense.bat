@echo off
REM SaySense - run from source checkout after Install-SaySense.bat
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo SaySense virtual environment not found.
    echo Run Install-SaySense.bat first.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "%~dp0saysense.py"
