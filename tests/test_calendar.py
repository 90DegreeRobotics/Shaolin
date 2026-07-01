"""Calendar is pure date math — assert every boundary of the 12-month blueprint."""

from datetime import date, timedelta

from chirox.calendar import dojo_day

START = date(2026, 1, 1)  # a Thursday


def on_day(n: int):
    """DojoDay for the nth day of the path (day 1 == START)."""
    return dojo_day(START, START + timedelta(days=n - 1))


def test_start_date_is_day_one():
    d = on_day(1)
    assert d.day_number == 1
    assert d.started is True
    assert d.phase == 1
    assert d.week_number == 1


def test_week_boundaries():
    assert on_day(7).week_number == 1
    assert on_day(8).week_number == 2
    assert on_day(14).week_number == 2
    assert on_day(15).week_number == 3


def test_phase_boundaries():
    assert on_day(30).phase == 1
    assert on_day(31).phase == 2
    assert on_day(180).phase == 2
    assert on_day(181).phase == 3
    assert on_day(365).phase == 3


def test_monthly_checkpoints():
    for n in (30, 90, 180, 270, 365):
        assert on_day(n).is_checkpoint is True, n
    assert on_day(45).is_checkpoint is False
    assert on_day(365).checkpoint_label.startswith("Day 365")


def test_quarter_arc_boundaries():
    assert on_day(1).quarter == 1 and on_day(1).quarter_name == "Stabilize"
    assert on_day(91).quarter == 1
    assert on_day(92).quarter == 2 and on_day(92).quarter_name == "Cleanse"
    assert on_day(182).quarter == 2
    assert on_day(183).quarter == 3 and on_day(183).quarter_name == "Sharpen"
    assert on_day(273).quarter == 3
    assert on_day(274).quarter == 4 and on_day(274).quarter_name == "Sustain"
    assert on_day(365).quarter == 4  # capped, never 5
    assert dojo_day(START, START - timedelta(days=1)).quarter == 0


def test_weekly_review_is_sunday():
    sunday = date(2026, 1, 4)  # first Sunday after START
    assert sunday.weekday() == 6
    d = dojo_day(START, sunday)
    assert d.is_weekly_review is True
    # A Thursday is not a review day.
    assert dojo_day(START, date(2026, 1, 8)).is_weekly_review is False


def test_before_start_is_not_begun():
    d = dojo_day(START, START - timedelta(days=5))
    assert d.started is False
    assert d.phase == 0
    assert "not begun" in d.headline().lower()


def test_beyond_the_year():
    d = on_day(400)
    assert d.beyond_year is True
    assert d.days_remaining < 0
    assert "behind you" in d.headline().lower()


def test_headline_marks_checkpoint():
    assert "checkpoint" in on_day(90).headline().lower()
