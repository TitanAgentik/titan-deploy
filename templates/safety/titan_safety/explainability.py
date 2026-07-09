"""Structured plain-English trade explainability with evidence trace."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    source: str
    summary: str
    confidence: float = 0.0
    data_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TradeExplanation:
    trade_id: str
    pipeline_id: str
    plain_english: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    equity_pct: float = 0.0
    confidence: float = 0.0
    severity: str = "INFO"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "pipeline_id": self.pipeline_id,
            "plain_english": self.plain_english,
            "evidence": [e.to_dict() for e in self.evidence],
            "equity_pct": self.equity_pct,
            "confidence": self.confidence,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }


@dataclass
class ExplainabilityConfig:
    material_equity_pct: float = 0.5
    high_confidence_threshold: float = 0.8
    always_explain_above_pct: float = 1.0


class ExplainabilityLayer:
    """Generate structured explanations for material or high-confidence trades."""

    def __init__(self, config: ExplainabilityConfig | None = None) -> None:
        self.config = config or ExplainabilityConfig()
        self._log: list[TradeExplanation] = []

    def requires_explanation(
        self, equity_pct: float, confidence: float, notional_usd: float = 0.0
    ) -> bool:
        if equity_pct >= self.config.always_explain_above_pct:
            return True
        if equity_pct >= self.config.material_equity_pct:
            return True
        if confidence >= self.config.high_confidence_threshold:
            return True
        return False

    def explain(
        self,
        trade_id: str,
        pipeline_id: str,
        side: str,
        notional_usd: float,
        equity_usd: float,
        confidence: float,
        signals: list[dict[str, Any]] | None = None,
        risk_checks: list[dict[str, Any]] | None = None,
        regime: str = "neutral",
    ) -> TradeExplanation | None:
        equity_pct = (notional_usd / equity_usd * 100.0) if equity_usd else 0.0
        if not self.requires_explanation(equity_pct, confidence):
            return None

        evidence: list[EvidenceItem] = []
        for sig in signals or []:
            evidence.append(
                EvidenceItem(
                    source=str(sig.get("source", "ORACLE")),
                    summary=str(sig.get("summary", sig.get("name", "signal"))),
                    confidence=float(sig.get("confidence", 0)),
                    data_ref=str(sig.get("ref", "")),
                )
            )
        for chk in risk_checks or []:
            evidence.append(
                EvidenceItem(
                    source="risk_kernel",
                    summary=f"{chk.get('code', 'CHECK')}: {chk.get('decision', 'OK')}",
                    confidence=1.0,
                )
            )

        severity = "INFO"
        if equity_pct >= 1.0:
            severity = "HIGH"
        elif confidence >= self.config.high_confidence_threshold and equity_pct >= self.config.material_equity_pct:
            severity = "HIGH"

        top_signal = (signals or [{}])[0]
        signal_name = top_signal.get("name", "composite signal")
        plain = (
            f"{pipeline_id} proposes {side.upper()} ${notional_usd:,.2f} "
            f"({equity_pct:.2f}% equity) driven by {signal_name} "
            f"in {regime} regime (confidence {confidence:.0%}). "
            f"{len(evidence)} evidence items attached."
        )

        expl = TradeExplanation(
            trade_id=trade_id,
            pipeline_id=pipeline_id,
            plain_english=plain,
            evidence=evidence,
            equity_pct=equity_pct,
            confidence=confidence,
            severity=severity,
        )
        self._log.append(expl)
        return expl

    def format_herald_payload(self, expl: TradeExplanation) -> dict[str, Any]:
        """Payload compatible with herald_notify institutional format."""
        return {
            "schema_version": "1.0",
            "type": "trade_explanation",
            "severity": expl.severity,
            "trade_id": expl.trade_id,
            "pipeline_id": expl.pipeline_id,
            "summary_md": expl.plain_english,
            "equity_pct": expl.equity_pct,
            "confidence": expl.confidence,
            "evidence_count": len(expl.evidence),
            "evidence": [e.to_dict() for e in expl.evidence],
            "json_block": json.dumps(expl.to_dict(), indent=2),
        }

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._log[-limit:]]
