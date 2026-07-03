"""Rep counting — deterministic, hysteresis-gated, spoken out loud.

A rep is a full cycle of one scalar signal crossing a low threshold and coming
back above a high one (hysteresis so jitter can never double-count). The signal
is pure geometry from the same landmarks the stances use — no model opinions.

Signals per exercise come from the reference charts:

- squats:       knee angle (visible side)      — down < 115, up > 158
- pushups:      elbow angle (visible side)     — down < 105, up > 150
- situps:       shoulder-hip-knee fold angle   — up (crunched) < 105, down > 135
- knee_raises:  lifted-knee height above hips  — up > +0.05 leg, down < -0.15
- jumping_jacks: wrists above shoulders        — open vs closed cycle
"""

from __future__ import annotations

from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST,
    _best_side, _body_scale, angle,
)


class RepCounter:
    """Count low→high cycles of a scalar with hysteresis. Pure, deterministic."""

    def __init__(self, enter_below: float, exit_above: float):
        assert enter_below < exit_above
        self.enter_below = enter_below
        self.exit_above = exit_above
        self.count = 0
        self._down = False

    def push(self, value: float | None) -> bool:
        """Feed one sample; True exactly when a rep completes."""
        if value is None:
            return False
        if not self._down and value < self.enter_below:
            self._down = True
            return False
        if self._down and value > self.exit_above:
            self._down = False
            self.count += 1
            return True
        return False


def _side_joint(points, side: str, name: str):
    return points.get(f"{side}_{name}")


def _angle_signal(points, a: str, b: str, c: str) -> float | None:
    side = _best_side(points)
    pa, pb, pc = (_side_joint(points, side, j) for j in (a, b, c))
    if not (pa and pb and pc) or min(pa[2], pb[2], pc[2]) < 0.5:
        return None
    return angle(pa, pb, pc)


def squat_signal(points) -> float | None:
    return _angle_signal(points, "hip", "knee", "ankle")


def pushup_signal(points) -> float | None:
    return _angle_signal(points, "shoulder", "elbow", "wrist")


def situp_signal(points) -> float | None:
    return _angle_signal(points, "shoulder", "hip", "knee")


def knee_raise_signal(points) -> float | None:
    """Height of the higher knee above the hip line, in leg-lengths (+ = up)."""
    need = (LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE)
    if any(j not in points or points[j][2] < 0.5 for j in need):
        return None
    hip_y = (points[LEFT_HIP][1] + points[RIGHT_HIP][1]) / 2
    knee_y = min(points[LEFT_KNEE][1], points[RIGHT_KNEE][1])   # higher knee
    return (hip_y - knee_y) / _body_scale(points)


def jack_signal(points) -> float | None:
    """+1-ish arms overhead, -1-ish arms down: wrist height vs shoulders."""
    need = (LEFT_WRIST, RIGHT_WRIST, LEFT_SHOULDER, RIGHT_SHOULDER)
    if any(j not in points or points[j][2] < 0.4 for j in need):
        return None
    sh_y = (points[LEFT_SHOULDER][1] + points[RIGHT_SHOULDER][1]) / 2
    wr_y = (points[LEFT_WRIST][1] + points[RIGHT_WRIST][1]) / 2
    return (sh_y - wr_y) / _body_scale(points)


# key -> (label, camera view, signal fn, enter_below, exit_above)
REP_CATALOG: dict[str, dict] = {
    "squats": {"label": "Slow Squats", "view": "side",
               "signal": squat_signal, "enter": 115.0, "exit": 158.0},
    "pushups": {"label": "Pushups", "view": "side",
                "signal": pushup_signal, "enter": 105.0, "exit": 150.0},
    "situps": {"label": "Situps", "view": "side",
               "signal": situp_signal, "enter": 105.0, "exit": 135.0},
    "knee_raises": {"label": "Knee Raises", "view": "front",
                    "signal": knee_raise_signal, "enter": -0.15, "exit": 0.05},
    "jumping_jacks": {"label": "Low-Impact Jumping Jacks", "view": "front",
                      "signal": jack_signal, "enter": -0.2, "exit": 0.45},
}


def make_counter(key: str) -> RepCounter:
    spec = REP_CATALOG[key]
    return RepCounter(spec["enter"], spec["exit"])
