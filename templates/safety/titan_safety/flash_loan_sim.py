"""Paper simulator for flash-loan routes — fee/slippage/profit distribution."""

from __future__ import annotations

import random
from typing import Any

from .flash_loan_router import FlashLoanConfig, FlashLoanRequest, FlashLoanRouter, FlashOperation


def run_simulation(
    count: int = 50,
    seed: int = 42,
    equity_usd: float = 2500.0,
    config: FlashLoanConfig | None = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    router = FlashLoanRouter(config)
    chains = list((config.source_priority if config else FlashLoanConfig().source_priority).keys()) or [
        "ethereum",
        "arbitrum",
        "base",
    ]
    strategies = (config.pipelines if config else FlashLoanConfig().pipelines) or ["P3", "P6", "P12"]

    passed = 0
    rejected = 0
    total_profit = 0.0
    samples: list[dict[str, Any]] = []

    for i in range(count):
        chain = chains[i % len(chains)]
        strategy = strategies[i % len(strategies)]
        amount = equity_usd * rng.uniform(0.05, 0.5)
        req = FlashLoanRequest(
            asset="WETH",
            amount_usd=amount,
            chain=chain,
            strategy_id=strategy,
            operations=[
                FlashOperation("swap", "uniswap_v3", "WETH", str(int(amount * 1e15))),
                FlashOperation("repay_flash", "flash_loan_router", "WETH", str(int(amount * 1e15))),
            ],
        )
        result = router.compose(req)
        if result.passed:
            passed += 1
            total_profit += result.expected_profit_usd
        else:
            rejected += 1
        samples.append(
            {
                "chain": chain,
                "strategy_id": strategy,
                "amount_usd": round(amount, 2),
                "passed": result.passed,
                "source": result.selected_source,
                "profit_usd": round(result.expected_profit_usd, 4),
                "reject_reason": result.reject_reason,
            }
        )

    return {
        "simulation": "flash_loan_router",
        "count": count,
        "seed": seed,
        "equity_usd": equity_usd,
        "passed": passed,
        "rejected": rejected,
        "pass_rate": round(passed / count, 4) if count else 0,
        "total_expected_profit_usd": round(total_profit, 2),
        "samples": samples[:10],
    }
