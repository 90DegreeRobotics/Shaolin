"""Conversation register — pure prompt assembly, no Ollama, no audio."""

from chirox.master.brain import _CONVERSE_TASK, MasterContext, conversation_prompt, render_evidence
from chirox.calendar import dojo_day
from chirox.master.discernment import read_signals
from datetime import date


def _ctx(question=None):
    return MasterContext(
        standing=dojo_day(date(2026, 7, 1), date(2026, 7, 3)),
        recent_days=[], latest_vision=None,
        discernment=read_signals([]), passages=[], question=question,
    )


def test_render_evidence_default_task_is_debrief():
    text = render_evidence(_ctx())
    assert text.strip().endswith("End with tomorrow's non-negotiable minimum.")


def test_render_evidence_converse_task_speaks_naturally():
    text = render_evidence(_ctx("what is horse stance for?"), task=_CONVERSE_TASK)
    assert "spoken conversation" in text
    assert "THE STUDENT ASKS: what is horse stance for?" in text
    assert "non-negotiable minimum" not in text


def test_converse_task_forbids_fabrication_and_symbols():
    assert "Never fabricate" in _CONVERSE_TASK
    assert "no lists, no symbols" in _CONVERSE_TASK


def test_conversation_prompt_without_history_is_just_evidence():
    assert conversation_prompt("EVIDENCE", []) == "EVIDENCE"


def test_conversation_prompt_includes_turns_in_order():
    history = [("what day is it", "Day three."), ("am I improving", "The record says yes, slowly.")]
    text = conversation_prompt("EVIDENCE", history)
    assert text.index("what day is it") < text.index("am I improving") < text.index("EVIDENCE")
    assert "Student: am I improving" in text
    assert "Chirox: Day three." in text
