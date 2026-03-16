#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# open_dashboard.command
# Double-click this file in Finder to launch the dashboard.
# macOS: right-click → Open the first time to bypass Gatekeeper.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Keep Terminal window open on error
trap 'echo ""; echo "Press any key to close…"; read -n1' ERR

bash run.sh

# Auto-open browser after a short delay
sleep 2 && open "http://localhost:8501" &
