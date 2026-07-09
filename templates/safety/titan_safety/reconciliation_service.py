"""Position reconciliation HTTP service."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from .http_server import SafetyHTTPServer
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy
from .reconciliation import BelievedPosition, ReconciliationService, get_adapter

logger = setup_logging("reconciliation")


def _load_live_fetcher(policy: Any) -> Any:
    """Build a live position fetcher from policy/env.

    Sources (first match wins):
      1. TITAN_RECON_FETCHER_URL — HTTP GET returning list of positions
      2. reconciliation.positions_file — JSON file of believed positions
      3. None — LiveExchangeAdapter will fail-closed on fetch
    """
    import json
    import os
    import urllib.request

    from .reconciliation import BelievedPosition

    recon = (policy.raw or {}).get("reconciliation", {})
    url = os.environ.get("TITAN_RECON_FETCHER_URL") or recon.get("fetcher_url")
    path = recon.get("positions_file")

    if url:

        def http_fetcher(_venues: list[str]) -> list[BelievedPosition]:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            raw = data if isinstance(data, list) else data.get("positions", [])
            return [
                BelievedPosition(
                    venue=str(p["venue"]),
                    contract=str(p["contract"]).lower(),
                    notional_usd=float(p["notional_usd"]),
                    side=str(p.get("side", "long")),
                )
                for p in raw
            ]

        return http_fetcher

    if path:
        from pathlib import Path

        pos_path = Path(str(path).replace("~", str(Path.home()))).expanduser()

        def file_fetcher(_venues: list[str]) -> list[BelievedPosition]:
            if not pos_path.exists():
                raise RuntimeError(f"positions_file missing: {pos_path}")
            data = json.loads(pos_path.read_text(encoding="utf-8"))
            raw = data if isinstance(data, list) else data.get("positions", [])
            return [
                BelievedPosition(
                    venue=str(p["venue"]),
                    contract=str(p["contract"]).lower(),
                    notional_usd=float(p["notional_usd"]),
                    side=str(p.get("side", "long")),
                )
                for p in raw
            ]

        return file_fetcher

    return None


def create_app(policy_path: Path) -> SafetyHTTPServer:
    policy = load_policy(policy_path)
    from .reconciliation import assert_adapter_allowed_for_policy

    capital_profile = str(policy.raw.get("capital_profile", "paper")).lower()
    try:
        assert_adapter_allowed_for_policy(policy.reconciliation.adapter, policy)
    except ValueError as exc:
        if capital_profile == "live":
            logger.error(str(exc))
            raise
        logger.warning(f"{exc} (capital_profile={capital_profile} — execution gate will DENY live trades)")

    adapter_name = policy.reconciliation.adapter
    fetcher = None
    if adapter_name in ("live", "exchange", "onchain", "live_exchange"):
        fetcher = _load_live_fetcher(policy)
        if fetcher is None:
            logger.warning(
                "live recon adapter without fetcher_url/positions_file — "
                "fetch will fail-closed until wired"
            )
    adapter = get_adapter(
        adapter_name,
        fetcher=fetcher,
        venues=list(policy.allowed_venues),
    )
    service = ReconciliationService(policy, adapter)

    def pre_trade(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        try:
            believed = [
                BelievedPosition(
                    venue=str(p["venue"]),
                    contract=str(p["contract"]).lower(),
                    notional_usd=float(p["notional_usd"]),
                    side=str(p.get("side", "long")),
                )
                for p in body.get("believed", [])
            ]
        except (KeyError, TypeError, ValueError) as exc:
            return 400, {"error": f"invalid believed positions: {exc}", "decision": "DENY"}
        pending_raw = body.get("pending", {})
        try:
            pending = BelievedPosition(
                venue=str(pending_raw.get("venue", "paper")),
                contract=str(pending_raw.get("contract", "")).lower(),
                notional_usd=float(pending_raw.get("notional_usd", 0)),
            )
        except (TypeError, ValueError) as exc:
            return 400, {"error": f"invalid pending: {exc}", "decision": "DENY"}
        result = service.pre_trade_gate(believed, pending)
        METRICS.inc("reconciliation_checks_total")
        if result.decision != "ALLOW":
            METRICS.inc("reconciliation_deny_total")
        return 200, result.to_dict()

    def reconcile(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        try:
            believed = [
                BelievedPosition(
                    venue=str(p["venue"]),
                    contract=str(p["contract"]).lower(),
                    notional_usd=float(p["notional_usd"]),
                )
                for p in body.get("believed", [])
            ]
        except (KeyError, TypeError, ValueError) as exc:
            return 400, {"error": f"invalid believed positions: {exc}", "decision": "DENY"}
        result = service.reconcile(believed)
        return 200, result.to_dict()

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, service.health()

    routes = {
        "POST /v1/pre_trade": pre_trade,
        "POST /v1/reconcile": reconcile,
        "GET /health": health,
        "GET /metrics": lambda _b, _h: (200, METRICS.to_json()),
    }
    return SafetyHTTPServer("127.0.0.1", policy.service.reconciliation_port, routes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Reconciliation Service")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    args = parser.parse_args(argv)
    policy_path = expand_path(args.policy)
    server = create_app(policy_path)
    policy = load_policy(policy_path)
    logger.info(f"Reconciliation listening on 127.0.0.1:{policy.service.reconciliation_port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
