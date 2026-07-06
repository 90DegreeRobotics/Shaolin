"""Conversation register — pure prompt assembly, memory recall, and sentence
streaming. No Ollama, no audio."""

from chirox.master.brain import (
    _CONVERSE_TASK,
    _REFLECT_TASK,
    MasterContext,
    conversation_prompt,
    recall_exchanges,
    render_evidence,
    sentences,
)
from chirox.calendar import dojo_day
from chirox.master.discernment import read_signals
from chirox.record.codex import Codex
from datetime import date


def _ctx(question=None, memory=None, wisdom_growth=None, wisdom_passages=None):
    return MasterContext(
        standing=dojo_day(date(2026, 7, 1), date(2026, 7, 3)),
        recent_days=[], latest_vision=None,
        discernment=read_signals([]), passages=[], question=question,
        memory=memory or [], wisdom_growth=wisdom_growth,
        wisdom_passages=wisdom_passages or [],
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


# --- memory: sealed conversations recalled as evidence ----------------------------


def _codex_with_conversations(tmp_path):
    cx = Codex(tmp_path / "record.jsonl")
    cx.append("conversation", {"at": "2026-07-01T06:00:00+00:00",
                               "question": "how deep should my horse stance sink",
                               "answer": "Until the thighs burn and the breath stays even."})
    cx.append("conversation", {"at": "2026-07-02T06:00:00+00:00",
                               "question": "what should I eat before morning practice",
                               "answer": "Lightly. The manual's food section asks for water first."})
    cx.append("conversation", {"at": "2026-07-03T06:00:00+00:00",
                               "question": "my knees shake in meditation",
                               "answer": "Shaking is the forge. Sit with it."})
    return cx


def test_recall_returns_recent_exchanges_even_without_question(tmp_path):
    got = recall_exchanges(_codex_with_conversations(tmp_path), question=None, recent=2)
    assert len(got) == 2
    assert got[0]["question"].startswith("what should I eat")
    assert got[1]["question"].startswith("my knees shake")


def test_recall_adds_older_relevant_exchange_by_topic(tmp_path):
    got = recall_exchanges(_codex_with_conversations(tmp_path),
                           question="tell me about horse stance depth", recent=1)
    questions = [g["question"] for g in got]
    assert any("horse stance" in q for q in questions)   # recalled by shared vocabulary
    assert questions[-1].startswith("my knees shake")     # the recent turn still present
    # oldest-first: the recalled exchange precedes the recent one
    assert questions.index("how deep should my horse stance sink") < len(questions) - 1


def test_recall_ignores_unrelated_older_exchanges(tmp_path):
    got = recall_exchanges(_codex_with_conversations(tmp_path),
                           question="tell me about sword forms", recent=1)
    assert len(got) == 1  # nothing shares vocabulary; only the recent turn returns


def test_recall_empty_codex_is_empty(tmp_path):
    assert recall_exchanges(Codex(tmp_path / "empty.jsonl"), question="anything") == []


def test_recall_honors_forget_events(tmp_path):
    cx = _codex_with_conversations(tmp_path)
    cx.forget(0, "withdrawn for the test", operator="tester")  # the horse-stance exchange
    got = recall_exchanges(cx, question="tell me about horse stance depth", recent=1)
    assert all("horse stance" not in g["question"] for g in got)


def test_render_evidence_includes_memory_section():
    mem = [{"at": "2026-07-01T06:00:00+00:00", "question": "how deep is horse stance",
            "answer": "Until the thighs burn."}]
    text = render_evidence(_ctx("horse stance again?", memory=mem))
    assert "MEMORY — SEALED PAST CONVERSATIONS" in text
    assert "[2026-07-01] Student: how deep is horse stance" in text
    assert "[2026-07-01] Chirox: Until the thighs burn." in text


def test_render_evidence_names_first_words_when_no_memory():
    text = render_evidence(_ctx("hello"))
    assert "first words together" in text


def test_render_evidence_includes_wisdom_trail_when_present():
    growth = {"count": 3, "themes": [("impermanence", 2), ("effort", 1)],
              "growth": {"searching": 2, "surface": 1}}
    text = render_evidence(_ctx("am I growing?", wisdom_growth=growth))
    assert "WISDOM TRAIL: 3 sage dialogues sealed" in text
    assert "impermanence" in text


def test_render_evidence_offers_wisdom_passage_as_quotable():
    class P:
        book = "Tao Te Ching"
        text = "The sage does not accumulate."

    text = render_evidence(_ctx("what is emptiness", wisdom_passages=[P()]))
    assert "WISDOM PASSAGE" in text
    assert 'From Tao Te Ching: "The sage does not accumulate."' in text


def test_render_evidence_forbids_quoting_when_nothing_retrieved():
    text = render_evidence(_ctx("hello"))
    assert "quote no text and cite no book" in text


def test_reflect_task_looks_back_and_ends_with_one_question():
    text = render_evidence(_ctx("look back with me"), task=_REFLECT_TASK)
    assert "reflection, not a debrief" in text
    assert "ONE question" in text


# --- sentence streaming ------------------------------------------------------------


def test_sentences_regroups_fragments_into_whole_sentences():
    chunks = ["The path ", "is walked. It is ", "not discussed. Walk", " it."]
    assert list(sentences(chunks)) == ["The path is walked.", "It is not discussed.", "Walk it."]


def test_sentences_does_not_split_decimals():
    assert list(sentences(["Hold for 3.5 minutes. Then rest."])) == \
        ["Hold for 3.5 minutes.", "Then rest."]


def test_sentences_yields_unterminated_tail():
    assert list(sentences(["First thought. And the rest never ends"])) == \
        ["First thought.", "And the rest never ends"]


def test_sentences_handles_questions_and_quotes():
    got = list(sentences(['What holds you back? "Sit with it." Then begin.']))
    assert got == ["What holds you back?", '"Sit with it."', "Then begin."]


def test_sentences_empty_stream():
    assert list(sentences([])) == []
