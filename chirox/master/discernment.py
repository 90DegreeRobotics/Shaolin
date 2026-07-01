"""The Master's discernment — NOT a filter.

This surfaces facts from the practitioner's OWN manual (the green/red Pain Rule,
the overload signs, the deload rhythm) so the Master can speak with a real
master's judgment. It never blocks, never refuses, never softens the voice. It
answers one question: *what does the evidence say the Master should be aware of?*

- **green** signals are the forge — shaking, heat, effort, boredom, breath
  challenge. The Master drives forward through these. They are not warnings.
- **red** signals are the fire that destroys — chest pain, faintness, radiating
  or sharp pain, loss of balance, panic. A crippled or dead student cannot walk
  the year. The Master names these once, with weight, in his own voice.
- **overload** signals (SAFETY.md / manual recovery) — sustained high pain,
  dread, insomnia, irritability, falling performance — mean the blade is losing
  its edge; the Master calls a deload, not because effort is bad, but because
  stupidity is.

The practitioner remains sovereign over his own risk. This module informs; it
does not command.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Each map is {match_substring: human-readable label}. Matching stays loose;
# what surfaces to the Master is always a clean word, never a raw stem.

# From SAFETY.md "Red" — stop-and-recover signals. Path-ending, not path-forging.
RED_TERMS = {
    "chest pain": "chest pain", "sharp pain": "sharp pain", "radiat": "radiating pain",
    "faint": "faintness", "black out": "blacking out", "blacked out": "blacking out",
    "loss of balance": "loss of balance", "lost balance": "loss of balance",
    "panic": "panic", "can't breathe": "breathlessness", "cannot breathe": "breathlessness",
    "passed out": "passing out", "numb": "numbness",
}

# The forge — the manual's "Green": continue with attention.
GREEN_TERMS = {
    "shak": "shaking", "trembl": "trembling", "burn": "burning effort", "heat": "heat",
    "boredom": "boredom", "bored": "boredom", "restless": "restlessness",
    "muscular": "muscular effort", "breath challenge": "breath challenge",
    "fatigue that resolved": "fatigue that resolves with rest",
}

# Overload pattern — the manual's recovery/deload triggers.
OVERLOAD_TERMS = {
    "dread": "dread", "insomnia": "insomnia", "can't sleep": "sleeplessness",
    "cannot sleep": "sleeplessness", "irritab": "irritability", "volatile": "emotional volatility",
    "joint pain": "joint pain", "no motivation": "loss of motivation",
    "exhausted": "exhaustion", "hate practice": "aversion to practice",
}

HIGH_PAIN = 6          # a single day at/above this is worth naming
SUSTAINED_PAIN = 5.0   # mean across recent days at/above this = overload trend


@dataclass
class Discernment:
    red_flags: list[str] = field(default_factory=list)
    overload_signals: list[str] = field(default_factory=list)
    green_signals: list[str] = field(default_factory=list)
    pain_note: str = ""

    def has_red(self) -> bool:
        return bool(self.red_flags)

    def has_overload(self) -> bool:
        return bool(self.overload_signals) or bool(self.pain_note)

    def summary_for_master(self) -> str:
        """Terse context lines for the prompt — facts, not instructions."""
        lines = []
        if self.red_flags:
            lines.append("PATH-ENDING SIGNAL in the record: " + "; ".join(self.red_flags)
                         + ". This is the fire that destroys — name it once, plainly, in voice.")
        if self.pain_note:
            lines.append(self.pain_note)
        if self.overload_signals:
            lines.append("Overload signs: " + "; ".join(self.overload_signals)
                         + ". Consider calling a deload — the blade is dulling.")
        if self.green_signals and not self.red_flags:
            lines.append("Forge signals (drive through these, do not coddle): "
                         + "; ".join(self.green_signals))
        return "\n".join(lines)


def _text_of(record: dict) -> str:
    return " ".join(str(v) for v in record.values() if isinstance(v, str)).lower()


def read_signals(recent_daily: list[dict]) -> Discernment:
    """Inspect recent daily check-in payloads (oldest..newest) for signals."""
    d = Discernment()
    if not recent_daily:
        return d

    hay = "\n".join(_text_of(r) for r in recent_daily)

    def collect(term_map: dict[str, str]) -> list[str]:
        found: list[str] = []
        for match, label in term_map.items():
            if match in hay and label not in found:
                found.append(label)
        return found

    d.red_flags = collect(RED_TERMS)
    d.green_signals = collect(GREEN_TERMS)
    d.overload_signals = collect(OVERLOAD_TERMS)

    pains = [int(r["pain_level"]) for r in recent_daily if str(r.get("pain_level", "")).strip().isdigit()]
    if pains:
        latest = pains[-1]
        mean = sum(pains) / len(pains)
        if latest >= HIGH_PAIN:
            d.pain_note = f"Latest recorded pain is {latest}/10 — high. Distinguish effort-ache from injury."
        elif mean >= SUSTAINED_PAIN:
            d.pain_note = f"Pain has averaged {mean:.1f}/10 across {len(pains)} days — a dulling trend."
    return d
