#!/usr/bin/env python3
"""HERALD institutional Telegram notification formatter.

Renders JSON-first + Markdown Telegram messages per §TGCMD.2 / §TGCMD.3.
Templates live in ~/.openclaw/workspace/telegram/ (deployed from templates/telegram/).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
MATERIAL_THRESHOLD_PCT = 0.5
IMMEDIATE_SEVERITIES = frozenset({"CRITICAL", "HIGH"})

DEFAULT_TELEGRAM_DIR = Path(
    os.environ.get(
        "TITAN_TELEGRAM_DIR",
        Path.home() / ".openclaw" / "workspace" / "telegram",
    )
)


def _telegram_root() -> Path:
    return Path(os.environ.get("TITAN_TELEGRAM_DIR", DEFAULT_TELEGRAM_DIR))


def _load_template(name: str) -> str:
    path = _telegram_root() / "templates" / name
    if not path.exists():
        alt = Path(__file__).resolve().parent.parent / "telegram" / "templates" / name
        path = alt if alt.exists() else path
    return path.read_text(encoding="utf-8")


def _render_template(name: str, **ctx: Any) -> str:
    text = _strip_template_comments(_load_template(name))
    for key, val in ctx.items():
        text = text.replace("{" + key + "}", str(val))
    return text.strip()


def _strip_template_comments(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
    return "\n".join(lines).strip()


def _fmt_sign(value: float | int | None) -> str:
    if value is None:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    return "+" if v >= 0 else ""


def _fmt_usd(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):,.{decimals}f}"


def _fmt_pct(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):.{decimals}f}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_block(payload: dict[str, Any]) -> str:
    """Compact JSON block for Telegram (monospace)."""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return f"```json\n{body}\n```"


def is_material(payload: dict[str, Any]) -> bool:
    severity = payload.get("severity", "INFO")
    if severity in IMMEDIATE_SEVERITIES:
        return True
    pnl = payload.get("pnl") or {}
    pct = abs(float(pnl.get("pct_equity") or 0))
    return pct >= MATERIAL_THRESHOLD_PCT


def should_send_immediate(payload: dict[str, Any]) -> bool:
    """Immediate alert when material trade or CRITICAL severity."""
    if payload.get("material") is True:
        return True
    return is_material(payload)


@dataclass
class RenderedMessage:
    payload: dict[str, Any]
    telegram_text: str
    immediate: bool
    parse_mode: str = "Markdown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "payload": self.payload,
            "telegram_text": self.telegram_text,
            "immediate": self.immediate,
            "parse_mode": self.parse_mode,
        }


def _portfolio_footer(portfolio: dict[str, Any] | None) -> str:
    if not portfolio:
        return ""
    daily_sign = _fmt_sign(portfolio.get("daily_pnl_usd"))
    unreal_sign = _fmt_sign(portfolio.get("unrealized_pnl_usd"))
    return _render_template(
        "portfolio_footer.md",
        equity_usd=_fmt_usd(portfolio.get("equity_usd")),
        daily_sign=daily_sign,
        daily_pnl_usd=_fmt_usd(abs(portfolio.get("daily_pnl_usd") or 0)),
        daily_pnl_pct=_fmt_pct(portfolio.get("daily_pnl_pct")),
        exposure_pct=_fmt_pct(portfolio.get("exposure_pct")),
        open_positions=str(portfolio.get("open_positions", 0)),
        unreal_sign=unreal_sign,
        unrealized_pnl_usd=_fmt_usd(abs(portfolio.get("unrealized_pnl_usd") or 0)),
    )


def _normalize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw)
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("timestamp", _now_iso())
    payload.setdefault("reason_codes", [])
    if not payload["reason_codes"]:
        raise ValueError("reason_codes required (min 1)")
    material = is_material(payload)
    payload["material"] = payload.get("material", material)
    return payload


def _outcome_icon(outcome: str | None, event_type: str | None = None) -> str:
    if outcome == "WIN":
        return "✅"
    if outcome == "LOSS":
        return "❌"
    if event_type in ("trade_entry", "trade_execution", "trade_exit"):
        return "⚡"
    if event_type == "hourly_digest":
        return "📊"
    return "⚡"


def render_trade_execution(raw: dict[str, Any]) -> RenderedMessage:
    payload = _normalize_payload(raw)
    payload.setdefault("event_type", "trade_execution")
    trade = payload.setdefault("trade", {})
    risk = payload.get("risk") or {}
    strategy = payload.get("strategy") or {}

    action = trade.get("action", "entry")
    direction = trade.get("direction", "LONG")
    price = trade.get("fill_price") or trade.get("entry_price") or trade.get("exit_price") or 0
    icon = _outcome_icon((payload.get("pnl") or {}).get("outcome"), payload["event_type"])
    headline = f"TRADE {action.upper()} — {payload.get('pipeline_id', 'P?')}"

    tx_line = ""
    if trade.get("tx_hash"):
        tx_line = f"Tx: `{trade['tx_hash'][:16]}…` block `{trade.get('block', '—')}`"

    risk_line = ""
    if risk.get("stop_loss_pct") or risk.get("stop_loss_price"):
        risk_line = (
            f"Stop: `{_fmt_pct(risk.get('stop_loss_pct'))}%` "
            f"@ `{risk.get('stop_loss_price', '—')}` | "
            f"DD 24h: `{_fmt_pct(risk.get('drawdown_24h_pct'))}%`"
        )

    pf = ""
    if payload.get("material") and payload.get("portfolio"):
        pf = _portfolio_footer(payload["portfolio"])

    ctx = {
        "json_block": json_block(payload),
        "icon": icon,
        "headline": headline,
        "action_label": action.upper(),
        "direction": direction,
        "size": trade.get("size", "—"),
        "asset": trade.get("asset", "—"),
        "price": _fmt_usd(price, 4) if price else "—",
        "chain": trade.get("chain", "—"),
        "venue": trade.get("venue", "—"),
        "pipeline_id": payload.get("pipeline_id", "—"),
        "agent_id": payload.get("agent_id", "HERALD"),
        "confidence_pct": _fmt_pct((trade.get("confidence") or 0) * 100 if (trade.get("confidence") or 0) <= 1 else trade.get("confidence")),
        "position_pct": _fmt_pct(risk.get("position_pct_equity")),
        "reason_summary": strategy.get("signal_summary") or payload.get("notes") or ", ".join(payload["reason_codes"]),
        "reason_codes_inline": ", ".join(payload["reason_codes"]),
        "tx_line": tx_line,
        "risk_line": risk_line,
        "portfolio_footer": pf,
    }

    text = _render_template("trade_execution.md", **ctx)
    return RenderedMessage(payload, text, should_send_immediate(payload))


def render_pnl_close(raw: dict[str, Any]) -> RenderedMessage:
    payload = _normalize_payload(raw)
    payload.setdefault("event_type", "pnl_realized")
    trade = payload.setdefault("trade", {})
    pnl = payload.setdefault("pnl", {})
    strategy = payload.get("strategy") or {}

    outcome = pnl.get("outcome", "BREAKEVEN")
    icon = _outcome_icon(outcome)
    net = pnl.get("net_usd") or pnl.get("realized_usd") or 0
    pct_eq = pnl.get("pct_equity") or pnl.get("realized_pct") or 0
    headline = f"{'PROFIT' if outcome == 'WIN' else 'LOSS' if outcome == 'LOSS' else 'PNL'} — {payload.get('pipeline_id', 'P?')}"

    pf = ""
    if payload.get("material") and payload.get("portfolio"):
        pf = _portfolio_footer(payload["portfolio"])

    ctx = {
        "json_block": json_block(payload),
        "icon": icon,
        "headline": headline,
        "pipeline_id": payload.get("pipeline_id", "—"),
        "workflow_name": strategy.get("workflow_name") or payload.get("workflow_name") or "—",
        "direction": trade.get("direction", "—"),
        "asset": trade.get("asset", "—"),
        "chain": trade.get("chain", "—"),
        "entry_price": _fmt_usd(trade.get("entry_price") or trade.get("fill_price"), 4),
        "exit_price": _fmt_usd(trade.get("exit_price"), 4),
        "sign": _fmt_sign(net),
        "net_usd": _fmt_usd(abs(net) if net else 0),
        "pct_equity": _fmt_pct(abs(pct_eq)),
        "fees_usd": _fmt_usd(pnl.get("fees_usd") or trade.get("fees_usd")),
        "slippage_bps": _fmt_pct(trade.get("slippage_bps") or 0),
        "reason_summary": strategy.get("signal_summary") or payload.get("notes") or ", ".join(payload["reason_codes"]),
        "reason_codes_inline": ", ".join(payload["reason_codes"]),
        "agent_id": payload.get("agent_id", "HERALD"),
        "timestamp": payload.get("timestamp", _now_iso()),
        "portfolio_footer": pf,
    }

    text = _render_template("pnl_close.md", **ctx)
    return RenderedMessage(payload, text, should_send_immediate(payload))


def render_material_alert(raw: dict[str, Any]) -> RenderedMessage:
    payload = _normalize_payload(raw)
    payload["material"] = True
    payload.setdefault("event_type", "material_alert")
    payload.setdefault("severity", "MATERIAL")
    trade = payload.get("trade") or {}
    pnl = payload.get("pnl") or {}
    risk = payload.get("risk") or {}

    net = pnl.get("net_usd") or pnl.get("realized_usd") or 0
    pct_eq = pnl.get("pct_equity") or 0
    direction = trade.get("direction", "")
    asset = trade.get("asset", "")
    size = trade.get("size", "")

    trade_summary = f"`{direction}` `{size}` `{asset}` on `{trade.get('chain', '—')}`"
    risk_block = ""
    if risk:
        parts = []
        if risk.get("cb_triggered"):
            parts.append(f"CB: `{risk['cb_triggered']}`")
        if risk.get("drawdown_tier"):
            parts.append(f"DD tier: `{risk['drawdown_tier']}`")
        if parts:
            risk_block = "Risk: " + " | ".join(parts)

    pf = _portfolio_footer(payload.get("portfolio") or {})

    ctx = {
        "json_block": json_block(payload),
        "severity": payload.get("severity", "MATERIAL"),
        "pipeline_id": payload.get("pipeline_id", "—"),
        "agent_id": payload.get("agent_id", "HERALD"),
        "timestamp": payload.get("timestamp", _now_iso()),
        "trade_summary": trade_summary,
        "sign": _fmt_sign(net if net else pct_eq),
        "pnl_pct_equity": _fmt_pct(abs(pct_eq)),
        "net_usd": _fmt_usd(abs(net)),
        "reason_summary": payload.get("notes") or ", ".join(payload["reason_codes"]),
        "reason_codes_inline": ", ".join(payload["reason_codes"]),
        "risk_block": risk_block,
        "portfolio_footer": pf,
    }

    text = _render_template("material_alert.md", **ctx)
    return RenderedMessage(payload, text, True)


def render_hourly_digest(raw: dict[str, Any]) -> RenderedMessage:
    payload = _normalize_payload(raw)
    payload.setdefault("event_type", "hourly_digest")
    payload.setdefault("severity", "INFO")
    digest = payload.setdefault("digest", {})
    portfolio = payload.get("portfolio") or {}

    wins = digest.get("wins", 0)
    losses = digest.get("losses", 0)
    total = wins + losses
    win_rate = (100.0 * wins / total) if total else 0.0

    strategy_blocks = ""
    for s in digest.get("strategies") or []:
        sign = _fmt_sign(s.get("pnl_usd"))
        strategy_blocks += (
            f"\n*{s.get('pipeline_id', 'P?')}* — "
            f"{s.get('trades', 0)} trades | "
            f"{sign}${_fmt_usd(s.get('pnl_usd'))}\n"
        )
    if not strategy_blocks:
        strategy_blocks = "\n_No strategy activity this hour._\n"

    health = digest.get("health") or {}
    health_block = ""
    if health:
        health_block = (
            f"\n⚙️ *SYSTEM*\n"
            f"Latency p50: {health.get('latency_p50_ms', '—')}ms | "
            f"CPU: {health.get('cpu_pct', '—')}% | "
            f"GPU: {health.get('gpu_pct', '—')}%\n"
        )

    flags = digest.get("flags") or []
    flags_block = ""
    if flags:
        flags_block = "\n🚩 *FLAGS*\n" + "\n".join(f"• {f}" for f in flags)
    else:
        flags_block = "\n🚩 *FLAGS*\n✅ No anomalies."

    hour_pnl = digest.get("hour_pnl_usd", 0)
    ctx = {
        "json_block": json_block(payload),
        "window_start": digest.get("window_start", "—"),
        "window_end": digest.get("window_end", "—"),
        "sign": _fmt_sign(hour_pnl),
        "hour_pnl_usd": _fmt_usd(abs(hour_pnl)),
        "hour_pnl_pct": _fmt_pct(digest.get("hour_pnl_pct")),
        "sign_daily": _fmt_sign(portfolio.get("daily_pnl_usd")),
        "daily_pnl_usd": _fmt_usd(abs(portfolio.get("daily_pnl_usd") or 0)),
        "daily_pnl_pct": _fmt_pct(portfolio.get("daily_pnl_pct")),
        "trades_count": str(digest.get("trades_count", 0)),
        "wins": str(wins),
        "losses": str(losses),
        "win_rate": _fmt_pct(win_rate),
        "exposure_pct": _fmt_pct(portfolio.get("exposure_pct")),
        "open_positions": str(portfolio.get("open_positions", 0)),
        "sign_unreal": _fmt_sign(portfolio.get("unrealized_pnl_usd")),
        "unrealized_pnl_usd": _fmt_usd(portfolio.get("unrealized_pnl_usd")),
        "gas_fees_usd": _fmt_usd(digest.get("gas_fees_usd")),
        "strategy_blocks": strategy_blocks,
        "health_block": health_block,
        "flags_block": flags_block,
    }
    # Fix daily sign in template
    ctx["sign"] = _fmt_sign(hour_pnl)
    daily_sign = _fmt_sign(portfolio.get("daily_pnl_usd"))
    unreal_sign = _fmt_sign(portfolio.get("unrealized_pnl_usd"))

    text = _render_template(
        "hourly_digest.md",
        json_block=ctx["json_block"],
        window_start=ctx["window_start"],
        window_end=ctx["window_end"],
        sign=ctx["sign"],
        hour_pnl_usd=ctx["hour_pnl_usd"],
        hour_pnl_pct=ctx["hour_pnl_pct"],
        daily_pnl_usd=f"{daily_sign}{ctx['daily_pnl_usd']}",
        daily_pnl_pct=ctx["daily_pnl_pct"],
        trades_count=ctx["trades_count"],
        wins=ctx["wins"],
        losses=ctx["losses"],
        win_rate=ctx["win_rate"],
        exposure_pct=ctx["exposure_pct"],
        open_positions=ctx["open_positions"],
        unrealized_pnl_usd=f"{unreal_sign}{ctx['unrealized_pnl_usd']}",
        gas_fees_usd=ctx["gas_fees_usd"],
        strategy_blocks=ctx["strategy_blocks"],
        health_block=ctx["health_block"],
        flags_block=ctx["flags_block"],
    )

    return RenderedMessage(payload, text, False)


def render(raw: dict[str, Any]) -> RenderedMessage:
    """Dispatch by event_type."""
    event = raw.get("event_type", "trade_execution")
    if event in ("capital_deposit", "capital_withdraw", "capital_balance", "capital_sweep"):
        return render_capital_event(raw)
    if event == "hourly_digest":
        return render_hourly_digest(raw)
    if event in ("pnl_realized", "pnl_unrealized"):
        return render_pnl_close(raw)
    if event == "material_alert" or (event != "hourly_digest" and is_material(raw)):
        if event not in ("trade_entry", "trade_exit", "trade_execution"):
            return render_material_alert(raw)
    if event in ("trade_entry", "trade_exit", "trade_execution"):
        msg = render_trade_execution(raw)
        if msg.immediate and event != "material_alert":
            # Also acceptable to send trade_execution; material uses dedicated template
            pass
        return msg
    return render_trade_execution(raw)


def render_capital_event(raw: dict[str, Any]) -> RenderedMessage:
    """Render capital deposit/withdraw/balance/sweep for Telegram."""
    payload = dict(raw)
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("timestamp", _now_iso())
    payload.setdefault("agent_id", "ATLAS")
    payload.setdefault("reason_codes", ["CAPITAL_OPERATOR"])
    payload.setdefault("severity", "INFO")
    capital = payload.setdefault("capital", {})
    state = capital.get("state") or {}

    event = payload.get("event_type", "capital_balance")
    ok = capital.get("ok", True)
    icon = "✅" if ok else "⚠️"
    action = capital.get("action", event)
    headlines = {
        "capital_deposit": "CAPITAL DEPOSIT",
        "capital_withdraw": "CAPITAL WITHDRAWAL",
        "capital_balance": "CAPITAL BALANCE",
        "capital_sweep": "TREZOR PROFIT SWEEP",
    }
    headline = headlines.get(event, f"CAPITAL — {action.upper()}")

    phase = "HARVEST" if state.get("harvest_phase") else "GROWTH"
    detail_lines = ""
    if capital.get("tx_hash"):
        detail_lines += f"Tx: `{capital['tx_hash'][:18]}…`\n"
    if capital.get("request_id"):
        detail_lines += f"Request: `{capital['request_id']}`\n"
    if capital.get("asset"):
        detail_lines += f"Asset: `{capital['asset']}`\n"

    confirm_line = ""
    if capital.get("needs_confirm") and capital.get("request_id"):
        confirm_line = (
            f"\n🔐 Large withdrawal — confirm:\n"
            f"`/withdraw confirm {capital['request_id']}`"
        )

    ctx = {
        "json_block": json_block(payload),
        "icon": icon,
        "headline": headline,
        "message": capital.get("message", ""),
        "equity_usd": _fmt_usd(state.get("equity_usd")),
        "available_usd": _fmt_usd(state.get("available_usd")),
        "reserved_usd": _fmt_usd(state.get("reserved_usd")),
        "max_withdrawable_usd": _fmt_usd(state.get("max_withdrawable_usd")),
        "min_operating_usd": _fmt_usd(state.get("min_operating_capital_usd")),
        "phase_label": phase,
        "detail_lines": detail_lines.strip(),
        "confirm_line": confirm_line,
    }
    text = _render_template("capital_event.md", **ctx)
    immediate = event in ("capital_withdraw", "capital_sweep") or capital.get("needs_confirm", False)
    return RenderedMessage(payload, text, immediate)


def render_capital(result: Any) -> RenderedMessage:
    """Build HERALD message from titan_safety CapitalResult."""
    action_map = {
        "deposit_recorded": "capital_deposit",
        "withdraw_executed": "capital_withdraw",
        "withdraw_pending_confirm": "capital_withdraw",
        "withdraw_denied": "capital_withdraw",
        "balance": "capital_balance",
        "sweep_executed": "capital_sweep",
        "sweep_skipped_growth": "capital_sweep",
        "sweep_skipped_loss_week": "capital_sweep",
        "sweep_denied": "capital_sweep",
        "sweep_skipped": "capital_sweep",
    }
    event = action_map.get(result.action, "capital_balance")
    raw = {
        "event_type": event,
        "agent_id": "ATLAS",
        "reason_codes": ["CAPITAL_OPERATOR"],
        "severity": "HIGH" if result.needs_confirm else "INFO",
        "capital": {
            "ok": result.ok,
            "action": result.action,
            "message": result.message,
            "state": result.state,
            "needs_confirm": result.needs_confirm,
            "request_id": result.request_id,
            "tx_hash": result.tx_hash,
        },
    }
    return render_capital_event(raw)


def sample_trade_payload() -> dict[str, Any]:
    """Example payload for smoke tests."""
    return {
        "schema_version": SCHEMA_VERSION,
        "event_type": "trade_execution",
        "timestamp": "2026-07-02T20:15:33Z",
        "agent_id": "TRENCH-OPS",
        "pipeline_id": "P3",
        "workflow_name": "flash_loan_arb_eth_mainnet",
        "reason_codes": ["SIGNAL_ARB_GAP", "SIGNAL_CONFLUENCE"],
        "severity": "INFO",
        "trade": {
            "trade_id": "tx-20260702-00142",
            "direction": "LONG",
            "action": "entry",
            "asset": "WETH/USDC",
            "size": 1.25,
            "size_unit": "ETH",
            "notional_usd": 4825.50,
            "chain": "ethereum",
            "venue": "uniswap_v3",
            "fill_price": 3860.40,
            "tx_hash": "0xabc123def4567890abcdef1234567890abcdef12",
            "block": 21234567,
            "confidence": 0.82,
            "slippage_bps": 4.2,
            "fees_usd": 3.15,
            "gas_usd": 12.40,
        },
        "strategy": {
            "pipeline_id": "P3",
            "workflow_name": "flash_loan_arb_eth_mainnet",
            "signals": ["ORACLE.price_divergence", "QUANT.spread_zscore"],
            "signal_summary": "ETH/ARB 18bps gap; QUANT z=2.4; ORACLE confirms",
        },
        "risk": {
            "position_pct_equity": 1.85,
            "stop_loss_pct": 1.1,
            "stop_loss_price": 3817.93,
            "drawdown_24h_pct": 0.4,
        },
        "pnl": {
            "outcome": "OPEN",
            "pct_equity": 0.0,
        },
        "portfolio": {
            "equity_usd": 261042.18,
            "exposure_pct": 12.4,
            "open_positions": 7,
            "daily_pnl_usd": 842.33,
            "daily_pnl_pct": 0.32,
            "unrealized_pnl_usd": 156.20,
        },
        "notes": "Cross-DEX arb entry; GUARDIAN sized at 1.85% equity",
    }


if __name__ == "__main__":
    import sys

    demo = sample_trade_payload()
    if len(sys.argv) > 1 and sys.argv[1] == "digest":
        demo = {
            "event_type": "hourly_digest",
            "timestamp": "2026-07-02T20:00:00Z",
            "agent_id": "HERALD",
            "pipeline_id": "P3",
            "reason_codes": ["SIGNAL_CONFLUENCE"],
            "severity": "INFO",
            "digest": {
                "window_start": "2026-07-02T19:00",
                "window_end": "2026-07-02T20:00",
                "hour_pnl_usd": 127.45,
                "hour_pnl_pct": 0.05,
                "trades_count": 4,
                "wins": 3,
                "losses": 1,
                "gas_fees_usd": 28.50,
                "strategies": [
                    {"pipeline_id": "P3", "trades": 2, "pnl_usd": 98.20},
                    {"pipeline_id": "P30", "trades": 2, "pnl_usd": 29.25},
                ],
                "health": {"latency_p50_ms": 42, "cpu_pct": 38, "gpu_pct": 52},
                "flags": [],
            },
            "portfolio": {
                "equity_usd": 261042.18,
                "exposure_pct": 12.4,
                "open_positions": 7,
                "daily_pnl_usd": 842.33,
                "daily_pnl_pct": 0.32,
                "unrealized_pnl_usd": 156.20,
            },
        }
    elif len(sys.argv) > 1 and sys.argv[1] == "capital":
        from types import SimpleNamespace

        demo_result = SimpleNamespace(
            ok=True,
            action="deposit_recorded",
            message="Deposited $2,500.00 USDC — equity now $2,500.00",
            state={
                "equity_usd": 2500.0,
                "available_usd": 2500.0,
                "reserved_usd": 0.0,
                "max_withdrawable_usd": 2000.0,
                "min_operating_capital_usd": 500.0,
                "harvest_phase": False,
            },
            needs_confirm=False,
            request_id=None,
            tx_hash="0xabc123def4567890abcdef",
        )
        msg = render_capital(demo_result)
        print(msg.telegram_text)
        print("\n--- immediate:", msg.immediate, "---")
        raise SystemExit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "pnl":
        demo = sample_trade_payload()
        demo.update({
            "event_type": "pnl_realized",
            "severity": "MATERIAL",
            "trade": {
                **demo["trade"],
                "action": "exit",
                "exit_price": 3891.22,
            },
            "pnl": {
                "outcome": "WIN",
                "realized_usd": 142.88,
                "net_usd": 142.88,
                "pct_equity": 0.55,
                "fees_usd": 5.55,
                "slippage_usd": 2.10,
            },
        })

    msg = render(demo)
    print(msg.telegram_text)
    print("\n--- immediate:", msg.immediate, "---")
