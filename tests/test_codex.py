"""The record must remember truthfully. Prove the chain links, catches tampering,
never silently deletes, and that the Sentinel fails closed without an operator."""

import json

import pytest

from chirox.config import Config
from chirox.record.codex import Codex, CodexIntegrityError
from chirox.sentinel import AuthorizationDenied, Sentinel


def make_codex(tmp_path):
    return Codex(tmp_path / "record.jsonl")


# --- Codex: Forever Law --------------------------------------------------------


def test_append_links_the_chain(tmp_path):
    cx = make_codex(tmp_path)
    a = cx.append("daily_checkin", {"day_number": 1})
    b = cx.append("daily_checkin", {"day_number": 2})
    assert a.seq == 0 and b.seq == 1
    assert a.prev_hash == "0" * 64
    assert b.prev_hash == a.hash
    ok, err = cx.verify()
    assert ok, err


def test_empty_codex_verifies(tmp_path):
    ok, err = make_codex(tmp_path).verify()
    assert ok and err is None


def test_tampering_is_detected(tmp_path):
    cx = make_codex(tmp_path)
    cx.append("daily_checkin", {"day_number": 1, "pain_level": 2})
    cx.append("daily_checkin", {"day_number": 2, "pain_level": 3})

    # Rewrite a payload value while leaving the stored hash intact.
    lines = cx.path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["payload"]["pain_level"] = 9  # a comforting lie
    lines[0] = json.dumps(first, ensure_ascii=False)
    cx.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, err = cx.verify()
    assert not ok
    assert "tampered" in err
    with pytest.raises(CodexIntegrityError):
        cx.require_intact()


def test_forget_is_recorded_not_silent(tmp_path):
    cx = make_codex(tmp_path)
    cx.append("daily_checkin", {"day_number": 1})
    cx.forget(target_seq=0, reason="entered wrong day", operator="local-operator")
    types = [e.type for e in cx.events()]
    # The original event still exists; the erasure is remembered as its own event.
    assert types == ["daily_checkin", "forget"]
    assert cx.verify()[0]


# --- Sentinel: authority -------------------------------------------------------


def test_sentinel_provisions_operator_once(tmp_path):
    cx = make_codex(tmp_path)
    cfg = Config(sentinel_mode="enforce")
    s = Sentinel(cx, cfg, key_path=tmp_path / "op.key")
    assert not s.operator_provisioned()
    grant = s.init_operator()
    assert grant is not None and grant.granted
    assert s.operator_provisioned()
    assert (tmp_path / "op.key").exists()
    # Idempotent: second init does nothing.
    assert s.init_operator() is None
    assert any(e.type == "operator_provisioned" for e in cx.events())


def test_authorize_seals_decision(tmp_path):
    cx = make_codex(tmp_path)
    cfg = Config(sentinel_mode="enforce")
    s = Sentinel(cx, cfg, key_path=tmp_path / "op.key")
    s.init_operator()
    grant = s.authorize("record.append:daily")
    assert grant.granted
    decisions = [e for e in cx.events("sentinel_authority_decision")]
    assert decisions and decisions[-1].payload["action"] == "record.append:daily"
    assert cx.verify()[0]


def test_enforce_fails_closed_without_operator(tmp_path):
    cx = make_codex(tmp_path)
    cfg = Config(sentinel_mode="enforce")
    s = Sentinel(cx, cfg, key_path=tmp_path / "missing.key")
    with pytest.raises(AuthorizationDenied):
        s.authorize("record.append:daily")
    # Even a denied decision is sealed as evidence.
    assert any(
        e.payload.get("granted") is False for e in cx.events("sentinel_authority_decision")
    )


def test_shadow_mode_observes_without_blocking(tmp_path):
    cx = make_codex(tmp_path)
    cfg = Config(sentinel_mode="shadow")
    s = Sentinel(cx, cfg, key_path=tmp_path / "missing.key")
    grant = s.authorize("record.append:daily")  # no raise
    assert grant.granted is False


def test_grant_is_single_use(tmp_path):
    cx = make_codex(tmp_path)
    cfg = Config(sentinel_mode="enforce")
    s = Sentinel(cx, cfg, key_path=tmp_path / "op.key")
    s.init_operator()
    grant = s.authorize("record.append:daily")
    s.consume(grant)
    with pytest.raises(AuthorizationDenied):
        s.consume(grant)
