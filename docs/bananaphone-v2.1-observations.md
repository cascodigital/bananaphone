# BananaPhone 2.1 Observations

Snapshot date: 2026-06-07

## Visual Direction

The `2.1-dev` pass moves the app away from a large button grid.

Main screen direction:

- route configuration should be compact
- Engine, Input, and Output belong together
- Jira mode is a mode toggle, not an output language
- Jira-specific actions belong inside the Jira panel
- maintenance actions stay at the bottom

## Current 2.1 Layout Intent

- Header:
  - app name
  - status
- Route panel:
  - Engine dropdown
  - Input dropdown
  - Output dropdown
  - `Jira Mode` as an Engine option
- Main action:
  - normal mode: `PRESS TO TALK`
  - Jira mode: `ADD NOTE`
- Result area:
  - normal mode: one output text area
  - Jira mode: tabbed panel with Raw Notes, Customer, Internal
- Bottom:
  - model cache status
  - Set Default
  - Settings

`Download Models` belongs in Settings, not on the main screen.

## Deferred Decisions

### Provider and model settings

Do not hard-code the long-term design around OpenAI only.

Later settings should separate:

- speech provider
- speech model
- text provider
- text model
- provider-specific API keys

Possible providers can be discussed later. Current code still uses OpenAI endpoints.

### Persistence

Later decision:

- persist last normal result
- persist Raw Notes
- restore/discard pending Jira notes on startup

Current 2.1 should keep Jira notes in memory only.

### Visual polish

The app is functional but still visibly Tkinter/Linux-native.

Later visual options:

- replace default `ttk.Combobox` styling with custom Tk widgets
- use a clearer route summary chip
- reduce dark empty space
- make the Jira tab panel visually closer to a modern utility app
- consider a lightweight web UI or customtkinter if Tkinter styling becomes the ceiling

### Distribution and donation

Optional donation is not unreasonable if the app is polished and packaged well.

Before any public release:

- document privacy clearly: where audio goes, when API is used, what is stored locally
- support provider configuration instead of OpenAI-only assumptions
- add install/update path
- add a real icon and launcher
- test on at least Linux and Windows
- avoid storing API keys in plain text long-term if distributing broadly

### Launcher and install

Keep v2 as a parallel experimental script until the UI and flow stabilize.

### Real-world tests

Still needed:

- quiet microphone test
- API transcription test
- Jira generation test
- PT input to EN Jira output
- PT input to PT Jira output
- no-API-key warning path
