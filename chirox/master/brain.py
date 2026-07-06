"""The Master's brain — evidence assembly + local Ollama call.

Evidence assembly is pure and testable (no network). The model call is the only
part that reaches the local Ollama server. If Ollama is not running or the model
is not present, the Master says so plainly and refuses to speak — he does not
fabricate a debrief. Silence is honest; a hallucinated master is not.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Iterator

import requests

from chirox.calendar import DojoDay, dojo_day
from chirox.config import Config
from chirox.curriculum import Curriculum, Section
from chirox.master.discernment import Discernment, read_signals
from chirox.master.persona import system_prompt


class MasterUnavailable(RuntimeError):
    """Raised when the local model cannot be reached — the Master will not fake it."""


# Map words a student is likely to use to the canonical curriculum topic, so the
# right manual section is always in context even if keyword search alone misses it.
_TOPIC_ALIASES = {
    "diet": ["eat", "food", "diet", "meal", "nutrition", "hydrat", "protein", "caffeine"],
    "breath": ["breath", "breathwork", "qi gong", "qigong"],
    "recovery": ["recover", "rest", "sleep", "deload", "tired", "overload"],
    "stance": ["stance", "form", "posture", "horse", "ma bu", "bow"],
    "meditation": ["meditat", "calm", "focus", "still"],
    "conduct": ["conduct", "respect", "relationship", "benevolence"],
}


# --- Ollama client -------------------------------------------------------------


class Ollama:
    def __init__(self, config: Config):
        self.url = config.ollama_url.rstrip("/")
        self.model = config.model

    def available(self) -> tuple[bool, str]:
        """Return (ok, reason). ok is False if the server is down or model absent."""
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=3)
            r.raise_for_status()
        except requests.RequestException as exc:
            return False, f"Ollama server not reachable at {self.url} ({exc.__class__.__name__}). Run: ollama serve"
        tags = [m.get("name", "") for m in r.json().get("models", [])]
        base = self.model.split(":")[0]
        if not any(t == self.model or t.split(":")[0] == base for t in tags):
            return False, f"model '{self.model}' not found locally. Run: ollama pull {self.model}"
        return True, "ok"

    # Without an explicit num_ctx Ollama defaults to a small window and silently
    # truncates from the top — decapitating the persona once evidence + memory
    # grow. 8192 fits qwen2.5:14b on a 12GB GPU with room to spare.
    NUM_CTX = 8192

    def _payload(self, system: str, user: str, temperature: float, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": stream,
            # An always-on ear should not pay the model-load cost on every
            # exchange after a silence — keep the Master resident.
            "keep_alive": "30m",
            "options": {"temperature": temperature, "num_ctx": self.NUM_CTX},
        }

    def chat(self, system: str, user: str, temperature: float = 0.7) -> str:
        try:
            r = requests.post(f"{self.url}/api/chat",
                              json=self._payload(system, user, temperature, stream=False),
                              timeout=300)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise MasterUnavailable(f"Ollama call failed: {exc}") from exc
        return r.json()["message"]["content"].strip()

    def chat_stream(self, system: str, user: str, temperature: float = 0.7) -> Iterator[str]:
        """Yield the reply as it is generated — the mouth need not wait for the whole thought."""
        try:
            with requests.post(f"{self.url}/api/chat",
                               json=self._payload(system, user, temperature, stream=True),
                               stream=True, timeout=300) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    piece = data.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if data.get("done"):
                        return
        except requests.RequestException as exc:
            raise MasterUnavailable(f"Ollama call failed: {exc}") from exc


_SENTENCE_END = re.compile(r"([.!?…]+[\"')\]]?)\s")


def sentences(chunks: Iterable[str]) -> Iterator[str]:
    """Regroup a stream of text fragments into whole sentences as they complete.

    Pure and deterministic: each sentence is yielded the moment its terminator
    (followed by whitespace) arrives, so speech can begin before the model has
    finished thinking. Decimals like 3.5 never split; the unterminated tail is
    yielded last.
    """
    buf = ""
    for chunk in chunks:
        buf += chunk
        while True:
            m = _SENTENCE_END.search(buf)
            if not m:
                break
            end = m.end(1)
            sent = buf[:end].strip()
            buf = buf[end:]
            if sent:
                yield sent
    tail = buf.strip()
    if tail:
        yield tail


# --- the Master's memory (pure) --------------------------------------------------

# Words too common to signal that two conversations are about the same thing.
_RECALL_STOPWORDS = frozenset(
    "the a an and or but if then is are was were be been being am i you he she it we they "
    "my your his her its our their of in on at to for with about from as this that these "
    "those what which who whom how when where why do does did doing done have has had having "
    "can could should would will shall may might must not no yes so very just really there "
    "here me him them us more most some any all each one two also into over under again "
    "today tomorrow yesterday day days chirox master".split()
)


def _keywords(text: str) -> set[str]:
    words = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower()).split()
    return {w for w in words if len(w) > 2 and w not in _RECALL_STOPWORDS}


def recall_exchanges(codex, question: str | None, recent: int = 2, relevant: int = 3) -> list[dict]:
    """The Master's memory: sealed conversations recalled into today's context.

    Always the last ``recent`` exchanges (continuity across sittings), plus up
    to ``relevant`` older ones that share real vocabulary with today's
    question. Returned oldest-first, each payload carrying its seal timestamp.
    Exchanges withdrawn by a ``forget`` event stay in the chain but are never
    recalled — an honored erasure, not a silent one.
    """
    forgotten = {e.payload.get("target_seq") for e in codex.events("forget")}
    events = [e for e in codex.events("conversation") if e.seq not in forgotten]
    if not events:
        return []
    chosen = {e.seq: e for e in (events[-recent:] if recent else [])}
    if question:
        qk = _keywords(question)
        older = events[:-recent] if recent else events
        if qk and older:
            need = min(2, len(qk))  # one stray shared word is not a memory
            scored = []
            for e in older:
                p = e.payload
                hit = len(qk & _keywords(f"{p.get('question', '')} {p.get('answer', '')}"))
                if hit >= need:
                    scored.append((hit, e.seq, e))
            scored.sort(key=lambda t: (-t[0], -t[1]))
            for _, _, e in scored[:relevant]:
                chosen.setdefault(e.seq, e)
    return [dict(e.payload, sealed_at=e.ts) for e in sorted(chosen.values(), key=lambda e: e.seq)]


# --- evidence assembly (pure) --------------------------------------------------


@dataclass
class MasterContext:
    standing: DojoDay
    recent_days: list[dict]
    latest_vision: dict | None
    discernment: Discernment
    passages: list[Section] = field(default_factory=list)
    question: str | None = None
    memory: list[dict] = field(default_factory=list)
    wisdom_growth: dict | None = None
    wisdom_passages: list = field(default_factory=list)


def gather_evidence(
    config: Config,
    codex,
    curriculum: Curriculum,
    today: date | None = None,
    question: str | None = None,
    deep: bool = False,
) -> MasterContext:
    """Assemble the Master's context. ``deep`` widens every window — used when
    the student asks to look back, because reflection needs a longer memory."""
    standing = dojo_day(config.practice_start_date, today)
    recent_days = [e.payload for e in codex.tail(14 if deep else 5, "daily_checkin")]
    vision_events = codex.tail(1, "vision_session")
    latest_vision = vision_events[0].payload if vision_events else None
    disc = read_signals(recent_days)
    memory = recall_exchanges(codex, question,
                              recent=6 if deep else 2, relevant=4 if deep else 3)
    from chirox.master.sage import growth_summary  # lazy: sage imports this module

    wisdom_growth = growth_summary(codex)

    # One real, checkable passage per question: a model that wants to cite a
    # book will cite one — give it true words or it will invent its own.
    wisdom_passages: list = []
    if question:
        try:
            from chirox.wisdom import WisdomLibrary

            wisdom_passages = WisdomLibrary().search(question, limit=1)
        except Exception:
            wisdom_passages = []

    passages: list[Section] = []
    seen: set[str] = set()

    def add(sec: Section | None):
        if sec and sec.title not in seen:
            passages.append(sec)
            seen.add(sec.title)

    if standing.phase:
        add(curriculum.phase(standing.phase))
    if question:
        # Guarantee the canonical section when the student names a topic, so
        # diet/breath/recovery guidance is grounded in the real passage.
        ql = question.lower()
        for topic, aliases in _TOPIC_ALIASES.items():
            if any(a in ql for a in aliases):
                for sec in curriculum.topic(topic, limit=1):
                    add(sec)
        # Diet questions also pull the current quarter of the Diet lane arc.
        if any(a in ql for a in _TOPIC_ALIASES["diet"]) and standing.quarter:
            add(curriculum.diet_quarter(standing.quarter))
        for sec in curriculum.search(question, limit=2):
            add(sec)
    if disc.has_red() or disc.has_overload():
        for sec in curriculum.topic("recovery", limit=1) + curriculum.topic("injury", limit=1):
            add(sec)
    if latest_vision and latest_vision.get("flags_observed"):
        add(curriculum.by_title("Learning the Forms"))

    return MasterContext(standing, recent_days, latest_vision, disc, passages, question,
                         memory, wisdom_growth, wisdom_passages)


def _clip(text: str, limit: int = 320) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def _fmt_day(rec: dict) -> str:
    keys = ["day_number", "sleep", "meditation", "qi_gong", "kung_fu", "walk",
            "food_hydration", "pain_level", "mood", "one_lesson"]
    parts = [f"{k}={rec.get(k)!r}" for k in keys if rec.get(k) not in (None, "", 0)]
    return "  - " + ", ".join(parts)


def render_evidence(ctx: MasterContext, task: str | None = None) -> str:
    lines: list[str] = []
    lines.append("STANDING")
    lines.append("  " + ctx.standing.headline())
    if ctx.standing.phase_focus:
        lines.append("  Phase focus: " + ctx.standing.phase_focus)

    lines.append("\nRECENT DOJO RECORD (facts — do not invent beyond these)")
    if ctx.recent_days:
        lines += [_fmt_day(r) for r in ctx.recent_days]
    else:
        lines.append("  (empty — nothing has been logged. Demand the work.)")

    lines.append("\nDETERMINISTIC VISION (the machine's measurement; the only form truth you have)")
    if ctx.latest_vision:
        v = ctx.latest_vision
        lines.append(f"  stance={v.get('stance')}, duration_s={v.get('duration_s')}, "
                     f"frames={v.get('frames_evaluated')}, uncertain={v.get('frames_uncertain')}, "
                     f"mean_confidence={v.get('mean_confidence')}")
        if v.get("metrics_summary"):
            lines.append(f"  metrics={v['metrics_summary']}")
        if v.get("flags_observed"):
            lines.append(f"  flags={v['flags_observed']}")
        for n in v.get("notes", []):
            lines.append(f"  note: {n}")
    else:
        lines.append("  (no vision session recorded. You may NOT assert anything about their form.)")

    disc_txt = ctx.discernment.summary_for_master()
    if disc_txt:
        lines.append("\nDISCERNMENT (your judgment context — facts from the manual, not a script)")
        lines += ["  " + ln for ln in disc_txt.splitlines()]

    lines.append("\nMEMORY — SEALED PAST CONVERSATIONS (your own memory of this student; "
                 "quote them honestly, never invent one)")
    if ctx.memory:
        for m in ctx.memory:
            when = str(m.get("at") or m.get("sealed_at") or "")[:10]
            lines.append(f"  [{when}] Student: {_clip(m.get('question', ''))}")
            lines.append(f"  [{when}] Chirox: {_clip(m.get('answer', ''))}")
    else:
        lines.append("  (none yet — these are among your first words together)")

    if ctx.wisdom_growth and ctx.wisdom_growth.get("count"):
        g = ctx.wisdom_growth
        themes = ", ".join(t for t, _ in g.get("themes", [])[:4])
        lines.append(f"\nWISDOM TRAIL: {g['count']} sage dialogues sealed; growth markers {g.get('growth')}"
                     + (f"; recurring themes: {themes}" if themes else ""))

    lines.append("\nCURRICULUM (ground your guidance in these; cite the section names)")
    if ctx.passages:
        for sec in ctx.passages:
            lines.append(f'  §"{sec.title}":')
            lines += ["    " + ln for ln in sec.excerpt(500).splitlines() if ln.strip()]
    else:
        lines.append("  (none retrieved)")

    if ctx.wisdom_passages:
        lines.append("\nWISDOM PASSAGE (real text from the shelf — besides the curriculum above, "
                     "the ONLY words you may quote; cite the book by name)")
        for p in ctx.wisdom_passages:
            lines.append(f'  From {p.book}: "{_clip(p.text, 600)}"')
    elif not ctx.passages:
        lines.append("\n(No passage retrieved: quote no text and cite no book in this reply — "
                     "speak from principle and name it as principle.)")

    if ctx.question:
        lines.append(f"\nTHE STUDENT ASKS: {ctx.question}")
    lines.append("\n" + (task or _DEBRIEF_TASK))
    return "\n".join(lines)


_DEBRIEF_TASK = "TASK: Speak as Chirox. Give the debrief. End with tomorrow's non-negotiable minimum."

_CONVERSE_TASK = (
    "TASK: This is a spoken conversation, not a debrief. Answer the student's question "
    "directly, in Chirox's own voice — two to five sentences of natural speech (your words "
    "will be read aloud; no headings, no lists, no symbols). Stay grounded: the record, the "
    "sealed conversations, and the manual are your facts. When they hold no answer, say so "
    "plainly, then answer from principle and name it as principle. Never fabricate "
    "measurements or history. If you quote or cite any text, the quoted words must appear "
    "verbatim in the passages above — when no passage is given, cite nothing and quote no one."
)

_REFLECT_TASK = (
    "TASK: The student asks you to look back with him. This is reflection, not a debrief. "
    "From the sealed conversations, the recorded days, and the wisdom trail above, name in "
    "Chirox's own voice: what has genuinely moved since the earliest evidence here, what has "
    "stalled or keeps repeating, and one pattern the student may not see in himself. Growth "
    "counts only if the record shows it — thin evidence is named as thin, never inflated. "
    "Speak for the ear: no headings, no lists, no symbols, at most ten sentences. If you "
    "quote, the words must appear verbatim in the evidence above. End with ONE question for "
    "the student to sit with."
)

# Conversation runs cooler than the default: on small local models a higher
# temperature is where invented quotations and decorative mysticism come from.
_CONVERSE_TEMPERATURE = 0.4


# --- orchestration -------------------------------------------------------------


def debrief(config: Config | None = None, today: date | None = None, question: str | None = None) -> str:
    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex

    config = config or Config.load()
    ollama = Ollama(config)
    ok, reason = ollama.available()
    if not ok:
        raise MasterUnavailable(reason)

    codex = Codex(CODEX_PATH)
    curriculum = Curriculum()
    ctx = gather_evidence(config, codex, curriculum, today, question)
    return ollama.chat(system_prompt(), render_evidence(ctx))


def conversation_prompt(evidence: str, history: list[tuple[str, str]]) -> str:
    """Evidence + this sitting's turns → one user message. Pure, testable."""
    if not history:
        return evidence
    lines = ["CONVERSATION SO FAR (this sitting)"]
    for q, a in history:
        lines.append(f"  Student: {q}")
        lines.append(f"  Chirox: {a}")
    return "\n".join(lines) + "\n\n" + evidence


