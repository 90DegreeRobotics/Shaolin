"""The recorder documents and measures, never grades. Prove the motion summary,
that video actually writes to a file, and that manifests seal in order."""

import numpy as np
import pytest

from chirox.config import Config
from chirox.record.codex import Codex
from chirox.record.ingest import commit_record
from chirox.sentinel import Sentinel
from chirox.vision import recorder
from chirox.vision.stances import LEFT_ELBOW, LEFT_SHOULDER, LEFT_WRIST, general_joint_angles


def seal_setup(tmp_path):
    cx = Codex(tmp_path / "r.jsonl")
    s = Sentinel(cx, Config(sentinel_mode="enforce"), key_path=tmp_path / "op.key")
    s.init_operator()
    return cx, s


# --- measurement, not a grade --------------------------------------------------


def test_general_joint_angles_measure_not_grade():
    pts = {LEFT_SHOULDER: (0, 0, 1.0), LEFT_ELBOW: (0, 1, 1.0), LEFT_WRIST: (1, 1, 1.0)}
    assert round(general_joint_angles(pts)["left_elbow"]) == 90
    # Low-visibility joints are omitted rather than reported as fact.
    faint = {k: (x, y, 0.2) for k, (x, y, _) in pts.items()}
    assert general_joint_angles(faint) == {}


def test_build_recording_summarizes_range_of_motion():
    samples = [
        {"confidence": 0.9, "angles": {"left_elbow": 90, "right_elbow": 100}},
        {"confidence": 0.8, "angles": {"left_elbow": 170, "right_elbow": 160}},
    ]
    rec = recorder.build_recording("eight_brocades", "2026-07-01", 3, "0", "/x/v.mp4",
                                   frames_total=2, duration_s=4.0, samples=samples)
    assert rec.frames_with_body == 2
    assert rec.motion["left_elbow"] == {"min": 90.0, "mean": 130.0, "max": 170.0}
    assert rec.mean_confidence == 0.85
    assert rec.RECORD_TYPE == "session_recording"


def test_build_recording_notes_when_no_body_seen():
    rec = recorder.build_recording("x", "2026-07-01", 3, "0", "/x/v.mp4",
                                   frames_total=10, duration_s=5.0, samples=[])
    assert rec.frames_with_body == 0
    assert any("No body" in n for n in rec.notes)


# --- the manifest seals into the append-only record ----------------------------


def test_recording_manifest_seals_and_verifies(tmp_path):
    cx, s = seal_setup(tmp_path)
    rec = recorder.build_recording("eight_brocades", "2026-07-01", 3, "0", "/x/v.mp4",
                                   5, 3.0, samples=[{"confidence": 0.9, "angles": {"left_elbow": 90}}])
    ev = commit_record(rec, cx, s)
    assert ev.type == "session_recording"
    assert cx.verify()[0]


def test_timeline_is_ordered_oldest_first(tmp_path):
    cx, s = seal_setup(tmp_path)
    for day in (3, 5):
        rec = recorder.build_recording("eight_brocades", f"2026-07-0{day}", day, "0",
                                       f"/x/v{day}.mp4", 5, 3.0, samples=[{"confidence": 0.9, "angles": {}}])
        commit_record(rec, cx, s)
    days = [e.payload["day_number"] for e in cx.events("session_recording")]
    assert days == [3, 5]


# --- video actually writes to a file (no camera needed) ------------------------


def test_video_writer_produces_a_real_file(tmp_path):
    cv2 = pytest.importorskip("cv2")
    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 20, (64, 48))
    if not writer.isOpened():
        pytest.skip("mp4v codec unavailable in this OpenCV build")
    for _ in range(10):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    assert path.exists() and path.stat().st_size > 0


def test_live_tee_recorder_writes_without_owning_camera(tmp_path, monkeypatch):
    pytest.importorskip("cv2")
    monkeypatch.setattr(recorder, "_video_path",
                        lambda exercise, day, date_str: tmp_path / f"{exercise}.mp4")
    tee = recorder.LiveTeeRecorder("crane_hold", "0", seconds=0.01, stance=None, fps_fallback=10)
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    assert tee.push(frame, None, 0.0) == "ok"
    # Force time-up on the next frame.
    tee._t0 = 0.0
    assert tee.push(frame, None, 1.0) == "time_up"
    rec = tee.finalize(seal=False)
    assert rec is not None
    assert rec.frames == 2
    assert (tmp_path / "crane_hold.mp4").exists()
