"""Unit tests for institutional Telegram notifications (no live API)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from titan_safety.telegram_notify import (
    NotifyEvent,
    escape_markdown,
    format_institutional_message,
    load_config,
    notify,
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
