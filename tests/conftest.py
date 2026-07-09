"""Pytest configuration — add safety package to path."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAFETY = ROOT / "templates" / "safety"
if str(SAFETY) not in sys.path:
    sys.path.insert(0, str(SAFETY))
