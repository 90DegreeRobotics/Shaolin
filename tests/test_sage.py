"""The growth ledger is real and honest: parse Chirox's structured reflection and
aggregate themes over time. (Model calls are exercised live, not in unit tests.)"""

from chirox.config import Config
from chirox.master.sage import SageDialogue, _parse_reflection, growth_summary
from chirox.record.codex import Codex
from chirox.record.ingest import commit_record
from chirox.sentinel import Sentinel


def test_parse_reflection_extracts_growth_and_themes():
    out = ("You reached for comfort where the question asked for honesty. Sit with the fear.\n"
           "GROWTH: searching\nTHEMES: fear, non-striving, honesty")
    growth, themes, reflection = _parse_reflection(out)
    assert growth == "searching"
    assert themes == ["fear", "non-striving", "honesty"]
    assert "GROWTH:" not in reflection and "comfort" in reflection


def test_parse_reflection_defaults_when_markers_absent():
    growth, themes, reflection = _parse_reflection("A plain reflection, no markers.")
    assert growth == "recorded" and themes == [] and reflection.startswith("A plain")


def test_growth_summary_tallies_themes_and_engagement(tmp_path):
    cx = Codex(tmp_path / "r.jsonl")
    s = Sentinel(cx, Config(sentinel_mode="enforce"), key_path=tmp_path / "op.key")
    s.init_operator()
    for gm, themes in (("searching", ["fear", "dao"]), ("deepening", ["fear", "stillness"])):
        commit_record(SageDialogue(3, "t", "probe", ["Tao Te Ching"], "ans", "refl", gm, themes), cx, s)

    g = growth_summary(cx)
    assert g["count"] == 2
    assert g["growth"] == {"searching": 1, "deepening": 1}
    assert dict(g["themes"])["fear"] == 2
