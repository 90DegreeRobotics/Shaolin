"""Deterministic practice sequences — named routines Wireguy can track.

Doctrine:
- The practitioner names the routine (or free-trains among known holds/reps).
- Phases advance by geometry gates and honest counts — never by a generative
  model guessing form lineage.
- Flowing work is identified and counted; it is not graded as "correct Shaolin."
- UNCERTAIN frames pause counting. Nothing is invented.

The first shipped sequence is Shaolin Temple Europe's Ba Duan Jin (Eight
Brocades) naming/order from Shi Heng Yi's published chapter list — encoded here
as reviewable phase specs, not scraped video.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

from chirox.vision.reps import RepCounter, jack_signal, knee_raise_signal
from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    RIGHT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST,
    STANCES, _body_scale, _best_side, angle,
)

Point = tuple[float, float, float]
SignalFn = Callable[[dict[str, Point]], float | None]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- geometry signals used by Ba Duan Jin phases ------------------------------------


def arms_overhead_signal(points: dict[str, Point]) -> float | None:
    """Wrist height above shoulders in body-lengths (+ = up). Same family as jacks."""
    return jack_signal(points)


def arrow_draw_signal(points: dict[str, Point]) -> float | None:
    """Horizontal stretch asymmetry: |left_wrist.x - right_wrist.x| / body scale."""
    need = (LEFT_WRIST, RIGHT_WRIST, LEFT_SHOULDER, RIGHT_SHOULDER)
    if any(j not in points or points[j][2] < 0.45 for j in need):
        return None
    span = abs(points[LEFT_WRIST][0] - points[RIGHT_WRIST][0])
    return span / _body_scale(points)


def heaven_earth_signal(points: dict[str, Point]) -> float | None:
    """One wrist high, one low: vertical separation of wrists in body-lengths."""
    need = (LEFT_WRIST, RIGHT_WRIST, LEFT_SHOULDER, RIGHT_SHOULDER)
    if any(j not in points or points[j][2] < 0.45 for j in need):
        return None
    return abs(points[LEFT_WRIST][1] - points[RIGHT_WRIST][1]) / _body_scale(points)


def owl_gaze_signal(points: dict[str, Point]) -> float | None:
    """Torso twist proxy: shoulder-line horizontal offset vs hip-line midpoint."""
    need = (LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP)
    if any(j not in points or points[j][2] < 0.45 for j in need):
        return None
    mid_sh = (points[LEFT_SHOULDER][0] + points[RIGHT_SHOULDER][0]) / 2
    mid_hip = (points[LEFT_HIP][0] + points[RIGHT_HIP][0]) / 2
    return abs(mid_sh - mid_hip) / _body_scale(points)


def big_bear_signal(points: dict[str, Point]) -> float | None:
    """Side bend proxy: shoulder height difference in body-lengths."""
    need = (LEFT_SHOULDER, RIGHT_SHOULDER)
    if any(j not in points or points[j][2] < 0.45 for j in need):
        return None
    return abs(points[LEFT_SHOULDER][1] - points[RIGHT_SHOULDER][1]) / _body_scale(points)


def bend_touch_signal(points: dict[str, Point]) -> float | None:
    """Standing fold: shoulder–hip–knee angle on the visible side (small = folded)."""
    side = _best_side(points)
    sh = points.get(f"{side}_shoulder")
    hip = points.get(f"{side}_hip")
    knee = points.get(f"{side}_knee")
    if not (sh and hip and knee) or min(sh[2], hip[2], knee[2]) < 0.5:
        return None
    return angle(sh, hip, knee)


def punch_guard_signal(points: dict[str, Point]) -> float | None:
    """Punch cycle: mean wrist forward of shoulders in x, normalized."""
    need = (LEFT_WRIST, RIGHT_WRIST, LEFT_SHOULDER, RIGHT_SHOULDER)
    if any(j not in points or points[j][2] < 0.4 for j in need):
        return None
    # Front camera: "forward" is not depth — use wrist height oscillation near
    # guard as a usable cycle (wrists rise/fall with punches).
    sh_y = (points[LEFT_SHOULDER][1] + points[RIGHT_SHOULDER][1]) / 2
    wr_y = (points[LEFT_WRIST][1] + points[RIGHT_WRIST][1]) / 2
    return (sh_y - wr_y) / _body_scale(points)


def heel_click_signal(points: dict[str, Point]) -> float | None:
    """Heel raise: ankle height above a quiet baseline proxy (hip-relative)."""
    need = (LEFT_ANKLE, RIGHT_ANKLE, LEFT_HIP, RIGHT_HIP)
    if any(j not in points or points[j][2] < 0.45 for j in need):
        return None
    hip_y = (points[LEFT_HIP][1] + points[RIGHT_HIP][1]) / 2
    ank_y = (points[LEFT_ANKLE][1] + points[RIGHT_ANKLE][1]) / 2
    # Standing: ankles below hips. A heel raise shortens the gap slightly.
    return (ank_y - hip_y) / _body_scale(points)


# --- phase / sequence specs ---------------------------------------------------------


@dataclass(frozen=True)
class PhaseSpec:
    key: str
    label: str
    kind: str = "reps"          # hold | reps | timed
    pose_key: str | None = None  # optional STANCES key for form_rate
    signal: SignalFn | None = None
    enter: float | None = None
    exit: float | None = None
    target_reps: int | None = None
    min_seconds: float = 3.0
    auto_advance: bool = True


@dataclass(frozen=True)
class SequenceSpec:
    key: str
    label: str
    source_note: str
    phases: tuple[PhaseSpec, ...]


def _rep_phase(key: str, label: str, signal: SignalFn, enter: float, exit: float,
               target: int, pose_key: str | None = None, min_seconds: float = 4.0) -> PhaseSpec:
    return PhaseSpec(
        key=key, label=label, kind="reps", pose_key=pose_key, signal=signal,
        enter=enter, exit=exit, target_reps=target, min_seconds=min_seconds,
    )


def _hold_phase(key: str, label: str, pose_key: str, min_seconds: float = 5.0) -> PhaseSpec:
    return PhaseSpec(
        key=key, label=label, kind="hold", pose_key=pose_key,
        min_seconds=min_seconds, target_reps=None, auto_advance=True,
    )


# Canonical order from Shaolin Temple Europe Ba Duan Jin (Shi Heng Yi chapters).
EIGHT_BROCADES_STE = SequenceSpec(
    key="eight_brocades_ste",
    label="Eight Brocades (Shaolin Temple Europe)",
    source_note=(
        "Phase names/order from Shaolin Temple Europe Ba Duan Jin "
        "(Shi Heng Yi). Encoded as geometry gates — not scraped video."
    ),
    phases=(
        _hold_phase("bdj_open", "Opening", "wuji_standing", min_seconds=4.0),
        _rep_phase("bdj_support_heaven", "Supporting the Heaven",
                   arms_overhead_signal, enter=-0.05, exit=0.35, target=8,
                   pose_key="arms_raised", min_seconds=6.0),
        _rep_phase("bdj_draw_arrow", "Drawing the Arrow",
                   arrow_draw_signal, enter=0.35, exit=0.85, target=8,
                   pose_key="horse", min_seconds=6.0),
        _rep_phase("bdj_separate_heaven_earth", "Separating Heaven and Earth",
                   heaven_earth_signal, enter=0.25, exit=0.7, target=8,
                   min_seconds=6.0),
        _rep_phase("bdj_owl_gaze", "Wise Owl Gazing Back",
                   owl_gaze_signal, enter=0.04, exit=0.14, target=8,
                   min_seconds=6.0),
        _rep_phase("bdj_big_bear", "Big Bear Turns to Side",
                   big_bear_signal, enter=0.04, exit=0.16, target=8,
                   min_seconds=6.0),
        _rep_phase("bdj_bend_touch", "Bending Back and Touching Toes",
                   bend_touch_signal, enter=100.0, exit=155.0, target=6,
                   min_seconds=8.0),
        _rep_phase("bdj_punch_fists", "Clenching the Fists",
                   punch_guard_signal, enter=-0.15, exit=0.2, target=8,
                   pose_key="horse_guard", min_seconds=8.0),
        _rep_phase("bdj_heel_clicks", "Clicking Heels 7 Times",
                   heel_click_signal, enter=0.85, exit=0.95, target=7,
                   min_seconds=6.0),
        _hold_phase("bdj_close", "Closing", "wuji_standing", min_seconds=4.0),
    ),
)

SEQUENCE_CATALOG: dict[str, SequenceSpec] = {
    EIGHT_BROCADES_STE.key: EIGHT_BROCADES_STE,
}


def list_sequences() -> list[dict]:
    return [
        {
            "key": s.key,
            "label": s.label,
            "source_note": s.source_note,
            "phase_count": len(s.phases),
            "phases": [{"key": p.key, "label": p.label, "kind": p.kind,
                        "target_reps": p.target_reps} for p in s.phases],
        }
        for s in SEQUENCE_CATALOG.values()
    ]


# --- live tracker -------------------------------------------------------------------


@dataclass
class PhaseResult:
    key: str
    label: str
    kind: str
    entered_ts: str
    exited_ts: str | None = None
    duration_s: float = 0.0
    reps_counted: int = 0
    target_reps: int | None = None
    form_rate: float | None = None
    flags: dict[str, int] = field(default_factory=dict)
    uncertain_frames: int = 0
    frames_seen: int = 0
    metrics_summary: dict[str, dict[str, float]] = field(default_factory=dict)
    advanced_by: str = "auto"  # auto | manual | stop


class SequenceTracker:
    """Push per-frame points; get honest phase/rep state. Pure enough to unit-test."""

    def __init__(self, spec: SequenceSpec):
        self.spec = spec
        self.started = _iso_now()
        self.finished: str | None = None
        self._phase_i = 0
        self._phase_t0 = 0.0
        self._elapsed0 = 0.0
        self._counter: RepCounter | None = None
        self._in_form = 0
        self._seen = 0
        self._uncertain = 0
        self._flags: dict[str, int] = {}
        self._metric_vals: dict[str, list[float]] = {}
        self._completed: list[PhaseResult] = []
        self._active_entered = _iso_now()
        self._done = False
        self._boot_phase()

    def _boot_phase(self) -> None:
        phase = self.spec.phases[self._phase_i]
        self._counter = None
        if phase.kind == "reps" and phase.signal is not None and phase.enter is not None and phase.exit is not None:
            self._counter = RepCounter(phase.enter, phase.exit)
        self._in_form = 0
        self._seen = 0
        self._uncertain = 0
        self._flags = {}
        self._metric_vals = {}
        self._active_entered = _iso_now()
        self._phase_t0 = 0.0
        self._elapsed0 = 0.0

    @property
    def done(self) -> bool:
        return self._done

    @property
    def phase(self) -> PhaseSpec:
        return self.spec.phases[min(self._phase_i, len(self.spec.phases) - 1)]

    def status(self) -> dict:
        phase = self.phase
        hold_s = max(0.0, self._phase_t0)
        form_rate = round(self._in_form / self._seen, 3) if self._seen else None
        return {
            "routine_key": self.spec.key,
            "label": self.spec.label,
            "phase_key": phase.key,
            "phase_label": phase.label,
            "phase_index": self._phase_i,
            "phase_count": len(self.spec.phases),
            "kind": phase.kind,
            "reps": self._counter.count if self._counter else 0,
            "target_reps": phase.target_reps,
            "hold_s": round(hold_s, 1),
            "min_seconds": phase.min_seconds,
            "form_rate": form_rate,
            "uncertain": self._uncertain > 0 and self._seen == self._uncertain,
            "done": self._done,
            "phases_completed": len(self._completed),
        }

    def push(self, points: dict[str, Point] | None, t: float) -> dict:
        """Feed one frame. ``t`` is seconds since session start. Returns status."""
        if self._done:
            return self.status()
        if self._elapsed0 == 0.0:
            self._elapsed0 = t
        self._phase_t0 = t - self._elapsed0
        phase = self.phase

        if points is None:
            self._uncertain += 1
            return self.status()

        pose_ok = True
        if phase.pose_key and phase.pose_key in STANCES:
            reading = STANCES[phase.pose_key](points)
            if reading.uncertain:
                self._uncertain += 1
                return self.status()  # pause counting
            self._seen += 1
            if reading.flags:
                pose_ok = False
                for f in reading.flags:
                    self._flags[f] = self._flags.get(f, 0) + 1
            else:
                self._in_form += 1
            for k, v in reading.metrics.items():
                self._metric_vals.setdefault(k, []).append(float(v))
        else:
            self._seen += 1
            self._in_form += 1

        if phase.kind == "reps" and self._counter is not None and phase.signal is not None:
            value = phase.signal(points)
            if value is not None:
                self._counter.push(value)
            # Auto-advance when target met and minimum time elapsed.
            if (phase.auto_advance and phase.target_reps
                    and self._counter.count >= phase.target_reps
                    and self._phase_t0 >= phase.min_seconds):
                self._advance("auto", t)
        elif phase.kind in ("hold", "timed"):
            if (phase.auto_advance and pose_ok
                    and self._phase_t0 >= phase.min_seconds
                    and self._seen >= 8):
                self._advance("auto", t)

        return self.status()

    def next_phase(self, t: float) -> dict:
        if self._done:
            return self.status()
        self._advance("manual", t)
        return self.status()

    def stop(self, t: float) -> dict:
        if not self._done:
            self._advance("stop", t, final=True)
        return self.summary()

    def _advance(self, how: str, t: float, final: bool = False) -> None:
        phase = self.phase
        duration = max(0.0, t - self._elapsed0) if self._elapsed0 else self._phase_t0
        metrics_summary = {
            k: {
                "min": round(min(vs), 2),
                "mean": round(sum(vs) / len(vs), 2),
                "max": round(max(vs), 2),
            }
            for k, vs in self._metric_vals.items() if vs
        }
        result = PhaseResult(
            key=phase.key,
            label=phase.label,
            kind=phase.kind,
            entered_ts=self._active_entered,
            exited_ts=_iso_now(),
            duration_s=round(duration, 1),
            reps_counted=self._counter.count if self._counter else 0,
            target_reps=phase.target_reps,
            form_rate=round(self._in_form / self._seen, 3) if self._seen else None,
            flags=dict(self._flags),
            uncertain_frames=self._uncertain,
            frames_seen=self._seen,
            metrics_summary=metrics_summary,
            advanced_by=how,
        )
        self._completed.append(result)

        if final or self._phase_i >= len(self.spec.phases) - 1:
            self._done = True
            self.finished = _iso_now()
            return

        self._phase_i += 1
        self._elapsed0 = t
        self._boot_phase()

    def summary(self) -> dict:
        phases = [asdict(p) for p in self._completed]
        # If stopped mid-phase without finalize via stop(), include nothing extra.
        reps_total = sum(p.reps_counted for p in self._completed)
        duration = sum(p.duration_s for p in self._completed)
        uncertain = sum(p.uncertain_frames for p in self._completed)
        seen = sum(p.frames_seen for p in self._completed)
        return {
            "routine_key": self.spec.key,
            "label": self.spec.label,
            "source_note": self.spec.source_note,
            "started": self.started,
            "finished": self.finished or _iso_now(),
            "phases": phases,
            "totals": {
                "phases_completed": len(self._completed),
                "phases_total": len(self.spec.phases),
                "reps_total": reps_total,
                "duration_s": round(duration, 1),
                "uncertain_ratio": round(uncertain / seen, 3) if seen else None,
            },
            "complete": self._done and len(self._completed) >= len(self.spec.phases),
        }


def make_tracker(routine_key: str) -> SequenceTracker:
    if routine_key not in SEQUENCE_CATALOG:
        raise ValueError(
            f"unknown routine '{routine_key}'. Known: {sorted(SEQUENCE_CATALOG)}"
        )
    return SequenceTracker(SEQUENCE_CATALOG[routine_key])


def detect_stance(points: dict[str, Point], *, min_score: float = 0.55) -> dict | None:
    """Best matching known hold from the reference-chart catalog.

    Pure geometry — no generative guess. Iterates ``HOLD_CATALOG`` keys only
    (never CLI aliases like ``ma_bu``). Prefers clean form, then confidence,
    then fewer flags, then more-specific templates so e.g. horse+guard names
    ``horse_guard`` instead of plain ``horse``.
    """
    from chirox.vision.stances import HOLD_CATALOG, template_specificity

    best_key = None
    best_reading = None
    best_score = -1.0
    for key in HOLD_CATALOG:
        evaluator = STANCES.get(key)
        if evaluator is None:
            continue
        reading = evaluator(points)
        if reading.uncertain:
            continue
        score = (
            reading.confidence
            + (0.35 if not reading.flags else 0.0)
            - 0.04 * len(reading.flags)
            + 0.03 * template_specificity(key)
        )
        if score > best_score:
            best_score = score
            best_key = key
            best_reading = reading
    if best_key is None or best_reading is None or best_score < min_score:
        return None
    return {
        "key": best_key,
        "label": best_reading.stance,
        "confidence": best_reading.confidence,
        "flags": list(best_reading.flags),
        "form_clean": not best_reading.flags,
        "score": round(best_score, 3),
    }


def free_train_tag(points: dict[str, Point]) -> dict | None:
    """Best matching known hold when cleanly measured. None if unsure."""
    # Slightly stricter than live auto-detect so free-train tags stay honest.
    hit = detect_stance(points, min_score=0.7)
    if hit is None:
        return None
    return {k: hit[k] for k in ("key", "label", "confidence", "flags", "form_clean")}


def seal_routine_session(summary: dict, source: str = "0",
                         video_path: str | None = None,
                         notes: list[str] | None = None) -> dict:
    """Seal a finished routine into the append-only Dojo Record forever."""
    from chirox.calendar import dojo_day
    from chirox.config import CODEX_PATH, Config
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    from datetime import date

    config = Config.load()
    day = dojo_day(config.practice_start_date)
    payload = {
        **summary,
        "source": str(source),
        "date": date.today().isoformat(),
        "day_number": day.day_number,
        "video_path": video_path,
        "notes": list(notes or []),
    }

    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize("vision.routine")
    event = codex.append("routine_session", payload)
    sentinel.consume(grant)
    return {"ok": True, "seq": event.seq, "type": event.type, "payload": payload}
