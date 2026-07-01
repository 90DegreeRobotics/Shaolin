"""Filled templates must parse into honest records and commit through the gate."""

import pytest

from chirox.config import Config
from chirox.record.codex import Codex
from chirox.record.ingest import (
    IngestError,
    blank_template,
    commit_record,
    ingest_file,
    parse_template,
)
from chirox.record.schema import RECORD_CLASSES
from chirox.sentinel import Sentinel

FILLED_DAILY = """# Daily Check-In
Date: 2026-06-30
Day number: 5
Sleep: 7h, solid
Meditation: 12 min, scattered
Qi Gong: Eight Brocades
Kung Fu / conditioning: Horse stance 3x45s
Walk: 20 min no phone
Food / hydration: clean, 3L water
Pain level 0-10: 3
Mood: steady
One trigger: email from work
One act of Ren: made tea for my father
One lesson: the knees shake before the mind quits
Tomorrow's minimum: sit 3 min, one stance hold
"""


def test_parse_filled_daily():
    rec = parse_template(FILLED_DAILY, "daily_checkin")
    assert rec.day_number == 5
    assert rec.pain_level == 3
    assert rec.date == "2026-06-30"
    assert "father" in rec.one_ren
    assert rec.tomorrow_minimum.startswith("sit 3 min")


def test_blank_daily_requires_date_and_day_number():
    with pytest.raises(IngestError):
        parse_template(blank_template("daily_checkin"), "daily_checkin")


def test_overrides_fill_only_blank_fields():
    rec = parse_template(
        blank_template("daily_checkin"),
        "daily_checkin",
        overrides={"date": "2026-06-30", "day_number": 5},
    )
    assert rec.date == "2026-06-30" and rec.day_number == 5
    # A filled field is not overwritten by an override.
    rec2 = parse_template(FILLED_DAILY, "daily_checkin", overrides={"day_number": 99})
    assert rec2.day_number == 5


def test_pain_out_of_range_rejected():
    bad = FILLED_DAILY.replace("Pain level 0-10: 3", "Pain level 0-10: 15")
    with pytest.raises(IngestError):
        parse_template(bad, "daily_checkin")


def test_every_template_ships_and_round_trips():
    # Each shipped blank template maps cleanly onto its record class fields.
    for record_type, cls in RECORD_CLASSES.items():
        text = blank_template(record_type)
        assert text.strip(), record_type
        # Fill required-ish numeric fields so construction succeeds.
        overrides = {}
        if "date" in cls.__dataclass_fields__:
            overrides["date"] = "2026-06-30"
        if "day_number" in cls.__dataclass_fields__:
            overrides["day_number"] = 30
        if "week_number" in cls.__dataclass_fields__:
            overrides["week_number"] = 4
        rec = parse_template(text, record_type, overrides=overrides)
        assert rec.RECORD_TYPE == record_type


def test_commit_record_seals_through_sentinel(tmp_path):
    cx = Codex(tmp_path / "record.jsonl")
    s = Sentinel(cx, Config(sentinel_mode="enforce"), key_path=tmp_path / "op.key")
    s.init_operator()
    rec = parse_template(FILLED_DAILY, "daily_checkin")
    ev = commit_record(rec, cx, s)
    assert ev.type == "daily_checkin"
    # Decision sealed before the record; chain intact.
    types = [e.type for e in cx.events()]
    assert types.index("sentinel_authority_decision") < types.index("daily_checkin")
    assert cx.verify()[0]


def test_ingest_file(tmp_path):
    p = tmp_path / "day5.md"
    p.write_text(FILLED_DAILY, encoding="utf-8")
    rec = ingest_file(p, "daily_checkin")
    assert rec.day_number == 5
