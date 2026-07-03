"""Session recorder — the visual timeline.

Records a training video to the private media archive, tracks raw range-of-motion
(measurement, not a form grade), and seals a manifest into the append-only Codex
so the timeline is a permanent, ordered record from day one — embarrassing early
attempts included. That is the point: the mirror does not flatter, and it does not
forget.

For flowing sequences like the Eight Brocades there is no pass/fail — Chirox
documents and measures; the eye and a qualified teacher judge the form. For a
static hold you may also pass ``--stance`` to get the deterministic stance summary
alongside the recording.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from pathlib import Path

from chirox.vision.schema import SessionAccumulator, SessionRecording
from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST,
    STANCES, general_joint_angles,
)

# MediaPipe indices -> joint names, including arms for flowing sequences.
_MP_INDEX = {
    11: LEFT_SHOULDER, 12: RIGHT_SHOULDER, 13: LEFT_ELBOW, 14: RIGHT_ELBOW,
    15: LEFT_WRIST, 16: RIGHT_WRIST, 23: LEFT_HIP, 24: RIGHT_HIP,
    25: LEFT_KNEE, 26: RIGHT_KNEE, 27: LEFT_ANKLE, 28: RIGHT_ANKLE,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def points_from_landmarks(landmarks) -> dict:
    return {name: (landmarks[i].x, landmarks[i].y, landmarks[i].visibility) for i, name in _MP_INDEX.items()}


def build_recording(exercise, date_str, day_number, source, video_path, frames_total,
                    duration_s, samples, stance_summary=None) -> SessionRecording:
    """Pure summary of a recorded session — testable without a camera.

    ``samples`` is one dict per body-detected frame: {"confidence": float,
    "angles": {joint: degrees}}.
    """
    angle_values: dict[str, list[float]] = {}
    for s in samples:
        for name, v in s["angles"].items():
            angle_values.setdefault(name, []).append(v)
    motion = {
        name: {"min": round(min(vs), 1), "mean": round(sum(vs) / len(vs), 1), "max": round(max(vs), 1)}
        for name, vs in angle_values.items()
    }
    frames_with_body = len(samples)
    mean_conf = round(sum(s["confidence"] for s in samples) / frames_with_body, 3) if frames_with_body else 0.0

    notes: list[str] = []
    if frames_total and frames_with_body / frames_total < 0.5:
        notes.append(f"Only {frames_with_body}/{frames_total} frames saw a body — check framing and lighting.")
    if 0 < mean_conf < 0.6:
        notes.append("Low landmark confidence; the motion numbers are weak evidence. The video is still the record.")
    if frames_with_body == 0:
        notes.append("No body detected — only raw video was saved.")

    return SessionRecording(
        exercise=exercise, date=date_str, day_number=day_number, source=str(source),
        video_path=str(video_path), duration_s=round(duration_s, 2), frames=frames_total,
        frames_with_body=frames_with_body, mean_confidence=mean_conf, motion=motion,
        stance_summary=stance_summary, notes=notes,
    )


def seal_recording(recording: SessionRecording, config=None):
    """Seal the recording manifest (not the video) into the Codex, via the Sentinel."""
    from chirox.config import CODEX_PATH, Config
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    config = config or Config.load()
    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize(f"vision.record:{recording.exercise}")
    event = codex.append(recording.RECORD_TYPE, recording.payload())
    sentinel.consume(grant)
    return event


def _video_path(exercise: str, day_number: int, date_str: str) -> Path:
    from chirox.config import MEDIA_DIR

    stamp = datetime.now().strftime("%H%M%S")
    folder = MEDIA_DIR / exercise
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"day{day_number:03d}_{date_str}_{stamp}.mp4"


def record_session(exercise: str, source=0, seconds: float | None = None, stance: str | None = None,
                   show: bool = True, seal: bool = True, fps_fallback: int = 20) -> SessionRecording:
    """Record a session to the archive and seal its manifest. Camera integration
    step — needs a real source; the summary/seal logic is unit-tested separately."""
    import cv2

    from chirox.calendar import dojo_day
    from chirox.config import Config
    from chirox.vision.capture import open_capture
    from chirox.vision.tracker import PoseTracker, draw_points

    if stance is not None and stance not in STANCES:
        raise ValueError(f"unknown stance '{stance}'. Known: {sorted(STANCES)}")

    config = Config.load()
    d = dojo_day(config.practice_start_date)
    date_str = date.today().isoformat()
    out_path = _video_path(exercise, d.day_number, date_str)

    cap = open_capture(source)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS) or fps_fallback
    if fps <= 0:
        fps = fps_fallback
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    tracker = PoseTracker()
    acc = SessionAccumulator(stance, str(source)) if stance else None
    samples: list[dict] = []
    frames_total = 0
    t0 = time.perf_counter()
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames_total += 1
            writer.write(frame)  # the raw record is saved regardless of tracking

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            lm = tracker.detect(rgb, int((time.perf_counter() - t0) * 1000))
            if lm:
                pts = points_from_landmarks(lm)
                angles = general_joint_angles(pts)
                conf = sum(p[2] for p in pts.values()) / len(pts)
                samples.append({"confidence": conf, "angles": angles})
                if acc is not None:
                    acc.add(time.perf_counter() - t0, STANCES[stance](pts))
                if show:
                    disp = frame.copy()
                    draw_points(disp, pts)
                    cv2.putText(disp, f"REC {exercise} day{d.day_number}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.imshow("Chirox Recorder", disp)
            if show and (cv2.waitKey(5) & 0xFF == ord("q")):
                break
            if seconds is not None and (time.perf_counter() - t0) >= seconds:
                break
    finally:
        duration = time.perf_counter() - t0
        cap.release()
        writer.release()
        if show:
            cv2.destroyAllWindows()
        tracker.close()

    stance_summary = acc.finalize(_iso_now(), _iso_now()).payload() if acc else None
    recording = build_recording(exercise, date_str, d.day_number, source, out_path,
                                frames_total, duration, samples, stance_summary)
    if seal:
        seal_recording(recording, config)
    return recording
