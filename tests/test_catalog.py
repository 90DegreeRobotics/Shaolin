"""The full drill catalog — template engine, rep counting, coverage. Pure."""

from chirox.trainer import DEFAULT_ROTATION, choose_plan, full_catalog
from chirox.vision.reps import (
    REP_CATALOG, RepCounter, jack_signal, knee_raise_signal, squat_signal,
)
from chirox.vision.stances import (
    HOLD_CATALOG, LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    POSE_TEMPLATES, RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER,
    RIGHT_WRIST, STANCES, evaluate_template,
)


# --- coverage: this is a year of training, not three poses -----------------------------


def test_catalog_is_a_real_training_catalog():
    holds = set(HOLD_CATALOG)
    assert {"horse", "bow", "crane", "one_leg_stand", "drop_stance", "t_stance",
            "parallel_ready", "meditation_stance", "empty_stance", "plank",
            "wall_sit", "squat_hold", "hollow_hold", "glute_bridge",
            "leg_raise_hold", "arms_raised", "wuji_standing", "horse_guard",
            "seated_meditation"} <= holds
    assert {"squats", "pushups", "situps", "knee_raises", "jumping_jacks"} == set(REP_CATALOG)
    assert len(full_catalog()) >= 24


def test_every_hold_has_an_evaluator():
    for key in HOLD_CATALOG:
        assert key in STANCES, key
        assert callable(STANCES[key])


def test_every_template_rule_has_a_message():
    for t in POSE_TEMPLATES:
        for rules in (t.angle_rules, t.above_rules, t.tilt_rules, t.asym_rules):
            for r in rules:
                assert r.message, f"{t.key}: rule {r.flag} has no spoken message"


# --- template engine on synthetic bodies -------------------------------------------------


def _standing(vis=1.0, knee_bend=0.0, wrists_y=0.55):
    """A simple front-view standing figure. y grows downward."""
    return {
        LEFT_SHOULDER: (0.4, 0.0, vis), RIGHT_SHOULDER: (0.6, 0.0, vis),
        LEFT_ELBOW: (0.35, 0.3, vis), RIGHT_ELBOW: (0.65, 0.3, vis),
        LEFT_WRIST: (0.35, wrists_y, vis), RIGHT_WRIST: (0.65, wrists_y, vis),
        LEFT_HIP: (0.45, 0.5, vis), RIGHT_HIP: (0.55, 0.5, vis),
        LEFT_KNEE: (0.45 + knee_bend, 1.0, vis), RIGHT_KNEE: (0.55 - knee_bend, 1.0, vis),
        LEFT_ANKLE: (0.45, 1.5, vis), RIGHT_ANKLE: (0.55, 1.5, vis),
    }


def _template(key):
    return next(t for t in POSE_TEMPLATES if t.key == key)


def test_wuji_standing_clean():
    r = evaluate_template(_template("wuji_standing"), _standing())
    assert not r.uncertain
    assert r.flags == []
    assert "held" in r.assessment


def test_wuji_flags_raised_hands():
    r = evaluate_template(_template("wuji_standing"), _standing(wrists_y=0.1))
    assert "hands_raised" in r.flags


def test_meditation_stance_flags_bent_knees():
    r = evaluate_template(_template("meditation_stance"), _standing(knee_bend=0.25))
    assert "knees_bent" in r.flags


def test_arms_raised_wants_hands_above_head():
    r = evaluate_template(_template("arms_raised"), _standing(wrists_y=0.55))
    assert "arms_low" in r.flags
    up = _standing(wrists_y=-0.5)
    r2 = evaluate_template(_template("arms_raised"), up)
    assert "arms_low" not in r2.flags


