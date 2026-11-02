#!/usr/bin/env bash
# Run the Sentinel Chatbot FastAPI Backend & Web App
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"
python -u "$DIR/backend/main.py" "$@"
