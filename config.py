import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# ── Hardcoded credentials (never shown in UI) ─────────────────────────────────
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


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
    else:
        merged = DEFAULT_CONFIG.copy()

    # Always enforce hardcoded credentials — never use whatever is in the file
    merged["app_key"] = HARDCODED_APP_KEY
    merged["app_secret"] = HARDCODED_APP_SECRET
    return merged


def save_config(config: dict):
    # Never persist app_key / app_secret — they live only in code
    safe = {k: v for k, v in config.items() if k not in ("app_key", "app_secret")}
    with open(CONFIG_FILE, "w") as f:
        json.dump(safe, f, indent=2)
