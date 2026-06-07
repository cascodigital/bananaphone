# BananaPhone v2 - Windows installer
# Bootstraps a local Python venv, installs dependencies, and creates
# Desktop + Start Menu shortcuts that launch the app with no console window.
#
# Usage (PowerShell):
#   .\install_windows.ps1
#   .\install_windows.ps1 -PromptForKey
#   .\install_windows.ps1 -OpenAIKey "sk-..."
#
# If PowerShell blocks the script, run once:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

param(
    [string]$OpenAIKey = "",
    [switch]$PromptForKey
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

# --- Python launcher check -------------------------------------------------
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' not found. Install Python 3.10+ from python.org and tick 'Add python.exe to PATH'."
}

# --- venv + dependencies ---------------------------------------------------
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..."
    py -3 -m venv .venv
}

Write-Host "Installing dependencies (this can take a while: faster-whisper is large)..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

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
Write-Host ""
Write-Host "Double-click the Desktop shortcut to start."
