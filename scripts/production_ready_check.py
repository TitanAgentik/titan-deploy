#!/usr/bin/env python3
"""Production readiness gate for live capital — fail-closed checklist.

Exit 0 only when software-side gates for real capital are satisfied.
Operator secrets / UPS / paper-days evidence remain human steps.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _ok(msg: str) -> dict[str, Any]:
    return {"status": "PASS", "check": msg}


def _fail(msg: str, detail: str = "") -> dict[str, Any]:
    return {"status": "FAIL", "check": msg, "detail": detail}


def _warn(msg: str, detail: str = "") -> dict[str, Any]:
    return {"status": "WARN", "check": msg, "detail": detail}


def check_policy(policy_path: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not policy_path.exists():
        return [_fail("policy.yaml present", str(policy_path))]
    raw = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    results.append(_ok(f"policy loaded ({policy_path})"))

    profile = raw.get("capital_profile", "paper")
    if profile == "paper":
        results.append(
            _warn(
                "capital_profile is paper",
                "Set capital_profile: live only after Phase 5 YES + checklist",
            )
        )
    elif profile == "live":
        results.append(_ok("capital_profile: live"))
        if os.environ.get("TITAN_LIVE_SIGNING_READY") != "1":
            results.append(
                _fail(
                    "TITAN_LIVE_SIGNING_READY=1",
                    "Required for live signing; set after Trezor/signing health OK",
                )
            )
        else:
            results.append(_ok("TITAN_LIVE_SIGNING_READY=1"))
    else:
        results.append(_fail("capital_profile valid", f"got {profile!r}"))

    asg = raw.get("autonomous_signing") or {}
    if profile == "live" and not asg.get("enabled"):
        results.append(
            _warn(
                "autonomous_signing.enabled",
                "live profile usually enables autonomous_signing after evidence",
            )
        )

    pg = raw.get("promotion_gates") or {}
    if pg.get("timeout_policy") not in ("hold_derisk", "hold", "HOLD"):
        results.append(
            _fail(
                "promotion timeout = HOLD",
                f"got {pg.get('timeout_policy')!r} — never auto-promote",
            )
        )
    else:
        results.append(_ok("promotion timeout_policy hold_derisk"))

    if not pg.get("phase5_requires_human_yes", True):
        results.append(_fail("phase5_requires_human_yes must be true"))
    else:
        results.append(_ok("phase5_requires_human_yes"))

    recon = raw.get("reconciliation") or {}
    if profile == "live" and recon.get("adapter") == "mock":
        results.append(
            _fail("live recon adapter", "mock recon forbidden on live capital")
        )
    elif profile == "paper":
        results.append(_ok("paper recon adapter ok"))

    dc = raw.get("daily_compound") or {}
    if dc.get("enabled", False):
        results.append(_ok("daily_compound.enabled"))
    else:
        results.append(
            _warn("daily_compound disabled", "enable for day-over-day compounding")
        )

    quantum = raw.get("quantum") or {}
    if quantum.get("enabled"):
        results.append(_fail("quantum must be disabled for live capital"))
    else:
        results.append(_ok("quantum dormant/disabled"))

    return results


def check_safety_package(openclaw: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    safety = openclaw / "safety"
    need = [
        "titan_safety/kernel.py",
        "titan_safety/execution_gate.py",
        "titan_safety/profit_loop.py",
        "titan_safety/daily_compound.py",
        "titan_safety/allocator.py",
        "titan_safety/capital.py",
    ]
    for rel in need:
        p = safety / rel
        if p.exists():
            results.append(_ok(f"safety module {rel}"))
        else:
            results.append(_fail(f"safety module {rel}", "run ./deploy.sh"))
    iron = openclaw / "iron-laws.md"
    if not iron.exists():
        # may live in workspace
        iron = openclaw / "workspace" / "iron-laws.md"
    if iron.exists() or (ROOT / "iron-laws.md").exists():
        results.append(_ok("iron-laws present"))
    else:
        results.append(_warn("iron-laws.md not in deploy path"))
    return results


def check_capital_seed(openclaw: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    state = openclaw / "capital" / "portfolio_state.json"
    if not state.exists():
        results.append(
            _warn(
                "capital portfolio_state",
                "seed with: titan-safety capital deposit --amount 2500 --asset USDC",
            )
        )
        return results
    data = json.loads(state.read_text(encoding="utf-8"))
    eq = float(data.get("equity_usd") or 0.0)
    if eq <= 0:
        results.append(_fail("capital equity > 0", "deposit starting capital"))
    else:
        results.append(_ok(f"capital equity ${eq:,.2f}"))
    return results


def check_control_plane_secret(openclaw: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in ("control_plane.secret", "kill_switch.secret"):
        p = openclaw / "safety" / name
        if p.exists():
            mode = oct(p.stat().st_mode & 0o777)
            if mode in ("0o600", "0o400"):
                results.append(_ok(f"{name} mode {mode}"))
            else:
                results.append(
                    _warn(f"{name} permissions", f"mode {mode} — prefer 0600")
                )
        else:
            results.append(
                _warn(f"{name} missing", "generated on first deploy/start")
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="TITAN production readiness check")
    parser.add_argument(
        "--openclaw",
        type=Path,
        default=Path.home() / ".openclaw",
        help="OpenClaw home",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Policy YAML (default: OPENCLAW/risk_kernel/policy.yaml)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict-live",
        action="store_true",
        help="Treat WARN as FAIL when capital_profile is live",
    )
    args = parser.parse_args()

    policy = args.policy or (args.openclaw / "risk_kernel" / "policy.yaml")
    if not policy.exists():
        # fall back to templates for pre-deploy checks
        policy = ROOT / "templates" / "risk_kernel" / "policy.yaml"

    results: list[dict[str, Any]] = []
    results.extend(check_policy(policy))
    results.extend(check_safety_package(args.openclaw))
    results.extend(check_capital_seed(args.openclaw))
    results.extend(check_control_plane_secret(args.openclaw))

    fails = [r for r in results if r["status"] == "FAIL"]
    warns = [r for r in results if r["status"] == "WARN"]

    profile = "paper"
    if policy.exists():
        raw = yaml.safe_load(policy.read_text(encoding="utf-8")) or {}
        profile = raw.get("capital_profile", "paper")

    if args.strict_live and profile == "live":
        fails.extend(warns)
        warns = []

    summary = {
        "profile": profile,
        "pass": sum(1 for r in results if r["status"] == "PASS"),
        "warn": len(warns),
        "fail": len(fails),
        "ready_for_paper": len(fails) == 0,
        "ready_for_live": (
            len(fails) == 0
            and profile == "live"
            and os.environ.get("TITAN_LIVE_SIGNING_READY") == "1"
        ),
        "checks": results,
        "honest_note": (
            "Software gates ≠ guaranteed profit. No system makes money every day. "
            "Daily compound cuts bleeders and feeds measured winners; markets still lose."
        ),
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("=== TITAN Production Readiness ===")
        for r in results:
            icon = {"PASS": "✓", "FAIL": "✗", "WARN": "!"}.get(r["status"], "?")
            line = f"  [{icon}] {r['check']}"
            if r.get("detail"):
                line += f" — {r['detail']}"
            print(line)
        print(
            f"\nPASS={summary['pass']} WARN={summary['warn']} FAIL={summary['fail']} "
            f"profile={profile}"
        )
        print(f"Paper-ready: {summary['ready_for_paper']}")
        print(f"Live-ready:  {summary['ready_for_live']}")
        print(f"\n{summary['honest_note']}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
