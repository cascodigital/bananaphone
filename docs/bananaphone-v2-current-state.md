# BananaPhone v2 Current State

Snapshot date: 2026-06-07

This document records the functional design before the visual cleanup pass toward `2.1-dev`.

## Purpose

`bananaphone_v2.py` is an experimental parallel version. It does not replace `bananafone.py`.

The v2 goal is to separate speech input language, final output language, and ticket-oriented Jira formatting.

## Runtime Files

- App file: `bananaphone_v2.py`
- Settings: `~/.config/bananafone/settings_v2.json`
- Log: `~/.local/state/bananafone/bananaphone_v2.log`

## Core Controls

- Engine:
  - `Normal`
  - `API`
- Input language:
  - `EN`
  - `PT`
  - `ES`
- Output language:
  - `EN`
  - `PT`
  - `ES`
- `JIRA MODE`:
  - forces `API`
  - changes the main button to add notes instead of generating final text immediately

## Normal Dictation Flow

When `JIRA MODE` is off:

1. The main button records audio.
2. The selected engine transcribes the audio.
3. If input and output languages match, the transcription is copied directly.
4. If input and output languages differ, the configured text model rewrites/translates into the selected output language.
5. The final text is copied to the clipboard.

## Jira Flow

When `JIRA MODE` is on:

1. `API` engine is forced.
2. The main button shows `ADD NOTE / JIRA MODE`.
3. Each dictation is transcribed and appended to `Raw Notes`.
4. `Generate JIRA` uses all accumulated raw notes.
5. The text model returns:
   - `Customer Comment`
   - `Internal Note`
6. `Customer Comment` is copied automatically.
7. `Customer` and `Internal` have manual copy buttons.
8. `Clear Notes` clears raw notes and generated Jira fields.

## Language Semantics

Input language means the language being spoken.

Output language means the language of the final text.

Examples:

- `Input PT` + `Output EN`: speak Portuguese, receive English.
- `Input PT` + `Output EN` + `JIRA MODE`: speak Portuguese, generate Jira text in English.
- `Input PT` + `Output PT` + `JIRA MODE`: speak Portuguese, generate Jira text in Portuguese.

## Deferred Items

- Provider/model settings beyond OpenAI.
- Persisting last result or pending ticket notes.
- Installer/launcher integration for v2.
- Visual polish and layout cleanup.
