# BananaPhone - Windows installer
#
# Self-contained: if Python is missing it installs it (winget, with a
# python.org fallback), then bootstraps a local venv, installs every
# dependency, and creates Desktop + Start Menu shortcuts that launch the
# app with no console window. tkinter is bundled and PyAudio ships as a
# prebuilt wheel, so no compiler is needed - but only on Python 3.10-3.13.
# The installer refuses newer interpreters rather than triggering a build.
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
$AppScript = Join-Path $ProjectDir "bananaphone.py"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "BananaPhone.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "BananaPhone"
$StartMenuShortcut = Join-Path $StartMenuDir "BananaPhone.lnk"
$ConfigDir = Join-Path $env:USERPROFILE ".config\bananafone"
$KeyFile = Join-Path $ConfigDir "ai-keys.md"

Set-Location $ProjectDir

# PyAudio ships prebuilt wheels only up to these interpreters. On anything
# newer pip falls back to a source build, which needs MSVC Build Tools and
# dies with "Microsoft Visual C++ 14.0 or greater is required".
$SupportedPyMinor = @(13, 12, 11, 10)

function Test-PythonUsable($Exe, $ArgList) {
    # Probing a missing "py -3.x" writes to stderr; with the script-level Stop
    # preference that would abort instead of just failing the probe.
    $ErrorActionPreference = "Continue"
    try {
        $v = & $Exe @ArgList -c "import sys; print(sys.version_info.minor)" 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        return $SupportedPyMinor -contains [int]$v
    }
    catch { return $false }
}

function Find-BasePython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        # Ask for a specific minor first; "py -3" hands back the NEWEST install,
        # which is exactly how you end up on a PyAudio-less interpreter.
        foreach ($m in $SupportedPyMinor) {
            $cand = @("py", "-3.$m")
            if (Test-PythonUsable $cand[0] $cand[1..($cand.Length - 1)]) { return $cand }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        # Skip the WindowsApps execution-alias stub that just opens the Store.
        $p = (Get-Command python).Source
        if ($p -notlike "*WindowsApps*" -and (Test-PythonUsable $p @())) { return @($p) }
    }
    return $null
}

# --- ensure Python is present ----------------------------------------------
$BasePy = Find-BasePython
if (-not $BasePy) {
    Write-Host "No supported Python found (need 3.10-3.13). Installing 3.12..." -ForegroundColor Yellow
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
# A venv left over from an unsupported interpreter poisons every later step,
# so rebuild it instead of installing into it.
if ((Test-Path $Python) -and -not (Test-PythonUsable $Python @())) {
    Write-Host "Existing .venv runs an unsupported Python. Rebuilding it..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..."
    $BaseExe = $BasePy[0]
    $BaseArgs = @()
    if ($BasePy.Length -gt 1) { $BaseArgs = $BasePy[1..($BasePy.Length - 1)] }
    & $BaseExe @BaseArgs -m venv .venv
    if (-not (Test-Path $Python)) { throw "venv creation failed - no python.exe at $Python" }
}

$PyVer = & $Python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
Write-Host "Using Python $PyVer at $Python" -ForegroundColor Cyan

Write-Host "Installing dependencies (this can take a while: faster-whisper is large)..."
& $Python -m pip install --upgrade pip

# --only-binary keeps pip from attempting a source build that would demand a
# C++ toolchain. PyAudio goes first and alone: when it fails inside a combined
# `-r requirements.txt` run, pip aborts the whole transaction and NOTHING gets
# installed, which is how a failed PyAudio build leaves you without a GUI.
& $Python -m pip install --only-binary=:all: "PyAudio>=0.2.13"
if ($LASTEXITCODE -ne 0) {
    throw ("No prebuilt PyAudio wheel for Python $PyVer (upstream ships wheels up " +
           "to 3.13 only). Install Python 3.12 with " +
           "'winget install --id Python.Python.3.12 -e', delete the .venv folder, " +
           "and re-run this installer.")
}

& $Python -m pip install --only-binary=:all: -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    # Some pure-Python deps may legitimately have no wheel; retry unrestricted
    # now that PyAudio - the only one needing a compiler - is already in place.
    & $Python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. See the pip output above." }
}

# --- sanity check ----------------------------------------------------------
Write-Host "Verifying imports..."
& $Python -c "import tkinter, customtkinter, numpy, speech_recognition, pyaudio; from faster_whisper import WhisperModel; print('All imports OK')"
if ($LASTEXITCODE -ne 0) { throw "Import check failed - the install is incomplete, see the traceback above." }

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
        # Must match the app default (PROVIDER_DEFAULT_MODEL in bananaphone.py) or
        # the app 404s on a model that was never pulled.
        Write-Host "Pulling default local model qwen2.5:7b (~4.7 GB)..."
        ollama pull qwen2.5:7b
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
    $Shortcut.Description = "BananaPhone - dictation and Jira documentation"
    $Shortcut.Save()
}

New-AppShortcut $DesktopShortcut
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
New-AppShortcut $StartMenuShortcut

Write-Host ""
Write-Host "BananaPhone installed." -ForegroundColor Green
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
