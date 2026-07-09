"""Six-gate memecoin trench filter — Pump.fun / Solana launch defense.

Deterministic pre-execution filter for P22. Rejects rugs/honeypots before capital.
No offensive tooling — defensive gates only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MemecoinFilterConfig:
    max_top10_holder_pct: float = 30.0
    max_insider_pct: float = 15.0
    min_curve_progress_pct: float = 2.0
    max_fast_fill_minutes: float = 30.0  # cabal signal if curve fills too fast
    min_curve_progress_for_climb: float = 15.0
    graduation_target_usd: float = 69000.0
    max_snipe_pct_equity: float = 0.5
    daily_sol_cap: float = 2.0
    require_sell_sim: bool = True
    strategies_enabled: list[str] = field(
        default_factory=lambda: [
            "curve_climb",
            "graduation",
            "post_grad_pullback",
            "smart_money_mirror",
            "first_block_snipe",
        ]
    )

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> MemecoinFilterConfig:
        m = raw.get("memecoin_trench", {}) if raw else {}
        d = cls()
        return cls(
            max_top10_holder_pct=float(m.get("max_top10_holder_pct", d.max_top10_holder_pct)),
            max_insider_pct=float(m.get("max_insider_pct", d.max_insider_pct)),
            min_curve_progress_pct=float(m.get("min_curve_progress_pct", d.min_curve_progress_pct)),
            max_fast_fill_minutes=float(m.get("max_fast_fill_minutes", d.max_fast_fill_minutes)),
            min_curve_progress_for_climb=float(
                m.get("min_curve_progress_for_climb", d.min_curve_progress_for_climb)
            ),
            graduation_target_usd=float(m.get("graduation_target_usd", d.graduation_target_usd)),
            max_snipe_pct_equity=float(m.get("max_snipe_pct_equity", d.max_snipe_pct_equity)),
            daily_sol_cap=float(m.get("daily_sol_cap", d.daily_sol_cap)),
            require_sell_sim=bool(m.get("require_sell_sim", d.require_sell_sim)),
            strategies_enabled=list(m.get("strategies_enabled", d.strategies_enabled)),
        )


@dataclass
class MintCandidate:
    mint: str
    mint_authority_revoked: bool = True
    freeze_authority_revoked: bool = True
    top10_holder_pct: float = 0.0
    insider_pct: float = 0.0
    curve_progress_pct: float = 0.0
    curve_fill_minutes: float = 999.0
    sell_sim_ok: bool = True
    graduated: bool = False
    smart_money_wallet: str = ""
    strategy: str = "curve_climb"
    liquidity_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FilterVerdict:
    mint: str
    passed: bool
    gates: dict[str, str]
    reject_reason: str = ""
    recommended_strategy: str = ""
    max_notional_pct_equity: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemecoinFilter:
    GATE_NAMES = (
        "G1_mint_authority",
        "G2_freeze_authority",
        "G3_holder_concentration",
        "G4_preload_cabal",
        "G5_curve_liquidity",
        "G6_sellability",
    )

    def __init__(self, config: MemecoinFilterConfig | None = None) -> None:
        self.config = config or MemecoinFilterConfig()

    def evaluate(self, candidate: MintCandidate) -> FilterVerdict:
        gates: dict[str, str] = {}
        reject = ""

        if not candidate.mint_authority_revoked:
            gates["G1_mint_authority"] = "FAIL"
            reject = reject or "mint authority not revoked"
        else:
            gates["G1_mint_authority"] = "PASS"

        if not candidate.freeze_authority_revoked:
            gates["G2_freeze_authority"] = "FAIL"
            reject = reject or "freeze authority active (honeypot risk)"
        else:
            gates["G2_freeze_authority"] = "PASS"

        if candidate.top10_holder_pct > self.config.max_top10_holder_pct:
            gates["G3_holder_concentration"] = "FAIL"
            reject = reject or f"top10 holders {candidate.top10_holder_pct:.1f}% > cap"
        elif candidate.insider_pct > self.config.max_insider_pct:
            gates["G3_holder_concentration"] = "FAIL"
            reject = reject or f"insider {candidate.insider_pct:.1f}% > cap"
        else:
            gates["G3_holder_concentration"] = "PASS"

        cabal = (
            candidate.curve_fill_minutes < self.config.max_fast_fill_minutes
            and candidate.curve_progress_pct > 50.0
        )
        if cabal:
            gates["G4_preload_cabal"] = "FAIL"
            reject = reject or "fast curve fill — coordinated preload suspected"
        else:
            gates["G4_preload_cabal"] = "PASS"

        if candidate.graduated:
            gates["G5_curve_liquidity"] = "PASS"
        elif candidate.curve_progress_pct < self.config.min_curve_progress_pct:
            gates["G5_curve_liquidity"] = "FAIL"
            reject = reject or "curve progress too low / dead"
        else:
            gates["G5_curve_liquidity"] = "PASS"

        if self.config.require_sell_sim and not candidate.sell_sim_ok:
            gates["G6_sellability"] = "FAIL"
            reject = reject or "sell simulation failed (honeypot)"
        else:
            gates["G6_sellability"] = "PASS"

        strategy, max_pct, conf = self._classify_strategy(candidate, bool(reject))
        return FilterVerdict(
            mint=candidate.mint,
            passed=not bool(reject),
            gates=gates,
            reject_reason=reject,
            recommended_strategy=strategy,
            max_notional_pct_equity=max_pct,
            confidence=conf,
        )

    def _classify_strategy(
        self, c: MintCandidate, rejected: bool
    ) -> tuple[str, float, float]:
        if rejected:
            return ("none", 0.0, 0.0)
        cfg = self.config
        if c.graduated and c.strategy in cfg.strategies_enabled:
            return ("post_grad_pullback", 1.0, 0.75)
        if c.smart_money_wallet and "smart_money_mirror" in cfg.strategies_enabled:
            return ("smart_money_mirror", 0.5, 0.7)
        if c.curve_progress_pct >= 85.0 and "graduation" in cfg.strategies_enabled:
            return ("graduation", 0.5, 0.65)
        if (
            c.curve_progress_pct >= cfg.min_curve_progress_for_climb
            and "curve_climb" in cfg.strategies_enabled
        ):
            return ("curve_climb", 0.5, 0.55)
        if "first_block_snipe" in cfg.strategies_enabled:
            return ("first_block_snipe", cfg.max_snipe_pct_equity, 0.35)
        return ("none", 0.0, 0.0)
