"""The curriculum — the Master's grounding corpus.

The manual (``1yeartoShaolin.md``) is parsed into heading-indexed sections.
Retrieval is deterministic keyword scoring — no embeddings, no external service.
Its whole purpose is discipline: the Master speaks diet, breath, stance, and
recovery guidance out of *these real passages*, and cites them. It does not
invent teaching, and it does not quote texts that are not present (Tao Te Ching /
Analects live in ``corpus/`` only if the practitioner adds them).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from chirox.config import DIET_DOC, FOODS_DOC, MANDARIN_DOCS, MANUAL_PATH, TEMPLE_DOC

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# Friendly topic -> query terms, so the Master can ask for "diet" or "breath".
TOPIC_QUERIES = {
    "diet": "food hydration stimulants caffeine protein eat meal alcohol sugar plate",
    "food": "food hydration stimulants caffeine protein eat meal plate",
    "foods": "foods catalog vegetables grains legumes fruit protein pantry shopping",
    "breath": "breath qi gong breathing brocades exhale inhale",
    "breathwork": "breath qi gong breathing brocades exhale inhale",
    "qigong": "qi gong breath brocades energy standing",
    "stance": "stance horse ma bu form posture knee spine root",
    "form": "form stance posture correction chirox knee spine",
    "recovery": "recovery sleep deload rest overload fatigue",
    "sleep": "sleep recovery rest hours",
    "meditation": "meditation breath sit chan mind pause",
    "conduct": "ren confucian respect conduct relationship benevolence",
    "lifestyle": "living clothing food digital screens sleep recovery boundaries",
    "injury": "pain injury knee joint red yellow stop",
    "mandarin": "mandarin pinyin tone character anki journal shadow aloud",
    "pinyin": "pinyin tone initial final sandhi pronunciation syllable",
    "characters": "character stroke radical hanzi write component",
    "speaking": "speaking shadow record aloud tone monologue mandarin",
    "vocabulary": "vocabulary hanzi pinyin stage word card",
    "schedule": "temple day rise bell block session morning evening gate",
    "routine": "temple day rise bell block session morning evening gate",
    "temple": "temple day rise bell block session morning evening gate",
}


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    body: str
    index: int
    source: str = "manual"   # "manual" | "diet" | other lane

    def excerpt(self, max_chars: int = 700) -> str:
        text = self.body.strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit("\n", 1)[0].rstrip() + "\n…"

    def cite(self) -> str:
        label = {
            "diet": "Diet lane",
            "mandarin": "Mandarin lane",
            "temple": "Temple day",
        }.get(self.source, "manual")
        return f'{label} §"{self.title}"'


# Default lane documents: source -> one path or a list of paths sharing the source.
DEFAULT_LANE_DOCS: dict[str, Path | list[Path]] = {
    "diet": [DIET_DOC, FOODS_DOC],
    "temple": TEMPLE_DOC,
    "mandarin": MANDARIN_DOCS,
}


class Curriculum:
    def __init__(
        self,
        manual_path: Path | None = None,
        lane_docs: dict[str, Path | list[Path]] | None = None,
    ):
        self.manual_path = Path(manual_path or MANUAL_PATH)
        # source -> path(s) for additional lane documents the Master grounds in.
        self.lane_docs = lane_docs if lane_docs is not None else DEFAULT_LANE_DOCS
        self.sections: list[Section] = self._parse_all()

    def _parse_all(self) -> list[Section]:
        sections: list[Section] = []
        idx = self._parse_doc(self.manual_path, "manual", sections, 0)
        for source, paths in self.lane_docs.items():
            for path in paths if isinstance(paths, list) else [paths]:
                idx = self._parse_doc(Path(path), source, sections, idx)
        return sections

    @staticmethod
    def _parse_doc(path: Path, source: str, out: list[Section], start_idx: int) -> int:
        if not path.exists():
            return start_idx
        lines = path.read_text(encoding="utf-8").splitlines()
        cur_title, cur_level, cur_body, idx = None, 0, [], start_idx
        for line in lines:
            m = _HEADING.match(line)
            if m:
                if cur_title is not None:
                    out.append(Section(cur_title, cur_level, "\n".join(cur_body), idx, source))
                    idx += 1
                cur_level = len(m.group(1))
                cur_title = m.group(2).strip()
                cur_body = []
            elif cur_title is not None:
                cur_body.append(line)
        if cur_title is not None:
            out.append(Section(cur_title, cur_level, "\n".join(cur_body), idx, source))
            idx += 1
        return idx

    # --- lookup --------------------------------------------------------------

    def by_title(self, substr: str) -> Section | None:
        s = substr.lower()
        for sec in self.sections:
            if s in sec.title.lower():
                return sec
        return None

    def search(self, query: str, limit: int = 3) -> list[Section]:
        terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
        scored: list[tuple[int, Section]] = []
        for sec in self.sections:
            title_l = sec.title.lower()
            body_l = sec.body.lower()
            score = sum(title_l.count(t) * 5 + body_l.count(t) for t in terms)
            if score:
                scored.append((score, sec))
        scored.sort(key=lambda x: (-x[0], x[1].index))
        return [sec for _, sec in scored[:limit]]

    def topic(self, name: str, limit: int = 2) -> list[Section]:
        query = TOPIC_QUERIES.get(name.lower(), name)
        return self.search(query, limit=limit)

    def phase(self, n: int) -> Section | None:
        for sec in self.sections:
            if sec.title.lower().startswith(f"phase {n}:"):
                return sec
        return None

    def daily_invariant(self) -> Section | None:
        return self.by_title("Daily Invariant")

    def diet_quarter(self, n: int) -> Section | None:
        for sec in self.sections:
            if sec.source == "diet" and sec.title.lower().startswith(f"quarter {n}:"):
                return sec
        return None
