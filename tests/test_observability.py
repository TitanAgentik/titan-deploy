"""Observability metrics tests."""

from __future__ import annotations

from titan_safety.observability import MetricsRegistry


def test_prometheus_format() -> None:
    m = MetricsRegistry()
    m.inc("test_counter")
    m.set_gauge("test_gauge", 1.5)
    out = m.to_prometheus()
    assert "test_counter 1" in out
    assert "test_gauge 1.5" in out


def test_json_export() -> None:
    m = MetricsRegistry()
    m.inc("a")
    data = m.to_json()
    assert data["counters"]["a"] == 1
