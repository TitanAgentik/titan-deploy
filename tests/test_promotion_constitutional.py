"""Constitutional block tests for promotion gate."""

from __future__ import annotations

from pathlib import Path

from titan_safety.promotion_gate import PromotionGate, PromotionRequest


def test_blocks_soul_modification(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    blocked, reason = gate.is_constitutionally_blocked("SOUL.md")
    assert blocked is True
    decision = gate.validate_promotion_artifact("evolution_deploy", ["SOUL.md"])
    assert decision.approved is False


def test_blocks_risk_kernel_path(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    blocked, _ = gate.is_constitutionally_blocked("risk_kernel/policy.yaml")
    assert blocked is True


def test_evaluate_with_changed_paths_denied(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    req = PromotionRequest(
        request_id="r1",
        category="evolution_deploy",
        subject="bad deploy",
        operator_response="YES",
        operator_id="op",
        metadata={"changed_paths": ["safety/titan_safety/kernel.py"]},
    )
    decision = gate.evaluate(req)
    assert decision.approved is False
