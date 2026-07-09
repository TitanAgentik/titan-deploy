"""AUGUR regime feed — file/HTTP/stub sources into portfolio risk."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RegimeReading:
    regime: str
    source: str
    ts: float
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "source": self.source,
            "ts": self.ts,
            "raw": self.raw,
        }


class RegimeFeed(ABC):
    @abstractmethod
    def read(self) -> RegimeReading:
        ...


class StubRegimeFeed(RegimeFeed):
    def __init__(self, regime: str = "neutral") -> None:
        self._regime = regime

    def read(self) -> RegimeReading:
        return RegimeReading(regime=self._regime, source="stub", ts=time.time())


class FileRegimeFeed(RegimeFeed):
    """Read regime from ~/.openclaw/safety/augur_regime.json written by AUGUR agent."""

    def __init__(self, path: Path, fallback: str = "neutral") -> None:
        self.path = path
        self.fallback = fallback

    def read(self) -> RegimeReading:
        if not self.path.exists():
            return RegimeReading(regime=self.fallback, source="file_missing", ts=time.time())
        data = json.loads(self.path.read_text(encoding="utf-8"))
        regime = str(data.get("regime", self.fallback))
        return RegimeReading(
            regime=regime,
            source="file",
            ts=float(data.get("ts", time.time())),
            raw=json.dumps(data),
        )


class HttpRegimeFeed(RegimeFeed):
    """Poll an AUGUR HTTP endpoint that returns {\"regime\": \"...\"}."""

    def __init__(self, url: str, timeout: float = 2.0, fallback: str = "neutral") -> None:
        self.url = url
        self.timeout = timeout
        self.fallback = fallback

    def read(self) -> RegimeReading:
        try:
            req = urllib.request.Request(self.url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
            return RegimeReading(
                regime=str(data.get("regime", self.fallback)),
                source="http",
                ts=time.time(),
                raw=json.dumps(data),
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return RegimeReading(regime=self.fallback, source="http_error", ts=time.time())


def get_regime_feed(
    kind: str = "stub",
    *,
    regime: str = "neutral",
    path: Path | None = None,
    url: str | None = None,
) -> RegimeFeed:
    if kind in ("file", "augur_file"):
        p = path or (Path.home() / ".openclaw" / "safety" / "augur_regime.json")
        return FileRegimeFeed(p, fallback=regime)
    if kind in ("http", "augur_http") and url:
        return HttpRegimeFeed(url, fallback=regime)
    return StubRegimeFeed(regime)


def write_regime_file(path: Path, regime: str, meta: dict[str, Any] | None = None) -> None:
    """Helper for AUGUR agent / tests to publish a regime reading."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"regime": regime, "ts": time.time(), **(meta or {})}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
