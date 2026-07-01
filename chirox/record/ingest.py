"""Parse filled Dojo Record templates into typed entries, then commit them
through the Sentinel into the Codex.

The templates are the exact ``Label: value`` blocks from the manual. Parsing is
deliberately forgiving of layout (blank lines, headings, comments) but strict
about content: an empty field stays empty (defaults apply), and a missing
required field is an error — the record reflects what was written, not what
would look complete.
"""

from __future__ import annotations

from pathlib import Path

from chirox.record.codex import Codex, Event
from chirox.record.schema import RECORD_CLASSES, RecordValidationError

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class IngestError(Exception):
    """Raised when a filled template cannot be turned into a valid record."""


# Manual label -> dataclass field, per record type. Labels are matched
# case-insensitively after stripping.
_LABELS: dict[str, dict[str, str]] = {
    "daily_checkin": {
        "date": "date",
        "day number": "day_number",
        "sleep": "sleep",
        "meditation": "meditation",
        "qi gong": "qi_gong",
        "kung fu / conditioning": "kung_fu",
        "walk": "walk",
        "food / hydration": "food_hydration",
        "pain level 0-10": "pain_level",
        "mood": "mood",
        "one trigger": "one_trigger",
        "one act of ren": "one_ren",
        "one lesson": "one_lesson",
        "tomorrow's minimum": "tomorrow_minimum",
    },
    "weekly_review": {
        "week number": "week_number",
        "best completed practice": "best_practice",
        "practice most often avoided": "most_avoided",
        "physical truth": "physical_truth",
        "emotional truth": "emotional_truth",
        "relationship truth": "relationship_truth",
        "screen / food / sleep truth": "screen_food_sleep_truth",
        "one adjustment for next week": "one_adjustment",
        "one thing to stop": "one_to_stop",
        "one thing to continue": "one_to_continue",
    },
    "monthly_checkpoint": {
        "day number": "day_number",
        "body": "body",
        "mind": "mind",
        "conduct": "conduct",
        "environment": "environment",
        "recovery": "recovery",
        "next month": "next_month",
    },
    "mandarin_journal": {
        "date": "date",
        "day number": "day_number",
        "physical truth": "physical_truth",
        "emotional truth": "emotional_truth",
        "conduct truth": "conduct_truth",
        "one sentence worth keeping": "one_sentence",
        "core word / phrase": "core_word",
        "mandarin": "mandarin",
        "pinyin": "pinyin",
        "character focus": "character_focus",
        "calligraphy repetitions": "calligraphy_reps",
        "what this character asked of me": "what_character_asked",
        "tomorrow's vow": "tomorrow_vow",
    },
}


def parse_template(text: str, record_type: str, *, overrides: dict | None = None):
    """Parse the text of a filled template into a validated record dataclass.

    ``overrides`` (e.g. an auto-computed date/day_number from the calendar) are
    applied only where the template left the field blank.
    """
    if record_type not in _LABELS:
        raise IngestError(f"unknown record type: {record_type}")
    labels = _LABELS[record_type]
    cls = RECORD_CLASSES[record_type]

    kwargs: dict[str, object] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        label, _, value = line.partition(":")
        field = labels.get(label.strip().lower())
        if field is None:
            continue
        value = value.strip()
        if value:
            kwargs[field] = value

    for k, v in (overrides or {}).items():
        kwargs.setdefault(k, v)

    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise IngestError(f"missing required field(s) for {record_type}: {exc}") from exc
    except RecordValidationError as exc:
        raise IngestError(str(exc)) from exc


def ingest_file(path: Path, record_type: str, *, overrides: dict | None = None):
    return parse_template(Path(path).read_text(encoding="utf-8"), record_type, overrides=overrides)


def commit_record(record, codex: Codex, sentinel) -> Event:
    """Authorize (fail-closed), then seal the record into the Codex.

    The Sentinel decision is sealed *before* the record, so absence of authority
    stops the write with nothing half-committed.
    """
    grant = sentinel.authorize(f"record.append:{record.RECORD_TYPE}")
    event = codex.append(record.RECORD_TYPE, record.payload())
    sentinel.consume(grant)
    return event


def blank_template(record_type: str) -> str:
    return (TEMPLATES_DIR / f"{record_type}.md").read_text(encoding="utf-8")
