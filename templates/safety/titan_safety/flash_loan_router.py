"""Multi-source flash-loan router — Balancer → Morpho → Uni V4 → Aave fallback.

Deterministic calldata/typed-data composition for ALCHEMY → TRENCH-OPS path.
Paper mode simulates fee + slippage; live requires flash_loan_live.enabled + kernel gate (no human YES).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

# Known provider vaults (mainnet) — extend per chain in infra/flash_loan.yaml
PROVIDER_CONTRACTS: dict[str, dict[str, str]] = {
    "ethereum": {
        "balancer": "0xba12222222228d8ba445958a685a0a280785497",
        "morpho": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62a37bf003",
        "aave_v3": "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
        "uniswap_v4": "0x000000000004444c5dc75cb3583809552e5464de",
    },
    "arbitrum": {
        "balancer": "0xba12222222228d8ba445958a685a0a280785497",
        "morpho": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62a37bf003",
        "aave_v3": "0x794a61358d6845594f94dc1db02a252b5b4814ad",
    },
    "base": {
        "morpho": "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62a37bf003",
        "aave_v3": "0xa238dd80c259a72e81d7e4664a98015993f2321",
        "balancer": "0xba12222222228d8ba445958a685a0a280785497",
    },
}

SOURCE_FEE_BPS: dict[str, float] = {
    "balancer": 0.0,
    "morpho": 0.0,
    "uniswap_v4": 0.0,
    "aave_v3": 9.0,
}

CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "arbitrum": 42161,
    "base": 8453,
}


@dataclass
class FlashLoanConfig:
    enabled: bool = False
    max_amount_usd: float = 500_000.0
    max_fee_bps: float = 9.0
    paper_sim_required_days: int = 3
    source_priority: dict[str, list[str]] = field(default_factory=dict)
    pipelines: list[str] = field(default_factory=lambda: ["P3", "P6", "P12"])

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> FlashLoanConfig:
        fl = raw.get("flash_loan_live") or {}
        d = cls()
        priority = fl.get("sources") or {
            "ethereum": ["balancer", "morpho", "uniswap_v4", "aave_v3"],
            "arbitrum": ["balancer", "morpho", "aave_v3"],
            "base": ["morpho", "balancer", "aave_v3"],
        }
        return cls(
            enabled=bool(fl.get("enabled", d.enabled)),
            max_amount_usd=float(fl.get("max_amount_usd", d.max_amount_usd)),
            max_fee_bps=float(fl.get("max_fee_bps", d.max_fee_bps)),
            paper_sim_required_days=int(fl.get("paper_sim_required_days", d.paper_sim_required_days)),
            source_priority={str(k): [str(s) for s in v] for k, v in priority.items()},
            pipelines=[str(p) for p in fl.get("pipeline_ids", d.pipelines)],
        )


@dataclass
class FlashOperation:
    op: str
    venue: str
    asset: str
    amount_wei: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FlashLoanRequest:
    asset: str
    amount_usd: float
    chain: str
    strategy_id: str = ""
    operations: list[FlashOperation] = field(default_factory=list)
    prefer_source: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlashLoanRequest:
        ops_raw = data.get("operations") or []
        ops: list[FlashOperation] = []
        for o in ops_raw:
            if not isinstance(o, dict):
                continue
            ops.append(
                FlashOperation(
                    op=str(o.get("op", "")),
                    venue=str(o.get("venue", "")),
                    asset=str(o.get("asset", "")),
                    amount_wei=str(o.get("amount_wei", o.get("amount", "0"))),
                    params=dict(o.get("params") or {}),
                )
            )
        return cls(
            asset=str(data.get("asset", "WETH")),
            amount_usd=float(data.get("amount_usd", 0)),
            chain=str(data.get("chain", "ethereum")).lower(),
            strategy_id=str(data.get("strategy_id", "")),
            operations=ops,
            prefer_source=str(data.get("prefer_source", "")),
        )


@dataclass
class RouteDecision:
    selected_source: str
    fallback_sources: list[str]
    provider_address: str
    fee_bps: float
    chain_id: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComposeResult:
    passed: bool
    selected_source: str
    provider_address: str
    asset: str
    amount_usd: float
    amount_wei: str
    fee_bps: float
    fee_usd: float
    callback_operations: list[dict[str, Any]]
    calldata: str
    typed_data: dict[str, Any]
    expected_profit_usd: float
    reject_reason: str = ""
    trade_hints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FlashLoanRouter:
    """Select lowest-fee flash source and compose atomic callback plan."""

    REPAY_OPS = frozenset({"repay", "repay_flash", "repayFlashLoan"})

    def __init__(self, config: FlashLoanConfig | None = None) -> None:
        self.config = config or FlashLoanConfig()

    def route(self, asset: str, amount_usd: float, chain: str, *, prefer: str = "") -> RouteDecision:
        chain_l = chain.lower()
        priority = list(self.config.source_priority.get(chain_l, ["balancer", "morpho", "aave_v3"]))
        if prefer and prefer in priority:
            priority = [prefer] + [s for s in priority if s != prefer]

        selected = ""
        for src in priority:
            fee = SOURCE_FEE_BPS.get(src, 99.0)
            if fee <= self.config.max_fee_bps and chain_l in PROVIDER_CONTRACTS:
                if src in PROVIDER_CONTRACTS[chain_l]:
                    selected = src
                    break

        if not selected:
            selected = priority[0] if priority else "balancer"
        fallback = [s for s in priority if s != selected]
        provider = PROVIDER_CONTRACTS.get(chain_l, {}).get(selected, "0x0000000000000000000000000000000000000000")
        fee_bps = SOURCE_FEE_BPS.get(selected, 0.0)
        return RouteDecision(
            selected_source=selected,
            fallback_sources=fallback,
            provider_address=provider,
            fee_bps=fee_bps,
            chain_id=CHAIN_IDS.get(chain_l, 1),
            reason="lowest_fee_source" if not prefer else f"prefer_{prefer}",
        )

    def _usd_to_wei(self, amount_usd: float, asset: str) -> str:
        # Paper stub — 1 ETH ≈ $3000 for deterministic sizing
        px = 3000.0 if asset.upper() in ("WETH", "ETH") else 1.0
        wei = int(max(amount_usd, 0) / px * 1e18)
        return str(wei)

    def _validate_operations(self, ops: list[FlashOperation]) -> tuple[bool, str]:
        if not ops:
            return False, "operations required (must include repay step)"
        has_repay = any(o.op.lower() in self.REPAY_OPS for o in ops)
        if not has_repay:
            return False, "missing repay/repay_flash operation in callback"
        return True, ""

    def _estimate_profit_usd(
        self, amount_usd: float, fee_bps: float, ops: list[FlashOperation]
    ) -> float:
        fee = amount_usd * fee_bps / 10_000.0
        slip_bps = 15.0 + 5.0 * len(ops)
        slip = amount_usd * slip_bps / 10_000.0
        # Simulated edge — arb/yield ops target 20–80 bps gross on notional
        gross_bps = 35.0 + (hash(tuple(o.op for o in ops)) % 45)
        gross = amount_usd * gross_bps / 10_000.0
        return gross - fee - slip

    def _build_typed_data(
        self,
        *,
        chain_id: int,
        source: str,
        provider: str,
        asset: str,
        amount_wei: str,
        strategy_id: str,
        callback_ops: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "FlashLoanExecution": [
                    {"name": "source", "type": "string"},
                    {"name": "provider", "type": "address"},
                    {"name": "asset", "type": "string"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "strategyId", "type": "string"},
                    {"name": "callbackHash", "type": "bytes32"},
                ],
            },
            "primaryType": "FlashLoanExecution",
            "domain": {"name": "TITAN", "version": "1", "chainId": chain_id},
            "message": {
                "source": source,
                "provider": provider,
                "asset": asset,
                "amount": amount_wei,
                "strategyId": strategy_id or "flash_loan",
                "callbackHash": "0x"
                + hashlib.sha256(json.dumps(callback_ops, sort_keys=True).encode()).hexdigest(),
            },
        }

    def _build_calldata_stub(
        self, source: str, provider: str, asset: str, amount_wei: str, callback_ops: list[dict[str, Any]]
    ) -> str:
        payload = f"{source}|{provider}|{asset}|{amount_wei}|{json.dumps(callback_ops, sort_keys=True)}"
        return "0x" + hashlib.sha256(payload.encode()).hexdigest()

    def compose(self, request: FlashLoanRequest) -> ComposeResult:
        if request.amount_usd <= 0:
            return ComposeResult(
                passed=False,
                selected_source="",
                provider_address="",
                asset=request.asset,
                amount_usd=request.amount_usd,
                amount_wei="0",
                fee_bps=0,
                fee_usd=0,
                callback_operations=[],
                calldata="0x",
                typed_data={},
                expected_profit_usd=0,
                reject_reason="amount_usd must be positive",
            )

        if request.amount_usd > self.config.max_amount_usd:
            return ComposeResult(
                passed=False,
                selected_source="",
                provider_address="",
                asset=request.asset,
                amount_usd=request.amount_usd,
                amount_wei="0",
                fee_bps=0,
                fee_usd=0,
                callback_operations=[],
                calldata="0x",
                typed_data={},
                expected_profit_usd=0,
                reject_reason=f"amount exceeds max {self.config.max_amount_usd}",
            )

        if request.strategy_id and self.config.pipelines and request.strategy_id not in self.config.pipelines:
            return ComposeResult(
                passed=False,
                selected_source="",
                provider_address="",
                asset=request.asset,
                amount_usd=request.amount_usd,
                amount_wei="0",
                fee_bps=0,
                fee_usd=0,
                callback_operations=[],
                calldata="0x",
                typed_data={},
                expected_profit_usd=0,
                reject_reason=f"strategy {request.strategy_id} not in flash_loan pipeline allowlist",
            )

        ok, op_reason = self._validate_operations(request.operations)
        if not ok:
            # Auto-inject minimal repay for route-only requests (paper probe)
            if not request.operations:
                request.operations = [
                    FlashOperation("swap", "uniswap_v3", request.asset, self._usd_to_wei(request.amount_usd, request.asset)),
                    FlashOperation(
                        "repay_flash",
                        "flash_loan_router",
                        request.asset,
                        self._usd_to_wei(request.amount_usd, request.asset),
                    ),
                ]
                ok, op_reason = self._validate_operations(request.operations)
            if not ok:
                return ComposeResult(
                    passed=False,
                    selected_source="",
                    provider_address="",
                    asset=request.asset,
                    amount_usd=request.amount_usd,
                    amount_wei="0",
                    fee_bps=0,
                    fee_usd=0,
                    callback_operations=[],
                    calldata="0x",
                    typed_data={},
                    expected_profit_usd=0,
                    reject_reason=op_reason,
                )

        route = self.route(
            request.asset,
            request.amount_usd,
            request.chain,
            prefer=request.prefer_source,
        )
        amount_wei = self._usd_to_wei(request.amount_usd, request.asset)
        callback_ops = [o.to_dict() for o in request.operations]
        fee_usd = request.amount_usd * route.fee_bps / 10_000.0
        profit = self._estimate_profit_usd(request.amount_usd, route.fee_bps, request.operations)

        if profit <= 0:
            return ComposeResult(
                passed=False,
                selected_source=route.selected_source,
                provider_address=route.provider_address,
                asset=request.asset,
                amount_usd=request.amount_usd,
                amount_wei=amount_wei,
                fee_bps=route.fee_bps,
                fee_usd=fee_usd,
                callback_operations=callback_ops,
                calldata="0x",
                typed_data={},
                expected_profit_usd=profit,
                reject_reason="negative expected profit after fee+slippage",
            )

        typed_data = self._build_typed_data(
            chain_id=route.chain_id,
            source=route.selected_source,
            provider=route.provider_address,
            asset=request.asset,
            amount_wei=amount_wei,
            strategy_id=request.strategy_id,
            callback_ops=callback_ops,
        )
        calldata = self._build_calldata_stub(
            route.selected_source,
            route.provider_address,
            request.asset,
            amount_wei,
            callback_ops,
        )

        return ComposeResult(
            passed=True,
            selected_source=route.selected_source,
            provider_address=route.provider_address,
            asset=request.asset,
            amount_usd=request.amount_usd,
            amount_wei=amount_wei,
            fee_bps=route.fee_bps,
            fee_usd=fee_usd,
            callback_operations=callback_ops,
            calldata=calldata,
            typed_data=typed_data,
            expected_profit_usd=profit,
            trade_hints={
                "uses_flash_loan": True,
                "flash_loan_source": route.selected_source,
                "flash_loan_amount_usd": request.amount_usd,
                "venue": "paper" if not self.config.enabled else "flashbots_protect",
                "contract": route.provider_address.lower(),
                "reason_code": "FLASH_LOAN_EXEC",
            },
        )
