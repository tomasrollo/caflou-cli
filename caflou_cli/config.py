import json
import os
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path.home() / ".config" / "caflou-cli" / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def resolve_account_id(value: str, config: Optional[dict] = None) -> str:
    """Resolve an account name or partial ID to a full account ID."""
    cfg = config or load_config()
    accounts = cfg.get("accounts", [])
    for a in accounts:
        if a["id"] == value:
            return value
    for a in accounts:
        if value.lower() in a["name"].lower():
            return a["id"]
    return value  # pass through as-is (may be a valid direct ID)
