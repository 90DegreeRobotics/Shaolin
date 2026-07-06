"""The Master keeps his teeth: discernment names the fire without becoming a
filter, the persona stays hard, evidence is assembled from facts only, and a
missing model is refused honestly rather than faked."""

from datetime import date

from chirox.config import Config
from chirox.curriculum import Curriculum
from chirox.master import brain
from chirox.master.discernment import read_signals
from chirox.master.persona import system_prompt
from chirox.record.codex import Codex


def daily(day, pain, **text):
    base = {"day_number": day, "pain_level": pain, "mood": "", "one_lesson": ""}
    base.update(text)
    return base


# --- discernment ---------------------------------------------------------------


def test_green_signals_are_the_forge_not_a_warning():
    d = read_signals([daily(3, 3, one_lesson="legs were shaking and boredom set in, pushed through")])
    assert d.green_signals
    assert not d.has_red()
    assert "drive through" in d.summary_for_master().lower()


def test_red_signal_is_named_once_with_weight():
    d = read_signals([daily(4, 5, mood="felt chest pain and had to stop")])
    assert d.has_red()
    assert any("chest pain" in f for f in d.red_flags)
    assert "fire that destroys" in d.summary_for_master().lower()


def test_overload_trend_calls_for_deload():
    d = read_signals([daily(10, 6, mood="insomnia and dread before practice")])
    assert d.has_overload()
    assert "deload" in d.summary_for_master().lower()


def test_high_latest_pain_is_noted():
    d = read_signals([daily(1, 2), daily(2, 3), daily(3, 8)])
    assert "8/10" in d.pain_note


def test_empty_record_no_signals():
    d = read_signals([])
    assert not d.has_red() and not d.has_overload() and d.summary_for_master() == ""


# --- persona -------------------------------------------------------------------


def test_persona_is_calm_firm_and_honest():
    p = system_prompt().lower()
    assert "chirox" in p
    assert "forge" in p
    assert "never contemptuous" in p or "humiliate" in p  # firm, not cruel
    assert "uncertain" in p                                 # no form flattery
    assert "sovereign" in p                                 # practitioner owns the risk
    # the studied register: calm, inward-turning, no performance
    assert "calm, measured, unhurried" in p
    assert "one exact question" in p
    assert "no theatre" in p
    assert "hindrance" in p                                 # real method, not decoration
    assert "never invent a memory" in p                     # reflection stays honest


# --- evidence assembly (pure, no network) --------------------------------------


def build_codex(tmp_path):
    cx = Codex(tmp_path / "record.jsonl")
    cx.append("daily_checkin", daily(3, 3, one_lesson="the knees shake before the mind quits"))
    cx.append("vision_session", {
        "stance": "Horse Stance (Ma Bu)", "duration_s": 45.0, "frames_evaluated": 120,
        "frames_uncertain": 4, "mean_confidence": 0.82,
        "metrics_summary": {"left_knee_angle": {"min": 92, "mean": 98, "max": 110}},
        "flags_observed": {"stance_too_high": 12}, "notes": ["4/120 frames UNCERTAIN."],
    })
    return cx


def test_gather_and_render_evidence(tmp_path):
    cfg = Config(practice_start=date(2026, 6, 27).isoformat())  # a few days in
    cx = build_codex(tmp_path)
    ctx = brain.gather_evidence(cfg, cx, Curriculum(), today=date(2026, 6, 30))
    assert ctx.standing.day_number == 4
    assert ctx.recent_days and ctx.latest_vision
    assert ctx.passages  # at least the phase section

    text = brain.render_evidence(ctx)
    assert "STANDING" in text
    assert "RECENT DOJO RECORD" in text
    assert "DETERMINISTIC VISION" in text
    assert "stance_too_high" in text


def test_topic_question_grounds_in_canonical_section(tmp_path):
    cfg = Config(practice_start=date(2026, 6, 27).isoformat())
    cx = build_codex(tmp_path)
    ctx = brain.gather_evidence(
        cfg, cx, Curriculum(), today=date(2026, 6, 30),
        question="what should I eat today to recover?",
    )
    titles = [s.title.lower() for s in ctx.passages]
    assert any("food" in t for t in titles)       # diet -> Food, Hydration section
    assert any("recovery" in t for t in titles)    # recover -> Recovery Discipline


def test_diet_question_pulls_current_quarter_of_diet_lane(tmp_path):
    cfg = Config(practice_start=date(2026, 6, 30).isoformat())  # today == day 1 -> quarter 1
    cx = build_codex(tmp_path)
    ctx = brain.gather_evidence(
        cfg, cx, Curriculum(), today=date(2026, 6, 30),
        question="what should I eat today?",
    )
    sources = {s.source for s in ctx.passages}
    assert "diet" in sources
    assert any(s.source == "diet" and "quarter 1" in s.title.lower() for s in ctx.passages)


def test_render_forbids_form_claims_without_vision(tmp_path):
    cfg = Config(practice_start=date(2026, 6, 27).isoformat())
    cx = Codex(tmp_path / "r.jsonl")
    cx.append("daily_checkin", daily(1, 1))
    ctx = brain.gather_evidence(cfg, cx, Curriculum(), today=date(2026, 6, 27))
    text = brain.render_evidence(ctx)
    assert "no vision session recorded" in text.lower()
    assert "may not assert" in text.lower()


def test_master_refuses_honestly_when_model_absent():
    # Point at a dead port: the Master must report unavailability, never fabricate.
    cfg = Config(ollama_url="http://localhost:1")
    ok, reason = brain.Ollama(cfg).available()
    assert ok is False
    assert "ollama" in reason.lower()
