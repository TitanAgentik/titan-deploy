"""Structured logging and Prometheus-style metrics for safety services."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": getattr(record, "service", "titan_safety"),
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra_fields"):
            payload.update(record.extra_fields)  # type: ignore[arg-type]
        return json.dumps(payload, separators=(",", ":"))


def setup_logging(service: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(f"titan.{service}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


@dataclass
class MetricsRegistry:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    gauges: dict[str, float] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self.gauges[name] = value

    def to_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for k, v in sorted(self.counters.items()):
                lines.append(f"# TYPE {k} counter")
                lines.append(f"{k} {v}")
            for k, v in sorted(self.gauges.items()):
                lines.append(f"# TYPE {k} gauge")
                lines.append(f"{k} {v}")
        return "\n".join(lines) + "\n"

    def to_json(self) -> dict[str, Any]:
        with self._lock:
            return {"counters": dict(self.counters), "gauges": dict(self.gauges)}


METRICS = MetricsRegistry()
