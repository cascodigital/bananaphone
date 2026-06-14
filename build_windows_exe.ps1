# SaySense - Windows standalone .exe builder
# Produces a self-contained build with PyInstaller so the app can run on a
# Windows machine that does NOT have Python installed.
#
# IMPORTANT: this must run ON Windows. A Windows .exe cannot be cross-compiled
# from Linux/macOS.
#
# Usage (PowerShell, from the project folder):
#   .\build_windows_exe.ps1            # one-folder build (recommended, reliable)
#   .\build_windows_exe.ps1 -OneFile   # single SaySense.exe (slower startup)
#
# Output:
#   dist\SaySense\SaySense.exe   (one-folder)  -> zip the whole folder
#   dist\SaySense.exe               (one-file)
#
# If PowerShell blocks the script, run once:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$AppScript = Join-Path $ProjectDir "bananaphone_v2.py"

Set-Location $ProjectDir

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\install_windows.ps1 first."
}

Write-Host "Ensuring build dependencies (PyInstaller)..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python -m pip install pyinstaller

# Heavy ML/UI deps ship data files and dynamic submodules that PyInstaller
# does not pick up automatically. Collect them explicitly.
$CommonArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "SaySense",
    "--collect-all", "customtkinter",
    "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2",
    "--collect-all", "av",
    "--hidden-import", "tokenizers"
)

if ($OneFile) {
    $ModeArgs = @("--onefile")
}
else {
    $ModeArgs = @("--onedir")
}

Write-Host "Building standalone executable (this takes a few minutes)..."
& $Python -m PyInstaller @CommonArgs @ModeArgs $AppScript

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
if ($OneFile) {
    Write-Host "Executable: $ProjectDir\dist\SaySense.exe"
    Write-Host "Hand over that single file. First launch is slower (it self-extracts)."
}
else {
    Write-Host "Build folder: $ProjectDir\dist\SaySense\"
    Write-Host "Executable  : $ProjectDir\dist\SaySense\SaySense.exe"
    Write-Host "To distribute: zip the entire 'SaySense' folder and share it."
}
Write-Host ""
Write-Host "Note: the local 'small'/'medium' Whisper models are downloaded on first"
Write-Host "use into %USERPROFILE%\.cache\huggingface. API mode needs only an OpenAI key."