def _prepare_conversation(config: Config, question: str,
                          history: list[tuple[str, str]] | None,
                          today: date | None, reflect: bool) -> tuple[Ollama, str]:
    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex

    ollama = Ollama(config)
    ok, reason = ollama.available()
    if not ok:
        raise MasterUnavailable(reason)
    ctx = gather_evidence(config, Codex(CODEX_PATH), Curriculum(), today, question, deep=reflect)
    evidence = render_evidence(ctx, task=_REFLECT_TASK if reflect else _CONVERSE_TASK)
    return ollama, conversation_prompt(evidence, history or [])


def converse(config: Config | None = None, question: str = "",
             history: list[tuple[str, str]] | None = None, today: date | None = None,
             reflect: bool = False) -> str:
    """A normal conversation with Chirox — one being, one voice, spoken register.

    Same honesty rules as the debrief: the model sees only real evidence, and is
    told to mark principle as principle when the record holds no answer. With
    ``reflect`` the evidence windows widen and the task becomes looking back.
    """
    ollama, prompt = _prepare_conversation(config or Config.load(), question, history, today, reflect)
    return ollama.chat(system_prompt(), prompt, temperature=_CONVERSE_TEMPERATURE)


def converse_stream(config: Config | None = None, question: str = "",
                    history: list[tuple[str, str]] | None = None, today: date | None = None,
                    reflect: bool = False) -> Iterator[str]:
    """Like :func:`converse`, but yields whole sentences as the model produces
    them — the mouth begins with the first sentence, not after the last."""
    ollama, prompt = _prepare_conversation(config or Config.load(), question, history, today, reflect)
    yield from sentences(ollama.chat_stream(system_prompt(), prompt,
                                            temperature=_CONVERSE_TEMPERATURE))


def seal_exchange(question: str, answer: str, config: Config | None = None):
    """Every conversation is part of the record — logged, always, as promised."""
    from datetime import datetime, timezone

    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    config = config or Config.load()
    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize("conversation.append")
    event = codex.append("conversation", {
        "at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
    })
    sentinel.consume(grant)
    return event
