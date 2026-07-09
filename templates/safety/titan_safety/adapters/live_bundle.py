"""Live capital adapters — env-driven, fail-closed until operator fills ~/.openclaw/.env.

No secrets in repo. Wire via policy.yaml:
  reconciliation.recon_module: titan_safety.adapters.live_bundle:build_position_fetcher
  signing.signer_module: titan_safety.adapters.live_bundle:live_signer
  flatten.revoker: titan_safety.adapters.live_bundle:LiveKeyRevoker
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

from ..flatten_executor import KeyRevoker


class NotConfiguredError(RuntimeError):
    """Raised when live credentials or endpoints are missing."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def credentials_status() -> dict[str, Any]:
    """Operator checklist — which live hooks are wired (no secret values)."""
    return {
        "recon_fetcher_url": bool(_env("TITAN_RECON_FETCHER_URL")),
        "binance": bool(_env("BINANCE_API_KEY") and _env("BINANCE_API_SECRET")),
        "okx": bool(_env("OKX_API_KEY") and _env("OKX_API_SECRET") and _env("OKX_PASSPHRASE")),
        "bybit": bool(_env("BYBIT_API_KEY") and _env("BYBIT_API_SECRET")),
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
    if any(st[k] for k in ("binance", "okx", "bybit", "hyperliquid", "evm_rpc", "solana_rpc")):
        return
    raise NotConfiguredError(
        "Live reconciliation not configured — set TITAN_RECON_FETCHER_URL or exchange/RPC "
        "keys in ~/.openclaw/.env (see templates/infra/live.env.example)"
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

    _require_any_recon_source()
    url = _env("TITAN_RECON_FETCHER_URL")
    if url:
        raw = _http_fetch_positions(url, venues)
        return [BelievedPosition(**p) for p in raw]

    # Direct exchange/RPC aggregation — operator extends or points fetcher URL.
    raise NotConfiguredError(
        "Exchange/RPC keys present but direct recon aggregator not wired — "
        "set TITAN_RECON_FETCHER_URL to your position aggregator or implement "
        "titan_safety.adapters.live_bundle:live_recon_fetcher"
    )


def build_position_fetcher() -> Callable[[list[str]], list[Any]]:
    """Factory for reconciliation_service — returns live_recon_fetcher."""
    return live_recon_fetcher


def live_signer(request: dict[str, Any]) -> dict[str, Any]:
    """Live signer hook — delegates to Trezor bridge when configured; never mock-signs."""
    if _env("TITAN_LIVE_SIGNING_READY").lower() not in ("1", "true", "yes"):
        raise NotConfiguredError(
            "Live signing not armed — set TITAN_LIVE_SIGNING_READY=1 after Trezor bridge "
            "and signing_node.yaml are verified (~/.openclaw/infra/signing_node.yaml)"
        )
    bridge = _env("TREZOR_BRIDGE_SOCKET") or _env("OPENCLAW_TREZOR_BRIDGE")
    if not bridge:
        raise NotConfiguredError(
            "TREZOR_BRIDGE_SOCKET or OPENCLAW_TREZOR_BRIDGE required for live signing"
        )
    # Delegation stub: operator wires openclaw-trezor-bridge; fail until RPC path exists.
    raise NotConfiguredError(
        f"Trezor bridge configured ({bridge}) but signing RPC not wired — "
        "install openclaw-trezor-bridge per signing_node.yaml"
    )


class LiveKeyRevoker(KeyRevoker):
    """Revoke session/API keys on flatten — requires exchange keys in env."""

    def revoke(self, venues: list[str], operator: str, reason: str) -> dict[str, Any]:
        st = credentials_status()
        if not any(st[k] for k in ("binance", "okx", "bybit", "hyperliquid")):
            raise NotConfiguredError(
                "Live key revoker needs exchange API keys in ~/.openclaw/.env"
            )
        # Fail-closed until operator implements revoke hooks per venue.
        return {
            "status": "revoke_pending",
            "venues": venues,
            "operator": operator,
            "reason": reason,
            "note": "Disable API keys operationally at exchange UI until revoke RPC wired",
            "configured_exchanges": {k: st[k] for k in ("binance", "okx", "bybit", "hyperliquid")},
        }
