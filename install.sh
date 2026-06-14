#!/usr/bin/env bash
# SaySense - Linux installer
#
# Installs EVERYTHING the app needs on a clean machine:
#   - system packages: python3 + venv, tkinter, PortAudio + build headers
#     (PyAudio compiles against PortAudio; tkinter is NOT pip-installable)
#   - a local .venv with all Python dependencies
#   - a .desktop launcher
#   - (optional) Ollama, for the local text LLM, via --with-ollama
#
# Usage:
#   ./install.sh                # app + dependencies
#   ./install.sh --with-ollama  # also install Ollama for offline text/Jira
#
# Works on Debian/Ubuntu/Zorin/Mint (apt), Fedora/RHEL (dnf), Arch (pacman).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/saysense.desktop"

WITH_OLLAMA=0
for arg in "$@"; do
  case "$arg" in
    --with-ollama) WITH_OLLAMA=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# --- sudo helper (no-op if already root) -----------------------------------
SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    fail "Not root and 'sudo' is missing. Re-run as root or install sudo."
  fi
fi

# --- system dependencies ---------------------------------------------------
install_system_deps() {
  if command -v apt-get >/dev/null 2>&1; then
    log "Installing system packages with apt..."
    $SUDO apt-get update -qq
    $SUDO apt-get install -y \
      python3 python3-venv python3-dev python3-tk \
      portaudio19-dev libportaudio2 \
      build-essential
  elif command -v dnf >/dev/null 2>&1; then
    log "Installing system packages with dnf..."
    $SUDO dnf install -y \
      python3 python3-virtualenv python3-devel python3-tkinter \
      portaudio portaudio-devel \
      gcc gcc-c++ make
  elif command -v pacman >/dev/null 2>&1; then
    log "Installing system packages with pacman..."
    $SUDO pacman -Sy --needed --noconfirm \
      python tk portaudio base-devel
  else
    fail "No supported package manager (apt/dnf/pacman) found. Install python3, python3-tk, and portaudio dev headers manually, then re-run."
  fi
  ok "System dependencies ready."
}

# --- optional Ollama for the local text LLM --------------------------------
install_ollama() {
  if command -v ollama >/dev/null 2>&1; then
    ok "Ollama already installed."
  else
    log "Installing Ollama (local LLM runtime)..."
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama installed."
  fi
  log "Pulling default local model qwen2.5:3b (~1.9 GB)..."
  ollama pull qwen2.5:3b || log "Pull skipped/failed — you can do it later from the app's Settings."
}

install_system_deps

# --- Python venv + deps ----------------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

log "Installing Python dependencies (faster-whisper is large, be patient)..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$REPO_DIR/requirements.txt"
ok "Python dependencies installed."

# --- sanity check ----------------------------------------------------------
log "Verifying imports..."
"$VENV_DIR/bin/python" - <<'PY'
import tkinter, customtkinter, numpy, speech_recognition, pyaudio
from faster_whisper import WhisperModel
print("All imports OK")
PY
ok "Imports verified."

# --- optional Ollama -------------------------------------------------------
if [[ "$WITH_OLLAMA" -eq 1 ]]; then
  install_ollama
fi

# --- desktop launcher ------------------------------------------------------
mkdir -p "$DESKTOP_DIR"
rm -f "$DESKTOP_DIR/bananaphone-v2.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=2.1
Name=SaySense
Comment=Dictation and Jira documentation (local + API)
Exec=$VENV_DIR/bin/python $REPO_DIR/bananaphone_v2.py
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;AudioVideo;Audio;
EOF
chmod +x "$DESKTOP_FILE"

echo
ok "SaySense installed."
echo "  Launcher : $DESKTOP_FILE"
echo "  Run      : $VENV_DIR/bin/python $REPO_DIR/bananaphone_v2.py"
if [[ "$WITH_OLLAMA" -ne 1 ]]; then
  echo "  Local LLM: not installed. Re-run with --with-ollama, or install from Settings."
fi
