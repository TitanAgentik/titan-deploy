"""Promotion gate — explicit human YES with append-only audit log."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .promotion_stats import StatsGateConfig, StrategyStats, StrategyStatsGate


AUDIT_FILE = "promotion_audit.jsonl"
REQUIRED_APPROVAL = "YES"

# Categories that must clear the statistical evidence gate (when stats supplied)
# in addition to the human YES.
STATS_GATED_CATEGORIES = frozenset(
    {"strategy_promotion", "evolution_deploy", "phase5_go_nogo"}
)


class PromotionCategory(str, Enum):
    STRATEGY_PROMOTION = "strategy_promotion"
    EVOLUTION_DEPLOY = "evolution_deploy"
    LEVERAGE_CHANGE = "leverage_change"
    FLASH_LOAN_LIVE = "flash_loan_live"
    POSITION_OVER_1PCT = "position_over_1pct_equity"
    PHASE5_GO_NOGO = "phase5_go_nogo"


GATED_CATEGORIES = {c.value for c in PromotionCategory}

CONSTITUTIONAL_BLOCKED_PATHS = frozenset(
    {
        "SOUL.md",
        "iron-laws.md",
        "risk_kernel/policy.yaml",
        "risk_kernel/",
        "safety/titan_safety/kernel.py",
        "safety/titan_safety/kill_switch.py",
        "safety/titan_safety/promotion_gate.py",
        "safety/titan_safety/reconciliation.py",
        "workspace/skills/trade_execution/",
        "workspace/skills/trench_ops_execution/",
    }
)

CONSTITUTIONAL_BLOCKED_PREFIXES = (
    "memory/risk/",
    "risk_kernel/",
    "safety/titan_safety/",
)


@dataclass
class PromotionRequest:
    request_id: str
    category: str
    subject: str
    operator_response: str
    operator_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_audit_record(self) -> dict[str, Any]:
        return {
            "ts": time.time(),
            "request_id": self.request_id,
            "category": self.category,
            "subject": self.subject,
            "operator_id": self.operator_id,
            "operator_response": self.operator_response,
            "approved": self.operator_response.strip().upper() == REQUIRED_APPROVAL,
            "metadata": self.metadata,
        }


@dataclass
class PromotionDecision:
    approved: bool
    reason: str
    audit_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PromotionGate:
    """Enforces explicit human YES for gated promotion categories."""

    def __init__(
        self,
        safety_dir: Path | None = None,
        stats_config: StatsGateConfig | None = None,
    ) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.safety_dir / AUDIT_FILE
        self.stats_gate = StrategyStatsGate(stats_config)

    def requires_gate(self, category: str) -> bool:
        return category in GATED_CATEGORIES

    def _evaluate_stats(self, request: PromotionRequest) -> tuple[bool, str, dict[str, Any]]:
        """Enforce statistical evidence for strategy promotions.

        If the category is stats-gated and `strategy_stats` is supplied in
        metadata, the strategy must clear deflated-Sharpe/PSR/cost/shadow gates.
        Missing stats on a stats-gated category is treated as a failure
        (fail-closed) — you cannot promote a strategy with no evidence.
        """
        if request.category not in STATS_GATED_CATEGORIES:
            return True, "not stats-gated", {}
        raw = request.metadata.get("strategy_stats")
        if raw is None:
            return False, "strategy_stats required for stats-gated promotion", {}
        stats = StrategyStats(
            strategy_id=str(raw.get("strategy_id", request.subject)),
            returns=[float(r) for r in raw.get("returns", [])],
            trials=int(raw.get("trials", 1)),
            sr_variance=raw.get("sr_variance"),
            num_trades=int(raw.get("num_trades", 0)),
            gross_bps=float(raw.get("gross_bps", 0.0)),
            cost_bps=float(raw.get("cost_bps", 0.0)),
            backtest_sharpe=float(raw.get("backtest_sharpe", 0.0)),
            shadow_sharpe=float(raw.get("shadow_sharpe", 0.0)),
        )
        result = self.stats_gate.evaluate(stats)
        reason = "stats gate passed" if result.passed else "; ".join(result.reasons)
        return result.passed, reason, result.metrics

    def is_constitutionally_blocked(self, target_path: str) -> tuple[bool, str]:
        """Block promotion of changes touching risk/execution/SOUL paths."""
        normalized = target_path.replace("\\", "/").lstrip("./")
        if normalized in CONSTITUTIONAL_BLOCKED_PATHS:
            return True, f"Constitutional block: {normalized}"
        for prefix in CONSTITUTIONAL_BLOCKED_PREFIXES:
            if normalized.startswith(prefix) or f"/{prefix}" in normalized:
                return True, f"Constitutional block prefix: {prefix}"
        lower = normalized.lower()
        if "soul.md" in lower or "iron-laws" in lower:
            return True, "SOUL/iron-laws modification forbidden"
        return False, ""

    def validate_promotion_artifact(
        self, category: str, changed_paths: list[str]
    ) -> PromotionDecision:
        for path in changed_paths:
            blocked, reason = self.is_constitutionally_blocked(path)
            if blocked:
                record = {
                    "ts": time.time(),
                    "category": category,
                    "blocked_paths": changed_paths,
                    "reason": reason,
                    "approved": False,
                }
                audit_hash = self._append_audit(record)
                return PromotionDecision(approved=False, reason=reason, audit_hash=audit_hash)
        return PromotionDecision(approved=True, reason="no constitutional violations")

    def _append_audit(self, record: dict[str, Any]) -> str:
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        prev_hash = ""
        if self.audit_path.exists():
            lines = self.audit_path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                prev = json.loads(lines[-1])
                prev_hash = prev.get("chain_hash", "")
        chain_hash = hashlib.sha256(f"{prev_hash}|{line}".encode()).hexdigest()
        record["chain_hash"] = chain_hash
        record["prev_hash"] = prev_hash
        final_line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(final_line + "\n")
        return chain_hash

    def evaluate(self, request: PromotionRequest) -> PromotionDecision:
        from .evolution_freeze import EvolutionFreeze

        freeze_reason = EvolutionFreeze(self.safety_dir).block_reason(request.category)
        if freeze_reason:
            record = request.to_audit_record()
            record["evolution_freeze"] = True
            audit_hash = self._append_audit(record)
            return PromotionDecision(approved=False, reason=freeze_reason, audit_hash=audit_hash)

        changed = request.metadata.get("changed_paths", [])
        if changed:
            artifact = self.validate_promotion_artifact(request.category, list(changed))
            if not artifact.approved:
                return artifact

        if not self.requires_gate(request.category):
            return PromotionDecision(approved=True, reason="category not gated")

        stats_ok, stats_reason, stats_metrics = self._evaluate_stats(request)
        if not stats_ok:
            record = request.to_audit_record()
            record["stats_gate"] = {"passed": False, "reason": stats_reason, **stats_metrics}
            audit_hash = self._append_audit(record)
            return PromotionDecision(
                approved=False,
                reason=f"Statistical evidence gate failed: {stats_reason}",
                audit_hash=audit_hash,
            )

        response = request.operator_response.strip().upper()
        if response != REQUIRED_APPROVAL:
            record = request.to_audit_record()
            record["stats_gate"] = {"passed": True, "reason": stats_reason, **stats_metrics}
            audit_hash = self._append_audit(record)
            return PromotionDecision(
                approved=False,
                reason=f"Explicit operator YES required; got '{request.operator_response}'",
                audit_hash=audit_hash,
            )

        record = request.to_audit_record()
        record["stats_gate"] = {"passed": True, "reason": stats_reason, **stats_metrics}
        audit_hash = self._append_audit(record)
        return PromotionDecision(
            approved=True,
            reason=f"operator YES recorded; {stats_reason}",
            audit_hash=audit_hash,
        )

    def verify_audit_chain(self) -> tuple[bool, str]:
        if not self.audit_path.exists():
            return True, "empty audit log"
        prev_hash = ""
        for i, line in enumerate(self.audit_path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            record = json.loads(line)
            stored = record.pop("chain_hash", "")
            stored_prev = record.pop("prev_hash", "")
            if stored_prev != prev_hash:
                return False, f"chain break at line {i + 1}: prev_hash mismatch"
            payload = json.dumps(record, separators=(",", ":"), sort_keys=True)
            expected = hashlib.sha256(f"{prev_hash}|{payload}".encode()).hexdigest()
            if expected != stored:
                return False, f"chain break at line {i + 1}: hash mismatch"
            prev_hash = stored
        return True, "audit chain valid"

    def list_approvals(self) -> list[dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        return [json.loads(l) for l in self.audit_path.read_text(encoding="utf-8").splitlines() if l.strip()]
