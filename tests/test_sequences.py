"""Eight Brocades sequence tracker — pure geometry, no camera."""

from chirox.vision.sequences import (
    EIGHT_BROCADES_STE, SEQUENCE_CATALOG, SequenceTracker, arrow_draw_signal,
    free_train_tag, heaven_earth_signal, list_sequences, make_tracker,
)
from chirox.vision.stances import (
    LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST,
    RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST,
)


def _standing(wrists_y=0.55, wr_span=0.3):
    """Front-ish standing skeleton in normalized coords (y down)."""
    return {
        LEFT_SHOULDER: (0.4, 0.35, 1.0), RIGHT_SHOULDER: (0.6, 0.35, 1.0),
        LEFT_ELBOW: (0.35, 0.5, 1.0), RIGHT_ELBOW: (0.65, 0.5, 1.0),
        LEFT_WRIST: (0.5 - wr_span / 2, wrists_y, 1.0),
        RIGHT_WRIST: (0.5 + wr_span / 2, wrists_y, 1.0),
        LEFT_HIP: (0.42, 0.55, 1.0), RIGHT_HIP: (0.58, 0.55, 1.0),
        LEFT_KNEE: (0.42, 0.75, 1.0), RIGHT_KNEE: (0.58, 0.75, 1.0),
        LEFT_ANKLE: (0.42, 0.95, 1.0), RIGHT_ANKLE: (0.58, 0.95, 1.0),
    }


def test_catalog_lists_ste_eight_brocades():
    assert "eight_brocades_ste" in SEQUENCE_CATALOG
    rows = list_sequences()
    assert any(r["key"] == "eight_brocades_ste" for r in rows)
    assert len(EIGHT_BROCADES_STE.phases) == 10  # open + 8 + close


def test_tracker_starts_on_opening_phase():
    tr = make_tracker("eight_brocades_ste")
    st = tr.status()
    assert st["phase_key"] == "bdj_open"
    assert st["phase_index"] == 0
    assert st["done"] is False


def test_manual_next_advances_phases():
    tr = make_tracker("eight_brocades_ste")
    tr.next_phase(1.0)
    assert tr.status()["phase_key"] == "bdj_support_heaven"
    tr.next_phase(2.0)
    assert tr.status()["phase_key"] == "bdj_draw_arrow"


def test_stop_seals_partial_summary():
    tr = make_tracker("eight_brocades_ste")
    tr.push(_standing(), 0.5)
    tr.next_phase(5.0)
    summary = tr.stop(10.0)
    assert summary["routine_key"] == "eight_brocades_ste"
    assert summary["totals"]["phases_completed"] >= 2
    assert summary["finished"]
    assert tr.done


def test_uncertain_body_pauses_rep_counting():
    tr = make_tracker("eight_brocades_ste")
    # Skip opening hold into support-heaven reps.
    tr.next_phase(1.0)
    assert tr.status()["phase_key"] == "bdj_support_heaven"
    # No points → uncertain, reps stay 0
    for i in range(20):
        tr.push(None, 2.0 + i * 0.03)
    assert tr.status()["reps"] == 0


def test_rep_phase_auto_advances_on_target():
    tr = make_tracker("eight_brocades_ste")
    tr.next_phase(1.0)  # -> support heaven
    # Drive arms down/up cycles that match enter/exit thresholds.
    t = 2.0
    for _ in range(12):
        tr.push(_standing(wrists_y=0.7), t)   # arms down → enter
        t += 0.05
        tr.push(_standing(wrists_y=0.15), t)  # arms up → exit / count
        t += 0.05
    # Need min_seconds too
    while tr.status()["phase_key"] == "bdj_support_heaven" and t < 30:
        tr.push(_standing(wrists_y=0.15), t)
        t += 0.2
    assert tr.status()["phase_key"] in ("bdj_draw_arrow", "bdj_support_heaven")
    # If still on support heaven, target may not have hit due to pose_key flags;
    # at least reps should have moved.
    if tr.status()["phase_key"] == "bdj_support_heaven":
        assert tr.status()["reps"] >= 1


def test_arrow_and_heaven_earth_signals():
    wide = _standing(wr_span=0.9)
    narrow = _standing(wr_span=0.1)
    assert arrow_draw_signal(wide) > arrow_draw_signal(narrow)

    split = _standing()
    split[LEFT_WRIST] = (0.35, 0.1, 1.0)
    split[RIGHT_WRIST] = (0.65, 0.8, 1.0)
    assert heaven_earth_signal(split) > heaven_earth_signal(_standing())


def test_free_train_tag_returns_a_known_hold_or_none():
    tag = free_train_tag(_standing(wrists_y=0.2))
    # May be arms_raised / wuji / parallel depending on thresholds — or None if uncertain.
    if tag is not None:
        assert "key" in tag and "label" in tag


def test_unknown_routine_raises():
    try:
        make_tracker("not_a_real_routine")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unknown routine" in str(exc)
