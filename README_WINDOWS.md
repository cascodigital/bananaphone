# BananaPhone on Windows

Same engine as Linux: PyAudio capture, local `faster-whisper` transcription or
cloud `API` mode via OpenAI, plus `JIRA MODE`. The UI is CustomTkinter (dark,
rounded controls).

## TL;DR — fastest install

Needs Python 3.10+ installed first (python.org, tick "Add python.exe to PATH").

Then pick one:

- **Easiest:** double-click **`Install-BananaPhone.bat`**. Done.
  (A `.ps1` cannot be run by double-click and is blocked by the execution
  policy — the `.bat` handles both for you. It only bypasses the policy for
  that one run; it does not change any system setting.)
- **Right-click:** right-click `install_windows.ps1` → *Run with PowerShell*.
- **Manual (PowerShell):**
  ```powershell
  cd path\to\bananaphone
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\install_windows.ps1
  ```

All three copy the app into `%LOCALAPPDATA%\BananaPhone`, create the venv there,
install dependencies, and put a **BananaPhone** shortcut on your Desktop and
Start Menu. The folder you unzipped is disposable - delete it afterwards; the
shortcuts point at the installed copy, not at your Downloads folder.
Double-click the shortcut to run.
Set the OpenAI key later inside the app's **Settings** (or use `-PromptForKey`,
see below).

---

Two ways to run on Windows:

1. **Python venv + shortcut** (fastest to set up, recommended for your own machine)
2. **Standalone `.exe`** (no Python needed on the target machine, good for handing over)

---

## Option 1 — Install with Python (venv + shortcut)

Requires Python 3.10+ from [python.org](https://www.python.org/downloads/) with
**"Add python.exe to PATH"** ticked.

In PowerShell:

```powershell
cd path\to\bananaphone
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_windows.ps1
```

The installer creates:

- an installed copy of the app at `%LOCALAPPDATA%\BananaPhone`
  (override with `-InstallDir "D:\Apps\BananaPhone"`)
- `.venv` inside it, with all dependencies (including `customtkinter`)
- a **Desktop** shortcut `BananaPhone.lnk`
- a **Start Menu** shortcut under `BananaPhone`
- shortcuts target `pythonw.exe` so there is **no black console window**

Then just double-click the Desktop shortcut. The source folder you ran the
installer from can be deleted.

### API key

Recommended, without writing the key into any script:

```powershell
.\install_windows.ps1 -PromptForKey
```

Or pass it directly:

```powershell
.\install_windows.ps1 -OpenAIKey "sk-..."
```

You can also leave it blank and set it later inside the app's **Settings** window.

`API` / `JIRA MODE` look for the key in this order:

1. environment variable `OPENAI_API_KEY`
2. the app Settings value (stored in `settings_v2.json`)
3. file pointed to by `BANANAFONE_OPENAI_KEY_FILE`
4. `%USERPROFILE%\ai\config\ai-keys.md`
5. `%USERPROFILE%\.config\bananafone\ai-keys.md`

File format:

```md
- **OpenAI (Speech):** `your-key-here`
```

### Run without the shortcut

```powershell
.\.venv\Scripts\pythonw.exe .\bananaphone.py
```

### Update

```powershell
cd path\to\bananaphone
git pull
.\install_windows.ps1
```

Refreshes the installed copy at `%LOCALAPPDATA%\BananaPhone`, reuses its
`.venv`, updates dependencies, and recreates the shortcuts.

---

## Option 2 — Build a standalone `.exe`

Use this to run on a Windows machine that has **no Python installed**.
The build must run **on Windows** (a Windows `.exe` cannot be cross-compiled
from Linux).

```powershell
cd path\to\bananaphone
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_windows.ps1          # if you have not set up the venv yet
.\build_windows_exe.ps1        # one-folder build (recommended)
```

Output:

- one-folder: `dist\BananaPhone\BananaPhone.exe` — zip the whole `BananaPhone` folder to share it
- one-file (`.\build_windows_exe.ps1 -OneFile`): `dist\BananaPhone.exe` — a single file, slower first launch

The build bundles `customtkinter`, `faster-whisper`, `ctranslate2` and `av`.
Local Whisper models (`small` / `medium`) are still downloaded on first use into
`%USERPROFILE%\.cache\huggingface`. `API` mode uses the configured cloud speech
provider, so it needs an OpenAI or Gemini key but no local model download.

---

## Settings and logs (Windows paths)

- settings: `%USERPROFILE%\.config\bananafone\settings_v2.json`
- log: `%USERPROFILE%\.local\state\bananafone\bananaphone.log`

## Notes

- Clipboard uses native PowerShell `Set-Clipboard`.
- `Ctrl+Shift+D` toggles quick dictation globally while BananaPhone is running:
  press once to start, press again to stop/transcribe. If global hooking is
  blocked by Windows policy, the same shortcut still works while the window is
  focused.
- `PT -> EN` / `EN -> PT` use the configured text provider to convert the transcription before copying.
- `PT -> PT` / `EN -> EN` copy the transcription directly.
- If Windows shows `Windows cannot access the specified device, path, or file`
  immediately when opening the installer, check Windows Security protection
  history. Defender may have blocked the unsigned PyInstaller/Inno package
  before SmartScreen can show `Run anyway`.
- If the installer is blocked, download the portable zip from the same release,
  run `Unblock-File` on the zip before extracting, then launch `BananaPhone.exe`
  from the extracted folder.
- In the portable PyInstaller zip, `BananaPhone.exe` must be beside the `_internal`
  folder. `_internal` is only the bundled dependency folder; do not run anything
  from inside it.
- If `BananaPhone.exe` silently exits after SmartScreen, use the debug console zip
  from `v1.3-beta` or later and run `BananaPhone-Debug.exe` from PowerShell so
  Python/PyInstaller errors stay visible.
- If company policy blocks bundled executables, use the source zip from
  `v1.3-beta` or later. Extract it, run `Install-BananaPhone.bat`, then start the
  app through the generated shortcut, `Run-BananaPhone.bat`, or with
  `.venv\Scripts\pythonw.exe bananaphone.py`.
- If `PyAudio` fails to install with *"Microsoft Visual C++ 14.0 or greater is
  required"*, your Python is too new: upstream ships prebuilt wheels only up to
  **3.13**, and anything newer forces a source build. Install Python 3.12
  (`winget install --id Python.Python.3.12 -e`), delete the `.venv` folder, and
  re-run the installer. From v2.4.1 the installer picks a supported interpreter
  by itself and refuses to start a source build.
- For personal use you may keep an `install_windows_private.ps1` with an embedded
  key. That file is gitignored and must not be committed.
