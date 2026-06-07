# BananaPhone v2

Private experimental dictation app with explicit input/output language routing and Jira documentation mode.

This repository is the canonical BananaPhone v2 workspace.

![BananaPhone v2 UI](docs/bananaphone-v2-ui.png)

The GUI uses [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (dark theme, rounded controls, tabbed Jira panel).

## Start Here

For AI handoff and project rules, read:

```text
docs/AI_HANDOFF.md
```

Then read:

```text
README_V2.md
docs/bananaphone-v2-current-state.md
docs/bananaphone-v2.1-observations.md
```

## Main File

```text
bananaphone_v2.py
```

Do not modify `bananafone.py` unless explicitly requested. It is kept only as inherited v1 reference code in this private repo.

The original v1 README was moved to:

```text
README_V1.md
```

## Install

Linux:

```bash
./install.sh
```

Windows (easiest): double-click **`Install-BananaPhone.bat`**.

Windows (PowerShell):

```powershell
.\install_windows.ps1
```

Windows standalone `.exe` (run on a machine without Python) — see [README_WINDOWS.md](README_WINDOWS.md):

```powershell
.\build_windows_exe.ps1
```

## Run

After creating/installing the local venv:

```bash
./.venv/bin/python bananaphone_v2.py
```

## Validate

If `.venv` exists:

```bash
./.venv/bin/python -m py_compile bananaphone_v2.py
```

If `.venv` has not been created yet:

```bash
python3 -m py_compile bananaphone_v2.py
```

## Git

Private remote:

```text
https://github.com/cascodigital/bananaphone_v2
```

Working branch:

```text
bananaphone-v2-next-ui
```

Known-good checkpoint:

```text
tag: bananaphone-v2-functional-prototype
commit: d5520f5
```
