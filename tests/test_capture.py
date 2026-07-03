import pytest

from chirox.vision.capture import (
    DEFAULT_HEIGHT, DEFAULT_WIDTH, WIDEST_ZOOM,
    normalize_source, open_capture, preferred_backend,
)


def test_normalize_source_digit_string_is_device_index():
    assert normalize_source("0") == 0
    assert normalize_source(2) == 2


def test_normalize_source_path_stays_a_path():
    assert normalize_source("clip.mp4") == "clip.mp4"
    assert normalize_source("Dojo/media/day001.mp4") == "Dojo/media/day001.mp4"


def test_open_capture_missing_file_fails_closed(tmp_path):
    missing = tmp_path / "no_such_clip.mp4"
    with pytest.raises(RuntimeError, match="could not open video source"):
        open_capture(str(missing))


def test_backend_dshow_only_for_the_pathological_device():
    # Source 1 (the generic HD cam) needs DirectShow: Media Foundation takes
    # ~40s to open it (measured 2026-07-03). The C920s stay on the default
    # backend, which gives them 30fps vs DSHOW's 10.
    assert preferred_backend(1) == "dshow"
    assert preferred_backend("1") == "dshow"
    assert preferred_backend(0) == "default"
    assert preferred_backend(2) == "default"


def test_backend_files_always_default():
    assert preferred_backend("clip.mp4") == "default"


def test_wide_view_defaults_are_full_sensor_16_9():
    # The point of the shared gate: 16:9 (full C920 sensor width) and no digital zoom.
    assert (DEFAULT_WIDTH, DEFAULT_HEIGHT) == (1280, 720)
    assert DEFAULT_WIDTH * 9 == DEFAULT_HEIGHT * 16
    assert WIDEST_ZOOM == 100
