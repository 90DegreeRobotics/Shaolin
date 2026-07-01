"""Chirox in the sage register — a grounded philosophical dialogue.

This is NOT a second personality. It is the same Master Chirox, teaching instead
of drilling. Chirox poses a question, koan, or short story grounded in the real
wisdom corpus (and cites the book), hears the student's answer, and reflects with
honesty — naming what the answer reveals and what to sit with. It is a GROWTH
ledger, not a competition: no numeric score, no flattery, no invented quotations.

Every teaching is grounded in retrieved passages. Chirox does not fabricate
scripture in a dead master's voice — the wisdom is real and checkable.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from chirox.calendar import dojo_day
from chirox.config import Config
from chirox.master.brain import Ollama
from chirox.master.persona import system_prompt
from chirox.wisdom import WisdomLibrary

SAGE_ADDENDUM = """

--- SAGE REGISTER ---
You are the same Chirox, now teaching philosophy rather than drilling the body. Same voice:
exacting, honest, unflattering — but contemplative, not barking.
- Ground every teaching ONLY in the passages you are given, and name the book it comes from.
- NEVER invent quotations or attributions. If a passage does not say it, you do not claim it.
- Pose ONE thing at a time: a single hard question, a short koan, or a two-sentence story ending
  in a question. Do not pre-answer it.
- When you reflect on the student's answer, this is GROWTH, not a grade. No numbers, no
  competition, no false praise. Name honestly what the answer reveals and what it avoids, and
  give one thing to sit with.
You are one being: Master Chirox. Never refer to yourself as anything else.
"""


@dataclass
class SageProbe:
    topic: str
    text: str
    citations: list[str] = field(default_factory=list)


@dataclass
class SageDialogue:
    day_number: int
    topic: str
    probe: str
    citations: list[str]
    answer: str
    reflection: str
    growth_marker: str
    themes: list[str] = field(default_factory=list)

    RECORD_TYPE = "wisdom_dialogue"

    def payload(self) -> dict:
        return asdict(self)


def pose_question(config: Config, wisdom: WisdomLibrary, topic: str | None = None,
                  ollama: Ollama | None = None, today=None, rng=None) -> SageProbe:
    ollama = ollama or Ollama(config)
    d = dojo_day(config.practice_start_date, today)
    if topic:
        seeds = wisdom.search(topic, limit=2)
        label = topic
    else:
        p = wisdom.random_passage(rng)
        seeds = [p] if p else []
        label = "the day's reflection"
    seed_txt = "\n\n".join(f'From {s.book}:\n"{s.text}"' for s in seeds) or "(no passage available)"
    citations = list(dict.fromkeys(s.book for s in seeds))
    user = (
        f"Day {d.day_number} of the path, Phase {d.phase}. Topic: {label}.\n"
        f"Ground your teaching ONLY in these passage(s), and cite the book:\n\n{seed_txt}\n\n"
        "Pose ONE thing to the student now: a single hard question, a short koan, or a "
        "two-sentence story that ends in a question. Cite the book it grows from. Do not explain "
        "the answer. Keep it under 120 words."
    )
    return SageProbe(label, ollama.chat(system_prompt() + SAGE_ADDENDUM, user), citations)


def _parse_reflection(out: str) -> tuple[str, list[str], str]:
    growth, themes = "recorded", []
    gm = re.search(r"GROWTH:\s*(surface|searching|deepening)", out, re.I)
    tm = re.search(r"THEMES:\s*(.+)", out)
    if gm:
        growth = gm.group(1).lower()
    if tm:
        themes = [t.strip() for t in re.split(r"[,;]", tm.group(1)) if t.strip()][:4]
    reflection = re.sub(r"\n*GROWTH:.*", "", out, flags=re.I | re.S).strip()
    return growth, themes, reflection


def reflect(config: Config, wisdom: WisdomLibrary, probe: SageProbe, answer: str,
            ollama: Ollama | None = None, today=None) -> SageDialogue:
    ollama = ollama or Ollama(config)
    d = dojo_day(config.practice_start_date, today)
    grounding = wisdom.search(answer, limit=1)
    seed_txt = "\n\n".join(f'From {s.book}: "{s.text}"' for s in grounding)
    user = (
        f"The student was asked:\n{probe.text}\n\n"
        f"The student answered:\n{answer}\n\n"
        f"Optional grounding passage:\n{seed_txt}\n\n"
        "Reflect as Chirox in the sage register. Name honestly what the answer reveals and what "
        "it avoids, and give ONE thing to sit with. This is GROWTH, not a grade — no numbers, no "
        "flattery, no false praise. Under 150 words.\n"
        "Then end with exactly two lines:\n"
        "GROWTH: <surface|searching|deepening>\n"
        "THEMES: <2-4 short comma-separated themes>"
    )
    growth, themes, reflection = _parse_reflection(ollama.chat(system_prompt() + SAGE_ADDENDUM, user))
    return SageDialogue(d.day_number, probe.topic, probe.text, probe.citations, answer,
                        reflection, growth, themes)


def seal_dialogue(dialogue: SageDialogue, config: Config | None = None):
    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    config = config or Config.load()
    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize("wisdom.dialogue")
    event = codex.append(dialogue.RECORD_TYPE, dialogue.payload())
    sentinel.consume(grant)
    return event


def growth_summary(codex) -> dict:
    from collections import Counter

    dialogues = [e.payload for e in codex.events("wisdom_dialogue")]
    themes: Counter = Counter()
    growth: Counter = Counter()
    for d in dialogues:
        themes.update(d.get("themes", []))
        growth[d.get("growth_marker", "recorded")] += 1
    return {"count": len(dialogues), "themes": themes.most_common(), "growth": dict(growth)}
