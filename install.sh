#!/usr/bin/env bash
# SaySense - Linux installer
#
# Installs EVERYTHING the app needs on a clean machine:
#   - system packages: python3 + venv, tkinter, PortAudio + build headers
#     (PyAudio compiles against PortAudio; tkinter is NOT pip-installable)
#   - a local .venv with all Python dependencies
#   - a .desktop launcher
#   - a GNOME quick-dictation shortcut (Ctrl+Shift+D) when gsettings exists
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
BIN_DIR="$HOME/.local/bin"
TOGGLE_SCRIPT="$BIN_DIR/saysense-toggle"

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
      build-essential xdotool
  elif command -v dnf >/dev/null 2>&1; then
    log "Installing system packages with dnf..."
    $SUDO dnf install -y \
      python3 python3-virtualenv python3-devel python3-tkinter \
      portaudio portaudio-devel \
      gcc gcc-c++ make xdotool
  elif command -v pacman >/dev/null 2>&1; then
    log "Installing system packages with pacman..."
    $SUDO pacman -Sy --needed --noconfirm \
      python tk portaudio base-devel xdotool
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
Exec=$VENV_DIR/bin/python $REPO_DIR/saysense.py
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;AudioVideo;Audio;
EOF
chmod +x "$DESKTOP_FILE"

# --- quick dictation hotkey ------------------------------------------------
mkdir -p "$BIN_DIR"
cat > "$TOGGLE_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$REPO_DIR"
PYTHON="$VENV_DIR/bin/python"
APP="\$APP_DIR/saysense.py"
CONFIG_DIR="\$HOME/.config/bananafone"
COMMAND_FILE="\$CONFIG_DIR/command.json"

send_record_command() {
  mkdir -p "\$CONFIG_DIR"
  local id tmp
  if command -v uuidgen >/dev/null 2>&1; then
    id="\$(uuidgen)"
  else
    id="\$(date +%s%N)"
  fi
  tmp="\$(mktemp "\$CONFIG_DIR/command.json.XXXXXX")"
  printf '{"id":"%s","action":"toggle_quick_dictation","created_at":%s}\n' "\$id" "\$(date +%s)" > "\$tmp"
  mv "\$tmp" "\$COMMAND_FILE"
}

launch_app() {
  nohup "\$PYTHON" "\$APP" >/dev/null 2>&1 &
}

pick_window() {
  local pid win name

  while read -r pid; do
    [[ -n "\$pid" ]] || continue
    while read -r win; do
      [[ -n "\$win" ]] || continue
      name="\$(xdotool getwindowname "\$win" 2>/dev/null || true)"
      if [[ "\$name" == SaySense* ]]; then
        printf '%s\n' "\$win"
        return 0
      fi
    done < <(xdotool search --pid "\$pid" 2>/dev/null || true)
  done < <(pgrep -f "\$APP" || true)

  while read -r win; do
    [[ -n "\$win" ]] || continue
    name="\$(xdotool getwindowname "\$win" 2>/dev/null || true)"
    if [[ "\$name" == SaySense* ]]; then
      printf '%s\n' "\$win"
      return 0
    fi
  done < <(xdotool search --name '^SaySense' 2>/dev/null || true)
}

send_record_command

if ! command -v xdotool >/dev/null 2>&1; then
  launch_app
  exit 0
fi

window="\$(pick_window || true)"
if [[ -z "\${window:-}" ]]; then
  launch_app
  exit 0
fi

xdotool windowactivate "\$window" 2>/dev/null || xdotool windowraise "\$window" 2>/dev/null || true
EOF
chmod +x "$TOGGLE_SCRIPT"

install_gnome_hotkey() {
  command -v gsettings >/dev/null 2>&1 || return 0

  local schema="org.gnome.settings-daemon.plugins.media-keys"
  local base="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
  local bindings path existing_paths next_index command_value

  bindings="$(gsettings get "$schema" custom-keybindings)"
  existing_paths="$(printf '%s\n' "$bindings" | grep -o "$base/custom[0-9]*/" || true)"
  path=""
  while read -r candidate; do
    [[ -n "$candidate" ]] || continue
    command_value="$(gsettings get "$schema.custom-keybinding:$candidate" command 2>/dev/null || true)"
    if [[ "$command_value" == "'$TOGGLE_SCRIPT'" ]]; then
      path="$candidate"
      break
    fi
  done <<< "$existing_paths"

  if [[ -z "$path" ]]; then
    path="$(printf '%s\n' "$existing_paths" | while read -r candidate; do
      [[ -n "$candidate" ]] || continue
      if [[ "$(gsettings get "$schema.custom-keybinding:$candidate" binding 2>/dev/null || true)" == "'<Shift><Control>d'" ]]; then
        printf '%s\n' "$candidate"
        break
      fi
    done)"
  fi

  if [[ -z "$path" ]]; then
    next_index=0
    while printf '%s\n' "$existing_paths" | grep -q "$base/custom$next_index/"; do
      next_index=$((next_index + 1))
    done
    path="$base/custom$next_index/"
    if [[ "$bindings" == "@as []" ]]; then
      gsettings set "$schema" custom-keybindings "['$path']"
    elif ! printf '%s\n' "$bindings" | grep -q "$path"; then
      gsettings set "$schema" custom-keybindings "$(python3 - "$bindings" "$path" <<'PY'
import ast, sys
items = ast.literal_eval(sys.argv[1])
path = sys.argv[2]
if path not in items:
    items.append(path)
print(repr(items))
PY
)"
    fi
  fi

  gsettings set "$schema.custom-keybinding:$path" name "Toggle SaySense"
  gsettings set "$schema.custom-keybinding:$path" command "$TOGGLE_SCRIPT"
  gsettings set "$schema.custom-keybinding:$path" binding "<Shift><Control>d"
}

install_gnome_hotkey || log "GNOME hotkey setup skipped/failed; run $TOGGLE_SCRIPT manually or bind it to Ctrl+Shift+D."

echo
ok "SaySense installed."
echo "  Launcher : $DESKTOP_FILE"
echo "  Run      : $VENV_DIR/bin/python $REPO_DIR/saysense.py"
echo "  Hotkey   : Ctrl+Shift+D -> $TOGGLE_SCRIPT"
if [[ "$WITH_OLLAMA" -ne 1 ]]; then
  echo "  Local LLM: not installed. Re-run with --with-ollama, or install from Settings."
fi
