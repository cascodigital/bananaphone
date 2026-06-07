# BananaPhone v2 AI Handoff

Status: active experimental project
Snapshot date: 2026-06-07

IMPORTANT: this repository directory is now the primary BananaPhone v2 checkout.

Main v2 code:

```text
/home/aristofeles/ai/projects/bananaphone_v2/bananaphone_v2.py
```

## Purpose

BananaPhone v2 is the experimental successor to Bananafone v1.

The goal is a polished dictation app with explicit input/output languages and an integrated Jira documentation workflow.

## Canonical Code Location

Local workspace:

```bash
cd /home/aristofeles/ai/projects/bananaphone_v2
```

Main v2 file:

```text
/home/aristofeles/ai/projects/bananaphone_v2/bananaphone_v2.py
```

Do not modify v1 unless explicitly requested:

```text
/home/aristofeles/ai/projects/bananaphone_v2/bananafone.py
```

## Git State

Private v2 remote:

```text
origin -> https://github.com/cascodigital/bananaphone_v2.git
```

Current v2 working branch:

```text
bananaphone-v2-next-ui
```

Known-good functional checkpoint:

```text
tag: bananaphone-v2-functional-prototype
commit: d5520f5
```

If UI work goes wrong, return to the tag.

## Required Reading Before Editing

Read these files first:

```text
/home/aristofeles/ai/projects/bananaphone_v2/README_V2.md
/home/aristofeles/ai/projects/bananaphone_v2/docs/bananaphone-v2-current-state.md
/home/aristofeles/ai/projects/bananaphone_v2/docs/bananaphone-v2.1-observations.md
```

## Current Functional Contract

Preserve all of this:

- Engine has `Normal`, `API`, and `Jira Mode`.
- Input language supports English, Portuguese, Spanish.
- Output language supports English, Portuguese, Spanish.
- `Jira Mode` forces API.
- `Jira Mode` changes the main action to `ADD NOTE`.
- Each Jira-mode dictation appends to `Raw Notes`.
- `Generate JIRA` uses all accumulated raw notes.
- Jira generation returns `Customer Comment` and `Internal Note`.
- `Customer Comment` is copied automatically after generation.
- `Copy Customer` and `Copy Internal` must continue working.
- Settings contains API key, silence timeout, and local model download/update.

## Current UI Direction

The functionality is strong. The GUI is not yet polished enough for public release.

Next UI work should make it feel like a modern utility app:

- less default Tkinter/Linux 2010 visual style
- fewer loose buttons
- clearer visual hierarchy
- cleaner route controls
- better Jira panel layout
- less dead dark space

Possible options:

- continue Tkinter but build custom controls instead of default `ttk.Combobox`
- use `customtkinter`
- build a lightweight local web UI while keeping the Python backend

Do not choose a new UI framework without explaining tradeoffs first.

## Deferred Decisions

Provider/model settings are intentionally deferred.

Do not hard-code the long-term design around OpenAI only. Future settings should separate:

- speech provider
- speech model
- text provider
- text model
- provider-specific API keys

Other deferred items:

- persist last normal result
- persist pending Jira raw notes
- restore/discard pending Jira notes on startup
- install/launcher packaging for v2
- public release/donation flow
- privacy documentation

## Validation

After code changes, run:

```bash
python3 -m py_compile bananaphone_v2.py
```

If `.venv` exists, this is also valid:

```bash
./.venv/bin/python -m py_compile bananaphone_v2.py
```

For UI-only changes, still preserve the functional contract above.

## Prompt For A New AI

Use this with another AI:

```text
We are working on BananaPhone v2.

Local workspace:
/home/aristofeles/ai/projects/bananaphone_v2

Private remote:
https://github.com/cascodigital/bananaphone_v2

Branch:
bananaphone-v2-next-ui

Known-good checkpoint:
tag bananaphone-v2-functional-prototype
commit d5520f5

Do not modify bananafone.py v1.

Read first:
- /home/aristofeles/ai/projects/bananaphone_v2/docs/AI_HANDOFF.md
- /home/aristofeles/ai/projects/bananaphone_v2/README.md
- README_V2.md
- docs/bananaphone-v2-current-state.md
- docs/bananaphone-v2.1-observations.md

Goal:
Redesign the GUI so it feels modern and elegant while preserving 100% of the current BananaPhone v2 functionality.

Before editing files, explain the visual and technical plan.

Validation:
python3 -m py_compile bananaphone_v2.py
```
