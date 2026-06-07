#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/bananaphone-v2.desktop"

mkdir -p "$DESKTOP_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=2.1
Name=BananaPhone v2
Comment=Dictation and Jira documentation (local + API)
Exec=$VENV_DIR/bin/python $REPO_DIR/bananaphone_v2.py
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;AudioVideo;Audio;
EOF

chmod +x "$DESKTOP_FILE"

echo "BananaPhone v2 installed."
echo "Launcher: $DESKTOP_FILE"
echo "Exec: $VENV_DIR/bin/python $REPO_DIR/bananaphone_v2.py"
