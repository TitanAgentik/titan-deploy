"""Jito bundle submit adapter stub — live path requires signing_node + gate receipt."""

from __future__ import annotations

from typing import Any


class NotConfiguredError(RuntimeError):
    pass


class JitoSubmitAdapter:
    """Submit buy/sell bundles via Jito block engine (EDGE-FRA)."""

    def __init__(self, block_engine_url: str = "", tip_lamports: int = 100_000) -> None:
        self.block_engine_url = block_engine_url.strip()
        self.tip_lamports = tip_lamports

    def configured(self) -> bool:
        return bool(self.block_engine_url)

    def submit_bundle(self, signed_txs: list[str], gate_receipt: str) -> dict[str, Any]:
        if not gate_receipt:
            return {"ok": False, "error": "gate receipt required"}
        if not self.configured():
            raise NotConfiguredError(
                "Jito block engine URL not set — configure infra/solana_memecoin.yaml "
                "and memecoinTrench in openclaw.json"
            )
        raise NotConfiguredError(
            "Live Jito submit not implemented in bundle — wire Rust/TS signer on signing_node"
        )

    def health(self) -> dict[str, Any]:
        return {
            "adapter": "jito_submit",
            "configured": self.configured(),
            "block_engine": self.block_engine_url or "none",
            "tip_lamports": self.tip_lamports,
        }
