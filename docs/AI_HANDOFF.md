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

DONE (2026-06-07): the GUI was redesigned with `customtkinter`. The old default
Tkinter/`ttk` look is gone. See `docs/bananaphone-v2-ui.png`.

Implemented:

- `customtkinter` dark theme, rounded controls
- compact route card with `CTkOptionMenu` for Engine / Input / Output
- large accent talk button (amber idle, red recording)
- Jira panel as a `CTkTabview` (Raw Notes / Customer / Internal)
- `CTkToplevel` settings window
- new dependency: `customtkinter>=5.2.2` (in `requirements.txt`)

Palette lives in the color constants at the top of `bananaphone_v2.py`
(`COLOR_*`, `TALK_*`, `BTN_*`). Tweak there for visual changes.

If a further UI framework change is ever considered (e.g. a local web UI),
explain the tradeoffs first. Current direction is to stay on customtkinter.

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
- public release/donation flow
- privacy documentation

Done: install/launcher packaging for v2 (`install.sh`, `install_windows.ps1`,
`build_windows_exe.ps1`).

## Branding / Tagline (for public launch)

DECISION (2026-06-07):

- Repo / internal codename: BananaPhone (unchanged; banana stays as icon/easter egg)
- Public product name (candidate): SaySense
- Tagline: "You speak. It makes sense."

Why SaySense: the name IS the tagline (say + sense), zero exact-name repo
collisions on GitHub at decision time. Still TODO before launch: verify
saysense.com/.app domain and trademark (USPTO/INPI) — GitHub name being free
does not guarantee domain/trademark.

Core idea: the human speaks raw, the machine creates meaning. Voice in,
polished/structured text out (transcription, translation, Jira docs).

Seed (PT): "O primata fala, a máquina cria o sentido."

Runner-up names (also 0 GitHub exact-name collisions): SayWise, SayNoted, VoxWrite.

Candidate taglines:

- EN:
  - "You speak. It makes sense."
  - "From mumble to meaning."
  - "Speak raw. Send polished."
  - "Talk like a human, write like a pro."
  - "Your voice, structured."
  - "Dictate the chaos. Ship the clarity."
- PT:
  - "Você fala. Ela faz sentido."
  - "Do balbucio ao significado."
  - "Fale solto. Mande pronto."
  - "Fale como gente, escreva como profissional."

Decide tone before launch: playful (primate/banana identity) vs. clean utility.
Keep one short hero line + one functional subline (e.g. "Dictation that writes
your tickets for you").

## Competitive Positioning (market scan 2026-06-07)

Honest prior-art assessment. The two core ideas are NOT blue ocean:

1. Speech -> polished professional text: crowded, hot 2026 category.
   Direct competitors: Wispr Flow (well funded), Typeless, WriteVoice,
   Voice Cursor, Google "Eloquent" (free, offline). The "ramble, we strip
   the filler and make it read like you typed it" pitch is now standard.
   Low originality; high market validation.

2. Voice -> Jira ticket: already exists too. SpeakOneAI (has a /jira page,
   does rewrite + translation + transcription = nearly our combo), Voice to
   Ticket for Jira, Talk2Task, Deviniti AI Ticket Assistant.

What is actually differentiated here (the defensible niche):

- Dual output from one dictation: public `Customer Comment` + private,
  technical `Internal Note`, tuned for IT support. No exact match found.
- Input != Output language as a first-class control (speak PT -> EN ticket).
  Competitors treat language as a detail, not a routing control.
- Local-first + hybrid (faster-whisper local + API), self-hosted, no SaaS,
  no subscription. All the commercial players are cloud SaaS.

Strategy: do NOT try to beat Wispr Flow at the SaaS game (they have capital).
Angle = "local, private dictation-to-Jira for bilingual IT support that splits
what the customer reads from what stays internal." Sell privacy + the IT niche,
not generic voice-to-text.

References:
- https://wisprflow.ai/  https://www.typeless.com/  https://appsumo.com/products/writevoice/
- https://speakoneai.com/use-cases/en/jira  https://marketplace.atlassian.com/apps/3939463879/voice-to-ticket-for-jira
- https://magneticonemobile.com/products/talk-2-task-for-jira/  https://deviniti.com/products/atlassian-apps/ai-ticket-assistant/

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
