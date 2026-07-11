"""Unit tests for institutional Telegram notifications (no live API)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from titan_safety.telegram_notify import (
    NotifyEvent,
    escape_markdown,
    format_institutional_message,
    load_config,
    notify,
    notify_pnl_realized,
    process_herald_queue,
    sample_test_event,
    send_telegram_message,
    TelegramConfig,
)


def test_escape_markdown_special_chars() -> None:
    assert escape_markdown("a_b*c") == r"a\_b\*c"
    assert escape_markdown("plain") == "plain"


def test_format_institutional_message_required_fields() -> None:
    ev = sample_test_event()
    text = format_institutional_message(ev)
    assert "TITAN — Telegram Notify Test" in text
    assert "Severity: `INFO`" in text
    assert "Agent: `HERALD`" in text
    assert "Event:" in text and "notify" in text
    assert "Description" in text
    assert "Details" in text
    assert "Action Required" in text
    assert "Reason codes:" in text
    assert "NOTIFY" in text
    assert "✅" not in text
    assert "⚡" not in text


def test_notify_event_defaults_timestamp_and_reason_codes() -> None:
    ev = NotifyEvent(
        name="X",
        event_type="unit",
        severity="LOW",
        agent_id="TEST",
        description="d",
    )
    assert ev.timestamp.endswith("Z")
    assert ev.reason_codes == ["UNIT"]


def test_notify_queues_without_send(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TITAN_TELEGRAM_ENABLED", "0")
    result = notify(sample_test_event(), safety_dir=tmp_path, send=False)
    assert result["ok"] is True
    assert result["queued"] is True
    queue = (tmp_path / "herald_queue.jsonl").read_text(encoding="utf-8")
    assert "notify_test" in queue
    assert result["send"] is None


def test_send_telegram_mock_http() -> None:
    captured: dict[str, object] = {}

    def mock_post(url: str, data: bytes, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
        captured["url"] = url
        captured["data"] = data.decode("utf-8")
        captured["headers"] = headers
        return 200, json.dumps({"ok": True, "result": {"message_id": 1}}).encode()

    cfg = TelegramConfig(bot_token="tok123", chat_id="999", enabled=True)
    result = send_telegram_message(
        "*hello*",
        config=cfg,
        http_post=mock_post,
    )
    assert result["ok"] is True
    assert "tok123" in str(captured["url"])
    assert "chat_id=999" in str(captured["data"])


def test_send_skips_when_unconfigured() -> None:
    cfg = TelegramConfig(bot_token="", chat_id="", enabled=True)
    result = send_telegram_message("x", config=cfg)
    assert result["ok"] is False
    assert result.get("skipped") is True


def test_send_dry_run() -> None:
    cfg = TelegramConfig(bot_token="t", chat_id="c", dry_run=True)
    result = send_telegram_message("msg", config=cfg)
    assert result["ok"] is True
    assert result.get("dry_run") is True


def test_process_herald_queue_drains_on_success(tmp_path: Path) -> None:
    path = tmp_path / "herald_queue.jsonl"
    ev = sample_test_event()
    path.write_text(
        json.dumps({"telegram_text": format_institutional_message(ev), "event_type": "notify_test"})
        + "\n",
        encoding="utf-8",
    )

    def mock_post(url: str, data: bytes, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
        return 200, b'{"ok":true}'

    cfg = TelegramConfig(bot_token="t", chat_id="1", enabled=True)
    results = process_herald_queue(tmp_path, config=cfg, http_post=mock_post)
    assert len(results) == 1
    assert results[0]["send"]["ok"] is True
    assert not path.exists()


def test_load_config_prefers_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setenv("TELEGRAM_USER_ID", "222")
    cfg = load_config()
    assert cfg.chat_id == "111"


def test_load_config_falls_back_to_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_USER_ID", "222")
    cfg = load_config()
    assert cfg.chat_id == "222"


def test_financial_summary_section_when_pnl_set() -> None:
    ev = NotifyEvent(
        name="PnL Close",
        event_type="pnl_realized",
        severity="MEDIUM",
        agent_id="ATLAS",
        description="WETH/USDC closed with profit.",
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
            "exposure_pct": 12.4,
            "open_positions": 7,
        },
    )
    text = format_institutional_message(ev)
    assert "*Financial Summary*" in text
    assert "Realized: +$142.88 (+0.55% equity)" in text
    assert "Unrealized: +$156.20" in text
    assert "Daily P&L: +$842.33 (+0.32%)" in text
    assert "Equity: $261,042.18" in text
    assert "Exposure: 12.40%" in text
    assert "Open: 7" in text
    assert "Outcome: `WIN`" in text


def test_financial_summary_negative_signs() -> None:
    ev = NotifyEvent(
        name="Loss",
        event_type="pnl_realized",
        severity="HIGH",
        agent_id="ATLAS",
        description="Loss on close.",
        pnl={"realized_usd": -87.50, "pct_equity": -0.34, "outcome": "LOSS"},
    )
    text = format_institutional_message(ev)
    assert "Realized: -$87.50 (-0.34% equity)" in text
    assert "Outcome: `LOSS`" in text


def test_financial_summary_absent_without_pnl() -> None:
    ev = sample_test_event()
    ev.pnl = None
    ev.portfolio = None
    text = format_institutional_message(ev)
    assert "Financial Summary" not in text


def test_sample_test_event_includes_financial_summary() -> None:
    text = format_institutional_message(sample_test_event())
    assert "*Financial Summary*" in text
    assert "+$142.88" in text


def test_process_herald_queue_includes_pnl_from_record(tmp_path: Path) -> None:
    path = tmp_path / "herald_queue.jsonl"
    record = {
        "name": "PnL Close",
        "event_type": "pnl_realized",
        "level": "MEDIUM",
        "source": "ATLAS",
        "description": "Closed with profit.",
        "pnl": {"realized_usd": 50.0, "pct_equity": 0.2, "outcome": "WIN"},
        "portfolio": {"equity_usd": 100000.0, "open_positions": 3},
        "reason_codes": ["PNL_REALIZED"],
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    def mock_post(url: str, data: bytes, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
        return 200, b'{"ok":true}'

    cfg = TelegramConfig(bot_token="t", chat_id="1", enabled=True)
    results = process_herald_queue(tmp_path, config=cfg, http_post=mock_post)
    assert len(results) == 1
    assert results[0]["send"]["ok"] is True


def test_notify_pnl_realized_helper(tmp_path: Path) -> None:
    result = notify_pnl_realized(
        pipeline_id="P3",
        asset="WETH/USDC",
        realized_usd=142.88,
        pct_equity=0.55,
        outcome="WIN",
        send=False,
        safety_dir=tmp_path,
    )
    assert result["ok"] is True
    assert "Financial Summary" in result["telegram_text"]
    assert "+$142.88" in result["telegram_text"]


def test_notify_pnl_cli_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    safety_pkg = repo_root / "templates" / "safety"
    import os

    env = {**os.environ, "PYTHONPATH": str(safety_pkg), "TITAN_TELEGRAM_ENABLED": "0"}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "titan_safety.cli",
            "notify",
            "pnl",
            "--realized",
            "142.88",
            "--pct-equity",
            "0.55",
            "--pipeline",
            "P3",
            "--asset",
            "WETH/USDC",
            "--outcome",
            "WIN",
            "--format-only",
            "--no-send",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Financial Summary" in proc.stdout
    assert "+$142.88" in proc.stdout
