"""Trainer + crane stance + speech scrub — all pure, no camera, no audio."""

from chirox.trainer import choose_plan, drill_summary, spoken_result
from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_HIP, LEFT_KNEE,
    RIGHT_ANKLE, RIGHT_HIP, RIGHT_KNEE,
    StanceReading, evaluate_crane_stance,
)
from chirox.voice import speakable


# --- speakable scrub (the "asterisk" bug) -----------------------------------------


def test_speakable_strips_markdown_symbols():
    assert speakable("Sink **lower** — hold the *root*.") == "Sink lower — hold the root."
    assert speakable("* * * * *") == ""
    assert speakable("100% honest, 90-100 degrees.") == "100% honest, 90-100 degrees."


def test_speakable_keeps_sentences_untouched():
    s = "The first victory is showing up tomorrow."
    assert speakable(s) == s


def test_speakable_colon_becomes_silent_pause():
    assert speakable("The rule: show up.") == "The rule, show up."
    assert speakable("Three things; one heart.") == "Three things, one heart."


def test_speakable_keeps_time_colons():
    assert speakable("Train at 10:30 daily.") == "Train at 10:30 daily."


def test_speakable_ampersand_and_slash_read_as_words():
    assert speakable("body & mind") == "body and mind"
    assert speakable("breath/recovery work") == "breath recovery work"


def test_speakable_never_stutters_pauses():
    # markdown headings like "**Focus:**" must not become ", ,"
    assert ",," not in speakable("**Focus:** , stand firm.")


# --- crane stance geometry ----------------------------------------------------------


def _crane_points(lift_left=True, standing_straight=True, knee_high=True, vis=1.0):
    # standing leg vertical: hip (0,0) knee (0,1) ankle (0,2); straight = 180
    standing_knee_x = 0 if standing_straight else 0.5
    lifted_knee_y = -0.2 if knee_high else 0.4     # hip line is y=0
    if lift_left:
        return {
            LEFT_HIP: (0.3, 0, vis), LEFT_KNEE: (0.4, lifted_knee_y, vis), LEFT_ANKLE: (0.4, 0.6, vis),
            RIGHT_HIP: (0, 0, vis), RIGHT_KNEE: (standing_knee_x, 1, vis), RIGHT_ANKLE: (0, 2, vis),
        }
    return {
        RIGHT_HIP: (0.3, 0, vis), RIGHT_KNEE: (0.4, lifted_knee_y, vis), RIGHT_ANKLE: (0.4, 0.6, vis),
        LEFT_HIP: (0, 0, vis), LEFT_KNEE: (standing_knee_x, 1, vis), LEFT_ANKLE: (0, 2, vis),
    }


def test_crane_balanced():
    r = evaluate_crane_stance(_crane_points())
    assert not r.uncertain
    assert r.flags == []
    assert r.assessment == "Crane balanced."
    assert r.metrics["lifted_leg_left"] == 1.0
    assert r.metrics["standing_knee_angle"] > 155


def test_crane_detects_right_leg_lift():
    r = evaluate_crane_stance(_crane_points(lift_left=False))
    assert r.metrics["lifted_leg_left"] == 0.0


def test_crane_flags_bent_standing_leg():
    r = evaluate_crane_stance(_crane_points(standing_straight=False))
    assert "standing_leg_bent" in r.flags


def test_crane_flags_low_knee():
    r = evaluate_crane_stance(_crane_points(knee_high=False))
    assert "knee_below_hip" in r.flags


def test_crane_no_lift_is_not_a_crane():
    pts = {
        LEFT_HIP: (0, 0, 1), LEFT_KNEE: (0, 1, 1), LEFT_ANKLE: (0, 2, 1),
        RIGHT_HIP: (0.3, 0, 1), RIGHT_KNEE: (0.3, 1, 1), RIGHT_ANKLE: (0.3, 2, 1),
    }
    r = evaluate_crane_stance(pts)
    assert "no_lift" in r.flags


def test_crane_uncertain_on_low_visibility():
    r = evaluate_crane_stance(_crane_points(vis=0.2))
    assert r.uncertain
    assert r.metrics == {}


# --- drill planning ------------------------------------------------------------------


def test_choose_plan_prefers_least_practiced():
    plan = choose_plan(["horse", "bow", "crane"], {"horse": 10, "bow": 2, "crane": 0}, n=2, seconds=45)
    assert plan == [("crane", 45), ("bow", 45)]


def test_choose_plan_ties_break_deterministically():
    plan = choose_plan(["horse", "bow", "crane"], {}, n=3)
    assert [s for s, _ in plan] == ["bow", "crane", "horse"]


# --- drill summary & spoken result -----------------------------------------------------


def _reading(flags=None, uncertain=False):
    return StanceReading("Horse Stance (Ma Bu)", {}, flags or [], "", 0.9, uncertain)


def test_drill_summary_counts_form_honestly():
    samples = [
        (1.0, _reading()),
        (2.0, _reading(["stance_too_high"])),
        (3.0, _reading()),
        (4.0, _reading(uncertain=True)),
    ]
    s = drill_summary(samples, 60)
    assert s["frames_seen"] == 3
    assert s["frames_uncertain"] == 1
    assert abs(s["form_rate"] - 2 / 3) < 0.01
    assert s["flags"] == {"stance_too_high": 1}


def test_spoken_result_reports_percent_and_worst_fault():
    s = drill_summary([(1.0, _reading(["spine_slouching"])), (2.0, _reading())], 60)
    line = spoken_result("Horse stance", s)
    assert "50 percent" in line
    assert "spine slouching" in line


def test_spoken_result_refuses_to_score_the_unseen():
    s = drill_summary([], 60)
    line = spoken_result("Crane stance", s)
    assert "Nothing is scored" in line
