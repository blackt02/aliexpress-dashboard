import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "app_key": "",
    "app_secret": "",
    "tracking_id": "",
    "access_token": "",
    "refresh_token": "",
    "token_expires": "",
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        # merge with defaults in case new keys added
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
