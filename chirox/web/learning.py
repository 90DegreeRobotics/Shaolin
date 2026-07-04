"""Learning Mode data and Dojo Record writes for the local cockpit."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from chirox.activity import read_activity, set_mode
from chirox.calendar import dojo_day
from chirox.config import CODEX_PATH, Config
from chirox.record.codex import Codex
from chirox.record.schema import DailyCheckIn, MandarinJournal
from chirox.sentinel import Sentinel


STARTER_CHARACTERS = [
    {"character": "道", "pinyin": "dao4", "meaning": "path, way, principle",
     "question": "Did I walk the path or only imagine it?"},
    {"character": "静", "pinyin": "jing4", "meaning": "stillness, quiet",
     "question": "Where did I become quiet instead of reactive?"},
    {"character": "仁", "pinyin": "ren2", "meaning": "humaneness, benevolence",
     "question": "Where did I make life easier for another person?"},
    {"character": "忍", "pinyin": "ren3", "meaning": "endurance, restraint",
     "question": "Where did I endure without becoming cruel?"},
    {"character": "明", "pinyin": "ming2", "meaning": "brightness, clarity",
     "question": "What became clearer today?"},
    {"character": "行", "pinyin": "xing2", "meaning": "action, conduct, walking",
     "question": "What did I actually do?"},
    {"character": "心", "pinyin": "xin1", "meaning": "heart, mind",
     "question": "What ruled my heart-mind today?"},
]


def _codex() -> Codex:
    return Codex(CODEX_PATH)


def day_date(config: Config, day_number: int) -> str:
    return (config.practice_start_date + timedelta(days=int(day_number) - 1)).isoformat()


def mandarin_focus(day_number: int) -> dict[str, str]:
    return STARTER_CHARACTERS[(max(1, int(day_number)) - 1) % len(STARTER_CHARACTERS)]


def latest_records() -> dict[str, dict[int, dict[str, Any]]]:
    days: dict[int, dict[str, Any]] = {}
    mandarin: dict[int, dict[str, Any]] = {}
    for ev in _codex().events():
        if ev.type not in {"daily_checkin", "mandarin_journal"}:
            continue
        day = int(ev.payload.get("day_number", 0) or 0)
        if day <= 0:
            continue
        row = {"seq": ev.seq, "ts": ev.ts, "type": ev.type, **ev.payload}
        if ev.type == "daily_checkin":
            days[day] = row
        else:
            mandarin[day] = row
    return {"daily": days, "mandarin": mandarin}


def record_day(day_number: int) -> dict:
    config = Config.load()
    day_number = int(day_number)
    records = latest_records()
    return {
        "day_number": day_number,
        "date": day_date(config, day_number),
        "daily": records["daily"].get(day_number),
        "mandarin": records["mandarin"].get(day_number),
        "mandarin_focus": mandarin_focus(day_number),
    }


def overview() -> dict:
    from chirox.web import control

    config = Config.load()
    today = dojo_day(config.practice_start_date)
    records = latest_records()
    days = sorted(set(records["daily"]) | set(records["mandarin"]) | {today.day_number})
    return {
        "mode": read_activity().get("mode", "training"),
        "activity": read_activity(),
        "library": control.library_items(),
        "today": {
            "day_number": today.day_number,
            "week_number": today.week_number,
            "phase": today.phase,
            "headline": today.headline(),
        },
        "mandarin_focus": mandarin_focus(today.day_number),
        "days": [
            {
                "day_number": d,
                "date": day_date(config, d),
                "has_daily": d in records["daily"],
                "has_mandarin": d in records["mandarin"],
            }
            for d in days[-60:]
        ],
        "record": record_day(today.day_number),
    }


def _save_record(record) -> dict:
    config = Config.load()
    codex = _codex()
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize(f"record.append:{record.RECORD_TYPE}")
    ev = codex.append(record.RECORD_TYPE, record.payload())
    sentinel.consume(grant)
    return {"ok": True, "seq": ev.seq, "type": ev.type, "payload": ev.payload}


def _payload(data: dict, day_number: int, date: str | None) -> dict:
    config = Config.load()
    payload = dict(data or {})
    payload["day_number"] = int(day_number)
    payload["date"] = date or day_date(config, int(day_number))
    return payload


def save_daily(day_number: int, date: str | None, data: dict) -> dict:
    payload = _payload(data, day_number, date)
    payload["pain_level"] = int(payload.get("pain_level") or 0)
    record = DailyCheckIn(**{k: payload.get(k, "") for k in DailyCheckIn.__dataclass_fields__})
    return _save_record(record)


def save_mandarin(day_number: int, date: str | None, data: dict) -> dict:
    payload = _payload(data, day_number, date)
    payload["calligraphy_reps"] = int(payload.get("calligraphy_reps") or 0)
    focus = mandarin_focus(day_number)
    payload.setdefault("character_focus", focus["character"])
    record = MandarinJournal(**{k: payload.get(k, "") for k in MandarinJournal.__dataclass_fields__})
    return _save_record(record)


def switch_mode(mode: str) -> dict:
    return set_mode(mode)
