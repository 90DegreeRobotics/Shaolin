"""The Master's brain — evidence assembly + local Ollama call.

Evidence assembly is pure and testable (no network). The model call is the only
part that reaches the local Ollama server. If Ollama is not running or the model
is not present, the Master says so plainly and refuses to speak — he does not
fabricate a debrief. Silence is honest; a hallucinated master is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

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

    def chat(self, system: str, user: str, temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            r = requests.post(f"{self.url}/api/chat", json=payload, timeout=300)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise MasterUnavailable(f"Ollama call failed: {exc}") from exc
        return r.json()["message"]["content"].strip()


# --- evidence assembly (pure) --------------------------------------------------


@dataclass
class MasterContext:
    standing: DojoDay
    recent_days: list[dict]
    latest_vision: dict | None
    discernment: Discernment
    passages: list[Section] = field(default_factory=list)
    question: str | None = None


def gather_evidence(
    config: Config,
    codex,
    curriculum: Curriculum,
    today: date | None = None,
    question: str | None = None,
) -> MasterContext:
    standing = dojo_day(config.practice_start_date, today)
    recent_days = [e.payload for e in codex.tail(5, "daily_checkin")]
    vision_events = codex.tail(1, "vision_session")
    latest_vision = vision_events[0].payload if vision_events else None
    disc = read_signals(recent_days)

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

    return MasterContext(standing, recent_days, latest_vision, disc, passages, question)


def _fmt_day(rec: dict) -> str:
    keys = ["day_number", "sleep", "meditation", "qi_gong", "kung_fu", "walk",
            "food_hydration", "pain_level", "mood", "one_lesson"]
    parts = [f"{k}={rec.get(k)!r}" for k in keys if rec.get(k) not in (None, "", 0)]
    return "  - " + ", ".join(parts)


def render_evidence(ctx: MasterContext) -> str:
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

    lines.append("\nCURRICULUM (ground your guidance in these; cite the section names)")
    if ctx.passages:
        for sec in ctx.passages:
            lines.append(f'  §"{sec.title}":')
            lines += ["    " + ln for ln in sec.excerpt(500).splitlines() if ln.strip()]
    else:
        lines.append("  (none retrieved)")

    if ctx.question:
        lines.append(f"\nTHE STUDENT ASKS: {ctx.question}")
    lines.append("\nTASK: Speak as Chirox. Give the debrief. End with tomorrow's non-negotiable minimum.")
    return "\n".join(lines)


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
