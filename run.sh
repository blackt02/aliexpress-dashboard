#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# AliExpress Affiliate Dashboard — launcher
# Usage:  ./run.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Python check ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌  python3 not found. Install Python 3.10+ first."
    exit 1
fi

PYTHON=$(command -v python3)
PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅  Python $PY_VER — $PYTHON"

# ── Virtual-env ───────────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "📦  Creating virtual environment…"
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

# ── Dependencies ──────────────────────────────────────────────────────────────
echo "📦  Installing / verifying dependencies…"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
echo "🚀  Starting AliExpress Affiliate Dashboard…"
echo "   Open http://localhost:8501 in your browser"
echo "   Press Ctrl+C to stop"
echo ""

streamlit run app.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false
