"""Tier 0 money path — broadcast authority, recon, HL adapter, flatten resume."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from titan_safety.broadcast_authority import (
    BroadcastAuthority,
    BroadcastSubmission,
    validate_broadcast_caller,
    validate_submission_bundle,
)
from titan_safety.flatten_executor import (
    BroadcastAuthorityCloser,
    FlattenExecutor,
    FlattenOrder,
    MockPositionCloser,
)
from titan_safety.gate_receipt import bind_receipt_to_payload, issue_gate_receipt, verify_gate_receipt
from titan_safety.kernel import RiskKernel, TradeRequest
from titan_safety.recon_aggregator import ReconAggregator, fetch_hyperliquid_positions
from titan_safety.reconciliation import BelievedPosition, MockPaperAdapter, ReconciliationService
from titan_safety.trade_verifier import compute_payload_hash, verify_receipt_payload_binding, verify_sign_payload


def _policy_raw(**tier0_overrides) -> dict:
    tier0 = {
        "enabled": True,
        "broadcast_authority_enforced": True,
        "agent_submit_denied": True,
        "require_payload_hash_binding": True,
        "session_envelope": {"enabled": True, "max_notional_usd": 100.0, "allowed_venues": ["hyperliquid"]},
    }
    tier0.update(tier0_overrides)
    return {
        "tier0_money_path": tier0,
        "autonomous_signing": {"require_typed_data_live": True},
        "allowed_venues": ["hyperliquid", "paper"],
    }


def _trade(**kwargs) -> TradeRequest:
    defaults = dict(
        trade_id="t-hl-1",
        venue="hyperliquid",
        contract="eth",
        side="buy",
        notional_usd=50.0,
    )
    defaults.update(kwargs)
    return TradeRequest(**defaults)


def test_broadcast_denies_agent_caller() -> None:
    ok, reason = validate_broadcast_caller("archon", _policy_raw())
    assert ok is False
    assert "denied" in reason.lower()


def test_broadcast_allows_trench_ops() -> None:
    ok, reason = validate_broadcast_caller("trench-ops", _policy_raw())
    assert ok is True


def test_payload_hash_binding(tmp_path: Path) -> None:
    trade = _trade()
    body = {"typed_data": {"message": {"coin": "ETH"}}, "calldata": None}
    phash = compute_payload_hash(body)
    receipt = issue_gate_receipt(trade, tmp_path, payload_hash=phash)
    ok, reason = verify_receipt_payload_binding(receipt.token, trade, body, _policy_raw())
    assert ok is True
    body_bad = {"typed_data": {"message": {"coin": "BTC"}}, "calldata": None}
    ok2, reason2 = verify_receipt_payload_binding(receipt.token, trade, body_bad, _policy_raw())
    assert ok2 is False
    assert "mismatch" in reason2.lower()


def test_blind_sign_rejected_live() -> None:
    trade = _trade()
    ok, reason = verify_sign_payload(trade, {}, _policy_raw())
    assert ok is False
    assert "BLIND_SIGN" in reason


def test_session_envelope_exceeded() -> None:
    trade = _trade(notional_usd=200.0)
    body = {"typed_data": {"x": 1}}
    ok, reason = verify_sign_payload(trade, body, _policy_raw())
    assert ok is False
    assert "ENVELOPE" in reason


def test_broadcast_authority_submit_denies_agent(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path)
    sub = BroadcastSubmission(
        caller_id="oracle",
        trade=trade,
        gate_receipt=receipt.token,
        typed_data={"x": 1},
    )
    auth = BroadcastAuthority(policy_raw=_policy_raw(), safety_dir=tmp_path)
    result = auth.submit(sub)
    assert result.decision == "DENY"
    assert result.code == "BROADCAST_CALLER_DENIED"


def test_broadcast_authority_submit_with_mock_venue(tmp_path: Path) -> None:
    trade = _trade(venue="paper")
    receipt = issue_gate_receipt(trade, tmp_path)
    sub = BroadcastSubmission(
        caller_id="trench-ops",
        trade=trade,
        gate_receipt=receipt.token,
    )

    def mock_submit(submission, t):
        return {"status": "mock_submitted", "trade_id": t.trade_id}

    auth = BroadcastAuthority(
        policy_raw=_policy_raw(),
        safety_dir=tmp_path,
        venue_submit=mock_submit,
    )
    result = auth.submit(sub)
    assert result.decision == "ALLOW"
    assert result.submit_status == "mock_submitted"


@patch("urllib.request.urlopen")
def test_fetch_hyperliquid_positions(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {
            "assetPositions": [
                {"position": {"coin": "ETH", "szi": "1.0", "entryPx": "3000.0"}},
            ]
        }
    ).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp

    positions = fetch_hyperliquid_positions("0xabc")
    assert len(positions) == 1
    assert positions[0].venue == "hyperliquid"
    assert positions[0].contract == "eth"
    assert positions[0].notional_usd == 3000.0


def test_recon_aggregator_http_override(monkeypatch: pytest.MonkeyPatch) -> None:
    positions_json = json.dumps(
        {"positions": [{"venue": "hyperliquid", "contract": "eth", "notional_usd": 100.0}]}
    ).encode()

    class FakeResp:
        def read(self):
            return positions_json

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setenv("TITAN_RECON_FETCHER_URL", "http://127.0.0.1:9999/positions")
    with patch("urllib.request.urlopen", return_value=FakeResp()):
        agg = ReconAggregator(venues=["hyperliquid"])
        pos = agg.fetch_positions()
    assert len(pos) == 1
    assert pos[0].notional_usd == 100.0


def test_recon_halt_writes_signing_halted(tmp_path: Path) -> None:
    data = {
        "version": "2.0",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 1000},
        "reconciliation": {
            "divergence_threshold_usd": 10.0,
            "divergence_threshold_pct": 1.0,
            "adapter": "mock",
            "recon_halt_on_divergence": True,
        },
        "tier0_money_path": {"recon_halt_on_divergence": True},
    }
    p = tmp_path / "policy.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    from titan_safety.policy_loader import load_policy

    policy = load_policy(p)
    adapter = MockPaperAdapter([BelievedPosition("hyperliquid", "eth", 500.0)])
    svc = ReconciliationService(policy, adapter, safety_dir=tmp_path)
    believed = [BelievedPosition("hyperliquid", "eth", 100.0)]
    result = svc.reconcile(believed)
    assert result.decision == "HALT"
    assert (tmp_path / "SIGNING_HALTED").exists()


def test_flatten_resume_after_partial(tmp_path: Path) -> None:
    executor = FlattenExecutor(safety_dir=tmp_path, closer=MockPositionCloser())
    orders = [
        FlattenOrder("hyperliquid", "eth", 100.0, "sell", "test"),
        FlattenOrder("hyperliquid", "btc", 50.0, "sell", "test"),
    ]
    executor._save_resume_state("run1", orders, [0], "in_progress", "chaos test")
    result = executor.resume_flatten()
    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["completed"] == 2


def test_hyperliquid_quote_simulate_mock_chain(tmp_path: Path) -> None:
    from titan_safety.adapters.hyperliquid_live import HyperliquidLiveAdapter, HyperliquidOrder

    adapter = HyperliquidLiveAdapter(safety_dir=tmp_path)
    order = HyperliquidOrder(
        trade_id="q1",
        venue="hyperliquid",
        contract="eth",
        side="buy",
        notional_usd=100.0,
    )
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ETH": "3000.0"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        quote = adapter.quote(order)
    assert quote["status"] == "quoted"
    sim = adapter.simulate(order, quote)
    assert sim["ok"] is True
    typed = adapter.build_typed_data(order, sim)
    assert typed["message"]["coin"] == "ETH"


def test_revoke_session_keys_sets_halt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from titan_safety.adapters.live_bundle import revoke_session_keys

    monkeypatch.setenv("HYPERLIQUID_WALLET_ADDRESS", "0xabc")
    result = revoke_session_keys(
        ["hyperliquid"],
        "operator",
        "test revoke",
        policy_raw=_policy_raw(),
        safety_dir=tmp_path,
    )
    assert result["status"] == "revoke_pending"
    assert (tmp_path / "SIGNING_HALTED").exists()


def test_bind_receipt_to_payload(tmp_path: Path) -> None:
    trade = _trade()
    base = issue_gate_receipt(trade, tmp_path)
    body = {"typed_data": {"a": 1}, "calldata": None}
    phash = compute_payload_hash(body)
    bound = bind_receipt_to_payload(base.token, trade, phash, tmp_path)
    ok, _ = verify_gate_receipt(bound.token, trade, tmp_path)
    assert ok is True
    parts = bound.token.split("|")
    assert parts[7] == phash
