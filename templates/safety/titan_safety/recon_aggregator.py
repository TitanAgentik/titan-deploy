"""Built-in DEX/on-chain position aggregator — not HTTP-only.

TITAN_RECON_FETCHER_URL remains an optional override. When unset, reads
Hyperliquid clearinghouse state and (stub) EVM positions directly.
Continuous recon HALT on divergence triggers kernel DENY via reconciliation service.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

from .observability import setup_logging
from .reconciliation import BelievedPosition

logger = setup_logging("recon_aggregator")

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def fetch_hyperliquid_positions(wallet: str) -> list[BelievedPosition]:
    """Read Hyperliquid clearinghouse state — wallet address only (no hot key)."""
    if not wallet:
        raise RuntimeError("HYPERLIQUID_WALLET_ADDRESS required for built-in HL recon")
    body = json.dumps({"type": "clearinghouseState", "user": wallet}).encode()
    req = urllib.request.Request(
        HYPERLIQUID_INFO_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"hyperliquid recon failed: {exc}") from exc

    positions: list[BelievedPosition] = []
    asset_positions = data.get("assetPositions") or []
    for ap in asset_positions:
        pos = ap.get("position") or {}
        coin = str(pos.get("coin", "")).upper()
        if not coin:
            continue
        szi = float(pos.get("szi", 0) or 0)
        if abs(szi) < 1e-12:
            continue
        entry_px = float(pos.get("entryPx", 0) or 0)
        notional = abs(szi * entry_px)
        side = "long" if szi > 0 else "short"
        positions.append(
            BelievedPosition(
                venue="hyperliquid",
                contract=coin.lower(),
                notional_usd=notional,
                side=side,
            )
        )
    return positions


def fetch_evm_positions_stub(wallet: str, rpc_url: str) -> list[BelievedPosition]:
    """STUB — EVM DEX position read requires operator RPC + indexer wiring.

    Returns empty list when RPC unset; raises when RPC set but indexer not wired.
  """
    if not rpc_url or not wallet:
        return []
    # STUB: operator extends with Uniswap/AAVE position indexer
    raise NotConfiguredError(
        "EVM built-in recon STUB — set TITAN_RECON_FETCHER_URL or wire evm indexer"
    )


class NotConfiguredError(RuntimeError):
    """Raised when recon sources are missing."""


def _http_override_fetch(url: str, venues: list[str]) -> list[BelievedPosition]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode())
    raw = data if isinstance(data, list) else data.get("positions", [])
    venue_set = {v.lower() for v in venues} if venues else set()
    out: list[BelievedPosition] = []
    for p in raw:
        venue = str(p.get("venue", "")).lower()
        if venue_set and venue not in venue_set:
            continue
        out.append(
            BelievedPosition(
                venue=venue,
                contract=str(p.get("contract", "")).lower(),
                notional_usd=float(p.get("notional_usd", 0)),
                side=str(p.get("side", "long")),
            )
        )
    return out


class ReconAggregator:
    """Aggregate positions from built-in sources with optional HTTP override."""

    def __init__(
        self,
        venues: list[str] | None = None,
        policy_raw: dict[str, Any] | None = None,
        fetcher_url: str | None = None,
    ) -> None:
        self.venues = [v.lower() for v in (venues or [])]
        self.policy_raw = policy_raw or {}
        tier0 = (self.policy_raw.get("tier0_money_path") or {})
        self.fetcher_url = (
            fetcher_url
            or _env("TITAN_RECON_FETCHER_URL")
            or str(tier0.get("recon_fetcher_url", "")).strip()
        )
        self.hyperliquid_wallet = _env("HYPERLIQUID_WALLET_ADDRESS")
        self.evm_rpc = _env("ETH_RPC_URL") or _env("ERIGON_HTTP_URL")
        self.evm_wallet = _env("EVM_WALLET_ADDRESS") or self.hyperliquid_wallet

    def fetch_positions(self) -> list[BelievedPosition]:
        if self.fetcher_url:
            logger.debug(f"recon via HTTP override: {self.fetcher_url[:48]}...")
            return _http_override_fetch(self.fetcher_url, self.venues)

        venue_set = set(self.venues)
        # Paper-only profile: no on-chain fetch required.
        if venue_set == {"paper"}:
            return []

        merged: dict[tuple[str, str], BelievedPosition] = {}

        if (not venue_set or "hyperliquid" in venue_set) and self.hyperliquid_wallet:
            for p in fetch_hyperliquid_positions(self.hyperliquid_wallet):
                merged[(p.venue, p.contract)] = p

        if venue_set & {"uniswap_v3", "curve", "aave_v3", "flashbots_protect"}:
            if self.evm_rpc and self.evm_wallet:
                try:
                    for p in fetch_evm_positions_stub(self.evm_wallet, self.evm_rpc):
                        merged[(p.venue, p.contract)] = p
                except NotConfiguredError:
                    if not merged:
                        raise

        if not merged:
            raise NotConfiguredError(
                "No recon source configured — set TITAN_RECON_FETCHER_URL, "
                "HYPERLIQUID_WALLET_ADDRESS, or tier0_money_path.recon_fetcher_url"
            )
        return list(merged.values())

    def as_fetcher(self) -> Callable[[list[str]], list[BelievedPosition]]:
        """Factory for reconciliation_service LiveExchangeAdapter."""

        def _fetcher(_venues: list[str]) -> list[BelievedPosition]:
            return self.fetch_positions()

        return _fetcher


def build_recon_fetcher(policy_raw: dict[str, Any] | None = None) -> Callable[[list[str]], list[Any]]:
    """Policy hook: tier0_money_path.recon_module or built-in aggregator."""
    raw = policy_raw or {}
    tier0 = raw.get("tier0_money_path") or {}
    if tier0.get("builtin_aggregator", True):
        venues = [str(v) for v in raw.get("allowed_venues", [])]
        return ReconAggregator(venues=venues, policy_raw=raw).as_fetcher()
    raise NotConfiguredError("tier0_money_path.builtin_aggregator=false — wire recon_module")
