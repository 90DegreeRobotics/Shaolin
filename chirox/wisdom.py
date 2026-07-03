"""The wisdom corpus — Chirox the sage's grounding in real texts.

Public-domain philosophy (Tao Te Ching, Analects, Dhammapada, Art of War) is
chunked into passages and retrieved by keyword. Chirox speaks and cites FROM
these passages; it does not fabricate quotations or attributions. This is the
honest form of a sage: the wisdom is real and checkable, not invented in the
voice of a dead master.

Texts are fetched once from Project Gutenberg (kept out of git; see
Wisdom/README.md) and are fully offline thereafter.
"""

from __future__ import annotations

import random
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# filename -> (display title, Project Gutenberg plain-text URL)
# IDs verified against the Gutendex catalog 2026-07-03. Daoism, Confucianism,
# and Buddhism each get real texts — the sage grounds in them, the narrator
# reads them aloud ("Chirox, read me the tao te ching").
CORPUS = {
    # Daoism
    "tao_te_ching.txt": ("Tao Te Ching", "https://www.gutenberg.org/cache/epub/216/pg216.txt"),
    "chuang_tzu.txt": ("Chuang Tzu", "https://www.gutenberg.org/cache/epub/59709/pg59709.txt"),
    # Confucianism
    "analects_confucius.txt": ("The Analects of Confucius", "https://www.gutenberg.org/cache/epub/3330/pg3330.txt"),
    "confucius_mencius.txt": ("Chinese Literature: Confucius and Mencius",
                              "https://www.gutenberg.org/cache/epub/10056/pg10056.txt"),
    # Buddhism
    "dhammapada.txt": ("The Dhammapada", "https://www.gutenberg.org/cache/epub/2017/pg2017.txt"),
    "gospel_of_buddha.txt": ("The Gospel of Buddha", "https://www.gutenberg.org/cache/epub/35895/pg35895.txt"),
    "light_of_asia.txt": ("The Light of Asia", "https://www.gutenberg.org/cache/epub/8920/pg8920.txt"),
    # Strategy
    "art_of_war_sunzi.txt": ("The Art of War", "https://www.gutenberg.org/cache/epub/132/pg132.txt"),
}

_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I | re.S)
_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I | re.S)
_BOILER = ("project gutenberg", "gutenberg", "transcriber", "produced by", "http://",
           "https://", "ebook", "copyright", "public domain", "distributed proofread")


def _wisdom_dir() -> Path:
    from chirox.config import WISDOM_DIR

    return WISDOM_DIR


def ensure_corpus(texts_dir: Path | None = None) -> list[str]:
    """Download any missing corpus texts once. Returns the filenames fetched."""
    d = Path(texts_dir or _wisdom_dir())
    d.mkdir(parents=True, exist_ok=True)
    fetched: list[str] = []
    for fn, (_title, url) in CORPUS.items():
        p = d / fn
        if not p.exists():
            try:
                urllib.request.urlretrieve(url, p)
                fetched.append(fn)
            except Exception:
                pass  # offline / blocked: the library simply grounds in what is present
    return fetched


@dataclass(frozen=True)
class Passage:
    book: str
    text: str
    index: int

    def cite(self) -> str:
        return self.book


def _strip_gutenberg(raw: str) -> str:
    s = _START.search(raw)
    if s:
        raw = raw[s.end():]
    e = _END.search(raw)
    if e:
        raw = raw[:e.start()]
    return raw


def _clean(paragraph: str) -> str:
    return re.sub(r"\s+", " ", paragraph).strip()


class WisdomLibrary:
    def __init__(self, texts_dir: Path | None = None):
        self.dir = Path(texts_dir or _wisdom_dir())
        self.passages: list[Passage] = self._load()

    def _load(self) -> list[Passage]:
        out: list[Passage] = []
        idx = 0
        for fn, (title, _url) in CORPUS.items():
            p = self.dir / fn
            if not p.exists():
                continue
            body = _strip_gutenberg(p.read_text(encoding="utf-8", errors="ignore"))
            for para in re.split(r"\n\s*\n", body):
                text = _clean(para)
                if not (80 <= len(text) <= 1200):
                    continue
                low = text.lower()
                if any(b in low for b in _BOILER):
                    continue
                out.append(Passage(title, text, idx))
                idx += 1
        return out

    def books(self) -> list[str]:
        return sorted({p.book for p in self.passages})

    def search(self, query: str, limit: int = 3) -> list[Passage]:
        terms = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2]
        scored: list[tuple[int, Passage]] = []
        for p in self.passages:
            low = p.text.lower()
            score = sum(low.count(t) for t in terms)
            if score:
                scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1].index))
        return [p for _, p in scored[:limit]]

    def random_passage(self, rng: random.Random | None = None, book: str | None = None) -> Passage | None:
        pool = [p for p in self.passages if book is None or p.book == book]
        if not pool:
            return None
        return (rng or random).choice(pool)
