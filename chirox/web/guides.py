"""Exercise guide data for the local cockpit.

The guide layer keeps the browser aligned with the real trainer catalog: every
visible drill card comes from the same deterministic catalog Chirox can call.
Reference charts are the practitioner's own ten posters; every drill maps to
the chart that actually shows it (verified by eye against the posters
2026-07-06), never to an arbitrary image. Measurements still come from the
backend pose engine.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote


REFERENCE_DIR = Path(__file__).resolve().parents[1] / "reference"

# The ten posters, by their printed titles. Index = the (N) in the filename.
CHART_TITLES = {
    1: "Stance Work — Foundational Stances",
    2: "Stance Work — Holds, Variations & Transitions",
    3: "Basic Kung Fu Conditioning",
    4: "Shaolin-Style Movement Drills",
    5: "Qi Gong",
    6: "Mobility",
    7: "Balance",
    8: "Breath & Meditation",
    9: "Small-Space Cardio",
    10: "Floor Work + Beginner Daily Circuit",
}

# Every trainable drill -> the chart number that actually depicts it.
DRILL_CHARTS = {
    # holds — stances (chart 1: foundational stances)
    "horse": 1,
    "bow": 1,
    "crane": 1,
    "drop_stance": 1,
    "t_stance": 1,
    "parallel_ready": 1,
    "meditation_stance": 1,
    "empty_stance": 1,
    # holds — variations and balance
    "horse_guard": 2,        # chart 2: static holds in horse
    "one_leg_stand": 7,      # chart 7: balance — one-leg stand
    "wuji_standing": 5,      # chart 5: qi gong — wuji standing
    # holds — conditioning and floor
    "plank": 10,             # chart 10: floor work — plank family
    "wall_sit": 3,           # chart 3: conditioning — wall sit
    "squat_hold": 3,         # chart 3: conditioning — squat holds
    "hollow_hold": 10,       # chart 10: floor work — hollow body hold
    "glute_bridge": 3,       # chart 3: conditioning — glute bridge
    "leg_raise_hold": 10,    # chart 10: floor work — leg raises (scaled)
    # holds — qigong / meditation
    "arms_raised": 5,        # chart 5: qi gong — two hands hold up the heavens
    "seated_meditation": 8,  # chart 8: breath & meditation — breath sits
    # reps
    "squats": 3,             # chart 3: conditioning — slow squats
    "pushups": 3,            # chart 3: conditioning — pushups
    "situps": 10,            # chart 10: floor work — situps
    "knee_raises": 4,        # chart 4: movement drills — knee raises
    "jumping_jacks": 9,      # chart 9: small-space cardio — low-impact jacks
}

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
    """All ten charts, in poster order, with their real printed titles."""
    images = sorted(REFERENCE_DIR.glob("*.png"), key=_image_number) if REFERENCE_DIR.exists() else []
    out = []
    for i, p in enumerate(images):
        number = _image_number(p)
        out.append({
            "index": i,
            "number": number,
            "title": CHART_TITLES.get(number, f"Reference {number}"),
            "file": p.name,
            "url": f"/reference/{quote(p.name)}",
        })
    return out


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


def _chart_for(key: str, refs: list[dict]) -> dict | None:
    """The drill's own chart — by number, never by list position."""
    number = DRILL_CHARTS.get(key)
    if number is None:
        return refs[0] if refs else None
    for ref in refs:
        if ref["number"] == number:
            return ref
    return refs[0] if refs else None


def drill_guides() -> dict:
    from chirox.trainer import full_catalog

    refs = reference_images()
    drills = []
    for drill in full_catalog():
        kind = guide_kind(drill["key"])
        copy = GUIDE_COPY[kind]
        image = _chart_for(drill["key"], refs)
        drills.append({
            **drill,
            "guide_kind": kind,
            "guide_title": copy["title"],
            "instruction": copy["instruction"],
            "camera_instruction": f"Best camera: {drill.get('view', 'front')}.",
            "guide_image": image,
        })
    return {"references": refs, "drills": drills}
