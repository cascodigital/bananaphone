# Future Releases

Status as of v2.0.1.

## Done

### Generic Jira presets (v2.0.1) ✅
- Renamed the default built-in Jira profile from a client-specific name to the
  generic "Company (Jira)" (id `default`). No client names in the source. A
  saved `active_jira_profile` pointing at the old id resolves gracefully to the
  default built-in (see `get_jira_profile`), so existing configs don't break.

### Offline-models UX + self-update (v2.0) ✅
- Real progress bar during the "Download offline models" flow: the Whisper
  medium (~1.5GB) download now polls the HF cache and shows MB/%, instead of
  freezing on a dead label. The Ollama pull also drives the same bar.
- Robust Ollama bring-up: `find_ollama_binary()` locates the binary at the
  default Windows/macOS install paths even when it isn't on PATH yet (fresh
  install), and the start/install workers retry the serve+poll loop patiently
  instead of giving up after one pass. Fixes the "stuck on Starting Ollama ->
  404 model not found" race where the pull was silently skipped.
- In-app self-update check against GitHub releases. Lists `/releases` (all the
  beta tags are prereleases, so `/releases/latest` is useless) and prompts to
  open the download page when a newer tag exists. Remembers the dismissed tag.

### Jira Profiles (v1.7) ✅
- Structured, switchable profiles driving the built-in Jira prompt: tone,
  length, internal-note section names and extra instructions — no prompt
  editing required.
- Built-in read-only presets: Company (Jira), Casco / MSP client, Internal
  Helpdesk, Strict (factual). Clone-to-edit for custom profiles.
- Quick profile switch in the Jira panel; full manager (new/clone/delete/
  test) in the Jira Profiles dialog.
- Full-custom prompt override kept as an advanced global escape hatch.
- Legacy `jira_extra_instructions` auto-migrated into an editable profile.

### Jira Mode behavior (v1.6) ✅
- Entering Jira Mode (Dictate -> Jira) clears leftover notes so a previous
  ticket's noise doesn't bleed into the next one.
- Output language follows the OUTPUT selector even in Jira Mode (e.g. PT
  output stays Portuguese), with a hard rule in the prompt.

### Main window layout (v1.8 - v1.8.4) ✅
- Two-column layout: left = controls, right = output panel at full window
  height (notes area no longer one cramped line).
- Dictate output uses a single-tab "Transcript" tabview, pixel-identical
  to the Jira tabs (no size/position jump when switching modes).
- Left column pinned to a fixed width (pack_propagate) so the variable
  talk-button text no longer shifts the right panel between modes.

### Call Notes ✅
- Notes already carry timestamps; history preserves time and order.

## Remaining

### Branding Polish
- Replace old banana-themed icon assets with SaySense-specific artwork.
- Refresh README screenshots for the new two-column UI.
- Migrate config/log paths from `~/.config/bananafone` and
  `~/.local/state/bananafone` to `saysense`, with automatic import of
  existing settings and history. (Settings file is already `settings_v2.json`
  but the parent dir is still `bananafone`.)

### Settings UX
- Split the main Settings dialog into tabs or a scrollable layout
  (General / AI Provider / Jira / Advanced). Currently a single flat window.

### Global Hotkeys (partial)
- Only one global hotkey exists today (Ctrl+Shift+D quick dictation).
- Add configurable global hotkeys for: push-to-talk, add Jira note,
  generate Jira output, copy Customer Comment, copy Internal Note.

### Installer and Updates
- In-app update check.
- Improve Windows installer trust/signing story.
- Show version and changelog from inside the app.

### Profile polish (nice-to-have)
- Per-profile language hint / default OUTPUT language.
- Reorder profiles in the dropdown.
- Export/import profiles for sharing across machines.
