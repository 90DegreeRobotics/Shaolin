"""Wireframe accuracy audit — is the mirror telling the truth?

Chirox's deterministic verdicts are only as good as the landmarks underneath
them. This tool makes that verifiable by a human (or reviewing agent) eye:

1. Run the pose tracker over a clip (video file) or a live capture window.
2. Save sampled frames with the full Chirox wireframe and measured angles
   drawn on the real image — so misalignment is *visible*, not hypothetical.
3. Report the numbers: per-angle spread across the clip. For a **still hold**
   the spread IS the measurement noise floor — the practitioner didn't move,
   so every wobble in the number is tracker error. If the noise floor is a
   few degrees, the mirror can measure growth; if it is tens of degrees, it
   cannot, and Chirox must say so instead of pretending.

Output: a folder of annotated PNGs plus ``audit.json``. Nothing is sealed to
the Codex — an audit interrogates the instrument; it is not training evidence.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path

from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST,
    STANCES, general_joint_angles,
)

# Same 12-joint map the recorder uses — the audit draws exactly what Chirox measures.
_MP_INDEX = {
    11: LEFT_SHOULDER, 12: RIGHT_SHOULDER, 13: LEFT_ELBOW, 14: RIGHT_ELBOW,
    15: LEFT_WRIST, 16: RIGHT_WRIST, 23: LEFT_HIP, 24: RIGHT_HIP,
    25: LEFT_KNEE, 26: RIGHT_KNEE, 27: LEFT_ANKLE, 28: RIGHT_ANKLE,
}

# The wireframe: bones between the joints Chirox reasons about.
BONES = [
    (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_HIP, RIGHT_HIP),
    (LEFT_SHOULDER, LEFT_HIP), (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW), (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_HIP, LEFT_KNEE), (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
]

# Where each measured angle is anchored when labelled on the frame.
_ANGLE_ANCHOR = {
    "left_knee": LEFT_KNEE, "right_knee": RIGHT_KNEE,
    "left_elbow": LEFT_ELBOW, "right_elbow": RIGHT_ELBOW,
    "left_shoulder": LEFT_SHOULDER, "right_shoulder": RIGHT_SHOULDER,
}


def points_from_landmarks(landmarks) -> dict:
    return {name: (landmarks[i].x, landmarks[i].y, landmarks[i].visibility) for i, name in _MP_INDEX.items()}


def draw_wireframe(bgr, pts: dict, angles: dict | None = None):
    """Draw the Chirox wireframe on a BGR frame, visibility-aware.

    Solid green above 0.6 visibility (Chirox's certainty gate), amber down to
    0.3, dim red below — so a weak joint *looks* weak in the audit image.
    """
    import cv2

    h, w = bgr.shape[:2]

    def px(name):
        x, y, _ = pts[name]
        return int(x * w), int(y * h)

    def color(v):
        if v >= 0.6:
            return (80, 220, 80)     # confident: green
        if v >= 0.3:
            return (0, 190, 255)     # weak: amber
        return (60, 60, 200)         # unreliable: dim red

    for a, b in BONES:
        if a in pts and b in pts:
            v = min(pts[a][2], pts[b][2])
            cv2.line(bgr, px(a), px(b), color(v), 2, cv2.LINE_AA)
    for name, (x, y, v) in pts.items():
        cv2.circle(bgr, (int(x * w), int(y * h)), 5, color(v), -1, cv2.LINE_AA)
        cv2.circle(bgr, (int(x * w), int(y * h)), 5, (0, 0, 0), 1, cv2.LINE_AA)

    if angles:
        for name, deg in angles.items():
            anchor = _ANGLE_ANCHOR.get(name)
            if anchor in pts:
                x, y = px(anchor)
                cv2.putText(bgr, f"{deg:.0f}", (x + 8, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(bgr, f"{deg:.0f}", (x + 8, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return bgr


def _stddev(vs: list[float]) -> float:
    if len(vs) < 2:
        return 0.0
    m = sum(vs) / len(vs)
    return math.sqrt(sum((v - m) ** 2 for v in vs) / (len(vs) - 1))


def summarize_audit(samples: list[dict], frames_total: int) -> dict:
    """Pure aggregation of per-frame audit samples — testable without a camera.

    Each sample: {"t": s, "confidence": float, "angles": {name: deg},
    "visibility": {joint: v}}. The angle ``spread`` (max-min) and ``std`` are
    the headline numbers: on a still-hold clip they are the noise floor.
    """
    angle_series: dict[str, list[float]] = {}
    vis_series: dict[str, list[float]] = {}
    for s in samples:
        for name, v in s["angles"].items():
            angle_series.setdefault(name, []).append(v)
        for joint, v in s["visibility"].items():
            vis_series.setdefault(joint, []).append(v)

    angles = {
        name: {
            "n": len(vs),
            "min": round(min(vs), 1),
            "mean": round(sum(vs) / len(vs), 1),
            "max": round(max(vs), 1),
            "std": round(_stddev(vs), 2),
            "spread": round(max(vs) - min(vs), 1),
        }
        for name, vs in angle_series.items()
    }
    visibility = {
        joint: {"mean": round(sum(vs) / len(vs), 3), "min": round(min(vs), 3)}
        for joint, vs in vis_series.items()
    }
    frames_with_body = len(samples)
    return {
        "frames_total": frames_total,
        "frames_with_body": frames_with_body,
        "body_rate": round(frames_with_body / frames_total, 3) if frames_total else 0.0,
        "mean_confidence": round(sum(s["confidence"] for s in samples) / frames_with_body, 3)
        if frames_with_body else 0.0,
        "angles": angles,
        "visibility": visibility,
    }


def run_audit(source, seconds: float | None = None, stance: str | None = None,
              n_annotated: int = 12, out_dir: Path | None = None) -> dict:
    """Audit a clip or a live capture window; write annotated frames + audit.json."""
    import cv2

    from chirox.config import MEDIA_DIR
    from chirox.vision.capture import normalize_source, open_capture
    from chirox.vision.tracker import PoseTracker

    if stance is not None and stance not in STANCES:
        raise ValueError(f"unknown stance '{stance}'. Known: {sorted(STANCES)}")

    src = normalize_source(source)
    is_file = isinstance(src, str)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = Path(src).stem if is_file else f"cam{src}"
    out = Path(out_dir) if out_dir else MEDIA_DIR / "audit" / f"{label}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    cap = open_capture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    tracker = PoseTracker()

    samples: list[dict] = []
    stance_flags: dict[str, int] = {}
    stance_uncertain = 0
    frames_total = 0
    # (frame_bgr, pts, angles, t) for evenly-spaced annotation at the end
    kept: list[tuple] = []
    t0 = time.perf_counter()
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames_total += 1
            t = (frames_total / fps) if (is_file and fps > 0) else (time.perf_counter() - t0)
            lm = tracker.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), int(t * 1000))
            if lm:
                pts = points_from_landmarks(lm)
                angles = general_joint_angles(pts)
                samples.append({
                    "t": round(t, 2),
                    "confidence": round(sum(p[2] for p in pts.values()) / len(pts), 3),
                    "angles": angles,
                    "visibility": {j: round(p[2], 3) for j, p in pts.items()},
                })
                if stance:
                    reading = STANCES[stance](pts)
                    if reading.uncertain:
                        stance_uncertain += 1
                    for f in reading.flags:
                        stance_flags[f] = stance_flags.get(f, 0) + 1
                kept.append((frame, pts, angles, t))
            else:
                kept.append((frame, None, None, t))
            if not is_file and seconds is not None and (time.perf_counter() - t0) >= seconds:
                break
    finally:
        cap.release()
        tracker.close()

    # Annotate evenly-spaced frames across the whole clip — truth as sampled,
    # including any no-body stretches.
    n = min(n_annotated, len(kept))
    written = []
    if n:
        step = len(kept) / n
        for k in range(n):
            frame, pts, angles, t = kept[int(k * step)]
            disp = frame.copy()
            if pts:
                draw_wireframe(disp, pts, angles)
                state = "MEASURED" if min(p[2] for p in pts.values()) >= 0.6 else "WEAK JOINTS"
            else:
                state = "NO BODY"
            cv2.putText(disp, f"t={t:.1f}s  {state}", (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(disp, f"t={t:.1f}s  {state}", (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            name = f"frame_{k:02d}_t{t:05.1f}s.png"
            cv2.imwrite(str(out / name), disp)
            written.append(name)

    report = summarize_audit(samples, frames_total)
    report.update({
        "source": str(source),
        "fps": round(fps, 1),
        "out_dir": str(out),
        "annotated_frames": written,
    })
    if stance:
        report["stance"] = {
            "name": stance,
            "uncertain_frames": stance_uncertain,
            "flag_counts": stance_flags,
        }
    (out / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Chirox wireframe accuracy audit")
    ap.add_argument("--source", default="0", help="video file path, or webcam index for a live grab")
    ap.add_argument("--seconds", type=float, default=None, help="live capture length (ignored for files)")
    ap.add_argument("--stance", default=None, choices=sorted(STANCES), help="also evaluate a stance per frame")
    ap.add_argument("--frames", type=int, default=12, help="how many annotated frames to write")
    ap.add_argument("--out", default=None, help="output directory (default: Dojo/media/audit/<name>_<stamp>)")
    args = ap.parse_args()

    r = run_audit(args.source, seconds=args.seconds, stance=args.stance,
                  n_annotated=args.frames, out_dir=Path(args.out) if args.out else None)
    print(json.dumps(r, indent=2))
