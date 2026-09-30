# Future Releases

Status as of v3.0.0.

## Open

### Text selection freezes desktop-wide while BananaPhone runs (unresolved, 2026-09-29)
- Symptom: mouse text selection stops working in other apps (native Wayland clients such as
  tilix) and only recovers when BananaPhone is closed. Intermittent, so any claim of a fix
  needs the real event observed, not a manual trigger.
- The v2.5.1 pynput entry below is neither the cause nor the cure. The log confirms the
  listener is disabled on **every** launch (most recent: 2026-09-29 08:48:38) and the freeze
  still happens. That fix addressed a real hazard and left the bug untouched.
- Measured and ruled out:
  - **Global X grab.** On Linux every CustomTkinter dropdown opens through `tk_popup`, which
    does `grab -global` — pointer *and* keyboard on the whole X server. Confirmed with an
    Xlib probe: `AlreadyGrabbed` while a dropdown is open, released on unpost. Two A/B runs
    holding the grab (120 s and a labelled 15 s phase against a 15 s no-grab control):
    selection in tilix kept working in all of them. The grab stays inside XWayland because
    `org.gnome.mutter.wayland xwayland-allow-grabs` is `false`, so it never reaches Wayland
    clients.
  - **X to Wayland selection bridge.** With a Tk client owning PRIMARY and its mainloop
    blocked, `wl-paste --primary` hangs and mutter applies no timeout of its own (measured
    25 s, it returned only when the owner unblocked). Real defect class, but it breaks
    pasting, not the act of selecting, and the user confirmed selection dies first.
  - **Stuck modifier, stuck mouse button, stuck keys.** Clean in every sample taken so far
    (only NumLock set).
- Open lead: the single clean reproduction (20:24:29-20:24:40) happened while a freshly
  mapped XWayland window took focus during an in-progress selection. The same grab held
  later, without a window appearing, broke nothing. Focus stealing on map is the suspect:
  `attributes("-topmost")` at startup and `deiconify`/`lift`/`focus_force` in
  `start_hotkey_recording_command`.
- Instrument left running: `tools/input-watch.py` samples the session every 2 s and logs
  only anomalies to `~/.local/state/bananafone/input-watch.log` (grabs, modifier and button
  mask, stuck keys, leaked override-redirect windows, PRIMARY owner, `wl-paste` latency).
  `--once` prints a snapshot and also tests for grabs. Baseline is self-calibrated at start,
  so mutter's own guard window does not show up as a finding. Next occurrence is meant to be
  decided from that log.

## Done

### Coach: Simple mode, rolling window, and two panel bugs (v3.0.0, fourth pass) ✅
- **Coach detail: Simple (default) | Advanced.** Simple returns exactly one
  correction rendered in two lines. A wall of corrections gets skimmed and then
  ignored, which is worse than one that lands -- so Simple is the default, not a
  hidden option. It is also 56% cheaper than Advanced (65 vs 207 output tokens),
  taking the whole feature's overhead from +118% to +72% over transcription alone.
- Nothing shown is lost: every tip is appended to `history` in the coach profile
  (last 200, timestamped), regardless of how many the panel displays.
- Short notes are trimmed on a word boundary. A note cut mid-word ("...batimento
  cardiaco; 'wrist')") reads as a bug.
- **The panel counter is now a rolling window of the last 30 corrections**, not a
  lifetime total. A total that can only grow can never show him improving:
  measured, a category he stopped making drops out of the window entirely while
  the lifetime count stays in the file as the permanent record.
- **Bug: a stale "coach off" message survived activation.** Switching INPUT from
  Portuguese to English swapped the title but left the old body text, so the panel
  kept insisting INPUT was Brazilian Portuguese. The body now tracks whether it
  holds a reason or live tips, so a stale reason is cleared while tips he is
  reading are never wiped by a repaint.

### Restyle the last dictation without speaking again (v3.0.0, third pass) ✅
- Flipping Raw <-> Professional now re-renders what he already said, panel and
  clipboard. Each style is generated once per dictation and cached: the first
  flip costs one call, every flip after that is instant (measured 0.9s vs 0.2s).
- The cache is dropped when the route changes, so a dictation is never restyled
  with the wrong pair of languages.
- A flip landing while another is in flight resolves to the newer selection.
- **Jira Mode is deliberately untouched.** `active_output_style()` pins it to the
  pre-3.0 behaviour; the selector is Dictate-only and no restyle fires there.

### Output style + coach on every spoken route (v3.0.0, second pass) ✅
- **Output style: Raw | Professional**, a segmented button under the INPUT/OUTPUT
  selectors. It is the third leg of the same decision (what goes in, what comes
  out, how hard the model may rewrite it), so it lives with the other two rather
  than in Settings. `Raw` is not "no processing": artifacts and outright errors
  are still fixed, but his sentence structure, word order and bluntness survive.
  The style applies to translated routes too, not just same-language ones.
