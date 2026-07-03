"""Chirox calls the training — the spoken drill caller.

The original vision: Chirox chooses the exercise, says it out loud, watches
through the mirror, and corrects you — like an instructor would. Everything he
says about your form comes from the deterministic geometry (``stances.py``),
never from a model's imagination:

- the drill plan is chosen from the stance catalog (weighted toward what the
  Dojo Record shows you have practiced least),
- each drill is announced by voice ("Horse stance. Sixty seconds. Begin."),
- corrections are the stance evaluator's own flag messages, spoken at most
  once every few seconds — the instructor does not nag every frame,
- what counts is measured: seconds held in form vs. out of form vs. unseen,
- the session summary is sealed to the Codex as measurement, labeled as
  measurement. **No pose from your body ever becomes a template.** Correct
  form lives in code, from published stance standards, reviewable by anyone.

While a session runs it holds the same voice lock a narration does, so the ear
ignores the trainer's speech and "Chirox, stop" ends the session.

Run it:  chirox train                (default plan)
         chirox train --stances horse,crane --seconds 45
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from chirox.vision.reps import REP_CATALOG, make_counter
from chirox.vision.stances import HOLD_CATALOG, STANCES

DEFAULT_SECONDS = 60
DEFAULT_REPS = 10
GRACE_S = 6.0            # settle-in time after the announcement, not judged
CORRECTION_GAP_S = 7.0   # minimum silence between spoken corrections

# The rotation Chirox draws from when choosing for you: a real session mix —
# stances, conditioning holds, and counted reps, all from the reference charts.
DEFAULT_ROTATION = [
    "horse", "bow", "crane", "one_leg_stand", "squat_hold", "wall_sit",
    "plank", "horse_guard", "drop_stance", "squats", "pushups", "knee_raises",
]


def drill_label(key: str) -> str:
    if key in REP_CATALOG:
        return REP_CATALOG[key]["label"]
    if key in HOLD_CATALOG:
        return HOLD_CATALOG[key]["label"]
    return key


def full_catalog() -> list[dict]:
    """Everything trainable, for the deck's chips: holds then reps."""
    out = [{"key": k, "label": v["label"], "kind": "hold", "view": v["view"]}
           for k, v in HOLD_CATALOG.items()]
    out += [{"key": k, "label": v["label"], "kind": "reps", "view": v["view"]}
            for k, v in REP_CATALOG.items()]
    return out


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- pure planning & summarizing (testable without camera or voice) --------------------


def choose_plan(available: list[str], history_counts: dict[str, int],
                n: int = 3, seconds: int = DEFAULT_SECONDS,
                reps: int = DEFAULT_REPS) -> list[dict]:
    """Least-practiced first: Chirox calls what the Record says you neglect.

    Deterministic: ties break alphabetically, no randomness to argue with.
    Returns drill dicts: {kind: hold|reps, key, seconds|target}.
    """
    ranked = sorted(available, key=lambda s: (history_counts.get(s, 0), s))
    plan = []
    for key in ranked[:n]:
        if key in REP_CATALOG:
            plan.append({"kind": "reps", "key": key, "target": reps})
        else:
            plan.append({"kind": "hold", "key": key, "seconds": seconds})
    return plan


def drill_summary(samples: list[tuple[float, object]], duration_s: float) -> dict:
    """Aggregate one drill: (elapsed_s, StanceReading) pairs → honest numbers."""
    in_form = out_form = uncertain = 0
    flags: dict[str, int] = {}
    last_t = None
    for t, r in samples:
        dt = (t - last_t) if last_t is not None else 0.0
        last_t = t
        if r.uncertain:
            uncertain += 1
            continue
        if r.flags:
            out_form += 1
            for f in r.flags:
                flags[f] = flags.get(f, 0) + 1
        else:
            in_form += 1
    seen = in_form + out_form
    return {
        "duration_s": round(duration_s, 1),
        "frames_seen": seen,
        "frames_uncertain": uncertain,
        "form_rate": round(in_form / seen, 3) if seen else 0.0,
        "flags": flags,
    }


