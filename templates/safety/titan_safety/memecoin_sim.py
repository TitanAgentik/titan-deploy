"""Paper simulator for P22 memecoin trench — mock Pump.fun events → filter → TCA fills."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from .memecoin_filter import MemecoinFilter, MemecoinFilterConfig, MintCandidate
from .tca import Fill, TCAEngine


@dataclass
class SimEvent:
    kind: str  # create | buy | graduate
    mint: str
    candidate: MintCandidate
    ts: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "mint": self.mint,
            "candidate": self.candidate.to_dict(),
            "ts": self.ts,
        }


def _random_mint(rng: random.Random) -> str:
    return "".join(rng.choices("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", k=44))


def generate_events(count: int, seed: int = 42) -> list[SimEvent]:
    rng = random.Random(seed)
    events: list[SimEvent] = []
    now = time.time()
    for i in range(count):
        mint = _random_mint(rng)
        rug_roll = rng.random()
        cand = MintCandidate(
            mint=mint,
            mint_authority_revoked=rug_roll > 0.12,
            freeze_authority_revoked=rug_roll > 0.08,
            top10_holder_pct=rng.uniform(5, 55) if rug_roll < 0.2 else rng.uniform(8, 25),
            insider_pct=rng.uniform(2, 25),
            curve_progress_pct=rng.uniform(1, 95),
            curve_fill_minutes=rng.uniform(5, 480),
            sell_sim_ok=rug_roll > 0.06,
            graduated=rng.random() > 0.92,
            smart_money_wallet="SMw" + str(rng.randint(1000, 9999)) if rng.random() > 0.85 else "",
        )
        kind = "graduate" if cand.graduated else ("buy" if cand.curve_progress_pct > 10 else "create")
        events.append(SimEvent(kind=kind, mint=mint, candidate=cand, ts=now + i * 0.5))
    return events


def run_simulation(
    count: int = 100,
    seed: int = 42,
    equity_usd: float = 2500.0,
    config: MemecoinFilterConfig | None = None,
) -> dict[str, Any]:
    flt = MemecoinFilter(config)
    tca = TCAEngine()
    events = generate_events(count, seed)
    passed = 0
    rejected = 0
    fills: list[Fill] = []
    rejections: list[dict[str, Any]] = []

    for ev in events:
        verdict = flt.evaluate(ev.candidate)
        if not verdict.passed:
            rejected += 1
            rejections.append({"mint": ev.mint, "reason": verdict.reject_reason})
            continue
        passed += 1
        notional = equity_usd * (verdict.max_notional_pct_equity / 100.0)
        gross = notional * rng_pnl(random.Random(hash(ev.mint) % 2**32))
        fills.append(
            Fill(
                pipeline_id="P22",
                venue="solana_pumpfun",
                side="buy",
                notional_usd=notional,
                expected_price=1.0,
                realized_price=1.0 + (gross / max(notional, 1)) * 0.01,
                gross_pnl_usd=gross,
                gas_usd=notional * 0.002,
                tip_usd=notional * 0.001,
                reverted=False,
                ts=ev.ts,
            )
        )
        tca.ingest(fills[-1])

    score = tca.scorecard("P22")
    return {
        "pipeline_id": "P22",
        "events": count,
        "passed": passed,
        "rejected": rejected,
        "pass_rate": round(passed / max(count, 1), 4),
        "fills": len(fills),
        "scorecard": score.to_dict() if score else {},
        "sample_rejections": rejections[:10],
    }


def rng_pnl(rng: random.Random) -> float:
    """Simulated return fraction — heavy left tail like real trench."""
    if rng.random() < 0.7:
        return rng.uniform(-0.4, -0.05)
    if rng.random() < 0.9:
        return rng.uniform(0.05, 0.5)
    return rng.uniform(0.5, 3.0)
