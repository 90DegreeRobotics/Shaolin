"""Exercise guide data for the local cockpit.

The guide layer keeps the browser aligned with the real trainer catalog: every
visible drill card comes from the same deterministic catalog Chirox can call.
Reference images are displayed as training aids only; measurements still come
from the backend pose engine.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote


REFERENCE_DIR = Path(__file__).resolve().parents[1] / "reference"

STANCE_KEYS = {
    "horse", "bow", "crane", "one_leg_stand", "drop_stance", "t_stance",
    "parallel_ready", "meditation_stance", "empty_stance", "horse_guard",
    "wuji_standing",
}
FLOOR_KEYS = {"plank", "pushups", "situps", "hollow_hold", "glute_bridge", "leg_raise_hold"}
LEG_STRENGTH_KEYS = {"squats", "squat_hold", "wall_sit", "knee_raises", "jumping_jacks"}
QIGONG_KEYS = {"arms_raised", "seated_meditation"}

GUIDE_COPY = {
    "stance": {
        "title": "Stance Work Reference",
        "instruction": "Set the body into the shape, root the feet, and hold still enough for Chirox to measure clean angles.",
    },
    "floor": {
        "title": "Floor Strength Reference",
        "instruction": "Use the side camera. Keep the whole body in frame so shoulders, hips, knees, ankles, elbows, and wrists stay visible.",
    },
    "leg_strength": {
        "title": "Leg Strength Reference",
        "instruction": "Move slowly through the full range. Chirox counts only complete, visible cycles or clean holds.",
    },
    "qigong": {
        "title": "Qigong / Mobility Reference",
        "instruction": "Move deliberately and keep the joints visible. Chirox tracks the shape, not performance theater.",
    },
    "general": {
        "title": "Training Reference",
        "instruction": "Stand where both cameras can see you. If Chirox marks uncertainty, fix framing before trusting the verdict.",
    },
}


def _image_number(path: Path) -> int:
    match = re.search(r"\((\d+)\)\.png$", path.name)
    return int(match.group(1)) if match else 999


def reference_images() -> list[dict]:
    images = sorted(REFERENCE_DIR.glob("*.png"), key=_image_number) if REFERENCE_DIR.exists() else []
    return [
        {
            "index": i,
            "title": f"Reference {i + 1}",
            "file": p.name,
            "url": f"/reference/{quote(p.name)}",
        }
        for i, p in enumerate(images)
    ]


def guide_kind(key: str) -> str:
    if key in STANCE_KEYS:
        return "stance"
    if key in FLOOR_KEYS:
        return "floor"
    if key in LEG_STRENGTH_KEYS:
        return "leg_strength"
    if key in QIGONG_KEYS:
        return "qigong"
    return "general"


def _guide_image(kind: str, refs: list[dict]) -> dict | None:
    if not refs:
        return None
    order = {"stance": 0, "floor": 1, "leg_strength": 2, "qigong": 3, "general": 0}
    return refs[min(order.get(kind, 0), len(refs) - 1)]


def drill_guides() -> dict:
    from chirox.trainer import full_catalog

    refs = reference_images()
    drills = []
    for drill in full_catalog():
        kind = guide_kind(drill["key"])
        copy = GUIDE_COPY[kind]
        image = _guide_image(kind, refs)
        drills.append({
            **drill,
            "guide_kind": kind,
            "guide_title": copy["title"],
            "instruction": copy["instruction"],
            "camera_instruction": f"Best camera: {drill.get('view', 'front')}.",
            "guide_image": image,
        })
    return {"references": refs, "drills": drills}
