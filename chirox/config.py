"""Chirox configuration and path resolution.

Runtime data (the practitioner's actual record and config) lives under
``Dojo/data`` in the repo and is git-ignored — the Dojo Record is private and is
never committed (see STATUS.md / ROADMAP.md).

The config is a plain dataclass persisted as JSON. On first run the practice
start date defaults to today, so ``day 1`` is the day Chirox first meets you.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# chirox/ package dir -> repo root is its parent.
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent

# The manual is the Master's grounding corpus.
MANUAL_PATH = REPO_ROOT / "1yeartoShaolin.md"

# Lane documents also grounded in by the Master (curriculum extends over these).
DIET_DOC = REPO_ROOT / "Diet" / "README.md"

# Private runtime data — git-ignored.
DATA_DIR = REPO_ROOT / "Dojo" / "data"
CONFIG_PATH = DATA_DIR / "chirox_config.json"
CODEX_PATH = DATA_DIR / "dojo_record.jsonl"
SENTINEL_KEY_PATH = DATA_DIR / "local_operator.key"

# Session video archive — the visual improvement timeline. Large + private, so
# git-ignored; the Codex holds the manifest (metadata), not the video itself.
MEDIA_DIR = REPO_ROOT / "Dojo" / "media"

# Local ML model assets (the pose landmarker). Downloaded once, kept out of git.
MODEL_DIR = REPO_ROOT / "Dojo" / "models"

# Public-domain philosophy corpus the sage grounds in. Fetched once, kept out of
# git (raw Gutenberg dumps); Wisdom/README.md documents the sources + licence.
WISDOM_DIR = REPO_ROOT / "Wisdom" / "texts"

# Local voice models (Whisper STT / Piper TTS). Downloaded once, kept out of git.
VOICE_DIR = REPO_ROOT / "Dojo" / "voice"


def ensure_data_dir() -> Path:
    """Create the private data directory if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Chirox runtime configuration.

    Fields:
        practice_start: ISO date the year began (day 1). Defaults to first run.
        model:          local Ollama model that gives the Master his voice.
                        Default qwen2.5:14b-instruct — fits a 12GB GPU, strong
                        instruction-following and passage grounding, and best-in-
                        class Chinese for the Mandarin lane.
        ollama_url:     base URL of the local Ollama server (sovereign, offline).
        sentinel_mode:  "enforce" (fail closed) or "shadow" (seal but do not block).
        operator_id:    the authorized local operator (the practitioner).
    """

    practice_start: str = field(default_factory=lambda: date.today().isoformat())
    model: str = "qwen2.5:14b-instruct"
    ollama_url: str = "http://localhost:11434"
    sentinel_mode: str = "enforce"
    operator_id: str = "local-operator"

    # --- persistence ---------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load config from disk, creating a default (and persisting it) if absent."""
        path = path or CONFIG_PATH
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**known)
        cfg = cls()
        cfg.save(path)
        return cfg

    def save(self, path: Path | None = None) -> Path:
        path = path or CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        return path

    @property
    def practice_start_date(self) -> date:
        return date.fromisoformat(self.practice_start)
