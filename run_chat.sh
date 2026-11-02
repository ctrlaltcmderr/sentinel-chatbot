#!/usr/bin/env bash
# Run the interactive Sentinel Chatbot CLI
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"
python -u "$DIR/live_chat.py" "$@"

