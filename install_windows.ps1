param(
    [string]$OpenAIKey = "",
    [switch]$PromptForKey
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$Pythonw = Join-Path $VenvDir "Scripts\pythonw.exe"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Bananafone.lnk"
$ConfigDir = Join-Path $env:USERPROFILE ".config\bananafone"
$KeyFile = Join-Path $ConfigDir "ai-keys.md"

Set-Location $ProjectDir

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' nao encontrado. Instale Python 3.10+ de python.org e marque 'Add python.exe to PATH'."
}

if (-not (Test-Path $Python)) {
    py -3 -m venv .venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

if ($PromptForKey -and [string]::IsNullOrWhiteSpace($OpenAIKey)) {
    $SecureKey = Read-Host "OpenAI API key" -AsSecureString
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

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$ShortcutTarget = $Python
if (Test-Path $Pythonw) {
    $ShortcutTarget = $Pythonw
}
$Shortcut.TargetPath = $ShortcutTarget
$Shortcut.Arguments = "`"$ProjectDir\bananafone.py`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$Shortcut.Save()

Write-Host "Bananafone instalado."
Write-Host "Atalho criado em: $ShortcutPath"
Write-Host "Executavel do atalho: $ShortcutTarget"
if (Test-Path $KeyFile) {
    Write-Host "Chave OpenAI configurada em: $KeyFile"
}
else {
    Write-Host "Chave OpenAI nao configurada. Rode com -PromptForKey ou configure OPENAI_API_KEY."
}
