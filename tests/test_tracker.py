"""Light checks for the pose tracker wrapper (offline — no download, no camera)."""

import numpy as np

from chirox.vision import tracker


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
