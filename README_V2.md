# BananaPhone v2

Experimental parallel version. It does not replace `bananafone.py`.

Functional snapshot:

- [`docs/bananaphone-v2-current-state.md`](docs/bananaphone-v2-current-state.md)
- [`docs/bananaphone-v2.1-observations.md`](docs/bananaphone-v2.1-observations.md)

Run it with:

```bash
./.venv/bin/python bananaphone_v2.py
```

## Current v2 scope

- English UI under the visible app name `BananaPhone`
- Separate input language selector: `EN`, `PT`, `ES`
- Separate output language selector: `EN`, `PT`, `ES`
- `Jira Mode` as an Engine option
- Default input/output: `EN -> EN`
- Visible engines: `Normal`, `API`
- Settings window for:
  - silence timeout: `4s`, `7s`, `10s`, `Off`
  - OpenAI API key
  - local model download/update
- Separate settings file: `~/.config/bananafone/settings_v2.json`
- Separate log file: `~/.local/state/bananafone/bananaphone_v2.log`

## Not included yet

- v2 installer or launcher

## Behavior

If input and output are the same language, the app copies the transcription directly.

If input and output are different languages, the app uses the configured OpenAI text model to rewrite the dictated text into the selected output language.

`JIRA MODE` forces the `API` engine and uses OpenAI to generate two fields:

- `Customer Comment`
- `Internal Note`

In `JIRA MODE`, the main button adds each dictation to `Raw Notes`. Use `Generate JIRA` when the notes are ready.

The Jira panel has three tabs:

- `Raw Notes`
- `Customer`
- `Internal`

After `Generate JIRA`, the app copies only `Customer Comment` automatically. `Customer` and `Internal` also have copy buttons.

In `JIRA MODE`, the generated Jira text uses the selected output language. For example:

- `Input PT` + `Output EN` + `JIRA MODE`: speak Portuguese, generate Jira text in English
- `Input PT` + `Output PT` + `JIRA MODE`: speak Portuguese, generate Jira text in Portuguese

`Off` silence timeout means recording continues until the main button is clicked again.
