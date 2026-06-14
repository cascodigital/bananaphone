# SaySense AI Handoff

## Current Product Identity

- Public product name: **SaySense**
- Version line: **1.0 Beta**
- Tagline: **You speak. It makes sense.**
- Internal repository / historical codename: `bananaphone_v2`
- Legacy app kept for reference: `bananafone.py` / `README_V1.md`

The public-facing app name is SaySense. Do not rebrand releases, screenshots,
installers, desktop entries, or README copy back to BananaPhone unless the owner
explicitly asks for that rollback.

## Compatibility Decisions

Keep these internal paths and environment variables for backward compatibility:

- Linux settings: `~/.config/bananafone/settings_v2.json`
- Linux logs: `~/.local/state/bananafone/bananaphone_v2.log`
- Jira history: `~/.config/bananafone/jira_history.json`
- Environment variable prefix: `BANANAFONE_*`
- Main source file: `bananaphone_v2.py`

These names are technical debt, but changing them now would lose existing keys,
history, defaults, and support notes. Public branding is SaySense; internal
storage remains Bananafone/BananaPhone-compatible until a dedicated migration is
implemented.

## Release Rules

- `v1.0-beta` and other tags containing `beta` publish prereleases.
- GitHub Actions builds:
  - Windows: `SaySense-Setup-<version>.exe`
  - Linux: `SaySense-<version>-x86_64.AppImage`
- The repository must remain private: `cascodigital/bananaphone_v2`.

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
cd /home/aristofeles/ai/projects/bananaphone_v2
./install.sh
```

Current launcher:

- `~/.local/share/applications/saysense.desktop`
- Exec: `/home/aristofeles/ai/projects/bananaphone_v2/.venv/bin/python /home/aristofeles/ai/projects/bananaphone_v2/bananaphone_v2.py`

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
- Add global hotkeys for push-to-talk and Jira actions.
- Add in-app update check and improve Windows signing/trust.
