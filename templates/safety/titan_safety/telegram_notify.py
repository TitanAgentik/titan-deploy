"""Institutional Telegram notifications — HERALD operator surface (notify-only).

All operational events are formatted consistently and delivered via Telegram.
Never blocks trading, signing, or the risk kernel. Secrets via environment only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"
HERALD_QUEUE = "herald_queue.jsonl"

SEVERITIES = frozenset({"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"})
MARKDOWN_ESCAPE_CHARS = "_*[]()`"


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = True
    dry_run: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


@dataclass
class NotifyEvent:
    """Institutional notification payload."""

    name: str
    event_type: str
    severity: str
    agent_id: str
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    action_required: str = ""
    reason_codes: list[str] = field(default_factory=list)
    pnl: dict[str, Any] | None = None
    portfolio: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()
        if self.severity not in SEVERITIES:
            self.severity = "INFO"
        if not self.reason_codes:
            self.reason_codes = [self.event_type.upper().replace(" ", "_")]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


HttpPostFn = Callable[[str, bytes, dict[str, str], float], tuple[int, bytes]]


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_config() -> TelegramConfig:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        or os.environ.get("TELEGRAM_USER_ID", "").strip()
    )
    enabled = os.environ.get("TITAN_TELEGRAM_ENABLED", "1").strip() not in (
        "0",
        "false",
        "False",
        "no",
    )
    dry_run = os.environ.get("TITAN_TELEGRAM_DRY_RUN", "").strip() in (
        "1",
        "true",
        "True",
        "yes",
    )
    return TelegramConfig(
        bot_token=token,
        chat_id=chat_id,
        enabled=enabled,
        dry_run=dry_run,
    )


def escape_markdown(text: str) -> str:
    """Escape Telegram Markdown special characters in user-controlled text."""
    out: list[str] = []
    for ch in str(text):
        if ch in MARKDOWN_ESCAPE_CHARS:
            out.append(f"\\{ch}")
        else:
            out.append(ch)
    return "".join(out)


def _format_details(details: dict[str, Any]) -> str:
    if not details:
        return "_None_"
    lines: list[str] = []
    for key in sorted(details.keys()):
        val = details[key]
        if isinstance(val, (dict, list)):
            val_str = json.dumps(val, separators=(",", ":"), ensure_ascii=False)
        else:
            val_str = str(val)
        lines.append(f"• *{escape_markdown(key)}:* `{escape_markdown(val_str)}`")
    return "\n".join(lines)


def _fmt_sign(value: float | int | None) -> str:
    if value is None:
        return ""
    try:
        return "+" if float(value) >= 0 else ""
    except (TypeError, ValueError):
        return ""


def _fmt_usd(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):,.{decimals}f}"


def _fmt_signed_usd(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "$0.00"
    v = float(value)
    sign = "+" if v >= 0 else "-"
    return f"{sign}${_fmt_usd(abs(v), decimals)}"


def _fmt_signed_pct(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "0.00"
    v = float(value)
    sign = "+" if v >= 0 else "-"
    return f"{sign}{_fmt_pct(abs(v), decimals)}"


def _fmt_pct(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):.{decimals}f}"


def _format_financial_summary(
    pnl: dict[str, Any] | None,
    portfolio: dict[str, Any] | None,
) -> str:
    """Render Financial Summary block when PnL or portfolio data is present."""
    if not pnl and not portfolio:
        return ""

    lines: list[str] = ["\n*Financial Summary*"]

    if pnl:
        realized = pnl.get("realized_usd")
        if realized is not None:
            pct_eq = pnl.get("pct_equity")
            line = f"Realized: {_fmt_signed_usd(realized)}"
            if pct_eq is not None:
                line += f" ({_fmt_signed_pct(pct_eq)}% equity)"
            lines.append(line)

        unrealized = pnl.get("unrealized_usd")
        if unrealized is not None:
            lines.append(f"Unrealized: {_fmt_signed_usd(unrealized)}")

        net = pnl.get("net_usd")
        if net is not None and net != realized:
            pct_eq = pnl.get("pct_equity")
            line = f"Net P&L: {_fmt_signed_usd(net)}"
            if pct_eq is not None:
                line += f" ({_fmt_signed_pct(pct_eq)}% equity)"
            lines.append(line)

        daily = pnl.get("daily_pnl_usd")
        if daily is not None:
            daily_pct = pnl.get("daily_pnl_pct")
            line = f"Daily P&L: {_fmt_signed_usd(daily)}"
            if daily_pct is not None:
                line += f" ({_fmt_signed_pct(daily_pct)}%)"
            lines.append(line)

        fees = pnl.get("fees_usd")
        if fees is not None:
            lines.append(f"Fees: ${_fmt_usd(fees)}")

        outcome = pnl.get("outcome")
        if outcome:
            lines.append(f"Outcome: `{escape_markdown(str(outcome))}`")

    if portfolio:
        parts: list[str] = []
        equity = portfolio.get("equity_usd")
        if equity is not None:
            parts.append(f"Equity: ${_fmt_usd(equity)}")
        available = portfolio.get("available_usd")
        if available is not None:
            parts.append(f"Available: ${_fmt_usd(available)}")
        exposure = portfolio.get("exposure_pct")
        if exposure is not None:
            parts.append(f"Exposure: {_fmt_pct(exposure)}%")
        open_pos = portfolio.get("open_positions")
        if open_pos is not None:
            parts.append(f"Open: {open_pos}")
        if parts:
            lines.append(" | ".join(parts))

        port_daily = portfolio.get("daily_pnl_usd")
        if port_daily is not None and not (pnl and pnl.get("daily_pnl_usd") is not None):
            port_daily_pct = portfolio.get("daily_pnl_pct")
            line = f"Daily P&L: {_fmt_signed_usd(port_daily)}"
            if port_daily_pct is not None:
                line += f" ({_fmt_signed_pct(port_daily_pct)}%)"
            lines.append(line)

    return "\n".join(lines)


def format_institutional_message(event: NotifyEvent) -> str:
    """Render institutional-grade Telegram Markdown (no emoji)."""
    action = event.action_required.strip() or "None — informational only."
    codes = ", ".join(event.reason_codes)
    financial = _format_financial_summary(event.pnl, event.portfolio)
    return (
        f"*TITAN — {escape_markdown(event.name)}*\n"
        f"Severity: `{event.severity}`\n"
        f"Time: `{event.timestamp}`\n"
        f"Agent: `{escape_markdown(event.agent_id)}`\n"
        f"Event: `{escape_markdown(event.event_type)}`\n"
        f"\n*Description*\n{escape_markdown(event.description)}\n"
        f"{financial}"
        f"\n*Details*\n{_format_details(event.details)}\n"
        f"\n*Action Required*\n{escape_markdown(action)}\n"
        f"\nReason codes: `{escape_markdown(codes)}`"
    )


def _default_http_post(
    url: str, data: bytes, headers: dict[str, str], timeout: float
) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def send_telegram_message(
    text: str,
    *,
    config: TelegramConfig | None = None,
    parse_mode: str = "Markdown",
    timeout: float = 10.0,
    http_post: HttpPostFn | None = None,
) -> dict[str, Any]:
    """POST to Telegram Bot API. Returns result dict; never raises on API errors."""
    cfg = config or load_config()
    if not cfg.enabled:
        return {"ok": False, "skipped": True, "reason": "telegram disabled"}
    if cfg.dry_run:
        return {"ok": True, "dry_run": True, "text": text}
    if not cfg.configured:
        return {"ok": False, "skipped": True, "reason": "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"}

    post = http_post or _default_http_post
    url = f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": cfg.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        status, body = post(url, payload, headers, timeout)
        parsed: dict[str, Any] = {}
        if body:
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                parsed = {"raw": body.decode("utf-8", errors="replace")}
        ok = 200 <= status < 300 and parsed.get("ok", status < 300)
        return {
            "ok": ok,
            "status": status,
            "response": parsed,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def enqueue_herald_event(safety_dir: Path, record: dict[str, Any]) -> None:
    safety_dir.mkdir(parents=True, exist_ok=True)
    path = safety_dir / HERALD_QUEUE
    line = json.dumps({**record, "timestamp": record.get("timestamp", _now_iso())})
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify(
    event: NotifyEvent | dict[str, Any],
    *,
    safety_dir: Path | None = None,
    send: bool | None = None,
    enqueue: bool = True,
    config: TelegramConfig | None = None,
    http_post: HttpPostFn | None = None,
) -> dict[str, Any]:
    """Format, optionally enqueue, and optionally send an institutional notification."""
    if isinstance(event, dict):
        ev = NotifyEvent(**{k: v for k, v in event.items() if k in NotifyEvent.__dataclass_fields__})
    else:
        ev = event

    text = format_institutional_message(ev)
    sd = safety_dir or DEFAULT_SAFETY_DIR
    queue_record = {
        "level": ev.severity,
        "event": ev.event_type,
        "event_type": ev.event_type,
        "source": ev.agent_id,
        "name": ev.name,
        "description": ev.description,
        "details": ev.details,
        "action_required": ev.action_required,
        "reason_codes": ev.reason_codes,
        "pnl": ev.pnl,
        "portfolio": ev.portfolio,
        "telegram_text": text,
        "immediate": ev.severity in ("HIGH", "CRITICAL"),
        "ts": time.time(),
    }
    if enqueue:
        enqueue_herald_event(sd, queue_record)

    cfg = config or load_config()
    should_send = send if send is not None else cfg.enabled
    send_result: dict[str, Any] | None = None
    if should_send:
        send_result = send_telegram_message(text, config=cfg, http_post=http_post)

    return {
        "ok": True,
        "event": ev.to_dict(),
        "telegram_text": text,
        "queued": True,
        "send": send_result,
    }


HERALD_RENDER_EVENTS = frozenset({
    "trade_entry",
    "trade_exit",
    "trade_execution",
    "pnl_realized",
    "pnl_unrealized",
    "hourly_digest",
    "material_alert",
    "capital_deposit",
    "capital_withdraw",
    "capital_balance",
    "capital_sweep",
})


def _render_herald_message(record: dict[str, Any]) -> str | None:
    """Delegate to herald_notify renderer when record is HERALD-format."""
    event_type = str(record.get("event_type", record.get("event", "")))
    if event_type not in HERALD_RENDER_EVENTS and not record.get("pnl") and not record.get("portfolio"):
        return None
    if event_type not in HERALD_RENDER_EVENTS:
        return None
    try:
        import importlib.util
        import sys

        herald_paths = [
            Path.home() / ".openclaw" / "workspace" / "skills" / "herald_notify" / "notify.py",
            Path(__file__).resolve().parents[2] / "skills" / "herald_notify" / "notify.py",
        ]
        herald_mod = None
        for hp in herald_paths:
            if hp.exists():
                spec = importlib.util.spec_from_file_location("herald_notify", hp)
                if spec and spec.loader:
                    herald_mod = importlib.util.module_from_spec(spec)
                    sys.modules["herald_notify"] = herald_mod
                    spec.loader.exec_module(herald_mod)
                    break
        if herald_mod is None:
            return None
        msg = herald_mod.render(record)
        return msg.telegram_text
    except Exception:
        return None


def process_herald_queue(
    safety_dir: Path | None = None,
    *,
    config: TelegramConfig | None = None,
    http_post: HttpPostFn | None = None,
    max_items: int = 50,
) -> list[dict[str, Any]]:
    """Drain herald_queue.jsonl and send pending Telegram messages."""
    sd = safety_dir or DEFAULT_SAFETY_DIR
    path = sd / HERALD_QUEUE
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []

    cfg = config or load_config()
    results: list[dict[str, Any]] = []
    remaining: list[str] = []

    for i, line in enumerate(lines):
        if i >= max_items:
            remaining.extend(lines[i:])
            break
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            remaining.append(line)
            continue
        text = record.get("telegram_text")
        if not text:
            herald_text = _render_herald_message(record)
            if herald_text:
                text = herald_text
            else:
                ev = NotifyEvent(
                    name=str(record.get("name", record.get("event", "ALERT"))),
                    event_type=str(record.get("event_type", record.get("event", "alert"))),
                    severity=str(record.get("level", "INFO")),
                    agent_id=str(record.get("source", "HERALD")),
                    description=str(record.get("message", record.get("description", ""))),
                    details={
                        k: v
                        for k, v in record.items()
                        if k
                        not in {
                            "telegram_text",
                            "message",
                            "description",
                            "level",
                            "event",
                            "event_type",
                            "source",
                            "name",
                            "ts",
                            "timestamp",
                            "pnl",
                            "portfolio",
                            "action_required",
                            "reason_codes",
                        }
                    },
                    pnl=record.get("pnl"),
                    portfolio=record.get("portfolio"),
                    action_required=str(record.get("action_required", "")),
                    reason_codes=list(record.get("reason_codes") or []),
                )
                text = format_institutional_message(ev)
        send_result = send_telegram_message(text, config=cfg, http_post=http_post)
        results.append({"record": record, "send": send_result})
        if not send_result.get("ok"):
            remaining.append(line)

    if remaining:
        path.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    else:
        path.unlink(missing_ok=True)

    return results


# --- Event-specific helpers (wire from safety modules) ---


def notify_risk_kernel_decision(
    trade_id: str,
    decision: str,
    reason: str,
    code: str = "",
    *,
    trade: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
    send: bool | None = None,
) -> dict[str, Any]:
    severity = "INFO" if decision == "ALLOW" else "HIGH"
    if code in ("KERNEL_UNREACHABLE", "HALT", "DRAWDOWN_HALT"):
        severity = "CRITICAL"
    return notify(
        NotifyEvent(
            name=f"Risk Kernel {decision}",
            event_type="risk_kernel_decision",
            severity=severity,
            agent_id="GUARDIAN",
            description=reason,
            details={
                "decision": decision,
                "code": code or "—",
                "trade_id": trade_id,
                **(trade or {}),
            },
            portfolio=portfolio if decision == "DENY" else None,
            action_required=(
                "Review deny reason before resubmitting trade."
                if decision == "DENY"
                else ""
            ),
            reason_codes=[code or "RISK_KERNEL", decision],
        ),
        safety_dir=safety_dir,
        send=send,
    )


def notify_gate_decision(
    trade: Any,
    decision: Any,
    *,
    safety_dir: Path | None = None,
) -> None:
    """Notify execution gate outcome — DENY always; ALLOW only when opted in."""
    dec = getattr(decision, "decision", str(decision))
    if dec == "ALLOW" and os.environ.get("TITAN_NOTIFY_GATE_ALLOW", "").strip() not in (
        "1",
        "true",
        "yes",
    ):
        return
    trade_id = getattr(trade, "trade_id", "") or (trade.get("trade_id") if isinstance(trade, dict) else "")
    strategy_id = getattr(trade, "strategy_id", "") or (
        trade.get("strategy_id") if isinstance(trade, dict) else ""
    )
    notify_risk_kernel_decision(
        str(trade_id),
        dec,
        getattr(decision, "reason", ""),
        getattr(decision, "code", ""),
        trade={
            "strategy_id": strategy_id,
            "venue": getattr(trade, "venue", ""),
            "notional_usd": getattr(trade, "notional_usd", 0),
        },
        safety_dir=safety_dir,
    )


def notify_circuit_breaker(
    tier_pct: float,
    drawdown_pct: float,
    action: str,
    *,
    severity: str = "HIGH",
    event_type: str = "circuit_breaker_tier",
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    return notify(
        NotifyEvent(
            name="Circuit Breaker Tier Change",
            event_type=event_type,
            severity=severity,
            agent_id="GUARDIAN",
            description=(
                f"Drawdown tier {tier_pct}% crossed at {drawdown_pct:.2f}% 24h drawdown. "
                f"Action: {action}. Trading continues unless HALT tier."
            ),
            details={
                "tier_pct": tier_pct,
                "drawdown_pct_24h": drawdown_pct,
                "action": action,
            },
            action_required=(
                "Monitor exposure; HALT tier requires operator review."
                if severity == "CRITICAL"
                else "Review portfolio risk posture."
            ),
            reason_codes=["DRAWDOWN_TIER", action.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_drawdown_tier(alert: Any, *, safety_dir: Path | None = None) -> dict[str, Any]:
    return notify_circuit_breaker(
        float(getattr(alert, "tier_pct", 0)),
        float(getattr(alert, "drawdown_pct", 0)),
        str(getattr(alert, "action", "notify_operator")),
        severity=str(getattr(alert, "severity", "HIGH")),
        event_type="drawdown_tier",
        safety_dir=safety_dir,
    )


def notify_trade_intent(
    status: str,
    trade_id: str,
    *,
    pipeline_id: str = "",
    venue: str = "",
    notional_usd: float = 0.0,
    details: dict[str, Any] | None = None,
    pnl: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    severity = "HIGH" if status == "failed" else "MEDIUM" if status == "filled" else "INFO"
    desc = f"Trade {trade_id} status: {status}."
    if pnl and pnl.get("net_usd") is not None:
        desc += f" Net P&L: {_fmt_sign(pnl['net_usd'])}${_fmt_usd(abs(pnl['net_usd']))}."
    elif pnl and pnl.get("realized_usd") is not None:
        desc += f" Realized: {_fmt_sign(pnl['realized_usd'])}${_fmt_usd(abs(pnl['realized_usd']))}."
    return notify(
        NotifyEvent(
            name=f"Trade Intent {status.replace('_', ' ').title()}",
            event_type=f"trade_{status}",
            severity=severity,
            agent_id="TRENCH-OPS",
            description=desc,
            details={
                "trade_id": trade_id,
                "pipeline_id": pipeline_id,
                "venue": venue,
                "notional_usd": notional_usd,
                **(details or {}),
            },
            pnl=pnl if status in ("filled", "failed") else None,
            portfolio=portfolio,
            action_required="Investigate failure logs." if status == "failed" else "",
            reason_codes=["TRADE_INTENT", status.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_signing(
    outcome: str,
    trade_id: str,
    *,
    code: str = "",
    reason: str = "",
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    severity = "CRITICAL" if outcome == "fail" else "MEDIUM"
    return notify(
        NotifyEvent(
            name=f"Signing {'Success' if outcome == 'success' else 'Failure'}",
            event_type="signing_success" if outcome == "success" else "signing_failure",
            severity=severity,
            agent_id="TRENCH-OPS",
            description=reason or f"In-process signing {outcome} for trade {trade_id}.",
            details={"trade_id": trade_id, "code": code, "outcome": outcome},
            action_required=(
                "Signing halted or receipt invalid — do not retry without gate ALLOW."
                if outcome == "fail"
                else ""
            ),
            reason_codes=[code or "SIGNING", outcome.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_halt(
    scope: str,
    operator: str,
    reason: str,
    *,
    active: bool,
    pipeline_id: str = "",
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    state = "activated" if active else "cleared"
    return notify(
        NotifyEvent(
            name=f"Kill Switch / HALT {state.title()}",
            event_type="halt_state_change",
            severity="CRITICAL" if active else "HIGH",
            agent_id="GUARDIAN",
            description=f"HALT {state} by {operator}: {reason}",
            details={
                "scope": scope,
                "operator": operator,
                "pipeline_id": pipeline_id or "—",
                "active": active,
            },
            action_required=(
                "Signed RESUME required before trading resumes."
                if active
                else "Verify services before resuming pipelines."
            ),
            reason_codes=["HALT", scope.upper(), state.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_pipeline_state(
    pipeline_id: str,
    state: str,
    operator: str,
    reason: str = "",
    *,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    return notify(
        NotifyEvent(
            name=f"Pipeline {pipeline_id} {state.title()}",
            event_type="pipeline_state_change",
            severity="HIGH" if state in ("halted", "paused") else "INFO",
            agent_id="ARCHON",
            description=reason or f"Pipeline {pipeline_id} is now {state}.",
            details={"pipeline_id": pipeline_id, "state": state, "operator": operator},
            action_required="Review pipeline health before resume." if state != "running" else "",
            reason_codes=["PIPELINE", state.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_agent_health(
    agent_id: str,
    status: str,
    *,
    details: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    severity = "HIGH" if status == "down" else "INFO"
    return notify(
        NotifyEvent(
            name=f"Agent {agent_id} {status.upper()}",
            event_type="agent_health",
            severity=severity,
            agent_id="FORGE",
            description=f"Agent {agent_id} reported status: {status}.",
            details={"agent_id": agent_id, "status": status, **(details or {})},
            action_required="Restart agent or check inference tier." if status == "down" else "",
            reason_codes=["AGENT_HEALTH", status.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_security_posture(
    change: str,
    operator: str,
    reason: str,
    *,
    details: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    return notify(
        NotifyEvent(
            name=f"Security Posture — {change}",
            event_type="security_posture_change",
            severity="CRITICAL" if "lockdown" in change.lower() else "HIGH",
            agent_id="SENTINEL",
            description=reason,
            details={"change": change, "operator": operator, **(details or {})},
            action_required="Acknowledge lockdown steps and verify kill switch state."
            if "lockdown" in change.lower()
            else "Review security posture in `titan-safety security status`.",
            reason_codes=["SECURITY_POSTURE", change.upper().replace(" ", "_")],
        ),
        safety_dir=safety_dir,
    )


def notify_power_ups(
    event: str,
    *,
    details: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    """Stub hook — wire when UPS telemetry adapter is available."""
    return notify(
        NotifyEvent(
            name=f"Power / UPS — {event}",
            event_type="power_ups_event",
            severity="CRITICAL" if "loss" in event.lower() or "fail" in event.lower() else "HIGH",
            agent_id="FORGE",
            description=f"UPS/power event: {event}.",
            details=details or {"status": "stub — connect UPS telemetry"},
            action_required="Verify Eaton UPS and power-loss HALT policy.",
            reason_codes=["POWER_UPS", event.upper().replace(" ", "_")],
        ),
        safety_dir=safety_dir,
        send=False,
    )


def notify_tca_daily_scorecard(
    digest: dict[str, Any],
    *,
    telegram_text: str = "",
    safety_dir: Path | None = None,
    send: bool = True,
) -> dict[str, Any]:
    """Publish daily TCA scorecard digest via HERALD / Telegram."""
    bleeding = digest.get("bleeding") or []
    severity = "CRITICAL" if bleeding else "INFO"
    return notify(
        NotifyEvent(
            name=f"TCA Daily Scorecard — {digest.get('date_utc', 'today')}",
            event_type="tca_daily_scorecard",
            severity=severity,
            agent_id="HERALD",
            description=telegram_text or "Daily TCA execution-quality scorecard.",
            details=digest,
            action_required=(
                "Review BLEEDING lanes — profit_loop auto-defunds; refund needs promotion YES."
                if bleeding
                else ""
            ),
            reason_codes=["TCA_DAILY", "HERALD_DIGEST"],
        ),
        safety_dir=safety_dir,
        send=send,
    )


def notify_promotion_gate(
    request_id: str,
    category: str,
    subject: str,
    approved: bool,
    reason: str,
    *,
    operator_id: str = "",
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    return notify(
        NotifyEvent(
            name=f"Promotion Gate {'Approved' if approved else 'Denied'}",
            event_type="promotion_gate",
            severity="CRITICAL" if approved and category == "phase5_go_nogo" else "HIGH",
            agent_id="ARCHON",
            description=reason,
            details={
                "request_id": request_id,
                "category": category,
                "subject": subject,
                "approved": approved,
                "operator_id": operator_id,
            },
            action_required=(
                "Phase gate opened — verify PRODUCTION_READINESS before capital."
                if approved and category == "phase5_go_nogo"
                else ""
            ),
            reason_codes=["PROMOTION_GATE", category.upper(), "YES" if approved else "DENY"],
        ),
        safety_dir=safety_dir,
    )


def notify_trezor_sweep(
    sweep_amount_usd: float,
    outcome: str,
    message: str,
    *,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    return notify(
        NotifyEvent(
            name="Trezor Weekly Profit Sweep",
            event_type="trezor_sweep",
            severity="HIGH" if outcome == "executed" else "INFO",
            agent_id="ATLAS",
            description=f"{message} Sweep amount: ${_fmt_usd(sweep_amount_usd)}.",
            details={"sweep_amount_usd": sweep_amount_usd, "outcome": outcome},
            pnl={"realized_usd": sweep_amount_usd, "outcome": "WIN" if outcome == "executed" else "OPEN"},
            action_required="Confirm Trezor Safe 7 receipt." if outcome == "executed" else "",
            reason_codes=["TREZOR_SWEEP", outcome.upper()],
        ),
        safety_dir=safety_dir,
    )


def notify_pnl_realized(
    *,
    pipeline_id: str,
    asset: str,
    realized_usd: float,
    pct_equity: float = 0.0,
    outcome: str = "WIN",
    fees_usd: float = 0.0,
    trade_id: str = "",
    details: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
    send: bool | None = None,
    enqueue: bool = True,
) -> dict[str, Any]:
    """Notify realized PnL on position close."""
    severity = "MEDIUM" if abs(pct_equity) < 0.5 else "HIGH"
    return notify(
        NotifyEvent(
            name=f"Realized P&L — {outcome}",
            event_type="pnl_realized",
            severity=severity,
            agent_id="ATLAS",
            description=(
                f"{asset} closed on {pipeline_id}: "
                f"{_fmt_sign(realized_usd)}${_fmt_usd(abs(realized_usd))} "
                f"({_fmt_sign(pct_equity)}{_fmt_pct(abs(pct_equity))}% equity)."
            ),
            details={
                "pipeline_id": pipeline_id,
                "asset": asset,
                "trade_id": trade_id,
                **(details or {}),
            },
            pnl={
                "realized_usd": realized_usd,
                "net_usd": realized_usd,
                "pct_equity": pct_equity,
                "fees_usd": fees_usd,
                "outcome": outcome,
            },
            portfolio=portfolio,
            reason_codes=["PNL_REALIZED", outcome],
        ),
        safety_dir=safety_dir,
        send=send,
        enqueue=enqueue,
    )


def notify_pnl_unrealized(
    *,
    unrealized_usd: float,
    pct_equity: float = 0.0,
    pipeline_id: str = "",
    asset: str = "",
    portfolio: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    """Notify unrealized PnL mark-to-market snapshot."""
    return notify(
        NotifyEvent(
            name="Unrealized P&L Update",
            event_type="pnl_unrealized",
            severity="INFO",
            agent_id="ATLAS",
            description=(
                f"Mark-to-market{f' for {asset}' if asset else ''}"
                f"{f' ({pipeline_id})' if pipeline_id else ''}: "
                f"{_fmt_sign(unrealized_usd)}${_fmt_usd(abs(unrealized_usd))} "
                f"({_fmt_sign(pct_equity)}{_fmt_pct(abs(pct_equity))}% equity)."
            ),
            details={"pipeline_id": pipeline_id, "asset": asset},
            pnl={
                "unrealized_usd": unrealized_usd,
                "pct_equity": pct_equity,
                "outcome": "OPEN",
            },
            portfolio=portfolio,
            reason_codes=["PNL_UNREALIZED"],
        ),
        safety_dir=safety_dir,
    )


def notify_hourly_digest(
    digest: dict[str, Any],
    *,
    portfolio: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
    send: bool | None = None,
) -> dict[str, Any]:
    """Send hourly digest — delegates to herald renderer when available."""
    record = {
        "event_type": "hourly_digest",
        "agent_id": "HERALD",
        "reason_codes": ["HOURLY_DIGEST"],
        "severity": "INFO",
        "digest": digest,
        "portfolio": portfolio or {},
    }
    herald_text = _render_herald_message(record)
    if herald_text:
        sd = safety_dir or DEFAULT_SAFETY_DIR
        queue_record = {**record, "telegram_text": herald_text, "ts": time.time()}
        enqueue_herald_event(sd, queue_record)
        cfg = load_config()
        should_send = send if send is not None else cfg.enabled
        send_result: dict[str, Any] | None = None
        if should_send:
            send_result = send_telegram_message(herald_text, config=cfg)
        return {
            "ok": True,
            "telegram_text": herald_text,
            "queued": True,
            "send": send_result,
            "renderer": "herald",
        }

    hour_pnl = digest.get("hour_pnl_usd", 0)
    wins = digest.get("wins", 0)
    losses = digest.get("losses", 0)
    return notify(
        NotifyEvent(
            name="Hourly Performance Digest",
            event_type="hourly_digest",
            severity="INFO",
            agent_id="HERALD",
            description=(
                f"Hour {_fmt_sign(hour_pnl)}${_fmt_usd(abs(hour_pnl))} | "
                f"{digest.get('trades_count', 0)} trades (W:{wins} L:{losses})"
            ),
            details=digest,
            pnl={
                "daily_pnl_usd": (portfolio or {}).get("daily_pnl_usd"),
                "daily_pnl_pct": (portfolio or {}).get("daily_pnl_pct"),
            },
            portfolio=portfolio,
            reason_codes=["HOURLY_DIGEST"],
        ),
        safety_dir=safety_dir,
        send=send,
    )


def notify_money_summary(
    *,
    period: str,
    realized_usd: float = 0.0,
    unrealized_usd: float = 0.0,
    daily_pnl_usd: float = 0.0,
    daily_pnl_pct: float = 0.0,
    equity_usd: float = 0.0,
    wins: int = 0,
    losses: int = 0,
    fees_usd: float = 0.0,
    portfolio: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    """Periodic PnL rollup for operator visibility."""
    total = wins + losses
    win_rate = (100.0 * wins / total) if total else 0.0
    net = realized_usd + unrealized_usd
    outcome = "WIN" if net > 0 else "LOSS" if net < 0 else "OPEN"
    port = portfolio or {
        "equity_usd": equity_usd,
        "daily_pnl_usd": daily_pnl_usd,
        "daily_pnl_pct": daily_pnl_pct,
    }
    return notify(
        NotifyEvent(
            name=f"Money Summary — {period}",
            event_type="money_summary",
            severity="INFO",
            agent_id="HERALD",
            description=(
                f"{period} rollup: net {_fmt_sign(net)}${_fmt_usd(abs(net))}, "
                f"win rate {_fmt_pct(win_rate)}% ({wins}W/{losses}L)."
            ),
            details={
                "period": period,
                "wins": wins,
                "losses": losses,
                "win_rate_pct": win_rate,
            },
            pnl={
                "realized_usd": realized_usd,
                "unrealized_usd": unrealized_usd,
                "net_usd": net,
                "daily_pnl_usd": daily_pnl_usd,
                "daily_pnl_pct": daily_pnl_pct,
                "fees_usd": fees_usd,
                "outcome": outcome,
            },
            portfolio=port,
            reason_codes=["MONEY_SUMMARY", period.upper().replace(" ", "_")],
        ),
        safety_dir=safety_dir,
    )


def notify_health_failure(
    check_name: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    safety_dir: Path | None = None,
) -> dict[str, Any]:
    return notify(
        NotifyEvent(
            name=f"Health Check Failed — {check_name}",
            event_type="health_verify_failure",
            severity="HIGH",
            agent_id="FORGE",
            description=message,
            details=details or {},
            action_required="Run `./verify.sh` and restore failing safety service.",
            reason_codes=["HEALTH_VERIFY", check_name.upper().replace(" ", "_")],
        ),
        safety_dir=safety_dir,
    )


def sample_test_event() -> NotifyEvent:
    return NotifyEvent(
        name="Telegram Notify Test",
        event_type="notify_test",
        severity="INFO",
        agent_id="HERALD",
        description="Institutional notification path verified with financial summary.",
        details={"environment": "test", "module": "telegram_notify", "pipeline_id": "P3"},
        pnl={
            "realized_usd": 142.88,
            "unrealized_usd": 156.20,
            "net_usd": 142.88,
            "pct_equity": 0.55,
            "daily_pnl_usd": 842.33,
            "daily_pnl_pct": 0.32,
            "fees_usd": 5.55,
            "outcome": "WIN",
        },
        portfolio={
            "equity_usd": 261042.18,
            "available_usd": 228500.00,
            "exposure_pct": 12.4,
            "open_positions": 7,
        },
        action_required="None — smoke test only.",
        reason_codes=["NOTIFY_TEST"],
    )
