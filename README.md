# SaySense — Dictation & Jira Notes

![Status](https://img.shields.io/badge/Status-1.5.1%20Beta-blue)
![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-STT%20%2B%20Text-412991?style=flat-square&logo=openai&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-STT%20%2B%20Text-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Offline%20Text-000000?style=flat-square&logo=ollama&logoColor=white)

Current SaySense repository: [cascodigital/saysense](https://github.com/cascodigital/saysense)

Project lineage: BananaPhone v1 ([cascodigital/bananafone](https://github.com/cascodigital/bananafone)) → BananaPhone v2 ([cascodigital/saysense](https://github.com/cascodigital/saysense)) → **SaySense**.

---

Desktop dictation app for IT support work across languages. Speak in Portuguese, Spanish or English and get clean, professional text in the language you choose, already on your clipboard. **Jira Mode** turns dictated case notes into ticket-ready documentation: a customer-facing reply and an internal note, generated in one click.

## Why

Working support tickets in a second language means constantly juggling a translator, a text editor, and the ticket system. SaySense collapses that loop: talk in your language, paste polished English (or PT/ES) wherever the cursor is. For Jira, it goes further: dictate raw notes during the call and generate both the public comment and the internal worklog when you're done.

## Screenshots

| Main window — Jira Mode | Settings |
|:---:|:---:|
| ![Main window](docs/screenshots/01-main-jira.png) | ![Settings](docs/screenshots/02-settings.png) |

## Features

| Feature | Description |
|---------|-------------|
| **Dictate mode** | Press to talk, auto-stops on silence (4s/7s/10s/off). Result lands in the result panel and on the clipboard |
| **Language routing** | Input PT/EN/ES → output PT/EN/ES. Translation handled by the configured text AI |
| **Jira Mode** | Each dictated note is polished into professional English at capture time. **Generate JIRA** produces a customer reply + internal note from all notes |
| **One AI provider selector** | OpenAI, Gemini, Ollama (local) or any custom OpenAI-compatible endpoint — drives speech, translation and Jira generation |
| **Offline path** | Ollama text + local faster-whisper transcription keep Jira Mode working when cloud APIs are firewalled |
| **Smart RAM use** | Local Ollama models stay loaded for 60s after a call, then free their memory |
| **Self-installing** | One script installs system packages, Python venv and dependencies on a clean machine (Linux or Windows) |

## How it works

```
 mic ──► Speech-to-text                      ──► text (input language)
         OpenAI /audio/transcriptions               │
         Gemini generateContent (WAV inline)        ▼
         faster-whisper (offline fallback)    Text AI (OpenAI / Gemini / Ollama)
                                                    │
                                       ┌────────────┴────────────┐
                                       ▼                         ▼
                                    DICTATE                  JIRA MODE
                                    translated text          polished EN notes
                                    → clipboard              → customer reply
                                                             → internal note
```

## Download

Latest release: **v1.5-beta.1** on the [SaySense Releases page](https://github.com/cascodigital/saysense/releases).

## Run from source

### Linux

```bash
git clone https://github.com/cascodigital/saysense.git
cd saysense
./install.sh                # app + all dependencies (apt/dnf/pacman auto-detected)
./install.sh --with-ollama  # also install Ollama for offline text/Jira
./.venv/bin/python saysense.py
```

### Windows

Double-click **`Install-SaySense.bat`**, or from PowerShell:

```powershell
.\install_windows.ps1               # installs Python via winget if missing
.\install_windows.ps1 -WithOllama   # also install Ollama
```

## Configuration

Everything lives in the in-app **Settings** panel:

- **API keys** — OpenAI and/or Gemini, stored only in `~/.config/bananafone/settings_v2.json` (env vars `OPENAI_API_KEY` / `GEMINI_API_KEY` also work)
- **AI provider** — one selector for speech, translation and Jira text: OpenAI, Gemini, Ollama or a custom OpenAI-compatible URL
- **Model & server URL** — per provider, with sane defaults
- **Silence timeout** — how long to wait before auto-stopping a capture

No key is required for the Ollama path; the app can install Ollama and pull the model for you from Settings.

## Privacy

- Cloud providers receive your audio (STT) and text (translation/Jira) — pick the provider you trust.
- The Ollama + faster-whisper path keeps audio and ticket content entirely on your machine.
- API keys never leave the local settings file.

## Structure

```
saysense/
├── saysense.py        # The whole app (CustomTkinter GUI + pipelines)
├── install.sh               # Linux from-source installer
├── install_windows.ps1      # Windows from-source installer (winget-aware)
├── Install-SaySense.bat     # Windows one-click wrapper
├── Run-SaySense.bat         # Windows source checkout launcher
├── build_windows_exe.ps1    # Local standalone .exe builder (PyInstaller)
├── packaging/               # Inno Setup script + AppImage desktop entry
├── .github/workflows/       # CI release pipeline (installer + AppImage)
├── assets/                  # App icon
├── desktop/                 # .desktop launchers
├── docs/screenshots/
├── bananafone.py            # Legacy v1 (kept for reference)
└── README_V1.md             # Legacy v1 docs
```

## License

MIT — see [LICENSE](LICENSE).
