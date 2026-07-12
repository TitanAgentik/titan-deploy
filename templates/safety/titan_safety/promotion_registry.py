"""Multiple-testing registry — every strategy/config ever tried.

Append-only ledger used to raise the deflated-Sharpe benchmark as the trial
count grows (Bailey & Lopez de Prado selection bias). Pure stdlib.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .promotion_stats import deflated_sharpe_ratio


REGISTRY_FILE = "promotion_registry.jsonl"
DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"


@dataclass
class StrategyAttempt:
    strategy_id: str
    config_hash: str
    ts: float = field(default_factory=time.time)
    dsr: float | None = None
    psr: float | None = None
    num_trades: int = 0
    promoted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegistrySummary:
    total_trials: int
    unique_strategies: int
    unique_configs: int
    promoted_count: int
    latest_dsr_by_strategy: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def config_hash(strategy_id: str, config: dict[str, Any] | None = None) -> str:
    payload = json.dumps(
        {"strategy_id": strategy_id, "config": config or {}},
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class PromotionRegistry:
    """Tracks all promotion attempts for multiple-testing correction."""

    def __init__(self, safety_dir: Path | None = None) -> None:
        self.safety_dir = safety_dir or DEFAULT_SAFETY_DIR
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.safety_dir / REGISTRY_FILE
        self._cache: list[StrategyAttempt] | None = None

    def _load(self) -> list[StrategyAttempt]:
        if self._cache is not None:
            return self._cache
        attempts: list[StrategyAttempt] = []
        if not self.registry_path.exists():
            self._cache = attempts
            return attempts
        for line in self.registry_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            attempts.append(
                StrategyAttempt(
                    strategy_id=str(raw.get("strategy_id", "")),
                    config_hash=str(raw.get("config_hash", "")),
                    ts=float(raw.get("ts", 0.0)),
                    dsr=raw.get("dsr"),
                    psr=raw.get("psr"),
                    num_trades=int(raw.get("num_trades", 0)),
                    promoted=bool(raw.get("promoted", False)),
                    metadata=dict(raw.get("metadata") or {}),
                )
            )
        self._cache = attempts
        return attempts

    def _append(self, record: dict[str, Any]) -> None:
        with self.registry_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
        self._cache = None

    def register_attempt(
        self,
        strategy_id: str,
        *,
        config: dict[str, Any] | None = None,
        returns: list[float] | None = None,
        sr_variance: float | None = None,
        num_trades: int = 0,
        promoted: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> StrategyAttempt:
        """Record a strategy/config trial; returns the attempt with computed DSR."""
        cfg_hash = config_hash(strategy_id, config)
        dsr: float | None = None
        psr: float | None = None
        if returns:
            trials = self.total_trials() + 1
            dsr = deflated_sharpe_ratio(returns, trials, sr_variance)
            from .promotion_stats import probabilistic_sharpe_ratio

            psr = probabilistic_sharpe_ratio(returns)
        attempt = StrategyAttempt(
            strategy_id=strategy_id,
            config_hash=cfg_hash,
            dsr=dsr,
            psr=psr,
            num_trades=num_trades,
            promoted=promoted,
            metadata=metadata or {},
        )
        self._append(attempt.to_record())
        return attempt

    def total_trials(self) -> int:
        """Unique config hashes ever tried — used as DSR `trials` count."""
        attempts = self._load()
        return len({a.config_hash for a in attempts})

    def trials_for_strategy(self, strategy_id: str) -> int:
        attempts = self._load()
        return len({a.config_hash for a in attempts if a.strategy_id == strategy_id})

    def global_trials_for_dsr(self, strategy_id: str) -> int:
        """DSR uses global trial count across all strategies ever mined."""
        total = self.total_trials()
        return max(1, total)

    def summary(self) -> RegistrySummary:
        attempts = self._load()
        latest_dsr: dict[str, float] = {}
        for a in reversed(attempts):
            if a.strategy_id not in latest_dsr and a.dsr is not None:
                latest_dsr[a.strategy_id] = a.dsr
        return RegistrySummary(
            total_trials=self.total_trials(),
            unique_strategies=len({a.strategy_id for a in attempts}),
            unique_configs=len({a.config_hash for a in attempts}),
            promoted_count=sum(1 for a in attempts if a.promoted),
            latest_dsr_by_strategy=latest_dsr,
        )

    def list_attempts(self, strategy_id: str | None = None) -> list[dict[str, Any]]:
        attempts = self._load()
        if strategy_id:
            attempts = [a for a in attempts if a.strategy_id == strategy_id]
        return [a.to_record() for a in attempts]
