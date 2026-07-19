"""Reproduction verifier — measure the body against known targets.

This is not status, ranking, or lineage. It is a ruler: how close is this
frame to a chart hold the practitioner is trying to reproduce. Scores speak
when the shape is ugly. UNCERTAIN speaks when the camera cannot see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from chirox.vision.stances import HOLD_CATALOG, STANCES, template_specificity

IN_BAND_SCORE = 70.0  # reproducing the target well enough to count as "in"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def match_hold(points: dict, key: str) -> dict[str, Any]:
    """Score one catalog hold. Always returns a verdict when the body is seen."""
    if key not in STANCES:
        raise ValueError(f"unknown hold '{key}'. Known: {sorted(HOLD_CATALOG)}")
    label = HOLD_CATALOG.get(key, {}).get("label") or key
    reading = STANCES[key](points)
    if reading.uncertain:
        return {
            "key": key,
            "label": reading.stance or label,
            "score": None,
            "uncertain": True,
            "in_band": False,
            "flags": list(reading.flags),
            "corrections": [reading.assessment] if reading.assessment else [],
            "confidence": reading.confidence,
            "assessment": reading.assessment,
        }
    n_flags = len(reading.flags)
    # Confidence sets the ceiling; each flag cuts hard. Clean form earns high marks.
    ceiling = 55.0 + 45.0 * float(reading.confidence)
    score = max(0.0, min(100.0, ceiling - 18.0 * n_flags))
    if n_flags == 0:
        score = max(score, 80.0 + 20.0 * float(reading.confidence))
    corrections: list[str] = []
    if reading.assessment and n_flags:
        corrections = [p.strip() for p in reading.assessment.split("|") if p.strip()]
    elif n_flags == 0:
        corrections = ["Root. The shape holds."]
    in_band = bool(n_flags == 0 and score >= IN_BAND_SCORE)
    return {
        "key": key,
        "label": reading.stance or label,
        "score": round(score, 1),
        "uncertain": False,
        "in_band": in_band,
        "flags": list(reading.flags),
        "corrections": corrections,
        "confidence": reading.confidence,
        "assessment": reading.assessment,
    }


def rank_holds(points: dict) -> list[dict[str, Any]]:
    """Every measurable hold, best first — including low scores. No silence until pretty."""
    ranked: list[dict[str, Any]] = []
    for key in HOLD_CATALOG:
        m = match_hold(points, key)
        if m["uncertain"]:
            continue
        ranked.append(m)
    ranked.sort(
        key=lambda m: (
            -(m["score"] if m["score"] is not None else -1.0),
            -template_specificity(m["key"]),
        )
    )
    return ranked


def verify_frame(points: dict, target_key: str | None = None) -> dict[str, Any]:
    """One frame of verification.

    ``target_key`` locks a hold. ``None`` / ``auto`` picks the closest catalog
    target and still reports the score — even when far from clean.
    """
    auto = target_key in (None, "", "auto")
    if not auto:
        m = match_hold(points, target_key)
        return {
            "auto": False,
            "target": m,
            "alternates": [],
            "mode": "locked",
        }
    ranked = rank_holds(points)
    if not ranked:
        return {
            "auto": True,
            "target": None,
            "alternates": [],
            "mode": "auto",
            "note": "Body unseen or no hold could be scored.",
        }
    return {
        "auto": True,
        "target": ranked[0],
        "alternates": [
            {"key": r["key"], "label": r["label"], "score": r["score"]}
            for r in ranked[1:4]
        ],
        "mode": "auto",
    }


@dataclass
class MatchSession:
    """Accumulate verification while the mirror runs — seal when practice ends."""

    target_key: str | None = None
    auto: bool = True
    started: str = field(default_factory=_iso_now)
    frames: int = 0
    in_band_frames: int = 0
    uncertain_frames: int = 0
    score_sum: float = 0.0
    score_n: int = 0
    best_score: float = 0.0
    last: dict[str, Any] | None = None
    label: str = "auto"

    def push(self, verify: dict[str, Any]) -> dict[str, Any]:
        target = verify.get("target")
        self.last = verify
        self.frames += 1
        if not target:
            self.uncertain_frames += 1
            return self.status()
        if verify.get("auto"):
            self.auto = True
            self.target_key = target.get("key")
            self.label = target.get("label") or self.label
        else:
            self.auto = False
            self.target_key = target.get("key")
            self.label = target.get("label") or self.label
        if target.get("uncertain"):
            self.uncertain_frames += 1
        else:
            score = target.get("score")
            if score is not None:
                self.score_sum += float(score)
                self.score_n += 1
                self.best_score = max(self.best_score, float(score))
            if target.get("in_band"):
                self.in_band_frames += 1
        return self.status()

    def status(self) -> dict[str, Any]:
        mean = round(self.score_sum / self.score_n, 1) if self.score_n else None
        in_band_ratio = (
            round(self.in_band_frames / self.frames, 3) if self.frames else None
        )
        return {
            "active": True,
            "auto": self.auto,
            "target_key": self.target_key,
            "label": self.label,
            "frames": self.frames,
            "in_band_frames": self.in_band_frames,
            "uncertain_frames": self.uncertain_frames,
            "in_band_ratio": in_band_ratio,
            "mean_score": mean,
            "best_score": round(self.best_score, 1) if self.score_n else None,
            "last": self.last,
        }

    def summary(self) -> dict[str, Any]:
        st = self.status()
        st["finished"] = _iso_now()
        st["started"] = self.started
        return st


def seal_match_session(summary: dict, source: str = "0") -> dict:
    """Seal a verification session into the append-only Dojo Record."""
    from datetime import date

    from chirox.calendar import dojo_day
    from chirox.config import CODEX_PATH, Config
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    config = Config.load()
    day = dojo_day(config.practice_start_date)
    payload = {
        **summary,
        "source": str(source),
        "date": date.today().isoformat(),
        "day_number": day.day_number,
    }
    # Drop bulky last-frame blob from the forever record — keep the numbers.
    payload.pop("last", None)

    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize("vision.verify")
    event = codex.append("match_session", payload)
    sentinel.consume(grant)
    return {"ok": True, "seq": event.seq, "type": event.type, "payload": payload}
