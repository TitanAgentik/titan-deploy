"""Telegram capital commands — simple operator UX for HERALD."""

from __future__ import annotations

from typing import Any

from .capital import CapitalManager, CapitalResult, load_capital_config


def _parse_amount_asset(tokens: list[str]) -> tuple[float, str, list[str]]:
    if len(tokens) < 2:
        raise ValueError("usage: <amount> <asset> [address|chain ...]")
    amount = float(tokens[0].replace(",", "").replace("$", ""))
    asset = tokens[1].upper()
    return amount, asset, tokens[2:]


def parse_capital_command(text: str) -> tuple[str, dict[str, Any]]:
    """Parse /deposit, /withdraw, /balance, /sweep, /capital subcommands."""
    raw = (text or "").strip()
    if not raw.startswith("/"):
        raise ValueError("not a command")

    body = raw.split(maxsplit=1)
    cmd = body[0].lower().split("@")[0]
    args = body[1].strip() if len(body) > 1 else ""

    if cmd in ("/balance", "/capital"):
        if not args or args.lower() in ("balance", "status"):
            return "balance", {}
        sub = args.split()
        subcmd = sub[0].lower()
        rest = sub[1:]
        if subcmd == "deposit":
            amount, asset, extra = _parse_amount_asset(rest)
            return "deposit", _deposit_kwargs(amount, asset, extra)
        if subcmd == "withdraw":
            return "withdraw", _withdraw_kwargs(rest)
        if subcmd == "balance":
            return "balance", {}
        if subcmd == "sweep":
            return "sweep", {}
        raise ValueError(f"unknown /capital subcommand: {subcmd}")

    if cmd == "/deposit":
        amount, asset, extra = _parse_amount_asset(args.split())
        return "deposit", _deposit_kwargs(amount, asset, extra)

    if cmd == "/withdraw":
        return "withdraw", _withdraw_kwargs(args.split())

    if cmd == "/sweep":
        return "sweep", {}

    raise ValueError(f"unknown capital command: {cmd}")


def _deposit_kwargs(
    amount: float, asset: str, extra: list[str]
) -> dict[str, Any]:
    kw: dict[str, Any] = {"amount": amount, "asset": asset}
    if not extra:
        return kw
    if extra[0].lower() in ("ethereum", "arbitrum", "base", "solana", "polygon"):
        kw["chain"] = extra[0].lower()
        if len(extra) > 1 and extra[1].startswith("0x"):
            kw["tx_hash"] = extra[1]
            if len(extra) > 2:
                kw["source"] = " ".join(extra[2:])
    elif extra[0].startswith("0x"):
        kw["tx_hash"] = extra[0]
        if len(extra) > 1:
            kw["source"] = " ".join(extra[1:])
    else:
        kw["source"] = " ".join(extra)
    return kw


def _withdraw_kwargs(tokens: list[str]) -> dict[str, Any]:
    if not tokens:
        raise ValueError("usage: /withdraw <amount> <asset> [address]")
    if tokens[0].lower() == "confirm":
        if len(tokens) < 2:
            raise ValueError("usage: /withdraw confirm <request_id>")
        return {"confirm_request_id": tokens[1]}
    amount, asset, extra = _parse_amount_asset(tokens)
    kw: dict[str, Any] = {"amount": amount, "asset": asset}
    if extra:
        kw["address"] = extra[0]
    return kw


def handle_capital_command(
    text: str,
    operator: str = "operator",
    manager: CapitalManager | None = None,
) -> CapitalResult:
    action, kwargs = parse_capital_command(text)
    mgr = manager or CapitalManager(load_capital_config())
    kwargs["operator"] = operator

    if action == "balance":
        bal = mgr.balance()
        phase = (
            "HARVEST"
            if bal["harvest_phase"]
            else f"GROWTH (<${mgr.config.trezor_sweep.harvest_threshold_usd:,.0f})"
        )
        return CapitalResult(
            True,
            "balance",
            (
                f"Equity ${bal['equity_usd']:,.2f} | Available ${bal['available_usd']:,.2f} | "
                f"Reserved ${bal['reserved_usd']:,.2f} | Phase: {phase}"
            ),
            bal,
        )
    if action == "deposit":
        return mgr.deposit(**kwargs)
    if action == "withdraw":
        return mgr.withdraw(**kwargs)
    if action == "sweep":
        return mgr.sweep(**kwargs)
    raise ValueError(f"unhandled action: {action}")


def format_telegram_response(result: CapitalResult) -> str:
    """Institutional Markdown for Telegram (HERALD style)."""
    try:
        from notify import render_capital  # type: ignore[import-not-found]

        return render_capital(result).telegram_text
    except ImportError:
        return _fallback_format(result)


def _fallback_format(result: CapitalResult) -> str:
    icon = "✅" if result.ok else "⚠️"
    lines = [
        f"{icon} *CAPITAL — {result.action.upper().replace('_', ' ')}*",
        "",
        result.message,
        "",
        f"Equity: `${result.state.get('equity_usd', 0):,.2f}` | "
        f"Available: `${result.state.get('available_usd', 0):,.2f}` | "
        f"Reserved: `${result.state.get('reserved_usd', 0):,.2f}`",
    ]
    if result.request_id:
        lines.append(f"Request: `{result.request_id}`")
    if result.tx_hash:
        lines.append(f"Tx: `{result.tx_hash[:18]}…`")
    if result.needs_confirm:
        lines.append(
            f"\nConfirm: `/withdraw confirm {result.request_id}`"
        )
    return "\n".join(lines)
