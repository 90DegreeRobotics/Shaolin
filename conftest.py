"""Ensure the repo root is importable so ``import chirox`` works under pytest
regardless of how it is invoked."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
