# BananaPhone v2 - Windows installer
#
# Self-contained: if Python is missing it installs it (winget, with a
# python.org fallback), then bootstraps a local venv, installs every
# dependency, and creates Desktop + Start Menu shortcuts that launch the
# app with no console window. tkinter and PyAudio ship as wheels/bundled on
# Windows, so no compiler is needed.
#
# Usage (PowerShell):
#   .\install_windows.ps1
#   .\install_windows.ps1 -PromptForKey
#   .\install_windows.ps1 -OpenAIKey "sk-..."
#   .\install_windows.ps1 -WithOllama        # also install Ollama + pull model
#
# Easiest path: just double-click Install-BananaPhone.bat (handles ExecutionPolicy).

param(
    [string]$OpenAIKey = "",
    [switch]$PromptForKey,
    [switch]$WithOllama
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$Pythonw = Join-Path $VenvDir "Scripts\pythonw.exe"
$AppScript = Join-Path $ProjectDir "bananaphone_v2.py"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "BananaPhone.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "BananaPhone"
$StartMenuShortcut = Join-Path $StartMenuDir "BananaPhone.lnk"
$ConfigDir = Join-Path $env:USERPROFILE ".config\bananafone"
$KeyFile = Join-Path $ConfigDir "ai-keys.md"

Set-Location $ProjectDir

function Find-BasePython {
    if (Get-Command py -ErrorAction SilentlyContinue) { return @("py", "-3") }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        # Skip the WindowsApps execution-alias stub that just opens the Store.
        $p = (Get-Command python).Source
        if ($p -notlike "*WindowsApps*") { return @("python") }
    }
    return $null
}

# --- ensure Python is present ----------------------------------------------
$BasePy = Find-BasePython
if (-not $BasePy) {
    Write-Host "Python not found. Installing it automatically..." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Python.Python.3.12 --source winget `
            --accept-package-agreements --accept-source-agreements --silent
    }
    else {
        Write-Host "winget unavailable. Downloading the official Python installer..." -ForegroundColor Yellow
        $Installer = Join-Path $env:TEMP "python-3.12-installer.exe"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -OutFile $Installer
        Start-Process -FilePath $Installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1" -Wait
    }
    # Refresh PATH for this process so we can find the new install.
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $BasePy = Find-BasePython
    if (-not $BasePy) {
        throw "Python was installed but is not on PATH yet. Close this window, open a NEW PowerShell, and re-run the installer."
    }
    Write-Host "Python installed." -ForegroundColor Green
}

# --- venv + dependencies ---------------------------------------------------
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..."
    $BaseExe = $BasePy[0]
    $BaseArgs = @()
    if ($BasePy.Length -gt 1) { $BaseArgs = $BasePy[1..($BasePy.Length - 1)] }
    & $BaseExe @BaseArgs -m venv .venv
}

Write-Host "Installing dependencies (this can take a while: faster-whisper is large)..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

# --- sanity check ----------------------------------------------------------
Write-Host "Verifying imports..."
& $Python -c "import tkinter, customtkinter, numpy, speech_recognition, pyaudio; from faster_whisper import WhisperModel; print('All imports OK')"

# --- optional OpenAI key ---------------------------------------------------
if ($PromptForKey -and [string]::IsNullOrWhiteSpace($OpenAIKey)) {
    $SecureKey = Read-Host "OpenAI API key (leave blank to set later in Settings)" -AsSecureString
    $Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
    try {
        $OpenAIKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
    }
}

if (-not [string]::IsNullOrWhiteSpace($OpenAIKey)) {
    New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
    "- **OpenAI (Speech):** ``$OpenAIKey``" | Set-Content -Path $KeyFile -Encoding UTF8
}

# --- optional Ollama for the local text LLM --------------------------------
if ($WithOllama) {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Write-Host "Installing Ollama (local LLM runtime)..." -ForegroundColor Yellow
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            winget install --id Ollama.Ollama --source winget `
                --accept-package-agreements --accept-source-agreements --silent
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path", "User")
        }
        else {
            Write-Host "winget unavailable. Install Ollama manually from https://ollama.com/download" -ForegroundColor Yellow
        }
    }
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        Write-Host "Pulling default local model qwen2.5:3b (~1.9 GB)..."
        ollama pull qwen2.5:3b
    }
}

# --- shortcuts (pythonw = no console window) -------------------------------
$LauncherTarget = $Python
if (Test-Path $Pythonw) {
    $LauncherTarget = $Pythonw
}

$WScriptShell = New-Object -ComObject WScript.Shell

function New-AppShortcut($Path) {
    $Shortcut = $WScriptShell.CreateShortcut($Path)
    $Shortcut.TargetPath = $LauncherTarget
    $Shortcut.Arguments = "`"$AppScript`""
    $Shortcut.WorkingDirectory = $ProjectDir
    $Shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
    $Shortcut.Description = "BananaPhone v2 - dictation and Jira documentation"
    $Shortcut.Save()
}

New-AppShortcut $DesktopShortcut
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
New-AppShortcut $StartMenuShortcut

Write-Host ""
Write-Host "BananaPhone v2 installed." -ForegroundColor Green
Write-Host "Desktop shortcut : $DesktopShortcut"
Write-Host "Start Menu       : $StartMenuShortcut"
Write-Host "Launcher         : $LauncherTarget `"$AppScript`""
if (Test-Path $KeyFile) {
    Write-Host "OpenAI key       : configured at $KeyFile"
}
else {
    Write-Host "OpenAI key       : not set. Add it in the app's Settings, or re-run with -PromptForKey."
}
if (-not $WithOllama) {
    Write-Host "Local LLM        : not installed. Re-run with -WithOllama, or install from Settings."
}
Write-Host ""
Write-Host "Double-click the Desktop shortcut to start."
