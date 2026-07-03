"""Tests for the wireframe accuracy audit — pure summary logic, no camera."""

from chirox.vision.audit import BONES, summarize_audit


def _sample(t, conf, angles, vis):
    return {"t": t, "confidence": conf, "angles": angles, "visibility": vis}


def test_summarize_empty_clip():
    r = summarize_audit([], frames_total=0)
    assert r["frames_total"] == 0
    assert r["frames_with_body"] == 0
    assert r["body_rate"] == 0.0
    assert r["mean_confidence"] == 0.0
    assert r["angles"] == {}


def test_summarize_no_body_frames_counted():
    r = summarize_audit([], frames_total=40)
    assert r["frames_total"] == 40
    assert r["body_rate"] == 0.0


def test_summarize_still_hold_noise_floor():
    # A still hold: knee angle wobbles 94..96 — spread and std are the noise floor.
    samples = [
        _sample(0.0, 0.9, {"left_knee": 95.0}, {"left_knee": 0.9}),
        _sample(0.5, 0.9, {"left_knee": 94.0}, {"left_knee": 0.95}),
        _sample(1.0, 0.9, {"left_knee": 96.0}, {"left_knee": 0.85}),
    ]
    r = summarize_audit(samples, frames_total=3)
    k = r["angles"]["left_knee"]
    assert k["n"] == 3
    assert k["min"] == 94.0
    assert k["max"] == 96.0
    assert k["mean"] == 95.0
    assert k["spread"] == 2.0
    assert 0.9 < k["std"] < 1.1  # sample stddev of {94,95,96} = 1.0
    assert r["body_rate"] == 1.0
    assert r["visibility"]["left_knee"]["min"] == 0.85


def test_summarize_partial_body_rate_and_confidence():
    samples = [
        _sample(0.0, 0.8, {"right_knee": 100.0}, {"right_knee": 0.8}),
        _sample(1.0, 0.6, {"right_knee": 120.0}, {"right_knee": 0.6}),
    ]
    r = summarize_audit(samples, frames_total=8)
    assert r["frames_with_body"] == 2
    assert r["body_rate"] == 0.25
    assert r["mean_confidence"] == 0.7
    assert r["angles"]["right_knee"]["spread"] == 20.0


def test_bones_cover_every_measured_joint():
    joints = {j for bone in BONES for j in bone}
    # every joint the audit tracks appears in the wireframe drawing
    from chirox.vision.audit import _MP_INDEX

    assert joints == set(_MP_INDEX.values())
