# SaySense AI Handoff

## Current Product Identity

- Public product name: **SaySense**
- Version line: **1.5.1 Beta**
- Tagline: **You speak. It makes sense.**
- Internal repository / historical codename: `saysense`
- Legacy app kept for reference: `bananafone.py` / `README_V1.md`

The public-facing app name is SaySense. Do not rebrand releases, screenshots,
installers, desktop entries, or README copy back to BananaPhone unless the owner
explicitly asks for that rollback.

## Compatibility Decisions

Keep these internal paths and environment variables for backward compatibility:

- Linux settings: `~/.config/bananafone/settings_v2.json`
- Linux logs: `~/.local/state/bananafone/saysense.log`
- Jira history: `~/.config/bananafone/jira_history.json`
- Environment variable prefix: `BANANAFONE_*`
- Main source file: `saysense.py`

These names are technical debt, but changing them now would lose existing keys,
history, defaults, and support notes. Public branding is SaySense; internal
storage remains Bananafone/BananaPhone-compatible until a dedicated migration is
implemented.

## Release Rules

- Tags containing `beta`, such as `v1.5-beta.1`, publish prereleases.
- GitHub Actions builds:
  - Windows installer: `SaySense-Setup-<version>.exe`
  - Windows source zip: `SaySense-Source-<version>.zip`
  - Linux AppImage: `SaySense-<version>-x86_64.AppImage`
  - Checksums: `*.sha256`
  - Optional diagnostic/portable artifacts: `SaySense-Portable-<version>.zip`
    and `SaySense-Debug-Console-<version>.zip`
- The active SaySense repository is `cascodigital/saysense`.
- The historical BananaPhone v2 repository is `cascodigital/saysense`.

## Current Workflow

- Dictate mode: speech-to-text plus optional translation to selected output
  language.
- Jira Mode: captures polished notes, generates Customer Comment and Internal
  Note, validates output, stores local history, and supports regeneration.
- Settings exposes silence timeout, provider selection, API keys, model/server
  settings, and Jira Extra Instructions.
- Hidden advanced Jira full-prompt override exists for power users.

## Local Install / Runtime

On Linux, install or refresh from source with:

```bash
cd /home/aristofeles/ai/projects/saysense
./install.sh
```

Current launcher:

- `~/.local/share/applications/saysense.desktop`
- Exec: `/home/aristofeles/ai/projects/saysense/.venv/bin/python /home/aristofeles/ai/projects/saysense/saysense.py`

Do not launch the GUI during automated verification unless the user explicitly
asks; use `py_compile`, static imports, and package/release checks first.

## Last UI Notes

- The Jira action row should contain only Generate, Clear, regeneration style,
  and Regenerate.
- Customer/Internal copy buttons live inside their own tabs to avoid horizontal
  overflow on the 560 px window.
- History stores the last 10 generated tickets locally and offers latest-output
  reopen/copy actions.

## Pending Branding Debt

- Icon assets still use the old banana-themed filenames and artwork.
- Config/log/env names still use `bananafone` for compatibility.
- Existing screenshots may need a visual refresh after the SaySense rename.

## Recommended Next Work

- Replace old banana-themed icon/screenshot assets with SaySense visuals.
- Add Jira documentation profiles instead of making users edit prompts first.
- Add Settings tabs or a scrollable Settings layout.
- Add call-note timestamps in Jira Mode.
- Add dedicated Jira action hotkeys.
- Add in-app update check and improve Windows signing/trust.

## Windows Installer Trust Note - 2026-06-14

The `v1.2-beta` Windows installer asset downloaded correctly and was a valid PE
file, but a Windows test machine reported:

```text
Windows cannot access the specified device, path, or file. You may not have the permissions.
```

This is not the normal SmartScreen `Run anyway` path. When the message appears
immediately, including when running as administrator, the likely causes are:

- Windows Defender or another AV blocked/quarantined the unsigned package.
- The downloaded file kept a blocked Mark-of-the-Web zone flag.
- Enterprise policy/AppLocker blocked execution from the download path.

Immediate user-side checks:

```powershell
Get-FileHash .\SaySense-Setup-1.2-beta.exe -Algorithm SHA256
Unblock-File .\SaySense-Setup-1.2-beta.exe
```

Expected SHA256 for `v1.2-beta` installer:

