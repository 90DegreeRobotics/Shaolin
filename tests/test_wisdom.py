"""The sage grounds in real texts. Tests are hermetic (a fixture, no network),
with one guarded check against the fetched corpus if present."""

import pytest

from chirox.wisdom import Passage, WisdomLibrary

FIXTURE = """The Project Gutenberg eBook of Test

*** START OF THE PROJECT GUTENBERG EBOOK TEST ***

The highest excellence is like water. Water benefits all things and does not strive; it dwells in places the crowd dislikes, and so is near to the Dao.

The superior man is modest in his speech but exceeds in his actions. To learn without thinking is labour lost; to think without learning is perilous.

*** END OF THE PROJECT GUTENBERG EBOOK TEST ***

This trailing paragraph mentions Project Gutenberg licence boilerplate and must be dropped.
"""


def make_lib(tmp_path):
    (tmp_path / "tao_te_ching.txt").write_text(FIXTURE, encoding="utf-8")
    return WisdomLibrary(tmp_path)


def test_loads_and_strips_boilerplate(tmp_path):
    lib = make_lib(tmp_path)
    assert lib.passages
    assert lib.books() == ["Tao Te Ching"]
    joined = " ".join(p.text for p in lib.passages).lower()
    assert "project gutenberg" not in joined  # boilerplate removed


def test_search_finds_relevant_passage(tmp_path):
    lib = make_lib(tmp_path)
    hits = lib.search("water benefits", limit=2)
    assert hits and isinstance(hits[0], Passage)
    assert "water" in hits[0].text.lower()


def test_random_and_citation(tmp_path):
    lib = make_lib(tmp_path)
    p = lib.random_passage()
    assert p is not None and p.cite() == p.book


def test_real_corpus_if_fetched():
    lib = WisdomLibrary()
    if not lib.passages:
        pytest.skip("wisdom corpus not fetched in this environment")
    assert len(lib.passages) > 50
    assert "The Analects of Confucius" in lib.books()