- **Coach is now keyed on the INPUT language, not on source == target.** The old
  gate silently excluded EN -> PT, where the English is still his own and still
  worth correcting. PT -> EN and PT -> PT stay off: there the English is the
  model's and his Portuguese is native. Coach no longer depends on the polish
  setting either.
- On a translated route there is no same-language polished text to diff against,
  so `coach_review` now runs from the raw dictation alone. Same tips, same
  categories, one less input.
- **Bug caught in testing, not in production:** given a short dictation, the
  Professional prompt turned "stopped in my pulse" into "stopped monitoring my
  pulse" -- a fact he never said -- and Raw deleted the clause instead. Both
  prompts now carry an explicit Portuguese false-friend table (pulse=wrist,
  actually=currently, pretend=intend, ...) plus a hard "never drop a clause you
  cannot resolve" rule. The false friend has to be read with the meaning he
  intended even when the English reading would make sense on its own.
- Changing style is refused mid-recording and the widget snaps back, so it can
  never display a state the app is not in.

### Same-language polish + Language coach (v3.0.0) ✅
- **The bug that defined the release.** `transform_output_text` opened with an
  unconditional `if source_language == target_language: return text`. Dictating
  EN -> EN therefore skipped the writing layer entirely and pasted the raw
  transcript, stumbles included. Only the translated routes (PT -> EN) ever got
  professional prose. Now gated behind `polish_same_language` (default on).
- `polish_same_language_text` is a separate prompt from `transform_output_text`:
  there is no translation step to hide behind, so it states plainly that the
  speaker is a fluent non-native, and it is told to keep his voice and his
  directness instead of inflating the text into corporate filler.
- **Language coach.** After a polished same-language dictation, a second pass
  diffs RAW against POLISHED and returns at most 4 corrections. The polished
  text alone teaches nothing; the delta is the entire lesson.
  - Closed category set (`misheard`, `false_friend`, `tense`, `phrasal_verb`,
    `preposition`, `word_order`, `word_choice`, `register`). Free-form tips
    cannot be counted, and a tip you cannot count cannot tell you what you keep
    getting wrong. The prompt is explicit that the most specific category wins,
    otherwise everything collapses into `word_choice` (measured).
  - `misheard` is the honest stand-in for pronunciation. No text pipeline hears
    you, but when the recognizer turns your word into a different real word,
    that is the machine failing to understand you.
  - Notes are written in Portuguese, his first language, so the rule lands.
  - Running tally in `~/.config/bananafone/coach_profile.json` drives a
    "Your #1 so far: X (12x)" header. One tip is noise; the same tip for the
    12th time is a curriculum.
- **Hard rules, each covered by a test:**
  - The coach never touches the clipboard. Work output stays paste-ready.
  - The coach runs on its own thread, started only after the clipboard is
    already loaded, and a coach failure never costs him the dictation.
  - Coach is off for translated routes (PT -> EN English is the model's, not
    his), off in Jira Mode, and off when the target is his native language.
  - A malformed model reply degrades to "no tips", never to a crash.
- The route status line now admits `Polish`/`Polish + Coach`, because on a
  same-language route his text now leaves the machine where it used to stay.
- Layout: the coach strip packs BEFORE either tabview. The Tk packer hands the
  whole cavity to the first widget that asks to expand, so packing it after
  collapsed it to zero height.

### Fix Wayland input grab / stuck modifiers on Linux (v2.5.1) ✅
- On Linux running Wayland (Zorin OS / GNOME Wayland), `pynput` hooked into XWayland
  via XRecord to capture global hotkeys. Focus transitions between native Wayland
  windows and the X11 app caused dropped `key release` events, desyncing modifier
  keys (Ctrl/Shift) and pointer grab locks desktop-wide. This broke mouse text
  selection, double-click word selection, and `Ctrl+A` across all applications
  until BananaPhone was closed.
- BananaPhone now detects Wayland sessions (`WAYLAND_DISPLAY`, `XDG_SESSION_TYPE=wayland`,
  or runtime `wayland-0` socket) and disables the `pynput` keyboard listener.
- On Linux, system shortcuts are already natively handled by GNOME / Zorin shortcuts
  calling `bananaphone-toggle` (via `command.json`), so no global hotkey functionality
  is lost. `BANANAPHONE_FORCE_PYNPUT=1` remains available as an override.

### Paste & translate, and a shorter silence timeout (v2.5.0) ✅
- Text he already had (an e-mail, a chat message, a ticket) had to be dictated back
  into the app to get translated. The Dictate panel now has a **Translate** tab:
  paste, `Ctrl+Enter`, result in the Transcript panel and on the clipboard.
- `translate_written_text` is a separate prompt from `transform_output_text` on
  purpose - pasted text has no speech-to-text artifacts to repair, so the prompt
  only translates and holds the layout (line breaks, lists, signatures, IDs,
  error codes, commands). Source language is auto-detected; only OUTPUT matters.
