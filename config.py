import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# ── Hardcoded credentials ─────────────────────────────────────────────────────
HARDCODED_APP_KEY = "517966"
HARDCODED_APP_SECRET = "2LkeLmkEp5J0EhXUHvH0JPb54fsBdG2l"

DEFAULT_CONFIG = {
    "app_key": HARDCODED_APP_KEY,
    "app_secret": HARDCODED_APP_SECRET,
    "tracking_id": "",
    "access_token": "",
    "refresh_token": "",
    "token_expires": "",
}


def _load_from_secrets() -> dict:
    """Read token info from Streamlit secrets (for cloud deploy)."""
    try:
        import streamlit as st

        return {
            "access_token": st.secrets.get("access_token", ""),
            "refresh_token": st.secrets.get("refresh_token", ""),
            "token_expires": str(st.secrets.get("token_expires", "")),
            "tracking_id": st.secrets.get("tracking_id", ""),
        }
    except Exception:
        return {}


def load_config() -> dict:
    merged = DEFAULT_CONFIG.copy()

    # 1. Load from config.json if exists (local dev)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        merged.update(data)

    # 2. Streamlit secrets override (cloud) — only overwrite if non-empty
    secrets = _load_from_secrets()
    for k, v in secrets.items():
        if v:
            merged[k] = v

    # 3. Always enforce hardcoded credentials
    merged["app_key"] = HARDCODED_APP_KEY
    merged["app_secret"] = HARDCODED_APP_SECRET
    return merged


def save_config(config: dict):
    safe = {k: v for k, v in config.items() if k not in ("app_key", "app_secret")}
    with open(CONFIG_FILE, "w") as f:
        json.dump(safe, f, indent=2)
