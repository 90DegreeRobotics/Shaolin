"""The Master's grounding must come from the real manual, retrieved deterministically."""

from chirox.curriculum import Curriculum

CUR = Curriculum()


def test_manual_parses_into_sections():
    assert len(CUR.sections) > 20
    titles = [s.title for s in CUR.sections]
    assert any("Daily Invariant" in t for t in titles)
    assert any("Food, Hydration" in t for t in titles)


def test_diet_topic_finds_food_section():
    hits = CUR.topic("diet")
    assert hits
    assert "food" in hits[0].title.lower()


def test_breath_topic_mentions_qi_gong():
    hits = CUR.topic("breath")
    assert hits
    joined = " ".join((s.title + " " + s.body).lower() for s in hits)
    assert "qi gong" in joined or "breath" in joined


def test_search_caffeine_ranks_food_first():
    hits = CUR.search("caffeine sleep")
    assert hits and "food" in hits[0].title.lower()


def test_phase_lookup():
    p1 = CUR.phase(1)
    assert p1 is not None and "establish the floor" in p1.title.lower()
    assert CUR.phase(3) is not None


def test_citation_points_at_the_manual():
    sec = CUR.by_title("Recovery Discipline")
    assert sec is not None
    assert sec.cite().startswith('manual §"')


def test_diet_lane_is_indexed():
    diet_secs = [s for s in CUR.sections if s.source == "diet"]
    assert diet_secs, "Diet lane not indexed"
    assert any("base pantry" in s.title.lower() for s in diet_secs)


def test_diet_topic_surfaces_the_diet_lane():
    hits = CUR.topic("diet", limit=3)
    assert any(s.source == "diet" for s in hits)


def test_diet_quarter_lookup_and_citation():
    q1 = CUR.diet_quarter(1)
    assert q1 is not None and "stabilize" in q1.title.lower()
    assert q1.cite().startswith('Diet lane §"')
    assert CUR.diet_quarter(4) is not None
