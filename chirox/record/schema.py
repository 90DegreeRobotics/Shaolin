"""Typed Dojo Record entries — the exact shapes the manual asks the practitioner
to write (manual: "Measurement and the Dojo Record").

These are light dataclasses: they normalize and range-check, then hand a plain
dict payload to the Codex. Validation is honest and minimal — the record must
reflect what was actually written, not what would look good.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields


class RecordValidationError(ValueError):
    """Raised when a record entry is malformed (e.g. pain level out of range)."""


@dataclass
class DailyCheckIn:
    """Nightly check-in (manual: "Daily Check-In")."""

    RECORD_TYPE = "daily_checkin"

    date: str
    day_number: int
    sleep: str = ""
    meditation: str = ""
    qi_gong: str = ""
    kung_fu: str = ""
    walk: str = ""
    food_hydration: str = ""
    pain_level: int = 0
    mood: str = ""
    one_trigger: str = ""
    one_ren: str = ""          # one act of benevolence
    one_lesson: str = ""
    tomorrow_minimum: str = ""

    def __post_init__(self):
        if not (0 <= int(self.pain_level) <= 10):
            raise RecordValidationError(f"pain_level must be 0-10, got {self.pain_level}")
        self.pain_level = int(self.pain_level)
        self.day_number = int(self.day_number)

    def payload(self) -> dict:
        return asdict(self)


@dataclass
class WeeklyReview:
    """Sunday review (manual: "Weekly Dojo Review")."""

    RECORD_TYPE = "weekly_review"

    week_number: int
    best_practice: str = ""
    most_avoided: str = ""
    physical_truth: str = ""
    emotional_truth: str = ""
    relationship_truth: str = ""
    screen_food_sleep_truth: str = ""
    one_adjustment: str = ""
    one_to_stop: str = ""
    one_to_continue: str = ""

    def __post_init__(self):
        self.week_number = int(self.week_number)

    def payload(self) -> dict:
        return asdict(self)


@dataclass
class MonthlyCheckpoint:
    """Long review on days 30/90/180/270/365 (manual: "Monthly Checkpoints")."""

    RECORD_TYPE = "monthly_checkpoint"

    day_number: int
    body: str = ""
    mind: str = ""
    conduct: str = ""
    environment: str = ""
    recovery: str = ""
    next_month: str = ""

    def __post_init__(self):
        self.day_number = int(self.day_number)

    def payload(self) -> dict:
        return asdict(self)


@dataclass
class MandarinJournal:
    """Calligraphy-linked journal page (manual: "Pencil Journal and Mandarin
    Calligraphy Method")."""

    RECORD_TYPE = "mandarin_journal"

    date: str
    day_number: int
    physical_truth: str = ""
    emotional_truth: str = ""
    conduct_truth: str = ""
    one_sentence: str = ""
    core_word: str = ""
    mandarin: str = ""
    pinyin: str = ""
    character_focus: str = ""
    calligraphy_reps: int = 0
    what_character_asked: str = ""
    tomorrow_vow: str = ""

    def __post_init__(self):
        self.day_number = int(self.day_number)
        self.calligraphy_reps = int(self.calligraphy_reps or 0)

    def payload(self) -> dict:
        return asdict(self)


RECORD_CLASSES = {
    DailyCheckIn.RECORD_TYPE: DailyCheckIn,
    WeeklyReview.RECORD_TYPE: WeeklyReview,
    MonthlyCheckpoint.RECORD_TYPE: MonthlyCheckpoint,
    MandarinJournal.RECORD_TYPE: MandarinJournal,
}


def field_names(record_cls) -> list[str]:
    return [f.name for f in fields(record_cls)]
