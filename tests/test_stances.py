"""The reflex is deterministic — prove the geometry, the uncertainty gate, the
session aggregation, and multi-camera fusion, all without a camera."""

from chirox.vision import multicam
from chirox.vision.schema import SessionAccumulator
from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER,
    RIGHT_ANKLE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER,
    angle, evaluate_bow_stance, evaluate_horse_stance,
)


def horse_points(l_ankle, r_ankle, l_shoulder=(0, -1, 1.0), r_shoulder=(0, -1, 1.0), vis=1.0):
    return {
        LEFT_SHOULDER: l_shoulder, LEFT_HIP: (0, 0, vis), LEFT_KNEE: (0, 1, vis), LEFT_ANKLE: l_ankle,
        RIGHT_SHOULDER: r_shoulder, RIGHT_HIP: (0, 0, vis), RIGHT_KNEE: (0, 1, vis), RIGHT_ANKLE: r_ankle,
    }


# --- geometry ------------------------------------------------------------------


def test_angle_is_ninety_degrees():
    assert round(angle((0, -1, 1), (0, 0, 1), (1, 0, 1))) == 90


def test_ideal_horse_stance_is_rooted():
    pts = horse_points((1, 1, 1.0), (1, 1, 1.0))  # knees 90, spine straight
    r = evaluate_horse_stance(pts)
    assert not r.uncertain
    assert r.flags == []
    assert r.assessment == "Stable and rooted."
    assert round(r.metrics["left_knee_angle"]) == 90


def test_stance_too_high_is_flagged():
    pts = horse_points((0, 2, 1.0), (0, 2, 1.0))  # knees straightened -> 180
    r = evaluate_horse_stance(pts)
    assert "stance_too_high" in r.flags
    assert "too high" in r.assessment.lower()


def test_slouch_is_flagged():
    pts = horse_points((1, 1, 1.0), (1, 1, 1.0), l_shoulder=(1, -1, 1.0), r_shoulder=(1, -1, 1.0))
    r = evaluate_horse_stance(pts)
    assert "spine_slouching" in r.flags


def test_low_visibility_yields_uncertain_not_a_verdict():
    pts = horse_points((1, 1, 0.2), (1, 1, 0.2), vis=0.2)
    r = evaluate_horse_stance(pts)
    assert r.uncertain is True
    assert r.metrics == {}
    assert "UNCERTAIN" in r.assessment


def test_bow_stance_grounded():
    pts = {
        LEFT_HIP: (0, 0, 1), LEFT_KNEE: (0, 1, 1), LEFT_ANKLE: (1, 1, 1),   # front knee 90
        RIGHT_HIP: (0, 0, 1), RIGHT_KNEE: (0, 1, 1), RIGHT_ANKLE: (0, 2, 1),  # rear straight
    }
    r = evaluate_bow_stance(pts, front="left")
    assert not r.uncertain
    assert r.flags == []
    assert "grounded" in r.assessment.lower()


# --- session aggregation -------------------------------------------------------


def test_session_accumulator_summarizes_and_keeps_uncertainty():
    clean = evaluate_horse_stance(horse_points((1, 1, 1.0), (1, 1, 1.0)))
    high = evaluate_horse_stance(horse_points((0, 2, 1.0), (0, 2, 1.0)))
    unsure = evaluate_horse_stance(horse_points((1, 1, 0.2), (1, 1, 0.2), vis=0.2))

    acc = SessionAccumulator("horse", "fixture")
    acc.add(0.0, clean)
    acc.add(1.0, high)
    acc.add(2.0, unsure)
    s = acc.finalize("t0", "t1")

    assert s.frames_evaluated == 3
    assert s.frames_uncertain == 1
    assert s.duration_s == 2.0
    assert s.flags_observed.get("stance_too_high") == 1
    # readable=2 (clean+high), clean=1 -> half the time in tolerance
    assert s.time_in_tolerance_s == 1.0
    assert any("UNCERTAIN" in n for n in s.notes)


# --- multi-camera fusion -------------------------------------------------------


def test_fusion_prefers_front_for_knees_and_side_for_spine():
    front = evaluate_horse_stance(horse_points((1, 1, 1.0), (1, 1, 1.0)))
    side = evaluate_horse_stance(
        horse_points((1, 1, 1.0), (1, 1, 1.0), l_shoulder=(1, -1, 1.0), r_shoulder=(1, -1, 1.0))
    )  # side view sees the slouch
    fused = multicam.fuse({multicam.FRONT: front, multicam.SIDE: side})
    assert fused.roles_present == ["front", "side"]
    assert fused.metrics["left_knee_angle"]["source"] == "front"
    assert fused.metrics["left_back_angle"]["source"] == "side"
    assert any(f.startswith("spine_slouching@side") for f in fused.flags)


def test_single_camera_names_its_blind_spot():
    front = evaluate_horse_stance(horse_points((1, 1, 1.0), (1, 1, 1.0)))
    fused = multicam.fuse({multicam.FRONT: front})
    assert fused.roles_present == ["front"]
    assert any("side camera" in lim.lower() for lim in fused.limitations)


def test_default_rig_registry():
    reg = multicam.CameraRegistry.default_rig()
    assert reg.by_role("front").source == 0
    assert set(reg.sources()) == {"front", "side"}
