"""Simple operator capital deposit, withdrawal, and Trezor sweep."""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .audit_chain import AuditChainWriter, DecisionLogEntry, build_fingerprint


DEFAULT_CAPITAL_DIR = Path.home() / ".openclaw" / "capital"
DEFAULT_STATE_PATH = DEFAULT_CAPITAL_DIR / "portfolio_state.json"
DEFAULT_AUDIT_PATH = DEFAULT_CAPITAL_DIR / "capital_audit.jsonl"


@dataclass
class TrezorSweepConfig:
    harvest_threshold_usd: float = 15000.0
    sweep_pct_of_weekly_profit: float = 20.0
    sweep_day_utc: str = "Sunday"
    pause_below_threshold: bool = True
    note: str = "Growth phase below threshold — 100% reinvest; no sweep"


@dataclass
class CapitalConfig:
    min_operating_capital_usd: float = 500.0
    max_single_withdrawal_pct: float = 20.0
    state_path: Path = field(default_factory=lambda: DEFAULT_STATE_PATH)
    audit_path: Path = field(default_factory=lambda: DEFAULT_AUDIT_PATH)
    withdrawal_adapter: str = "mock"
    trezor_sweep: TrezorSweepConfig = field(default_factory=TrezorSweepConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapitalConfig:
        sweep_raw = data.get("trezor_sweep") or {}
        sweep = TrezorSweepConfig(
            harvest_threshold_usd=float(
                sweep_raw.get("harvest_threshold_usd", 15000.0)
            ),
            sweep_pct_of_weekly_profit=float(
                sweep_raw.get("sweep_pct_of_weekly_profit", 20.0)
            ),
            sweep_day_utc=str(sweep_raw.get("sweep_day_utc", "Sunday")),
            pause_below_threshold=bool(sweep_raw.get("pause_below_threshold", True)),
            note=str(
                sweep_raw.get(
                    "note",
                    "Growth phase below threshold — 100% reinvest; no sweep",
                )
            ),
        )
        state = str(data.get("state_path", DEFAULT_STATE_PATH))
        audit = str(data.get("audit_path", DEFAULT_AUDIT_PATH))
        return cls(
            min_operating_capital_usd=float(
                data.get("min_operating_capital_usd", 500.0)
            ),
            max_single_withdrawal_pct=float(
                data.get("max_single_withdrawal_pct", 20.0)
            ),
            state_path=Path(state.replace("~", str(Path.home()))).expanduser(),
            audit_path=Path(audit.replace("~", str(Path.home()))).expanduser(),
            withdrawal_adapter=str(data.get("withdrawal_adapter", "mock")),
            trezor_sweep=sweep,
        )


def _expand(path: str | Path) -> Path:
    return Path(str(path).replace("~", str(Path.home()))).expanduser()


def load_capital_config(
    config_path: str | Path | None = None,
) -> CapitalConfig:
    """Load capital section from Hermes config.yaml or openclaw.json."""
    candidates: list[Path] = []
    if config_path:
        candidates.append(_expand(config_path))
    candidates.extend(
        [
            Path.home() / ".hermes" / "config.yaml",
            Path.home() / ".openclaw" / "config.yaml",
            Path.home() / ".openclaw" / "openclaw.json",
        ]
    )
    for path in candidates:
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(raw).get("capital") or {}
        else:
            data = yaml.safe_load(raw) or {}
            data = data.get("capital") or {}
        if data:
            return CapitalConfig.from_dict(data)
    return CapitalConfig()


@dataclass
class PendingWithdrawal:
    request_id: str
    amount_usd: float
    asset: str
    address: str | None
    status: str
    operator: str
    created_at: float
    needs_confirm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapitalResult:
    ok: bool
    action: str
    message: str
    state: dict[str, Any]
    needs_confirm: bool = False
    request_id: str | None = None
    tx_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "message": self.message,
            "state": self.state,
            "needs_confirm": self.needs_confirm,
            "request_id": self.request_id,
            "tx_hash": self.tx_hash,
        }