def spoken_result(stance_label: str, summary: dict) -> str:
    """The honest one-line verdict Chirox speaks after a drill."""
    if not summary["frames_seen"]:
        return f"{stance_label}: I could not see you clearly enough to measure. Nothing is scored."
    pct = int(round(summary["form_rate"] * 100))
    if summary["flags"]:
        worst = max(summary["flags"], key=summary["flags"].get).replace("_", " ")
        return f"{stance_label}: {pct} percent in form. Most frequent fault: {worst}."
    return f"{stance_label}: {pct} percent in form. Clean hold."


def history_counts(codex) -> dict[str, int]:
    """How many sealed sessions exist per stance (vision sessions + drills)."""
    counts: dict[str, int] = {}
    for e in codex.events():
        stance = None
        if e.type == "vision_session":
            stance = e.payload.get("stance")
        elif e.type == "training_call":
            for d in e.payload.get("drills", []):
                s = d.get("stance")
                if s:
                    counts[s] = counts.get(s, 0) + 1
            continue
        if stance:
            counts[stance] = counts.get(stance, 0) + 1
    return counts


# --- the caller ---------------------------------------------------------------------


class Trainer:
    def __init__(self, source=0, speak: bool = True):
        self.source = source
        self.speak_enabled = speak
        self._voice = None

    def _say(self, text: str) -> None:
        print(f"[train] {text}")
        if not self.speak_enabled:
            return
        try:
            from chirox.voice import Voice

            if self._voice is None:
                self._voice = Voice()
            self._voice.speak(text)
        except Exception as exc:
            print(f"[train] (voice unavailable: {exc})")

    def run(self, plan: list[tuple[str, int]], seal: bool = True) -> dict:
        import cv2

        from chirox.narrator import _lock_path
        from chirox.vision.capture import open_capture
        from chirox.vision.pipeline import points_from_landmarks
        from chirox.vision.tracker import PoseTracker

        lock = _lock_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(str(os.getpid()), encoding="utf-8")

        started = _iso_now()
        drills: list[dict] = []
        cap = open_capture(self.source)
        tracker = PoseTracker()
        self._clock_ms = 0
        try:
            self._say(f"Training call. {len(plan)} drills. I measure; I do not flatter.")
            for drill in plan:
                key = drill["key"]
                label = drill_label(key)
                if drill["kind"] == "reps":
                    drills.append(self._run_reps(cap, tracker, key, drill["target"]))
                    continue

                seconds = drill["seconds"]
                evaluator = STANCES[key]
                view = HOLD_CATALOG.get(key, {}).get("view", "front")
                self._say(f"{label}. {seconds} seconds. Begin.")

                samples: list[tuple[float, object]] = []
                last_correction = 0.0
                t0 = time.perf_counter()
                while True:
                    elapsed = time.perf_counter() - t0
                    if elapsed >= seconds + GRACE_S:
                        break
                    ret, frame = cap.read()
                    if not ret:
                        break
                    self._clock_ms += 33
                    lm = tracker.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), self._clock_ms)
                    if lm is None or elapsed < GRACE_S:
                        continue
                    reading = evaluator(points_from_landmarks(lm))
                    samples.append((elapsed, reading))
                    # speak the evaluator's own words, but do not nag
                    if (reading.flags and not reading.uncertain
                            and elapsed - last_correction >= CORRECTION_GAP_S):
                        self._say(reading.assessment)
                        last_correction = time.perf_counter() - t0

                summary = drill_summary(samples, seconds)
                summary["stance"] = key
                drills.append(summary)
                self._say(spoken_result(label, summary))

            payload = {"started": started, "finished": _iso_now(),
                       "source": str(self.source), "drills": drills}
            if seal:
                self._seal(payload)
                self._say("Session sealed into the record. Train again tomorrow.")
            else:
                self._say("Session complete. Not sealed.")
            return payload
        finally:
            cap.release()
            tracker.close()
            lock.unlink(missing_ok=True)

    def _run_reps(self, cap, tracker, key: str, target: int) -> dict:
        """A counted set: he says each rep number as your body completes it."""
        import cv2

        from chirox.vision.pipeline import points_from_landmarks

        spec = REP_CATALOG[key]
        label = spec["label"]
        self._say(f"{label}. {target} repetitions. I count only what I see. Begin.")
        counter = make_counter(key)
        seen = 0
        t0 = time.perf_counter()
        time_cap = GRACE_S + target * 8.0    # slow, controlled reps; no rush
        while time.perf_counter() - t0 < time_cap and counter.count < target:
            ret, frame = cap.read()
            if not ret:
                break
            self._clock_ms += 33
            lm = tracker.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), self._clock_ms)
            if lm is None:
                continue
            seen += 1
            signal = spec["signal"](points_from_landmarks(lm))
            if counter.push(signal):
                self._say(str(counter.count))
        summary = {"kind": "reps", "stance": key, "count": counter.count,
                   "target": target, "frames_with_body": seen,
                   "duration_s": round(time.perf_counter() - t0, 1)}
        if counter.count >= target:
            self._say(f"{target}. Done. Counted, every one.")
        elif seen == 0:
            self._say(f"{label}: I could not see you. Nothing is counted.")
        else:
            self._say(f"Time. {counter.count} of {target} - the honest count.")
        return summary

    @staticmethod
    def _seal(payload: dict):
        from chirox.config import CODEX_PATH, Config
        from chirox.record.codex import Codex
        from chirox.sentinel import Sentinel

        config = Config.load()
        codex = Codex(CODEX_PATH)
        sentinel = Sentinel(codex, config)
        sentinel.init_operator()
        grant = sentinel.authorize("vision.train")
        event = codex.append("training_call", payload)
        sentinel.consume(grant)
        return event


