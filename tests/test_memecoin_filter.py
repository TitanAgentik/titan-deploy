"""Tests for P22 memecoin six-gate filter."""

from __future__ import annotations

from titan_safety.memecoin_filter import MemecoinFilter, MintCandidate


def test_honeypot_freeze_rejected() -> None:
    flt = MemecoinFilter()
    v = flt.evaluate(
        MintCandidate(
            mint="abc",
            mint_authority_revoked=True,
            freeze_authority_revoked=False,
            sell_sim_ok=True,
        )
    )
    assert not v.passed
    assert "freeze" in v.reject_reason.lower()


def test_clean_mint_passes_curve_climb() -> None:
    flt = MemecoinFilter()
    v = flt.evaluate(
        MintCandidate(
            mint="good",
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            top10_holder_pct=20.0,
            insider_pct=5.0,
            curve_progress_pct=40.0,
            curve_fill_minutes=120.0,
            sell_sim_ok=True,
        )
    )
    assert v.passed
    assert v.recommended_strategy == "curve_climb"
    assert v.max_notional_pct_equity == 0.5


def test_cabal_fast_fill_rejected() -> None:
    flt = MemecoinFilter()
    v = flt.evaluate(
        MintCandidate(
            mint="cabal",
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            top10_holder_pct=15.0,
            curve_progress_pct=70.0,
            curve_fill_minutes=10.0,
            sell_sim_ok=True,
        )
    )
    assert not v.passed
    assert "cabal" in v.reject_reason.lower() or "preload" in v.reject_reason.lower()


def test_graduated_post_grad_strategy() -> None:
    flt = MemecoinFilter()
    v = flt.evaluate(
        MintCandidate(
            mint="grad",
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            top10_holder_pct=18.0,
            curve_progress_pct=100.0,
            curve_fill_minutes=200.0,
            sell_sim_ok=True,
            graduated=True,
        )
    )
    assert v.passed
    assert v.recommended_strategy == "post_grad_pullback"


def test_sell_sim_honeypot_rejected() -> None:
    flt = MemecoinFilter()
    v = flt.evaluate(
        MintCandidate(
            mint="honeypot",
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            top10_holder_pct=12.0,
            insider_pct=5.0,
            curve_progress_pct=40.0,
            curve_fill_minutes=90.0,
            sell_sim_ok=False,
        )
    )
    assert not v.passed
    assert "sell" in v.reject_reason.lower() or "honeypot" in v.reject_reason.lower()


def test_first_block_snipe_size_cap() -> None:
    flt = MemecoinFilter()
    v = flt.evaluate(
        MintCandidate(
            mint="snipe",
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            top10_holder_pct=10.0,
            insider_pct=3.0,
            curve_progress_pct=5.0,
            curve_fill_minutes=60.0,
            sell_sim_ok=True,
        )
    )
    assert v.passed
    assert v.recommended_strategy == "first_block_snipe"
    assert v.max_notional_pct_equity == 0.5
    assert v.confidence < 0.5
