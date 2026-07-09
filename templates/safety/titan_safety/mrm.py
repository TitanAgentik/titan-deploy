"""Model Risk Management — per-pipeline performance by regime, drift throttle."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PipelineStatus(str, Enum):
    ACTIVE = "active"
    THROTTLED = "throttled"
    CHALLENGER = "challenger"
    RETIRED = "retired"


@dataclass
class SignalMetrics:
    signal_id: str
    pipeline_id: str
    regime: str
    sharpe: float = 0.0
    hit_rate: float = 0.0
    avg_return_bps: float = 0.0
    sample_count: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class DriftVerdict:
    pipeline_id: str
    signal_id: str
    status: str
    reason: str
    baseline_sharpe: float
    current_sharpe: float
    throttle_factor: float = 1.0
    challenger_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MRMConfig:
    min_samples: int = 30
    sharpe_degradation_threshold: float = 0.5
    hit_rate_floor: float = 0.45
    throttle_factor_on_drift: float = 0.5
    challenger_min_sharpe: float = 1.0
    lookback_regimes: list[str] = field(
        default_factory=lambda: ["risk_off", "neutral", "risk_on"]
    )


class ModelRiskManager:
    """Track per-pipeline/per-signal performance by regime; auto-throttle on degradation."""

    def __init__(self, config: MRMConfig | None = None) -> None:
        self.config = config or MRMConfig()
        self._baselines: dict[str, SignalMetrics] = {}
        self._current: dict[str, SignalMetrics] = {}
        self._pipeline_status: dict[str, PipelineStatus] = {}
        self._challengers: dict[str, str] = {}

    def _key(self, pipeline_id: str, signal_id: str, regime: str) -> str:
        return f"{pipeline_id}:{signal_id}:{regime}"

    def record_baseline(self, metrics: SignalMetrics) -> None:
        self._baselines[self._key(metrics.pipeline_id, metrics.signal_id, metrics.regime)] = metrics

    def record_current(self, metrics: SignalMetrics) -> None:
        key = self._key(metrics.pipeline_id, metrics.signal_id, metrics.regime)
        self._current[key] = metrics
        verdict = self.evaluate_drift(metrics.pipeline_id, metrics.signal_id, metrics.regime)
        if verdict.status == PipelineStatus.THROTTLED.value:
            self._pipeline_status[metrics.pipeline_id] = PipelineStatus.THROTTLED
        elif metrics.pipeline_id not in self._pipeline_status:
            self._pipeline_status[metrics.pipeline_id] = PipelineStatus.ACTIVE

    def evaluate_drift(
        self, pipeline_id: str, signal_id: str, regime: str
    ) -> DriftVerdict:
        key = self._key(pipeline_id, signal_id, regime)
        baseline = self._baselines.get(key)
        current = self._current.get(key)

        if not current or current.sample_count < self.config.min_samples:
            return DriftVerdict(
                pipeline_id=pipeline_id,
                signal_id=signal_id,
                status=PipelineStatus.ACTIVE.value,
                reason="insufficient samples",
                baseline_sharpe=baseline.sharpe if baseline else 0.0,
                current_sharpe=current.sharpe if current else 0.0,
            )

        base_sharpe = baseline.sharpe if baseline else current.sharpe
        if baseline and baseline.sharpe > 0:
            degradation = (baseline.sharpe - current.sharpe) / baseline.sharpe
        else:
            degradation = 0.0

        if current.hit_rate < self.config.hit_rate_floor:
            self._pipeline_status[pipeline_id] = PipelineStatus.THROTTLED
            return DriftVerdict(
                pipeline_id=pipeline_id,
                signal_id=signal_id,
                status=PipelineStatus.THROTTLED.value,
                reason=f"Hit rate {current.hit_rate:.2f} below floor {self.config.hit_rate_floor}",
                baseline_sharpe=base_sharpe,
                current_sharpe=current.sharpe,
                throttle_factor=self.config.throttle_factor_on_drift,
            )

        if degradation > self.config.sharpe_degradation_threshold:
            self._pipeline_status[pipeline_id] = PipelineStatus.THROTTLED
            return DriftVerdict(
                pipeline_id=pipeline_id,
                signal_id=signal_id,
                status=PipelineStatus.THROTTLED.value,
                reason=f"Sharpe degraded {degradation:.0%} vs baseline",
                baseline_sharpe=base_sharpe,
                current_sharpe=current.sharpe,
                throttle_factor=self.config.throttle_factor_on_drift,
            )

        challenger_ready = current.sharpe >= self.config.challenger_min_sharpe
        return DriftVerdict(
            pipeline_id=pipeline_id,
            signal_id=signal_id,
            status=self._pipeline_status.get(pipeline_id, PipelineStatus.ACTIVE).value,
            reason="within tolerance",
            baseline_sharpe=base_sharpe,
            current_sharpe=current.sharpe,
            throttle_factor=1.0,
            challenger_ready=challenger_ready,
        )

    def get_throttle_factor(self, pipeline_id: str) -> float:
        if self._pipeline_status.get(pipeline_id) == PipelineStatus.THROTTLED:
            return self.config.throttle_factor_on_drift
        return 1.0

    def register_challenger(self, pipeline_id: str, challenger_id: str) -> dict[str, Any]:
        """Stub — challenger promotion requires promotion gate YES."""
        self._challengers[pipeline_id] = challenger_id
        self._pipeline_status[challenger_id] = PipelineStatus.CHALLENGER
        return {
            "pipeline_id": pipeline_id,
            "challenger_id": challenger_id,
            "status": "pending_promotion_gate",
            "note": "Requires titan-safety promotion approve --response YES",
        }

    def pipeline_status(self, pipeline_id: str) -> str:
        return self._pipeline_status.get(pipeline_id, PipelineStatus.ACTIVE).value

    def health(self) -> dict[str, Any]:
        throttled = [
            pid for pid, st in self._pipeline_status.items() if st == PipelineStatus.THROTTLED
        ]
        return {
            "status": "ok",
            "tracked_pipelines": len(self._pipeline_status),
            "throttled": throttled,
            "challengers": dict(self._challengers),
        }
