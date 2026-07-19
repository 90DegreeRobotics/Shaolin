"""Reproduction verifier — scores the body against chart holds. Pure geometry."""

from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST,
)
from chirox.vision.verify import MatchSession, match_hold, rank_holds, verify_frame


def _horse_ish():
    """Deep knees (90 deg), upright trunk — should score horse strongly."""
    return {
        LEFT_SHOULDER: (0.35, 0.15, 1.0), RIGHT_SHOULDER: (0.65, 0.15, 1.0),
        LEFT_ELBOW: (0.30, 0.30, 1.0), RIGHT_ELBOW: (0.70, 0.30, 1.0),
        LEFT_WRIST: (0.30, 0.45, 1.0), RIGHT_WRIST: (0.70, 0.45, 1.0),
        LEFT_HIP: (0.40, 0.40, 1.0), RIGHT_HIP: (0.60, 0.40, 1.0),
        LEFT_KNEE: (0.40, 0.70, 1.0), RIGHT_KNEE: (0.60, 0.70, 1.0),
        LEFT_ANKLE: (0.20, 0.70, 1.0), RIGHT_ANKLE: (0.80, 0.70, 1.0),
    }


def test_match_hold_scores_even_when_flags_present():
    tall = _horse_ish()
    # Stand tall — horse should be OUT of band but still scored (not silent).
    tall[LEFT_KNEE] = (0.38, 0.62, 1.0)
    tall[RIGHT_KNEE] = (0.62, 0.62, 1.0)
    tall[LEFT_ANKLE] = (0.38, 0.95, 1.0)
    tall[RIGHT_ANKLE] = (0.62, 0.95, 1.0)
    m = match_hold(tall, "horse")
    assert m["uncertain"] is False
    assert m["score"] is not None
    assert 0 <= m["score"] <= 100


def test_match_hold_uncertain_when_joints_invisible():
    blank = {k: (0.5, 0.5, 0.1) for k in _horse_ish()}
    m = match_hold(blank, "horse")
    assert m["uncertain"] is True
    assert m["score"] is None
    assert m["in_band"] is False


def test_verify_frame_auto_returns_closest_target():
    v = verify_frame(_horse_ish(), None)
    assert v["auto"] is True
    assert v["target"] is not None
    assert v["target"]["score"] is not None
    assert v["target"]["key"] in {"horse", "horse_guard", "parallel_ready", "squat_hold", "half_squat"}


def test_rank_holds_orders_by_score():
    ranked = rank_holds(_horse_ish())
    assert ranked
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_match_session_accumulates_in_band_time():
    sess = MatchSession(auto=True)
    v = verify_frame(_horse_ish(), "horse")
    for _ in range(10):
        sess.push(v)
    st = sess.status()
    assert st["frames"] == 10
    assert st["mean_score"] is not None
    assert st["last"] is not None
