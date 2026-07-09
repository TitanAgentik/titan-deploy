#!/usr/bin/env python3
"""
Chaos / adversarial test harness for TITAN safety services.

Simulates failure modes and asserts risk kernel + kill switch respond correctly.
Run: python3 tests/chaos/chaos_harness.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SAFETY_SRC = ROOT / "templates" / "safety"
sys.path.insert(0, str(SAFETY_SRC))

from titan_safety.client import RiskKernelClient  # noqa: E402
from titan_safety.http_server import SafetyHTTPServer  # noqa: E402
from titan_safety.kernel import RiskKernel, TradeRequest  # noqa: E402
from titan_safety.kill_switch import KillSwitch  # noqa: E402
from titan_safety.policy_loader import load_policy  # noqa: E402
from titan_safety.risk_kernel_service import create_app  # noqa: E402


def make_policy(tmp: Path) -> Path:
    src = ROOT / "templates" / "risk_kernel" / "policy.yaml"
    policy = yaml.safe_load(src.read_text())
    policy["service"]["risk_kernel_port"] = 19101
    path = tmp / "policy.yaml"
    path.write_text(yaml.dump(policy), encoding="utf-8")
    return path


def assert_deny(result, code_fragment: str, label: str) -> None:
    assert result.decision == "DENY", f"{label}: expected DENY got {result.decision}"
    assert code_fragment in (result.code or result.reason), f"{label}: {result}"


def scenario_kill_inference_mid_trade(tmp: Path, safety_dir: Path) -> None:
    """Simulate inference :30000 dying — kernel must still veto bad trades."""
    policy_path = make_policy(tmp)
    state_path = safety_dir / "kernel_state.json"
    server, kernel = create_app(policy_path, state_path, safety_dir)
    server.start(background=True)
    time.sleep(0.2)
    client = RiskKernelClient("http://127.0.0.1:19101")
    bad = TradeRequest(
        trade_id="chaos1",
        venue="paper",
        contract="0x0000000000000000000000000000000000000000",
        side="buy",
        notional_usd=9999,
        leverage=1.0,
    )
    result = client.validate(bad)
    assert_deny(result, "NOTIONAL", "kill-inference-mid-trade")
    server.stop()


def scenario_kernel_unreachable_fail_closed() -> None:
    client = RiskKernelClient("http://127.0.0.1:1", timeout=0.5)
    result = client.validate(
        {
            "trade_id": "chaos2",
            "venue": "paper",
            "contract": "0x0",
            "notional_usd": 10,
        }
    )
    assert_deny(result, "KERNEL_UNREACHABLE", "nats-kernel-down")


def scenario_kill_switch_overrides_all(tmp: Path, safety_dir: Path) -> None:
    policy_path = make_policy(tmp)
    ks = KillSwitch(safety_dir)
    ks.activate("chaos", "simulated halt")
    kernel = RiskKernel.from_policy_path(
        policy_path, safety_dir / "k2.json", kill_switch_active=True
    )
    trade = TradeRequest(
        trade_id="chaos3",
        venue="paper",
        contract="0x0000000000000000000000000000000000000000",
        side="buy",
        notional_usd=10,
    )
    result = kernel.validate_trade(trade)
    assert_deny(result, "KILL_SWITCH", "kill-switch")
    ks.deactivate("chaos")


def scenario_corrupt_lora_audit_detected(tmp: Path) -> None:
    from titan_safety.audit_chain import AuditChainWriter, DecisionLogEntry, VersionFingerprint

    log = tmp / "decisions.jsonl"
    writer = AuditChainWriter(log)
    good_fp = VersionFingerprint("good" * 16, "lora" * 16, "v1", "soul" * 16)
    writer.append(DecisionLogEntry("c1", "LAMARCK", "infer", good_fp, {}))
    corrupt_fp = VersionFingerprint("bad" * 16, "lora" * 16, "v1", "soul" * 16)
    writer.append(DecisionLogEntry("c2", "LAMARCK", "infer", corrupt_fp, {"corrupt": True}))
    ok, _ = writer.verify()
    assert ok is True
    # Tamper simulates corrupted LoRA decision after the fact
    text = log.read_text()
    log.write_text(text.replace("infer", "execute"))
    ok2, msg = writer.verify()
    assert ok2 is False, f"corrupt-lora: chain should break: {msg}"


def scenario_flash_crash_loss_velocity(tmp: Path, safety_dir: Path) -> None:
  policy_path = make_policy(tmp)
  kernel = RiskKernel.from_policy_path(policy_path, safety_dir / "k3.json")
  # 30% flash crash — record rapid losses
  for _ in range(5):
      kernel.state.record_loss(50.0)
  trade = TradeRequest(
      trade_id="chaos5",
      venue="paper",
      contract="0x0000000000000000000000000000000000000000",
      side="buy",
      notional_usd=10,
  )
  result = kernel.validate_trade(trade)
  assert_deny(result, "LOSS_VELOCITY", "flash-crash")


def scenario_poisoned_feed_slippage(tmp: Path, safety_dir: Path) -> None:
    policy_path = make_policy(tmp)
    kernel = RiskKernel.from_policy_path(policy_path, safety_dir / "k4.json")
    trade = TradeRequest(
        trade_id="chaos6",
        venue="paper",
        contract="0x0000000000000000000000000000000000000000",
        side="buy",
        notional_usd=10,
        expected_price=100.0,
        worst_price=140.0,  # 40% poisoned quote
    )
    result = kernel.validate_trade(trade)
    assert_deny(result, "SLIPPAGE", "poisoned-feed")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="titan_chaos_"))
    safety_dir = tmp / "safety"
    safety_dir.mkdir()
    scenarios = [
        ("kill-inference-mid-trade", lambda: scenario_kill_inference_mid_trade(tmp, safety_dir)),
        ("kernel-unreachable", scenario_kernel_unreachable_fail_closed),
        ("kill-switch", lambda: scenario_kill_switch_overrides_all(tmp, safety_dir)),
        ("corrupt-lora-audit", lambda: scenario_corrupt_lora_audit_detected(tmp)),
        ("flash-crash", lambda: scenario_flash_crash_loss_velocity(tmp, safety_dir)),
        ("poisoned-feed", lambda: scenario_poisoned_feed_slippage(tmp, safety_dir)),
    ]
    passed = 0
    for name, fn in scenarios:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as exc:
            print(f"FAIL: {name} — {exc}")
        except Exception as exc:
            print(f"ERROR: {name} — {exc}")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nChaos harness: {passed}/{len(scenarios)} passed")
    return 0 if passed == len(scenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
