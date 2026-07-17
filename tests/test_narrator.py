"""Tests for the narrator — pure text preparation and doc resolution. No audio."""

from chirox.narrator import CHUNK_TARGET, chunk_text, clean_markdown, resolve_doc


# --- markdown cleaning -----------------------------------------------------------


def test_clean_strips_code_fences():
    md = "Before.\n\n```python\nx = 1\n```\n\nAfter."
    out = clean_markdown(md)
    assert "x = 1" not in out
    assert "Before." in out
    assert "After." in out


def test_clean_headers_become_sentences():
    out = clean_markdown("## The Daily Loop\n\nTrain daily.")
    assert "The Daily Loop." in out
    assert "#" not in out


def test_clean_links_read_as_text():
    out = clean_markdown("See [the manual](docs/manual.md) for details.")
    assert out == "See the manual for details."


def test_clean_images_and_hrules_dropped():
    out = clean_markdown("![diagram](x.png)\n\n---\n\nText.")
    assert out == "Text."


def test_clean_table_rows_become_lists():
    out = clean_markdown("| Machine | Role |\n|---|---|\n| Mirror | measures |")
    assert "Machine, Role." in out
    assert "Mirror, measures." in out
    assert "|" not in out


def test_clean_bullets_and_emphasis():
    out = clean_markdown("- **Measured** means real\n- *Uncertain* means weak")
    assert "Measured means real" in out
    assert "*" not in out


# --- chunking ----------------------------------------------------------------------


def test_chunks_group_sentences_under_target():
    text = "One. Two. Three. Four."
    chunks = chunk_text(text, target=12)
    assert all(len(c) <= 12 or "." not in c[:-1] for c in chunks)
    assert " ".join(chunks) == text


def test_paragraph_is_a_chunk_boundary():
    chunks = chunk_text("First paragraph here.\n\nSecond paragraph here.", target=1000)
    assert chunks == ["First paragraph here.", "Second paragraph here."]


def test_long_unpunctuated_run_is_hard_split():
    text = "word " * 400  # ~2000 chars, no sentence ends
    chunks = chunk_text(text.strip(), target=200)
    assert len(chunks) > 1
    assert all(len(c) <= 2 * 200 for c in chunks)


def test_no_text_is_lost():
    text = ("Alpha beta gamma. Delta epsilon zeta! Eta theta iota?\n\n"
            "Kappa lambda mu. Nu xi omicron.")
    chunks = chunk_text(text, target=30)
    rejoined = " ".join(chunks).split()
    assert rejoined == text.replace("\n\n", " ").split()


def test_default_target_sane():
    assert 200 <= CHUNK_TARGET <= 1000


# --- spoken doc resolution ------------------------------------------------------------


def test_resolve_doc_manual():
    got = resolve_doc("read the manual")
    assert got is not None
    label, path = got
    assert label == "the manual"
    assert path.name == "1yeartoShaolin.md"


def test_resolve_doc_guide():
    got = resolve_doc("read me the dummies guide please")
    assert got is not None
    assert got[1].name == "Shaolin_For_Dummies.md"


def test_resolve_doc_kung_fu_study_guide():
    got = resolve_doc("read me the kung fu study guide please")
    assert got is not None
    assert got[0] == "the Kung Fu study guide"
    assert got[1].name == "SHAOLIN_KUNG_FU_STUDY_GUIDE.md"


def test_resolve_doc_study_guide_disambiguates_from_beginner_guide():
    got = resolve_doc("read me the study guide please")
    assert got is not None
    assert got[0] == "the Kung Fu study guide"


def test_resolve_doc_none_for_unknown():
    assert resolve_doc("read me a poem") is None
    assert resolve_doc("what should i read next") is None


# --- the reading library ---------------------------------------------------------------


def test_title_keys_drop_stopwords():
    from chirox.narrator import title_keys

    assert title_keys("The Gospel of Buddha") == {"gospel", "buddha"}
    assert title_keys("Tao Te Ching") == {"tao", "te", "ching"}


def _catalog(tmp_path):
    from pathlib import Path

    return [
        ("Tao Te Ching", {"tao", "te", "ching"}, Path("tao.txt")),
        ("The Gospel of Buddha", {"gospel", "buddha"}, Path("gospel.txt")),
        ("The Dhammapada", {"dhammapada"}, Path("dhamma.txt")),
        ("the manual", {"manual"}, Path("manual.md")),
    ]


def test_match_readable_best_overlap(tmp_path):
    from chirox.narrator import match_readable

    label, path = match_readable("read me the gospel of buddha", _catalog(tmp_path))
    assert label == "The Gospel of Buddha"


def test_match_readable_survives_whisper_splits(tmp_path):
    from chirox.narrator import match_readable

    # Whisper often splits unfamiliar words: "dhamma pada"
    got = match_readable("read me the dhamma pada", _catalog(tmp_path))
    assert got is not None
    assert got[0] == "The Dhammapada"


def test_match_readable_none_when_nothing_matches(tmp_path):
    from chirox.narrator import match_readable

    assert match_readable("read me war and peace", _catalog(tmp_path)) is None


# --- bookmarks -------------------------------------------------------------------------


def test_reading_progress_roundtrip(tmp_path):
    from chirox.narrator import reading_progress, set_reading_progress

    p = tmp_path / "progress.json"
    assert reading_progress(p) == {}
    set_reading_progress("tao.txt", 42, path=p)
    assert reading_progress(p) == {"tao.txt": 42}
    set_reading_progress("tao.txt", 0, path=p)   # finishing clears the bookmark
    assert reading_progress(p) == {}


# --- gutenberg auto-strip ---------------------------------------------------------------


def test_prepare_strips_gutenberg_boilerplate(tmp_path):
    from chirox.narrator import prepare

    raw = ("The Project Gutenberg eBook of Testbook\n\nlicense junk\n\n"
           "*** START OF THE PROJECT GUTENBERG EBOOK TESTBOOK ***\n\n"
           "The way that can be told is not the eternal way.\n\n"
           "*** END OF THE PROJECT GUTENBERG EBOOK TESTBOOK ***\n\nmore junk")
    f = tmp_path / "book.txt"
    f.write_text(raw, encoding="utf-8")
    chunks = prepare(f)
    joined = " ".join(chunks)
    assert "eternal way" in joined
    assert "license junk" not in joined
    assert "more junk" not in joined


# --- narration lock (ear echo gate) -----------------------------------------------------


def test_claim_narration_lock_writes_pid(tmp_path, monkeypatch):
    from chirox.narrator import claim_narration_lock, narration_pid

    lock = tmp_path / "_narration.pid"
    monkeypatch.setattr("chirox.narrator._lock_path", lambda: lock)
    monkeypatch.setattr("chirox.narrator._pid_alive", lambda pid: pid == 4242)
    claim_narration_lock(4242)
    assert lock.read_text(encoding="utf-8").strip() == "4242"
    assert narration_pid() == 4242


def test_spawn_narration_claims_lock_before_returning(tmp_path, monkeypatch):
    import subprocess

    from chirox import narrator

    lock = tmp_path / "_narration.pid"
    monkeypatch.setattr(narrator, "_lock_path", lambda: lock)

    class _Proc:
        pid = 9090

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _Proc())
    pid = narrator.spawn_narration(tmp_path / "manual.md")
    assert pid == 9090
    assert lock.read_text(encoding="utf-8").strip() == "9090"
