"""Light checks for the pose tracker wrapper (offline — no download, no camera)."""

import numpy as np

from chirox.vision.pipeline import points_from_landmarks
from chirox.vision import tracker
from chirox.vision.stances import LEFT_ELBOW, LEFT_WRIST, RIGHT_ELBOW, RIGHT_WRIST


def test_default_model_path_name():
    assert tracker.default_model_path().name == "pose_landmarker.task"


def test_ensure_model_returns_existing_without_downloading(tmp_path):
    f = tmp_path / "m.task"
    f.write_bytes(b"not really a model")
    assert tracker.ensure_model(f) == f  # present -> returned as-is, no network


def test_draw_points_overlays_without_error():
    img = np.zeros((48, 64, 3), np.uint8)
    out = tracker.draw_points(img, {"seen": (0.5, 0.5, 0.9), "faint": (0.1, 0.1, 0.2)})
    assert out.shape == (48, 64, 3)


def test_points_from_landmarks_includes_arm_joints():
    class Lm:
        x = 0.1
        y = 0.2
        visibility = 0.9

    pts = points_from_landmarks([Lm() for _ in range(33)])
    assert {LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST} <= set(pts)
