"""Solana reconciliation adapter stub — wire live fetcher via policy module path."""

from __future__ import annotations

from typing import Any


class NotConfiguredError(RuntimeError):
    pass


class SolanaReconAdapter:
    """Fetch believed vs on-chain positions for Solana memecoin lane."""

    def __init__(self, module_path: str = "") -> None:
        self.module_path = module_path.strip()

    def configured(self) -> bool:
        return bool(self.module_path) and self.module_path != "mock"

    def fetch_positions(self) -> list[dict[str, Any]]:
        if not self.configured():
            raise NotConfiguredError(
                "Solana recon not configured — set memecoin_trench.recon_module in policy "
                "and capital_profile=live before real SOL"
            )
        raise NotConfiguredError(f"Live module not loaded: {self.module_path}")

    def health(self) -> dict[str, Any]:
        return {"adapter": "solana_recon", "configured": self.configured(), "module": self.module_path or "none"}
