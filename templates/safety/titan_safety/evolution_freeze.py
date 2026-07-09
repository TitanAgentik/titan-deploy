"""Evolution freeze — block self-mod / evolution deploy while live capital is at risk.

When EVOLUTION_FROZEN is set (or capital_profile=live + freezeDuringLive),
promotion categories evolution_deploy / strategy_promotion that touch live
paths are denied until an operator explicitly unfreezes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

EVOLUTION_FROZEN_FLAG = "EVOLUTION_FROZEN"


class EvolutionFreeze:
    def __init__(self, safety_dir: Path | None = None) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.flag_path = self.safety_dir / EVOLUTION_FROZEN_FLAG

    def is_frozen(self) -> bool:
        return self.flag_path.exists()

    def freeze(self, operator: str, reason: str = "live capital") -> dict[str, Any]:
        payload = {"ts": time.time(), "operator": operator, "reason": reason, "frozen": True}
        self.flag_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def unfreeze(self, operator: str, reason: str = "operator YES") -> dict[str, Any]:
        payload = {"ts": time.time(), "operator": operator, "reason": reason, "frozen": False}
        if self.flag_path.exists():
            self.flag_path.unlink()
        # Append audit sibling
        audit = self.safety_dir / "evolution_freeze_audit.jsonl"
        with audit.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")
        return payload

    def status(self) -> dict[str, Any]:
        if not self.flag_path.exists():
            return {"frozen": False}
        data = json.loads(self.flag_path.read_text(encoding="utf-8"))
        return {"frozen": True, **data}

    def block_reason(self, category: str) -> str | None:
        """Return deny reason if this promotion category is blocked while frozen."""
        if not self.is_frozen():
            return None
        blocked = {
            "evolution_deploy",
            "strategy_promotion",
            "phase5_go_nogo",
            "flash_loan_live",
        }
        if category in blocked:
            return f"evolution frozen — cannot approve '{category}' until unfreeze"
        return None
