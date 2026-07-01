"""Multi-camera fusion for the Weatherman rig.

Two planes tell two truths:

    front view (frontal plane) — knee angles, stance width, symmetry
    side  view (sagittal plane) — spine lean, stance depth

This module fuses per-camera ``StanceReading``s into one honest verdict, tagging
each metric with the camera it came from and naming what a missing camera cannot
see. It is pure and testable on synthetic readings.

Honest gate: **synchronized capture on the physical rig is not proven here** — it
needs the hardware (C920s into OBS, per WEATHERMAN_STUDIO_TASKS.md). The fusion
logic below is real and single-source verified; the two-camera live run is a
hardware integration step, and is labeled as such until it is actually run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chirox.vision.stances import StanceReading

FRONT, SIDE = "front", "side"


@dataclass(frozen=True)
class CameraSpec:
    role: str          # "front" | "side"
    source: object     # device index (int) or video path (str)
    label: str = ""


@dataclass
class CameraRegistry:
    """Maps logical roles to physical sources. Defaults follow the Weatherman rig
    (direct-USB C920 as the front source); the side camera is a second device."""

    cameras: list[CameraSpec] = field(default_factory=list)

    @classmethod
    def default_rig(cls) -> "CameraRegistry":
        return cls([
            CameraSpec(FRONT, 0, "Desktop C920 (USB) — front"),
            CameraSpec(SIDE, 1, "Second camera — side"),
        ])

    def by_role(self, role: str) -> CameraSpec | None:
        return next((c for c in self.cameras if c.role == role), None)

    def sources(self) -> dict[str, object]:
        return {c.role: c.source for c in self.cameras}


@dataclass
class FusedReading:
    stance: str
    roles_present: list[str]
    metrics: dict[str, dict]          # key -> {"value": float, "source": role}
    flags: list[str]                  # "flag@role"
    assessment: str
    confidence: float
    limitations: list[str] = field(default_factory=list)


def _preferred_role(metric_key: str) -> str | None:
    if "knee" in metric_key:
        return FRONT
    if "back" in metric_key or "spine" in metric_key:
        return SIDE
    return None


def fuse(readings_by_role: dict[str, StanceReading]) -> FusedReading:
    if not readings_by_role:
        raise ValueError("fuse() needs at least one camera reading")

    roles = sorted(readings_by_role)
    stance = next(iter(readings_by_role.values())).stance
    limitations: list[str] = []

    if FRONT not in readings_by_role:
        limitations.append("No front camera: knee symmetry and stance width are unverified.")
    if SIDE not in readings_by_role:
        limitations.append("No side camera: spine lean and stance depth cannot be measured reliably.")
    for role, r in readings_by_role.items():
        if r.uncertain:
            limitations.append(f"{role} view UNCERTAIN (low visibility) — its numbers are unreliable.")

    # Choose each metric from its ideal plane when available.
    metrics: dict[str, dict] = {}
    all_keys = {k for r in readings_by_role.values() for k in r.metrics}
    for key in sorted(all_keys):
        pref = _preferred_role(key)
        chosen_role = pref if (pref in readings_by_role and key in readings_by_role[pref].metrics) else None
        if chosen_role is None:
            chosen_role = next((role for role in roles if key in readings_by_role[role].metrics), None)
        if chosen_role is not None:
            metrics[key] = {"value": readings_by_role[chosen_role].metrics[key], "source": chosen_role}
            if pref is not None and chosen_role != pref:
                limitations.append(f"'{key}' read from {chosen_role} view, not the ideal {pref} view.")

    flags = [f"{f}@{role}" for role in roles for f in readings_by_role[role].flags]
    confidence = round(min(r.confidence for r in readings_by_role.values()), 3)

    if any(readings_by_role[r].uncertain for r in roles):
        assessment = "UNCERTAIN — at least one view could not read the body clearly."
    elif flags:
        parts = [readings_by_role[role].assessment for role in roles if readings_by_role[role].flags]
        assessment = " | ".join(dict.fromkeys(parts))
    else:
        assessment = "Rooted across all available views."

    return FusedReading(
        stance=stance,
        roles_present=roles,
        metrics=metrics,
        flags=flags,
        assessment=assessment,
        confidence=confidence,
        limitations=list(dict.fromkeys(limitations)),
    )
