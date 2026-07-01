"""The Codex — an append-only, hash-chained Dojo Record.

Forever Law made concrete: every entry links to the one before it by SHA-256,
so the chain is tamper-evident and derivable without trusting mutable state.
There is deliberately **no update and no delete**. Forgetting is a distinct,
recorded ``forget`` event — the record of an erasure, never a silent one.

Storage is JSON Lines (one event per line) so the record is human-readable and
survives migrations and tooling changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

GENESIS_HASH = "0" * 64


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seal(seq: int, ts: str, event_type: str, payload: dict, prev_hash: str) -> str:
    """Deterministic hash over the sealed content of one event."""
    body = json.dumps(
        {"seq": seq, "ts": ts, "type": event_type, "payload": payload, "prev_hash": prev_hash},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Event:
    seq: int
    ts: str
    type: str
    payload: dict
    prev_hash: str
    hash: str

    def to_line(self) -> str:
        return json.dumps(
            {
                "seq": self.seq,
                "ts": self.ts,
                "type": self.type,
                "payload": self.payload,
                "prev_hash": self.prev_hash,
                "hash": self.hash,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_line(cls, line: str) -> "Event":
        d = json.loads(line)
        return cls(
            seq=d["seq"],
            ts=d["ts"],
            type=d["type"],
            payload=d["payload"],
            prev_hash=d["prev_hash"],
            hash=d["hash"],
        )


class CodexIntegrityError(Exception):
    """Raised when the chain fails verification — the record cannot be trusted."""


class Codex:
    """An append-only hash-chained event log at ``path``."""

    def __init__(self, path: Path):
        self.path = Path(path)

    # --- reading -------------------------------------------------------------

    def _read_lines(self) -> list[str]:
        if not self.path.exists():
            return []
        return [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def events(self, event_type: str | None = None) -> Iterator[Event]:
        for ln in self._read_lines():
            ev = Event.from_line(ln)
            if event_type is None or ev.type == event_type:
                yield ev

    def head(self) -> Event | None:
        lines = self._read_lines()
        return Event.from_line(lines[-1]) if lines else None

    def head_hash(self) -> str:
        h = self.head()
        return h.hash if h else GENESIS_HASH

    def next_seq(self) -> int:
        h = self.head()
        return (h.seq + 1) if h else 0

    def tail(self, n: int, event_type: str | None = None) -> list[Event]:
        evs = list(self.events(event_type))
        return evs[-n:] if n > 0 else evs

    def is_empty(self) -> bool:
        return not self._read_lines()

    # --- writing (append-only) ----------------------------------------------

    def append(self, event_type: str, payload: dict) -> Event:
        """Seal one new event onto the end of the chain.

        Forever Law: if the record cannot be committed, the action must fail —
        so this raises rather than returning on any write failure.
        """
        prev_hash = self.head_hash()
        seq = self.next_seq()
        ts = _now_iso()
        digest = _seal(seq, ts, event_type, payload, prev_hash)
        ev = Event(seq=seq, ts=ts, type=event_type, payload=payload, prev_hash=prev_hash, hash=digest)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(ev.to_line() + "\n")
            fh.flush()
        return ev

    def forget(self, target_seq: int, reason: str, *, operator: str) -> Event:
        """Record an act of forgetting — never a silent delete.

        The forgotten event stays in the chain (its history is not rewritten);
        this seals an explicit, attributable marker that it is to be treated as
        withdrawn. Erasure is remembered.
        """
        return self.append(
            "forget",
            {"target_seq": target_seq, "reason": reason, "operator": operator},
        )

    # --- integrity -----------------------------------------------------------

    def verify(self) -> tuple[bool, str | None]:
        """Walk the chain; confirm sequence, linkage, and every seal.

        Returns (ok, error_message). ok is False on the first break found.
        """
        prev_hash = GENESIS_HASH
        expected_seq = 0
        for ev in self.events():
            if ev.seq != expected_seq:
                return False, f"sequence break at seq {ev.seq}: expected {expected_seq}"
            if ev.prev_hash != prev_hash:
                return False, f"chain break at seq {ev.seq}: prev_hash does not match prior event"
            recomputed = _seal(ev.seq, ev.ts, ev.type, ev.payload, ev.prev_hash)
            if recomputed != ev.hash:
                return False, f"tampered content at seq {ev.seq}: seal does not match payload"
            prev_hash = ev.hash
            expected_seq += 1
        return True, None

    def require_intact(self) -> None:
        ok, err = self.verify()
        if not ok:
            raise CodexIntegrityError(err or "codex integrity check failed")