class WithdrawalAdapter(ABC):
    """Pluggable on-chain / Trezor execution (mock in bundle)."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def execute_withdrawal(
        self,
        amount_usd: float,
        asset: str,
        address: str | None,
        operator: str,
    ) -> dict[str, Any]:
        ...


class MockWithdrawalAdapter(WithdrawalAdapter):
    """Mock adapter — no real keys; ops wires Trezor / in-process SigningNode later."""

    @property
    def name(self) -> str:
        return "mock"

    def execute_withdrawal(
        self,
        amount_usd: float,
        asset: str,
        address: str | None,
        operator: str,
    ) -> dict[str, Any]:
        return {
            "status": "mock_executed",
            "tx_hash": f"0xmock{uuid.uuid4().hex[:56]}",
            "amount_usd": amount_usd,
            "asset": asset,
            "address": address or "trezor:cold-vault",
            "operator": operator,
            "note": "Mock execution — wire in-process SigningNode + Trezor for production",
        }


class SigningNodeWithdrawalAdapter(WithdrawalAdapter):
    """Routes withdrawals through in-process SigningNode (requires gate receipt).

    Live profile: set capital.withdrawal_adapter to trezor_signing / signing_node.
    Until a hardware signer is plugged in, this still uses the mock signer behind
    the receipt gate — but it refuses unsigned requests. Legacy HTTP :19010 via
    mode=http + endpoint.
    """

    def __init__(
        self,
        endpoint: str = "",
        safety_dir: Path | None = None,
        timeout: float = 5.0,
        mode: str = "in_process",
        policy_path: Path | None = None,
        policy_raw: dict[str, Any] | None = None,
    ) -> None:
        self.endpoint = (endpoint or "").rstrip("/")
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.timeout = timeout
        self.mode = mode
        self.policy_path = policy_path
        self.policy_raw = policy_raw or {}

    @property
    def name(self) -> str:
        return "trezor_signing"

    def execute_withdrawal(
        self,
        amount_usd: float,
        asset: str,
        address: str | None,
        operator: str,
    ) -> dict[str, Any]:
        from .gate_receipt import RECEIPT_HEADER, issue_gate_receipt
        from .kernel import TradeRequest
        from .signing_service import build_signing_node

        trade_id = f"withdraw-{uuid.uuid4().hex[:12]}"
        trade = TradeRequest(
            trade_id=trade_id,
            venue="capital",
            contract=asset.lower(),
            side="withdraw",
            notional_usd=amount_usd,
        )
        receipt = issue_gate_receipt(trade, self.safety_dir)
        body = {
            "request_id": trade_id,
            "trade": {
                "trade_id": trade_id,
                "venue": "capital",
                "contract": asset.lower(),
                "side": "withdraw",
                "notional_usd": amount_usd,
            },
            "calldata": {
                "action": "withdraw",
                "asset": asset,
                "address": address or "trezor:cold-vault",
                "operator": operator,
            },
            "gate_receipt": receipt.token,
        }
        headers = {RECEIPT_HEADER: receipt.token}

        if self.mode == "http" and self.endpoint:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(
                f"{self.endpoint}/v1/sign",
                data=json.dumps(body).encode(),
                headers={
                    "Content-Type": "application/json",
                    RECEIPT_HEADER: receipt.token,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                err = json.loads(exc.read().decode()) if exc.fp else {"reason": str(exc)}
                return {
                    "status": "denied",
                    "error": err,
                    "amount_usd": amount_usd,
                    "asset": asset,
                }
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                return {
                    "status": "unreachable",
                    "error": str(exc),
                    "amount_usd": amount_usd,
                    "note": "signing HTTP unreachable — fail-closed",
                }
        else:
            node = build_signing_node(
                policy_path=self.policy_path,
                safety_dir=self.safety_dir,
                policy_raw=self.policy_raw,
                require_live_signer=False,
            )
            code, result = node.sign(body, headers)
            if code >= 400:
                return {
                    "status": "denied",
                    "error": result,
                    "amount_usd": amount_usd,
                    "asset": asset,
                }

        return {
            "status": result.get("status", "signed"),
            "tx_hash": result.get("signature", ""),
            "amount_usd": amount_usd,
            "asset": asset,
            "address": address or "trezor:cold-vault",
            "operator": operator,
            "signing": result,
        }


def get_withdrawal_adapter(name: str, **kwargs: Any) -> WithdrawalAdapter:
    if name == "mock":
        return MockWithdrawalAdapter()
    if name in ("trezor_signing", "signing_node", "live", "trezor", "in_process"):
        return SigningNodeWithdrawalAdapter(
            endpoint=str(kwargs.get("endpoint", "") or ""),
            safety_dir=kwargs.get("safety_dir"),
            mode=str(kwargs.get("mode", "in_process") or "in_process"),
            policy_path=kwargs.get("policy_path"),
            policy_raw=kwargs.get("policy_raw"),
        )
    raise ValueError(f"Unknown withdrawal adapter: {name}")


class CapitalManager:
    """Deposit, withdraw, balance, and profit sweep with audit trail."""

    def __init__(
        self,
        config: CapitalConfig | None = None,
        adapter: WithdrawalAdapter | None = None,
    ) -> None:
        self.config = config or load_capital_config()
        self.adapter = adapter or get_withdrawal_adapter(
            self.config.withdrawal_adapter
        )
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._audit = AuditChainWriter(self.config.audit_path)

    def _default_state(self) -> dict[str, Any]:
        return {
            "version": 1,
            "equity_usd": 0.0,
            "available_usd": 0.0,
            "reserved_usd": 0.0,
            "weekly_profit_usd": 0.0,
            "assets": {},
            "pending_withdrawals": [],
            "last_sweep_at": None,
            "updated_at": time.time(),
        }

    def load_state(self) -> dict[str, Any]:
        if not self.config.state_path.exists():
            return self._default_state()
        data = json.loads(self.config.state_path.read_text(encoding="utf-8"))
        for key, val in self._default_state().items():
            data.setdefault(key, val)
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = time.time()
        self.config.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _sync_tax_ledger(self, event: dict[str, Any]) -> None:
        try:
            import sys

            tax_dir = self.config.state_path.parent
            if str(tax_dir) not in sys.path:
                sys.path.insert(0, str(tax_dir))
            from tax_ledger import TaxLedger  # type: ignore[import-untyped]

            ledger = TaxLedger(tax_dir / "tax_lots.jsonl")
            ledger.sync_from_capital_event(event)
        except Exception:
            pass

    def _log_audit(self, action: str, operator: str, payload: dict[str, Any]) -> None:
        fp = build_fingerprint(prompt_version="capital-v1")
        entry = DecisionLogEntry(
            decision_id=f"cap-{uuid.uuid4().hex[:12]}",
            agent_id="ATLAS",
            action=action,
            fingerprint=fp,
            payload={"operator": operator, **payload},
        )
        self._audit.append(entry)

    def balance(self) -> dict[str, Any]:
        state = self.load_state()
        pending_total = sum(
            w["amount_usd"]
            for w in state.get("pending_withdrawals", [])
            if w.get("status") in ("pending_confirmation", "queued")
        )
        return {
            "equity_usd": state["equity_usd"],
            "available_usd": state["available_usd"],
            "reserved_usd": state["reserved_usd"],
            "pending_withdrawals_usd": pending_total,
            "min_operating_capital_usd": self.config.min_operating_capital_usd,
            "max_withdrawable_usd": max(
                0.0,
                state["available_usd"] - self.config.min_operating_capital_usd,
            ),
            "assets": state.get("assets", {}),
            "harvest_phase": state["equity_usd"]
            >= self.config.trezor_sweep.harvest_threshold_usd,
            "pending_withdrawals": state.get("pending_withdrawals", []),
        }

    def deposit(
        self,
        amount: float,
        asset: str,
        *,
        chain: str | None = None,
        tx_hash: str | None = None,
        source: str = "operator",
        operator: str = "operator",
    ) -> CapitalResult:
        if amount <= 0:
            return CapitalResult(
                False,
                "deposit_denied",
                "Deposit amount must be positive",
                self.balance(),
            )
        state = self.load_state()
        state["equity_usd"] = round(state["equity_usd"] + amount, 2)
        state["available_usd"] = round(state["available_usd"] + amount, 2)
        assets = state.setdefault("assets", {})
        assets[asset.upper()] = round(assets.get(asset.upper(), 0.0) + amount, 2)
        self.save_state(state)
        payload = {
            "amount_usd": amount,
            "asset": asset.upper(),
            "chain": chain,
            "tx_hash": tx_hash,
            "source": source,
            "equity_after": state["equity_usd"],
        }
        self._log_audit("capital_deposit", operator, payload)
        self._sync_tax_ledger({"action": "deposit", **payload})
        return CapitalResult(
            True,
            "deposit_recorded",
            f"Deposited ${amount:,.2f} {asset.upper()} — equity now ${state['equity_usd']:,.2f}",
            self.balance(),
            tx_hash=tx_hash,
        )

    def _withdrawal_pct(self, amount: float, equity: float) -> float:
        if equity <= 0:
            return 100.0
        return (amount / equity) * 100.0

    def withdraw(
        self,
        amount: float,
        asset: str,
        *,
        address: str | None = None,
        operator: str = "operator",
        confirm_request_id: str | None = None,
    ) -> CapitalResult:
        if confirm_request_id:
            return self._confirm_withdrawal(confirm_request_id, operator)

        if amount <= 0:
            return CapitalResult(
                False,
                "withdraw_denied",
                "Withdrawal amount must be positive",
                self.balance(),
            )

        state = self.load_state()
        bal = self.balance()
        if amount > state["available_usd"]:
            return CapitalResult(
                False,
                "withdraw_denied",
                f"Insufficient available (${state['available_usd']:,.2f})",
                bal,
            )

        post_equity = state["equity_usd"] - amount
        if post_equity < self.config.min_operating_capital_usd:
            return CapitalResult(
                False,
                "withdraw_denied",
                (
                    f"Would breach min operating capital "
                    f"(${self.config.min_operating_capital_usd:,.2f})"
                ),
                bal,
            )

        pct = self._withdrawal_pct(amount, state["equity_usd"])
        needs_confirm = pct > self.config.max_single_withdrawal_pct

        if needs_confirm:
            request_id = f"wd-{uuid.uuid4().hex[:8]}"
            pending = PendingWithdrawal(
                request_id=request_id,
                amount_usd=amount,
                asset=asset.upper(),
                address=address,
                status="pending_confirmation",
                operator=operator,
                created_at=time.time(),
                needs_confirm=True,
            )
            state.setdefault("pending_withdrawals", []).append(pending.to_dict())
            state["reserved_usd"] = round(state["reserved_usd"] + amount, 2)
            state["available_usd"] = round(state["available_usd"] - amount, 2)
            self.save_state(state)
            self._log_audit(
                "capital_withdraw_pending",
                operator,
                {
                    "request_id": request_id,
                    "amount_usd": amount,
                    "asset": asset.upper(),
                    "address": address,
                    "pct_equity": pct,
                },
            )
            return CapitalResult(
                True,
                "withdraw_pending_confirm",
                (
                    f"Withdrawal ${amount:,.2f} {asset.upper()} ({pct:.1f}% of equity) "
                    f"requires confirmation. Reply: /withdraw confirm {request_id}"
                ),
                self.balance(),
                needs_confirm=True,
                request_id=request_id,
            )

        return self._execute_withdrawal(
            state, amount, asset.upper(), address, operator
        )

    def _confirm_withdrawal(
        self, request_id: str, operator: str
    ) -> CapitalResult:
        state = self.load_state()
        pending_list = state.get("pending_withdrawals", [])
        match = next(
            (p for p in pending_list if p["request_id"] == request_id), None
        )
        if not match:
            return CapitalResult(
                False,
                "withdraw_denied",
                f"Unknown withdrawal request: {request_id}",
                self.balance(),
            )
        if match.get("status") != "pending_confirmation":
            return CapitalResult(
                False,
                "withdraw_denied",
                f"Request {request_id} is not pending confirmation",
                self.balance(),
            )
        amount = float(match["amount_usd"])
        asset = str(match["asset"])
        address = match.get("address")
        state["reserved_usd"] = round(state["reserved_usd"] - amount, 2)
        match["status"] = "confirmed"
        result = self._execute_withdrawal(
            state, amount, asset, address, operator, request_id=request_id
        )
        for p in pending_list:
            if p["request_id"] == request_id:
                p["status"] = "executed" if result.ok else "failed"
        state["pending_withdrawals"] = pending_list
        self.save_state(state)
        return result

    def _execute_withdrawal(
        self,
        state: dict[str, Any],
        amount: float,
        asset: str,
        address: str | None,
        operator: str,
        request_id: str | None = None,
    ) -> CapitalResult:
        exec_result = self.adapter.execute_withdrawal(
            amount, asset, address, operator
        )
        state["equity_usd"] = round(state["equity_usd"] - amount, 2)
        if request_id is None:
            state["available_usd"] = round(state["available_usd"] - amount, 2)
        assets = state.setdefault("assets", {})
        assets[asset] = round(max(0.0, assets.get(asset, 0.0) - amount), 2)
        self.save_state(state)
        self._log_audit(
            "capital_withdraw_execute",
            operator,
            {
                "request_id": request_id,
                "amount_usd": amount,
                "asset": asset,
                "address": address,
                "adapter": self.adapter.name,
                "execution": exec_result,
                "equity_after": state["equity_usd"],
            },
        )
        self._sync_tax_ledger(
            {
                "action": "withdraw",
                "amount": amount,
                "amount_usd": amount,
                "asset": asset,
                "request_id": request_id,
            }
        )
        return CapitalResult(
            True,
            "withdraw_executed",
            (
                f"Withdrew ${amount:,.2f} {asset} — equity now "
                f"${state['equity_usd']:,.2f} (adapter: {self.adapter.name})"
            ),
            self.balance(),
            request_id=request_id,
            tx_hash=exec_result.get("tx_hash"),
        )

    def sweep(
        self,
        *,
        weekly_profit_usd: float | None = None,
        operator: str = "operator",
    ) -> CapitalResult:
        state = self.load_state()
        threshold = self.config.trezor_sweep.harvest_threshold_usd
        equity = state["equity_usd"]

        if equity < threshold:
            return CapitalResult(
                False,
                "sweep_skipped_growth",
                (
                    f"Growth phase — portfolio ${equity:,.2f} below "
                    f"${threshold:,.0f} harvest threshold. No sweep."
                ),
                self.balance(),
            )

        profit = (
            weekly_profit_usd
            if weekly_profit_usd is not None
            else float(state.get("weekly_profit_usd", 0.0))
        )
        if profit <= 0:
            return CapitalResult(
                False,
                "sweep_skipped_loss_week",
                "No sweep — weekly net profit is zero or negative.",
                self.balance(),
            )

        sweep_amount = round(
            profit * (self.config.trezor_sweep.sweep_pct_of_weekly_profit / 100.0),
            2,
        )
        if sweep_amount <= 0:
            return CapitalResult(
                False,
                "sweep_skipped",
                "Computed sweep amount is zero.",
                self.balance(),
            )

        if sweep_amount > state["available_usd"]:
            return CapitalResult(
                False,
                "sweep_denied",
                (
                    f"Sweep ${sweep_amount:,.2f} exceeds available "
                    f"${state['available_usd']:,.2f}"
                ),
                self.balance(),
            )

        post_equity = state["equity_usd"] - sweep_amount
        if post_equity < self.config.min_operating_capital_usd:
            return CapitalResult(
                False,
                "sweep_denied",
                "Sweep would breach min operating capital reserve.",
                self.balance(),
            )

        exec_result = self.adapter.execute_withdrawal(
            sweep_amount,
            "USDC",
            "trezor:safe7-cold",
            operator,
        )
        state["equity_usd"] = round(state["equity_usd"] - sweep_amount, 2)
        state["available_usd"] = round(state["available_usd"] - sweep_amount, 2)
        state["last_sweep_at"] = time.time()
        self.save_state(state)
        self._log_audit(
            "capital_sweep",
            operator,
            {
                "sweep_amount_usd": sweep_amount,
                "weekly_profit_usd": profit,
                "pct": self.config.trezor_sweep.sweep_pct_of_weekly_profit,
                "execution": exec_result,
                "equity_after": state["equity_usd"],
            },
        )
        return CapitalResult(
            True,
            "sweep_executed",
            (
                f"Swept ${sweep_amount:,.2f} ({self.config.trezor_sweep.sweep_pct_of_weekly_profit:.0f}% "
                f"of ${profit:,.2f} weekly profit) to Trezor Safe 7"
            ),
            self.balance(),
            tx_hash=exec_result.get("tx_hash"),
        )

    def verify_audit(self) -> tuple[bool, str]:
        return self._audit.verify()
