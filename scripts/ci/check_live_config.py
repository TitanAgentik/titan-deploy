#!/usr/bin/env python3
"""CI: live capital_profile must not use mock adapters or CEX-direct venues.

Scans template and optional deployed policy paths. Wired from verify.sh and CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_POLICY = ROOT / "templates" / "risk_kernel" / "policy.yaml"

CEX_VENUES = frozenset(
    {
        "binance_spot",
        "binance_futures",
        "okx_spot",
        "okx_futures",
        "bybit_spot",
        "bybit_futures",
        "coinbase_spot",
        "coinbase_advanced",
        "kraken_spot",
        "cex_api_direct",
    }
)

MOCK_MODULE_MARKERS = ("mock", "stub", "paper_adapter")


def _is_mock_spec(value: str) -> bool:
    lower = value.lower()
    return any(m in lower for m in MOCK_MODULE_MARKERS)


def check_live_policy(path: Path, label: str) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return errors

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profile = str(raw.get("capital_profile", "paper")).lower()
    if profile != "live":
        return errors

    venues = [str(v).lower() for v in raw.get("allowed_venues", [])]
    live_venues = [v for v in venues if v not in ("paper", "mock", "test")]
    cex_hits = [v for v in live_venues if v in CEX_VENUES]
    if cex_hits:
        errors.append(f"{label}: CEX-direct venues forbidden on live profile: {cex_hits}")

    recon = raw.get("reconciliation") or {}
    adapter = str(recon.get("adapter", "mock")).lower()
    if live_venues and adapter == "mock":
        errors.append(f"{label}: mock reconciliation adapter with live venues")

    recon_module = str(recon.get("recon_module") or "").strip()
    if recon_module and _is_mock_spec(recon_module):
        errors.append(f"{label}: mock recon_module on live profile: {recon_module}")

    flatten = raw.get("flatten") or {}
    closer = str(flatten.get("closer", "mock")).lower()
    revoker = str(flatten.get("revoker", "mock")).lower()
    if closer == "mock":
        errors.append(f"{label}: flatten.closer=mock forbidden on live profile")
    if revoker == "mock":
        errors.append(f"{label}: flatten.revoker=mock forbidden on live profile")

    signing = raw.get("signing") or {}
    signer_module = str(signing.get("signer_module") or "").strip()
    if not signer_module:
        errors.append(f"{label}: signing.signer_module required on live profile")
    elif _is_mock_spec(signer_module):
        errors.append(f"{label}: mock signer_module on live profile: {signer_module}")

    tier0 = raw.get("tier0_money_path") or {}
    venue_adapter = str(tier0.get("venue_adapter") or "").strip()
    if venue_adapter and _is_mock_spec(venue_adapter):
        errors.append(f"{label}: mock tier0 venue_adapter: {venue_adapter}")

    return errors


def check_paper_template_defaults(path: Path) -> list[str]:
    """Ensure template ROOT defaults match go-live policy intent."""
    errors: list[str] = []
    if not path.is_file():
        return [f"missing template policy: {path}"]

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if str(raw.get("capital_profile", "")).lower() != "paper":
        errors.append("template: capital_profile must be paper at root")

    if (raw.get("autonomous_signing") or {}).get("enabled") is not False:
        errors.append("template: autonomous_signing.enabled must be false at root")

    venues = [str(v).lower() for v in raw.get("allowed_venues", [])]
    if venues != ["paper"]:
        errors.append(f"template: allowed_venues must be [paper] at root, got {venues}")

    if (raw.get("flash_loan_live") or {}).get("enabled") is not False:
        errors.append("template: flash_loan_live.enabled must be false")

    alloc = raw.get("allocator") or {}
    if alloc.get("advisory_mode") is not True:
        errors.append("template: allocator.advisory_mode must be true at root")
    if int(alloc.get("max_active_pipelines", 0)) != 2:
        errors.append("template: allocator.max_active_pipelines must be 2 at root")

    tier1 = raw.get("tier1_capital_risk") or {}
    live_prof = (tier1.get("profiles") or {}).get("live") or {}
    if live_prof.get("drawdown_notify_only") is not False:
        errors.append("template: tier1 live profile must set drawdown_notify_only: false")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate live capital policy config")
    parser.add_argument(
        "--policy",
        action="append",
        default=[],
        help="Additional policy.yaml paths to scan (e.g. deployed ~/.openclaw/risk_kernel/policy.yaml)",
    )
    args = parser.parse_args(argv)

    all_errors: list[str] = []
    all_errors.extend(check_paper_template_defaults(TEMPLATE_POLICY))
    all_errors.extend(check_live_policy(TEMPLATE_POLICY, "templates/risk_kernel/policy.yaml (template)"))

    for p in args.policy:
        path = Path(p).expanduser().resolve()
        all_errors.extend(check_live_policy(path, str(path)))

    if all_errors:
        for err in all_errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print("OK: live config checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