def run_training(source=0, stances: list[str] | None = None,
                 seconds: int = DEFAULT_SECONDS, n: int = 3,
                 reps: int = DEFAULT_REPS,
                 speak: bool = True, seal: bool = True) -> dict:
    """Entry point: Chirox chooses the drills (or takes yours) and calls them.

    ``stances`` accepts any catalog key — stance holds, conditioning holds, or
    counted rep drills (squats, pushups, situps, knee_raises, jumping_jacks).
    """
    if stances:
        plan = []
        for s in stances:
            if s in REP_CATALOG:
                plan.append({"kind": "reps", "key": s, "target": reps})
            elif s in STANCES:
                plan.append({"kind": "hold", "key": s, "seconds": seconds})
            else:
                raise ValueError(
                    f"unknown drill '{s}'. Known: {sorted(set(STANCES) | set(REP_CATALOG))}")
    else:
        from chirox.config import CODEX_PATH
        from chirox.record.codex import Codex

        counts = history_counts(Codex(CODEX_PATH))
        plan = choose_plan(DEFAULT_ROTATION, counts, n=n, seconds=seconds, reps=reps)
    return Trainer(source=source, speak=speak).run(plan, seal=seal)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Chirox calls the training")
    ap.add_argument("--source", default="0", help="camera index")
    ap.add_argument("--stances", default=None,
                    help="comma list of catalog keys, holds or reps (default: Chirox chooses)")
    ap.add_argument("--seconds", type=int, default=DEFAULT_SECONDS, help="seconds per hold")
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS, help="target per rep drill")
    ap.add_argument("--drills", type=int, default=3, help="how many drills when Chirox chooses")
    ap.add_argument("--no-speak", action="store_true")
    ap.add_argument("--no-seal", action="store_true")
    args = ap.parse_args()

    result = run_training(
        source=int(args.source) if str(args.source).isdigit() else args.source,
        stances=args.stances.split(",") if args.stances else None,
        seconds=args.seconds, n=args.drills, reps=args.reps,
        speak=not args.no_speak, seal=not args.no_seal,
    )
    print(json.dumps(result, indent=2))