```text
a45bd54e4d038c363579bdd5a6bb597402b31822a1781007a727505a885cdc6d
```

For `v1.2-beta.1` and later, the release workflow also uploads a portable zip
and SHA256 files. If the installer is blocked, download the portable zip,
unblock the zip before extracting, and run `SaySense.exe` from the extracted
folder.

Follow-up: the portable zip extracted correctly as `SaySense.exe` plus the
`_internal` dependency folder, but `SaySense.exe` still did not launch after the
SmartScreen bypass on the user's Windows machine. That can still be endpoint
policy, but it can also be a hidden runtime crash because the normal PyInstaller
build uses `--windowed`.

For `v1.4-beta` and later, the Windows release workflow also uploads:

- `SaySense-Debug-Console-<version>.zip`: a console PyInstaller build. Run
  `SaySense-Debug.exe` from PowerShell to see traceback/runtime errors.
- `SaySense-Source-<version>.zip`: source + Windows installer scripts. Extract,
  run `Install-SaySense.bat`, then launch via the generated shortcut,
  `Run-SaySense.bat`, or `.venv\Scripts\pythonw.exe saysense.py`.

Portable PyInstaller structure reminder:

```text
SaySense.exe
_internal\
```

`_internal` is not executable by itself; `SaySense.exe` must live beside it.

## Local Linux Quick Dictation Hotkey - 2026-06-14

Goal: make SaySense usable without permanently occupying screen space on the
Linux desktop.

Current desktop environment observed:

- Desktop: Zorin/GNOME
- Session type: Wayland
- `xdotool` is installed and can see the Tk/XWayland SaySense window.
- GNOME custom shortcut slot used: `custom3`

Shortcut installed by `install.sh` when `gsettings` is available:

```text
Name: Toggle SaySense
Command: /home/aristofeles/.local/bin/saysense-toggle
Binding: <Shift><Control>d
```

Before this change, `custom3` was:

```text
Name: dictate
Command: /home/aristofeles/ditado_gui.py
Binding: <Shift><Control>d
```

Local wrapper installed by `install.sh`:

```text
/home/aristofeles/.local/bin/saysense-toggle
```

Wrapper behavior:

- Defines the source checkout as `/home/aristofeles/ai/projects/saysense`.
- Defines the app entrypoint as `saysense.py` inside that checkout.
- Writes a command request atomically to:

```text
/home/aristofeles/.config/bananafone/command.json
```

- Command payload format:

```json
{"id":"<uuid-or-timestamp>","action":"toggle_quick_dictation","created_at":1781469296}
```

- If a SaySense window exists, it tries to activate/raise it with `xdotool`.
- If no window exists, it launches:

```bash
/home/aristofeles/ai/projects/saysense/.venv/bin/python /home/aristofeles/ai/projects/saysense/saysense.py
```

App-side implementation:

- `COMMAND_FILE = os.path.join(CONFIG_DIR, "command.json")`.
- `poll_command_file()` runs every 150 ms via `root.after`.
- Commands older than 15 seconds are ignored to prevent stale auto-recording on
  a later app launch.
- On `{"action": "start_hotkey_recording"}` or
  `{"action": "toggle_quick_dictation"}`:
  - `deiconify()`, `lift()`, `focus_force()`
  - if already recording, call `stop_recording()`
  - if model is still loading, mark pending start
  - otherwise call `start_recording(from_hotkey=True)`
- `start_recording(from_hotkey=True)` marks the recording so the app minimizes
  itself after no-audio, transcription success, or transcription error.

Final UX:

1. Press `Ctrl+Shift+D`.
2. SaySense opens/raises and immediately starts recording.
3. User speaks normally.
4. Silence timeout stops recording, or pressing `Ctrl+Shift+D` again forces
   stop/transcribe.
5. App transcribes, copies to clipboard, then minimizes.
6. On Windows, the same `Ctrl+Shift+D` toggle is registered globally with
   `pynput` while the app is running. If endpoint policy blocks global hooks,
   the focused-window shortcut still works.

Why this route was chosen:

- Pure global hold-to-talk with `Ctrl+Shift` under GNOME/Wayland is unreliable
  without a dedicated background daemon or compositor-specific integration.
- A GNOME shortcut invoking a small wrapper is much simpler and matches the
  current local install.
- Polling a local command file avoids needing DBus or socket plumbing for this
  private desktop workflow.
