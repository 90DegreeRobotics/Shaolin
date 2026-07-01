"""Pose tracking via the MediaPipe **Tasks** API (PoseLandmarker).

The legacy ``mediapipe.solutions.pose`` API was removed in the installed mediapipe
(0.10.31), so Chirox uses the current Tasks API. Same 33-landmark BlazePose
topology, so all of ``stances.py`` geometry is unchanged — only detector setup
differs. The model is a single ``.task`` file downloaded once and kept locally
(sovereign: after the one-time fetch, tracking is fully offline).

This module is imported only when a live/video session actually runs, so the pure
geometry and the rest of the package stay importable without mediapipe/opencv.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)


def default_model_path() -> Path:
    from chirox.config import MODEL_DIR

    return MODEL_DIR / "pose_landmarker.task"


def ensure_model(path: Path | None = None) -> Path:
    """Return a local path to the pose model, downloading it once if missing."""
    path = Path(path) if path else default_model_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading pose model (once) → {path} …")
        urllib.request.urlretrieve(POSE_MODEL_URL, path)
    return path


class PoseTracker:
    """VIDEO-mode PoseLandmarker. ``detect`` returns the first pose's 33 landmarks
    (objects with ``.x``, ``.y``, ``.z``, ``.visibility``) or None.

    detect_for_video requires strictly increasing timestamps; the tracker enforces
    that internally so callers can pass a best-effort millisecond clock.
    """

    def __init__(self, model_path=None, num_poses: int = 1):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        self._mp = mp
        model = ensure_model(model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=num_poses,
        )
        self._detector = vision.PoseLandmarker.create_from_options(options)
        self._last_ts = -1

    def detect(self, rgb, timestamp_ms: int):
        mp = self._mp
        ts = int(timestamp_ms)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.detect_for_video(image, ts)
        return result.pose_landmarks[0] if result.pose_landmarks else None

    def close(self) -> None:
        self._detector.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def draw_points(bgr, pts: dict, min_visibility: float = 0.5):
    """Minimal landmark overlay (Tasks API has no solutions drawing helper)."""
    import cv2

    h, w = bgr.shape[:2]
    for (x, y, v) in pts.values():
        if v >= min_visibility:
            cv2.circle(bgr, (int(x * w), int(y * h)), 4, (0, 255, 0), -1)
    return bgr
