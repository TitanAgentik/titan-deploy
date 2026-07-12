"""Live capital adapters — env-driven, fail-closed until operator fills ~/.openclaw/.env.

No secrets in repo. Wire via policy.yaml:
  reconciliation.recon_module: titan_safety.adapters.live_bundle:build_position_fetcher
  signing.signer_module: titan_safety.adapters.live_bundle:live_signer
  flatten.revoker: titan_safety.adapters.live_bundle:LiveKeyRevoker
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from ..flatten_executor import KeyRevoker


class NotConfiguredError(RuntimeError):
    """Raised when live credentials or endpoints are missing."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def credentials_status() -> dict[str, Any]:
    """Operator checklist — which live hooks are wired (no secret values). DEX-only."""
    return {
        "recon_fetcher_url": bool(_env("TITAN_RECON_FETCHER_URL")),
        "hyperliquid": bool(_env("HYPERLIQUID_PRIVATE_KEY") or _env("HYPERLIQUID_WALLET_ADDRESS")),
        "evm_rpc": bool(_env("ETH_RPC_URL") or _env("ERIGON_HTTP_URL")),
        "solana_rpc": bool(_env("SOLANA_RPC_URL")),
        "geyser": bool(_env("GEYSER_GRPC_URL")),
        "jito": bool(_env("JITO_BLOCK_ENGINE_URL")),
        "trezor_bridge": bool(_env("TREZOR_BRIDGE_SOCKET") or _env("OPENCLAW_TREZOR_BRIDGE")),
        "live_signing_ready": _env("TITAN_LIVE_SIGNING_READY").lower() in ("1", "true", "yes"),
    }


def _require_any_recon_source() -> None:
    st = credentials_status()
    if st["recon_fetcher_url"]:
        return
    if any(st[k] for k in ("hyperliquid", "evm_rpc", "solana_rpc")):
        return
    raise NotConfiguredError(
        "Live reconciliation not configured — set TITAN_RECON_FETCHER_URL or DEX/RPC "
        "keys in ~/.openclaw/.env (see templates/infra/live.env.example). "
        "CEX keys are not supported (R02 / R46 DEX-only)."
    )


def _http_fetch_positions(url: str, venues: list[str]) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"recon fetch failed: {exc}") from exc
    raw = data if isinstance(data, list) else data.get("positions", [])
    out: list[dict[str, Any]] = []
    venue_set = {v.lower() for v in venues} if venues else set()
    for p in raw:
        venue = str(p.get("venue", "")).lower()
        if venue_set and venue not in venue_set:
            continue
        out.append(
            {
                "venue": venue,
                "contract": str(p.get("contract", "")).lower(),
                "notional_usd": float(p.get("notional_usd", 0)),
                "side": str(p.get("side", "long")),
            }
        )
    return out


def live_recon_fetcher(venues: list[str]) -> list[Any]:
    """Aggregate believed positions from configured live sources."""
    from ..reconciliation import BelievedPosition
    from ..recon_aggregator import ReconAggregator, NotConfiguredError as ReconNotConfigured

    _require_any_recon_source()
    url = _env("TITAN_RECON_FETCHER_URL")
    if url:
        raw = _http_fetch_positions(url, venues)
        return [BelievedPosition(**p) for p in raw]

    try:
        agg = ReconAggregator(venues=venues)
        return agg.fetch_positions()
    except ReconNotConfigured:
        raise NotConfiguredError(
            "Built-in recon aggregator not configured — set TITAN_RECON_FETCHER_URL, "
            "HYPERLIQUID_WALLET_ADDRESS, or exchange keys in ~/.openclaw/.env"
        ) from None


def build_position_fetcher() -> Callable[[list[str]], list[Any]]:
    """Factory for reconciliation_service — returns live_recon_fetcher."""
    return live_recon_fetcher


