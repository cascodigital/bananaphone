@echo off
REM BananaPhone - run from source checkout after Install-BananaPhone.bat
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo BananaPhone virtual environment not found.
    echo Run Install-BananaPhone.bat first.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "%~dp0bananaphone.py"
