"""The Master's sense of time.

Pure date math over the 12-month blueprint (manual: "The 12-Month Blueprint").
No I/O, no clock hidden inside — ``today`` is always passed in or defaulted once
at the boundary, so every result is reproducible and unit-testable.

Phase boundaries follow the manual:

    Phase 1 — Days 1-30       Establish the floor.
    Phase 2 — Months 2-6      Deepen the practice.   (days 31-180)
    Phase 3 — Months 7-12     Integrate and lead.    (days 181-365)

Monthly checkpoints fall on days 30, 90, 180, 270, 365. The Weekly Dojo Review
is every Sunday (manual: "Do this every Sunday").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

PHASE_FOCUS = {
    1: "Establish the floor. Break old patterns. Build the daily return.",
    2: "Deepen the practice. Learn forms, build endurance, master the pause, practice Wu Wei.",
    3: "Integrate and lead. The practice is no longer what you do; it is who you are.",
}

CHECKPOINT_DAYS = {30: "Day 30", 90: "Day 90", 180: "Day 180", 270: "Day 270", 365: "Day 365 — the One-Year Gate"}

# The Diet lane's four-quarter arc (Diet/README.md), ~91 days each.
QUARTERS = {
    1: ("Stabilize", "Fix the container: set meal times, remove junk, move the plate plant-forward."),
    2: ("Cleanse", "Simplify the food; cut the heavy and overstimulating — hold protein up as volume rises."),
    3: ("Sharpen", "Windowed, consistent, full attention. Sharpen the rules, not the calories."),
    4: ("Sustain", "Hold the pattern independently. Balance, not asceticism."),
}


@dataclass(frozen=True)
class DojoDay:
    """Where the practitioner stands in the year, on a given day."""

    day_number: int          # day 1 is the practice start date
    phase: int               # 1, 2, or 3 (0 before the path begins)
    phase_name: str
    phase_focus: str
    week_number: int
    quarter: int             # 1-4 (0 before the path begins) — the Diet lane arc
    quarter_name: str
    quarter_focus: str
    is_weekly_review: bool   # Sunday
    is_checkpoint: bool
    checkpoint_label: str | None
    days_remaining: int      # to day 365; negative once beyond the year
    started: bool            # False if today is before the start date
    beyond_year: bool        # True once past day 365

    def headline(self) -> str:
        """A single terse line a Master would open with."""
        if not self.started:
            return f"The path has not begun. Day 1 is still ahead ({-self.day_number + 1} days)."
        if self.beyond_year:
            return f"Day {self.day_number}. The first year is behind you. The floor is laid; the work continues."
        line = f"Day {self.day_number} of 365 — Phase {self.phase} ({self.phase_name}). Week {self.week_number}."
        if self.is_checkpoint:
            line += f"  ***{self.checkpoint_label} checkpoint — write the long review.***"
        elif self.is_weekly_review:
            line += "  (Sunday — Weekly Dojo Review.)"
        return line


def _phase_for_day(day_number: int) -> tuple[int, str]:
    if day_number <= 0:
        return 0, "not yet begun"
    if day_number <= 30:
        return 1, "Days 1-30"
    if day_number <= 180:
        return 2, "Months 2-6"
    return 3, "Months 7-12"


def dojo_day(practice_start: date, today: date | None = None) -> DojoDay:
    """Compute the practitioner's standing on ``today`` (defaults to system date)."""
    today = today or date.today()
    day_number = (today - practice_start).days + 1  # start date == day 1
    started = day_number >= 1
    phase, phase_name = _phase_for_day(day_number)
    week_number = ((day_number - 1) // 7) + 1 if started else 0
    quarter = min(4, ((day_number - 1) // 91) + 1) if started else 0
    quarter_name, quarter_focus = QUARTERS.get(quarter, ("", ""))
    is_checkpoint = day_number in CHECKPOINT_DAYS
    return DojoDay(
        day_number=day_number,
        phase=phase,
        phase_name=phase_name,
        phase_focus=PHASE_FOCUS.get(phase, ""),
        week_number=week_number,
        quarter=quarter,
        quarter_name=quarter_name,
        quarter_focus=quarter_focus,
        is_weekly_review=started and today.weekday() == 6,  # Monday=0 ... Sunday=6
        is_checkpoint=is_checkpoint,
        checkpoint_label=CHECKPOINT_DAYS.get(day_number),
        days_remaining=365 - day_number,
        started=started,
        beyond_year=day_number > 365,
    )
