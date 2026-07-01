"""The vision session payload — the deterministic JSON that the Reflex hands to
the Codex. Pure aggregation over per-frame ``StanceReading``s; no camera here, so
it is unit-testable.

Uncertainty is preserved, not smoothed away: the count of unreadable frames and
the mean landmark confidence travel with the numbers, so the Master (and the
practitioner) can see how much to trust a session.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

from chirox.vision.stances import StanceReading

RECORD_TYPE = "vision_session"


@dataclass
class VisionSession:
    stance: str
    source: str
    started_ts: str
    ended_ts: str
    duration_s: float
    frames_evaluated: int
    frames_uncertain: int
    mean_confidence: float
    time_in_tolerance_s: float
    metrics_summary: dict[str, dict[str, float]] = field(default_factory=dict)
    flags_observed: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    RECORD_TYPE = RECORD_TYPE

    def payload(self) -> dict:
        return asdict(self)


@dataclass
class SessionRecording:
    """Manifest for one archived training video — the unit of the visual timeline.

    The video file lives in the git-ignored media archive; THIS (metadata only)
    is what gets sealed into the append-only Codex, so the timeline is a permanent,
    ordered record even though the footage is not in git. ``motion`` is raw range-
    of-motion measurement, never a form grade.
    """

    exercise: str
    date: str
    day_number: int
    source: str
    video_path: str
    duration_s: float
    frames: int
    frames_with_body: int
    mean_confidence: float
    motion: dict[str, dict[str, float]] = field(default_factory=dict)
    stance_summary: dict | None = None
    notes: list[str] = field(default_factory=list)

    RECORD_TYPE = "session_recording"

    def payload(self) -> dict:
        return asdict(self)


class SessionAccumulator:
    """Collect per-frame readings, then finalize a deterministic session summary."""

    def __init__(self, stance: str, source: str):
        self.stance = stance
        self.source = source
        self._samples: list[tuple[float, StanceReading]] = []

    def add(self, t: float, reading: StanceReading) -> None:
        self._samples.append((t, reading))

    def finalize(self, started_ts: str, ended_ts: str) -> VisionSession:
        samples = self._samples
        total = len(samples)
        if total == 0:
            return VisionSession(
                self.stance, self.source, started_ts, ended_ts, 0.0, 0, 0, 0.0, 0.0,
                notes=["No frames were evaluated — the tracker never saw a body."],
            )

        times = [t for t, _ in samples]
        duration = max(0.0, times[-1] - times[0])
        uncertain = sum(1 for _, r in samples if r.uncertain)
        mean_conf = sum(r.confidence for _, r in samples) / total

        # Aggregate each metric that appeared.
        metric_values: dict[str, list[float]] = {}
        for _, r in samples:
            for k, v in r.metrics.items():
                metric_values.setdefault(k, []).append(v)
        metrics_summary = {
            k: {"min": round(min(vs), 2), "mean": round(sum(vs) / len(vs), 2), "max": round(max(vs), 2)}
            for k, vs in metric_values.items()
        }

        flags = Counter()
        clean = 0
        for _, r in samples:
            if r.uncertain:
                continue
            if r.flags:
                flags.update(r.flags)
            else:
                clean += 1

        readable = total - uncertain
        time_in_tolerance = duration * (clean / readable) if readable else 0.0

        notes: list[str] = []
        if uncertain:
            notes.append(f"{uncertain}/{total} frames were UNCERTAIN (low visibility) and excluded from the verdict.")
        if mean_conf < 0.6:
            notes.append("Mean landmark confidence is low; treat this session as weak evidence.")

        return VisionSession(
            stance=self.stance,
            source=self.source,
            started_ts=started_ts,
            ended_ts=ended_ts,
            duration_s=round(duration, 2),
            frames_evaluated=total,
            frames_uncertain=uncertain,
            mean_confidence=round(mean_conf, 3),
            time_in_tolerance_s=round(time_in_tolerance, 2),
            metrics_summary=metrics_summary,
            flags_observed=dict(flags),
            notes=notes,
        )
