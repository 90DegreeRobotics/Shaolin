"""The Sentinel — the authority gate (Sentinel Law).

No action of consequence occurs without explicit, recorded authorization. Every
decision — grant or denial — is sealed into the Codex as evidence *before* the
action proceeds. Absence of proof is denial.

Scope, stated honestly: this is a **local single-operator** gate. The operator's
authority is a locally generated key established once, in a sealed provisioning
event. It is fail-closed against a missing or malformed key. It does not attempt
cross-machine identity or cross-process replay defense — those are not
meaningful for a private, single-user Dojo Record, and claiming them would be
theater. What it does guarantee is real: no write without a present operator key
under ``enforce``, and a sealed authorization trail for every consequential act.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from chirox.config import Config
from chirox.record.codex import Codex

_KEY_RE = re.compile(r"^[0-9a-f]{64}$")


class AuthorizationDenied(Exception):
    """Raised under ``enforce`` when an action is not authorized."""


@dataclass(frozen=True)
class Grant:
    action: str
    operator: str
    granted: bool
    nonce: str
    decision_seq: int
    mode: str


class Sentinel:
    def __init__(self, codex: Codex, config: Config, key_path: Path | None = None):
        self.codex = codex
        self.config = config
        from chirox.config import SENTINEL_KEY_PATH

        self.key_path = Path(key_path) if key_path else SENTINEL_KEY_PATH
        self._consumed: set[str] = set()

    # --- operator identity ---------------------------------------------------

    def operator_provisioned(self) -> bool:
        return self._load_key() is not None

    def init_operator(self) -> Grant | None:
        """Establish the local operator once, sealing the act. Idempotent.

        Returns the sealed provisioning grant on first establishment, or None if
        the operator already exists.
        """
        if self.operator_provisioned():
            return None
        key = secrets.token_hex(32)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_text(key + "\n", encoding="utf-8")
        ev = self.codex.append(
            "operator_provisioned",
            {"operator": self.config.operator_id, "key_fingerprint": key[:8]},
        )
        return Grant(
            action="operator.provision",
            operator=self.config.operator_id,
            granted=True,
            nonce=secrets.token_hex(8),
            decision_seq=ev.seq,
            mode=self.config.sentinel_mode,
        )

    def _load_key(self) -> str | None:
        if not self.key_path.exists():
            return None
        key = self.key_path.read_text(encoding="utf-8").strip()
        return key if _KEY_RE.match(key) else None

    # --- the gate ------------------------------------------------------------

    def authorize(self, action: str) -> Grant:
        """Authorize a consequential action, sealing the decision as evidence.

        Under ``enforce`` a denial raises ``AuthorizationDenied`` and the caller
        must not proceed. Under ``shadow`` the decision is still sealed but a
        denied grant is returned (``granted=False``) rather than raised.
        """
        key = self._load_key()
        granted = key is not None
        nonce = secrets.token_hex(8)
        ev = self.codex.append(
            "sentinel_authority_decision",
            {
                "action": action,
                "operator": self.config.operator_id,
                "granted": granted,
                "nonce": nonce,
                "mode": self.config.sentinel_mode,
            },
        )
        grant = Grant(
            action=action,
            operator=self.config.operator_id,
            granted=granted,
            nonce=nonce,
            decision_seq=ev.seq,
            mode=self.config.sentinel_mode,
        )
        if not granted and self.config.sentinel_mode == "enforce":
            raise AuthorizationDenied(
                f"no authorized operator for '{action}' (absent or malformed key). "
                "Run operator provisioning, or set sentinel_mode='shadow' to observe only."
            )
        return grant

    def consume(self, grant: Grant) -> None:
        """Single-use enforcement within this process."""
        if grant.nonce in self._consumed:
            raise AuthorizationDenied(f"grant nonce already consumed for '{grant.action}'")
        self._consumed.add(grant.nonce)