def test_plank_side_view():
    vis = 1.0
    flat = {  # horizontal body, left side visible
        LEFT_SHOULDER: (0.1, 0.5, vis), LEFT_HIP: (0.5, 0.52, vis),
        LEFT_ANKLE: (0.9, 0.54, vis),
        RIGHT_SHOULDER: (0.1, 0.5, 0.1), RIGHT_HIP: (0.5, 0.52, 0.1), RIGHT_ANKLE: (0.9, 0.54, 0.1),
    }
    r = evaluate_template(_template("plank"), flat)
    assert not r.uncertain
    assert r.flags == []
    sagging = dict(flat)
    sagging[LEFT_HIP] = (0.5, 0.75, vis)   # hips dropped
    r2 = evaluate_template(_template("plank"), sagging)
    assert "hips_broken" in r2.flags


def test_template_uncertain_gate_holds():
    r = evaluate_template(_template("wuji_standing"), _standing(vis=0.2))
    assert r.uncertain
    assert r.metrics == {}


def test_missing_required_joints_returns_uncertain_not_error():
    pts = _standing()
    del pts[LEFT_ELBOW]
    del pts[RIGHT_ELBOW]
    del pts[LEFT_WRIST]
    del pts[RIGHT_WRIST]
    r = evaluate_template(_template("arms_raised"), pts)
    assert r.uncertain
    assert r.metrics == {}
    assert "low_visibility" in r.flags


# --- rep counting -------------------------------------------------------------------------


def test_rep_counter_counts_full_cycles_only():
    c = RepCounter(115, 158)
    for v in [170, 160, 120, 118, 116]:      # descending but never below 115
        assert not c.push(v)
    assert c.count == 0
    c.push(110)                               # down
    assert c.count == 0
    assert c.push(165)                        # up -> one rep
    assert c.count == 1
    c.push(150)                               # jitter in the middle: no double count
    assert not c.push(160)
    assert c.count == 1


def test_rep_counter_ignores_unseen_frames():
    c = RepCounter(0.0, 1.0)
    assert not c.push(None)
    c.push(-0.5)
    assert c.push(1.5)
    assert c.count == 1


def test_squat_signal_uses_visible_side():
    pts = {
        LEFT_HIP: (0.5, 0.5, 0.9), LEFT_KNEE: (0.5, 1.0, 0.9), LEFT_ANKLE: (0.5, 1.5, 0.9),
        RIGHT_HIP: (0.5, 0.5, 0.1), RIGHT_KNEE: (0.5, 1.0, 0.1), RIGHT_ANKLE: (0.5, 1.5, 0.1),
    }
    assert round(squat_signal(pts)) == 180


def test_knee_raise_signal_positive_when_knee_above_hip():
    pts = {
        LEFT_HIP: (0.45, 0.5, 1), RIGHT_HIP: (0.55, 0.5, 1),
        LEFT_KNEE: (0.45, 0.3, 1), RIGHT_KNEE: (0.55, 1.0, 1),   # left knee lifted high
        LEFT_ANKLE: (0.45, 1.5, 1), RIGHT_ANKLE: (0.55, 1.5, 1),
    }
    assert knee_raise_signal(pts) > 0


def test_jack_signal_cycles():
    def body(wrist_y):
        return {
            LEFT_SHOULDER: (0.4, 0.0, 1), RIGHT_SHOULDER: (0.6, 0.0, 1),
            LEFT_WRIST: (0.3, wrist_y, 1), RIGHT_WRIST: (0.7, wrist_y, 1),
            LEFT_HIP: (0.45, 0.5, 1), LEFT_ANKLE: (0.45, 1.5, 1),
        }
    down = jack_signal(body(0.6))
    up = jack_signal(body(-0.6))
    assert down < -0.2 and up > 0.45


# --- planning mixes holds and reps ---------------------------------------------------------


def test_choose_plan_mixes_kinds():
    counts = {k: 5 for k in DEFAULT_ROTATION}
    counts["pushups"] = 0
    counts["wall_sit"] = 1
    plan = choose_plan(DEFAULT_ROTATION, counts, n=2, seconds=45, reps=8)
    assert plan[0] == {"kind": "reps", "key": "pushups", "target": 8}
    assert plan[1] == {"kind": "hold", "key": "wall_sit", "seconds": 45}
