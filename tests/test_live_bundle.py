"""Live bundle adapters — fail-closed until env configured."""

from __future__ import annotations

import pytest

from titan_safety.adapters.live_bundle import (
    NotConfiguredError,
    build_position_fetcher,
    credentials_status,
    live_signer,
)
from titan_safety.policy_loader import load_component


def test_build_position_fetcher_factory() -> None:
    fn = build_position_fetcher()
    assert callable(fn)
    with pytest.raises(NotConfiguredError):
        fn([])


def test_live_signer_not_armed() -> None:
    with pytest.raises(NotConfiguredError, match="not armed"):
        live_signer({"request_id": "t1"})


def test_load_component_live_signer() -> None:
    fn = load_component("titan_safety.adapters.live_bundle:live_signer")
    assert fn is live_signer


def test_credentials_status_no_secrets() -> None:
    st = credentials_status()
    assert "live_signing_ready" in st
    # DEX-only posture — no CEX keys; recon via RPC / Hyperliquid / fetcher URL
    for key in ("hyperliquid", "evm_rpc", "solana_rpc", "recon_fetcher_url"):
        assert key in st
        assert isinstance(st[key], bool)
