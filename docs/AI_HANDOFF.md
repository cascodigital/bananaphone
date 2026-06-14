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

## Pending Branding Debt

- Icon assets still use the old banana-themed filenames and artwork.
- Config/log/env names still use `bananafone` for compatibility.
- Existing screenshots may need a visual refresh after the SaySense rename.
