"""Small shared state for the local Chirox cockpit.

This is not evidence and it is not the Dojo Record. It is just the current UI
mode and the latest voice/read-along activity so the browser can show what the
local processes are doing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from chirox.config import DATA_DIR

STATE_PATH = DATA_DIR / "chirox_activity.json"
MODES = {"training", "learning"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_activity(path: Path | None = None) -> dict:
    p = path or STATE_PATH
    if not p.exists():
        return {"mode": "training"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {"mode": "training"}
    if data.get("mode") not in MODES:
        data["mode"] = "training"
    return data


def update_activity(path: Path | None = None, **fields) -> dict:
    p = path or STATE_PATH
    data = read_activity(p)
    data.update(fields)
    data["updated_at"] = _now()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def set_mode(mode: str, path: Path | None = None) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    return update_activity(path, mode=mode)
