"""Deterministic stance geometry — the unthinking combat algorithm.

No mediapipe, no opencv, no model here on purpose: this module is pure math over
named 2D points, so it is fully unit-testable without a camera. That is the
whole point — the reflex layer's correctness is *proven*, not asserted.

A point is ``(x, y, visibility)``. Visibility (0..1) comes from the tracker; when
the required joints are not clearly seen, the reading is flagged UNCERTAIN and no
confident verdict is given (SAFETY.md: explicit uncertainty, never confident
diagnosis on thin evidence).

Thresholds are honest heuristics for conditioning, not lineage-certified form
law. They are meant to be tightened as the practitioner advances (the Noret
Protocol) — never to impersonate a master's eye.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

Point = tuple[float, float, float]  # (x, y, visibility)

UNCERTAINTY_THRESHOLD = 0.6

# Joint names Chirox reasons about.
LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, LEFT_SHOULDER = "left_hip", "left_knee", "left_ankle", "left_shoulder"
RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE, RIGHT_SHOULDER = "right_hip", "right_knee", "right_ankle", "right_shoulder"
LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST = "left_elbow", "right_elbow", "left_wrist", "right_wrist"


def angle(a: Point, b: Point, c: Point) -> float:
    """Angle at vertex ``b`` formed by a-b-c, in degrees [0, 180]."""
    rad = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0])
    deg = abs(rad * 180.0 / math.pi)
    return 360 - deg if deg > 180 else deg


@dataclass
class StanceReading:
    stance: str
    metrics: dict[str, float]
    flags: list[str] = field(default_factory=list)
    assessment: str = ""
    confidence: float = 1.0     # min visibility of required joints
    uncertain: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _confidence(points: dict[str, Point], required: list[str]) -> float:
    vis = [points[j][2] for j in required if j in points]
    return min(vis) if vis else 0.0


def _uncertain_reading(stance: str, required: list[str], confidence: float) -> StanceReading:
    return StanceReading(
        stance=stance,
        metrics={},
        flags=["low_visibility"],
        assessment=(
            "UNCERTAIN — required landmarks are not clearly visible; the measurement is "
            "unreliable. Fix the framing/lighting before trusting any verdict."
        ),
        confidence=round(confidence, 3),
        uncertain=True,
    )


# --- Ma Bu (Horse Stance) ------------------------------------------------------

HORSE_REQUIRED = [
    LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, LEFT_SHOULDER,
    RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE, RIGHT_SHOULDER,
]


def evaluate_horse_stance(points: dict[str, Point]) -> StanceReading:
    """Ma Bu: knees ~90-100°, spine upright (shoulder-hip-knee ≥ ~150°)."""
    conf = _confidence(points, HORSE_REQUIRED)
    if conf < UNCERTAINTY_THRESHOLD:
        return _uncertain_reading("Horse Stance (Ma Bu)", HORSE_REQUIRED, conf)

    lk = angle(points[LEFT_HIP], points[LEFT_KNEE], points[LEFT_ANKLE])
    rk = angle(points[RIGHT_HIP], points[RIGHT_KNEE], points[RIGHT_ANKLE])
    lb = angle(points[LEFT_SHOULDER], points[LEFT_HIP], points[LEFT_KNEE])
    rb = angle(points[RIGHT_SHOULDER], points[RIGHT_HIP], points[RIGHT_KNEE])

    metrics = {
        "left_knee_angle": round(lk, 2),
        "right_knee_angle": round(rk, 2),
        "left_back_angle": round(lb, 2),
        "right_back_angle": round(rb, 2),
    }
    flags: list[str] = []
    if lk > 120 or rk > 120:
        flags.append("stance_too_high")
    elif lk < 80 or rk < 80:
        flags.append("stance_collapsing")
    if lb < 150 or rb < 150:
        flags.append("spine_slouching")

    assessment = "Stable and rooted." if not flags else " | ".join(_HORSE_MESSAGES[f] for f in flags)
    return StanceReading("Horse Stance (Ma Bu)", metrics, flags, assessment, round(conf, 3), False)


_HORSE_MESSAGES = {
    "stance_too_high": "Stance too high — knees above 120°. Sink lower; drop your center.",
    "stance_collapsing": "Stance collapsing — knee below 80°. Rebuild structure; do not fold.",
    "spine_slouching": "Spine slouching — hold the trunk upright like a pine.",
}


# --- Gong Bu (Bow Stance) ------------------------------------------------------

BOW_REQUIRED = [LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE]


def evaluate_bow_stance(points: dict[str, Point], front: str = "left") -> StanceReading:
    """Gong Bu: front knee bent ~90-120° over the ankle, rear leg near-straight (≥150°)."""
    conf = _confidence(points, BOW_REQUIRED)
    if conf < UNCERTAINTY_THRESHOLD:
        return _uncertain_reading("Bow Stance (Gong Bu)", BOW_REQUIRED, conf)

    if front == "left":
        fh, fk, fa = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
        bh, bk, ba = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
    else:
        fh, fk, fa = RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
        bh, bk, ba = LEFT_HIP, LEFT_KNEE, LEFT_ANKLE

    front_knee = angle(points[fh], points[fk], points[fa])
    rear_knee = angle(points[bh], points[bk], points[ba])
    metrics = {"front_knee_angle": round(front_knee, 2), "rear_knee_angle": round(rear_knee, 2)}

    flags: list[str] = []
    if not (80 <= front_knee <= 120):
        flags.append("front_knee_out_of_range")
    if rear_knee < 150:
        flags.append("rear_leg_bent")

    messages = {
        "front_knee_out_of_range": "Front knee outside 80-120° — set the bend over the ankle, not past the toes.",
        "rear_leg_bent": "Rear leg bent — drive the back leg straight to root the stance.",
    }
    assessment = "Bow stance grounded." if not flags else " | ".join(messages[f] for f in flags)
    return StanceReading("Bow Stance (Gong Bu)", metrics, flags, assessment, round(conf, 3), False)


STANCES = {
    "horse": evaluate_horse_stance,
    "ma_bu": evaluate_horse_stance,
    "bow": evaluate_bow_stance,
    "gong_bu": evaluate_bow_stance,
}


# --- General motion measurement (flowing sequences, e.g. Eight Brocades) --------

_ANGLE_TRIPLETS = {
    "left_knee": (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE),
    "right_knee": (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE),
    "left_elbow": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST),
    "right_elbow": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST),
    "left_shoulder": (LEFT_HIP, LEFT_SHOULDER, LEFT_ELBOW),
    "right_shoulder": (RIGHT_HIP, RIGHT_SHOULDER, RIGHT_ELBOW),
}


def general_joint_angles(points: dict[str, Point], min_visibility: float = 0.5) -> dict[str, float]:
    """Raw joint angles for a flowing sequence. This is **measurement, not a
    verdict** — no pass/fail, no claim of correct form. It documents range of
    motion so a timeline can be built; the eye and the teacher judge the form."""
    out: dict[str, float] = {}
    for name, (a, b, c) in _ANGLE_TRIPLETS.items():
        if a in points and b in points and c in points:
            if min(points[a][2], points[b][2], points[c][2]) >= min_visibility:
                out[name] = round(angle(points[a], points[b], points[c]), 2)
    return out