- Silence timeout ladder was 4s / 6s / 8s / off, and 4s was already too long a wait
  after every capture. Now 3s / 4s / 5s / 8s, default 3s.

### Source install lands in the user profile, not Downloads (v2.4.2) ✅
- `install_windows.ps1` built the venv and pointed both shortcuts at whatever folder
  the source zip was unpacked into - typically `Downloads\BananaPhone-Source-<ver>`.
  Cleaning out Downloads silently killed the app, and the shortcut then pointed at a
  dead path.
- The installer now copies the app to `%LOCALAPPDATA%\BananaPhone` (overridable with
  `-InstallDir`) and installs the venv and shortcuts there. Re-running it from the
  install directory itself is detected and reuses it in place instead of self-copying.
- Copying uses robocopy with `/XD .venv .git __pycache__`; `Copy-Item -Recurse` onto an
  existing directory nests it (`docs\docs`) instead of merging.
- Desktop shortcut is always created, gets the real banana icon from
  `assets\bananaphone.ico`, and its parent directory is created first - a redirected
  Desktop (OneDrive/Known Folder Move) no longer silently skips it. The installer warns
  if the shortcut is missing after the attempt.
- Final summary prints the install path and tells you the source folder is disposable.


### Windows installer: Python 3.14 / PyAudio wheel failure (v2.4.1) ✅
- `install_windows.ps1` resolved the base interpreter with `py -3`, which returns the
  **newest** Python present. PyAudio 0.2.14 publishes prebuilt wheels only up to
  cp313, so on Python 3.14 pip fell through to a source build and died with
  "Microsoft Visual C++ 14.0 or greater is required" — unfixable on a locked-down
  work machine where a C++ toolchain is not an option.
- Worse, dependencies installed as a single `pip install -r requirements.txt`. PyAudio
  failing aborted the entire pip transaction, so customtkinter/numpy/faster-whisper
  were never installed either — and the script still printed "BananaPhone installed"
  and created shortcuts pointing at an empty venv.
- Fixes:
  - Interpreter discovery probes `py -3.13/-3.12/-3.11/-3.10` and validates via
    `sys.version_info`, instead of accepting whatever `py -3` hands back.
  - A pre-existing `.venv` built on an unsupported interpreter is detected and
    rebuilt rather than reused.
  - PyAudio installs first and alone with `--only-binary=:all:`, so pip never
    attempts a source build; failure raises an actionable error instead of taking
    every other dependency down with it.
  - The import sanity check now honors `$LASTEXITCODE`, so a broken install can no
    longer report success.

### Window always-on-top fix (v2.2.1) ✅
- The dictation window set `-topmost True` at init and never cleared it, so it stayed
  glued over every other window for its whole lifetime. Now it pops to front on launch
  and releases topmost after 400ms (`bananaphone.py` `DictationApp.__init__`), keeping the
  intended "appear when summoned" behavior without hogging the foreground.

### Local Jira quality + model tiers + one-shot (v2.1.0) ✅
- **Robust local Jira pipeline.** Small local models (qwen2.5:7b) used to break the
  Jira output four ways: sections jammed onto one line, dropped/`None` follow-ups,
  internal jargon leaking into the public Customer Comment, and genericized
  identifiers. All addressed without changing models:
  - A one-shot few-shot example (local providers only) anchors format and verbatim
    identifier preservation. No ticket number/name in the example so the model can't
    parrot it into unrelated tickets.
  - `normalize_jira_sections()` deterministically forces each section label onto its
    own line, independent of how well the model followed the prompt.
  - A forced (then discarded) `resolution_state` key makes the model commit to
    resolved/workaround/open before writing the Result, fixing the "issue persists"
    contradiction.
  - The public Customer Comment is re-derived in a separate, narrowly-scoped
    jargon-strip pass (`refine_customer_comment_local`) — a task a 7B does cleanly —
    instead of being produced in the same breath as the technical note.
  - HARD RULES rewritten as short numbered imperatives (small models follow lists
    better than dense prose). A one-shot repair pass re-asks if a backbone section is
    missing. Local generation timeout raised (a 7B on CPU can take minutes).
- **Local model tiers in Settings.** For Ollama, the free-text model field becomes a
  named picker: **7B — Balanced (recommended)** (`qwen2.5:7b`, ~4.7 GB, runs anywhere)
  or **14B — Best quality** (`qwen2.5:14b`, ~9 GB, needs a 12 GB+ GPU), plus a
  **Custom model…** escape hatch. A best-effort NVIDIA/AMD GPU probe drives an honest
  recommendation, shown only for the 14B tier. The Server URL field is hidden for a
  local preset tier (localhost implied). Tier owns the model tag; the rest of the
  pipeline is unchanged.
- **One-shot Jira.** Optional *Auto-generate after each dictation* setting: a single
  dictated note generates the ticket automatically, no Generate Jira click.

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
