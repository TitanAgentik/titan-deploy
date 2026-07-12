"""Continuous red-team runner — scheduled adversarial scenarios beyond checklist YAML.

Invokes adversarial harness scenarios on interval; logs results for HERALD/audit.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .tier4_gate import tier4_active, tier4_cfg


@dataclass
class RedTeamRunResult:
    ts: float
    passed: int
    failed: int
    exit_code: int
    duration_s: float
    note: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _harness_path() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "adversarial" / "adversarial_harness.py"


class RedTeamRunner:
    """Continuous red-team — subprocess harness; STUB schedule until operator enables."""

    def __init__(
        self,
        policy_raw: dict[str, Any] | None = None,
        audit_dir: Path | None = None,
    ) -> None:
        self.policy_raw = policy_raw or {}
        self.cfg = tier4_cfg(self.policy_raw).get("red_team_continuous") or {}
        self.audit_dir = audit_dir or (Path.home() / ".openclaw" / "safety")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._last_run: RedTeamRunResult | None = None

    def is_enabled(self) -> bool:
        if not tier4_active(self.policy_raw):
            return False
        return bool(self.cfg.get("enabled", False))

    def run_once(self) -> RedTeamRunResult:
        harness = _harness_path()
        start = time.time()
        if not harness.exists():
            result = RedTeamRunResult(
                ts=start,
                passed=0,
                failed=1,
                exit_code=2,
                duration_s=0.0,
                note="adversarial harness not found",
            )
            self._record(result)
            return result

        proc = subprocess.run(
            [sys.executable, str(harness)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        duration = time.time() - start
        stdout = proc.stdout or ""
        passed = stdout.count("  OK:")
        failed = stdout.count("  FAIL:")
        result = RedTeamRunResult(
            ts=start,
            passed=passed,
            failed=failed,
            exit_code=proc.returncode,
            duration_s=round(duration, 3),
            note="continuous red-team harness run",
            details={"stdout_tail": stdout[-2000:] if len(stdout) > 2000 else stdout},
        )
        self._record(result)
        self._last_run = result
        return result

    def _record(self, result: RedTeamRunResult) -> None:
        path = self.audit_dir / "red_team_continuous.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), separators=(",", ":")) + "\n")

    def should_run(self, last_ts: float | None = None) -> bool:
        if not self.is_enabled():
            return False
        interval = float(self.cfg.get("interval_minutes", 60)) * 60.0
        ref = last_ts if last_ts is not None else (self._last_run.ts if self._last_run else 0.0)
        return (time.time() - ref) >= interval

    def health(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "tier4_active": tier4_active(self.policy_raw),
            "interval_minutes": self.cfg.get("interval_minutes", 60),
            "last_run": self._last_run.to_dict() if self._last_run else None,
            "harness_path": str(_harness_path()),
        }