def live_signer(request: dict[str, Any]) -> dict[str, Any]:
    """Live signer hook — delegates to Trezor bridge when configured; never mock-signs."""
    from ..trade_verifier import compute_payload_hash

    if _env("TITAN_LIVE_SIGNING_READY").lower() not in ("1", "true", "yes"):
        raise NotConfiguredError(
            "Live signing not armed — set TITAN_LIVE_SIGNING_READY=1 after Trezor bridge "
            "and signing_node.yaml are verified (~/.openclaw/infra/signing_node.yaml)"
        )
    trade = request.get("trade") or {}
    typed_data = request.get("typed_data")
    calldata = request.get("calldata")
    if not typed_data and not calldata:
        raise NotConfiguredError(
            "BLIND_SIGN_REJECTED — typed_data or calldata required for live signing"
        )

    policy_raw = request.get("policy_raw") or {}
    tier0 = policy_raw.get("tier0_money_path") or {}
    envelope = tier0.get("session_envelope") or {}
    if envelope.get("enabled", False):
        max_n = float(envelope.get("max_notional_usd", 0) or 0)
        notional = float(trade.get("notional_usd", 0) or 0)
        if max_n > 0 and notional > max_n:
            raise NotConfiguredError(
                f"SESSION_ENVELOPE_EXCEEDED — {notional:.2f} > {max_n:.2f} USD"
            )

    bridge = _env("TREZOR_BRIDGE_SOCKET") or _env("OPENCLAW_TREZOR_BRIDGE")
    if not bridge:
        raise NotConfiguredError(
            "TREZOR_BRIDGE_SOCKET or OPENCLAW_TREZOR_BRIDGE required for live signing"
        )
    payload_hash = compute_payload_hash(request)
    # Delegation stub: operator wires openclaw-trezor-bridge; fail until RPC path exists.
    raise NotConfiguredError(
        f"Trezor bridge configured ({bridge}) but signing RPC not wired — "
        f"install openclaw-trezor-bridge per signing_node.yaml "
        f"(payload_hash={payload_hash[:16]}...)"
    )


def revoke_session_keys(
    venues: list[str],
    operator: str,
    reason: str,
    policy_raw: dict[str, Any] | None = None,
    safety_dir: Any = None,
) -> dict[str, Any]:
    """Rotate/revoke session keys — policy checks + HERALD notify; revoke RPC STUB."""
    from pathlib import Path

    policy_raw = policy_raw or {}
    tier0 = policy_raw.get("tier0_money_path") or {}
    st = credentials_status()
    dex_keys = ("hyperliquid", "evm_rpc", "solana_rpc", "jito")
    if not any(st[k] for k in dex_keys):
        raise NotConfiguredError(
            "revoke_session_keys needs DEX credentials in ~/.openclaw/.env"
        )

    safety = Path(safety_dir) if safety_dir else Path.home() / ".openclaw" / "safety"
    safety.mkdir(parents=True, exist_ok=True)
    (safety / "SIGNING_HALTED").write_text(
        json.dumps({"ts": time.time(), "reason": f"keys_revoked:{reason}"}),
        encoding="utf-8",
    )

    try:
        from ..telegram_notify import notify_signing

        notify_signing(
            "fail",
            f"revoke-{operator}",
            code="SESSION_KEYS_REVOKED",
            reason=reason,
            safety_dir=safety,
        )
    except Exception:
        pass

    # STUB: operator implements per-venue session key disable via exchange API
    return {
        "status": "revoke_pending",
        "venues": venues,
        "operator": operator,
        "reason": reason,
        "note": "STUB — disable session keys operationally; SIGNING_HALTED set",
        "configured_sources": {k: st[k] for k in dex_keys},
        "dual_control_withdrawals": tier0.get("dual_control_withdrawals", True),
    }


class LiveKeyRevoker(KeyRevoker):
    """Revoke session/API keys on flatten — requires exchange keys in env."""

    def revoke(self, venues: list[str], operator: str, reason: str) -> dict[str, Any]:
        return revoke_session_keys(venues, operator, reason)
