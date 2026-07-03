"""The live/video Reflex runner.

This is the only vision module that touches the camera. It maps MediaPipe pose
landmarks onto the named points the pure ``stances`` geometry expects, evaluates
each frame deterministically, accumulates a session, and can seal the
deterministic summary into the Codex through the Sentinel.

Source may be a webcam index (``0``) or a video file path — so the same code path
is usable with a fixture clip, not only live hardware.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from chirox.vision.schema import SessionAccumulator, VisionSession
from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER,
    RIGHT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER,
    STANCES,
)

# MediaPipe BlazePose landmark indices -> Chirox joint names.
_MP_INDEX = {
    11: LEFT_SHOULDER, 12: RIGHT_SHOULDER,
    23: LEFT_HIP, 24: RIGHT_HIP,
    25: LEFT_KNEE, 26: RIGHT_KNEE,
    27: LEFT_ANKLE, 28: RIGHT_ANKLE,
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def points_from_landmarks(landmarks) -> dict:
    """Extract the named 2D points (with visibility) the geometry needs."""
    pts = {}
    for idx, name in _MP_INDEX.items():
        lm = landmarks[idx]
        pts[name] = (lm.x, lm.y, lm.visibility)
    return pts


class DojoVision:
    def __init__(self, source=0, stance: str = "horse", model_complexity: int = 1, show: bool = True):
        if stance not in STANCES:
            raise ValueError(f"unknown stance '{stance}'. Known: {sorted(STANCES)}")
        self.source = int(source) if str(source).isdigit() else str(source)
        self.stance = stance
        self.evaluator = STANCES[stance]
        self.model_complexity = model_complexity
        self.show = show

    def run(self, seconds: float | None = None) -> VisionSession:
        import cv2  # imported here so pure geometry stays importable without opencv

        from chirox.vision.capture import open_capture
        from chirox.vision.tracker import PoseTracker, draw_points

        cap = open_capture(self.source)
        tracker = PoseTracker()

        acc = SessionAccumulator(self.stance, str(self.source))
        started_ts = _iso_now()
        t0 = time.perf_counter()
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break  # end of video file, or dropped webcam frame
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                lm = tracker.detect(rgb, int((time.perf_counter() - t0) * 1000))

                if lm:
                    pts = points_from_landmarks(lm)
                    reading = self.evaluator(pts)
                    acc.add(time.perf_counter() - t0, reading)

                    if self.show:
                        disp = frame.copy()
                        draw_points(disp, pts)
                        y = 30
                        for k, v in reading.metrics.items():
                            cv2.putText(disp, f"{k}: {v}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            y += 26
                        cv2.putText(disp, reading.assessment[:60], (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                        cv2.imshow("Chirox Reflex (Chan Wu Yi)", disp)

                if self.show and (cv2.waitKey(5) & 0xFF == ord("q")):
                    break
                if seconds is not None and (time.perf_counter() - t0) >= seconds:
                    break
        finally:
            cap.release()
            if self.show:
                cv2.destroyAllWindows()
            tracker.close()

        return acc.finalize(started_ts, _iso_now())


def seal_session(session: VisionSession, config=None):
    """Seal a deterministic vision summary into the Codex, through the Sentinel."""
    from chirox.config import CODEX_PATH, Config
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    config = config or Config.load()
    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize(f"vision.append:{session.stance}")
    event = codex.append(session.RECORD_TYPE, session.payload())
    sentinel.consume(grant)
    return event


def run_session(source=0, stance: str = "horse", seconds: float | None = None,
                show: bool = True, seal: bool = False) -> VisionSession:
    """Run one reflex session; optionally seal the deterministic summary to the Codex."""
    session = DojoVision(source=source, stance=stance, show=show).run(seconds=seconds)
    if seal:
        seal_session(session)
    return session


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Chirox deterministic reflex runner")
    ap.add_argument("--source", default="0", help="webcam index (e.g. 0) or a video file path")
    ap.add_argument("--stance", default="horse", choices=sorted(STANCES))
    ap.add_argument("--seconds", type=float, default=None, help="stop after N seconds")
    ap.add_argument("--no-show", action="store_true", help="run headless (no window)")
    args = ap.parse_args()

    sess = DojoVision(source=args.source, stance=args.stance, show=not args.no_show).run(seconds=args.seconds)
    import json

    print(json.dumps(sess.payload(), indent=2))
