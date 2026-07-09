"""Dead-man's switch — operator heartbeat enforcement."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_STATE = Path.home() / ".openclaw" / "safety" / "dead_mans_switch.json"


@dataclass
class DeadMansConfig:
    operator_heartbeat_hours: float = 48.0
    flatten_after_hours: float = 72.0
    never_auto_promote: bool = True


@dataclass
class DeadMansState:
    last_heartbeat: float
    derisk_triggered: bool = False
    flatten_triggered: bool = False
    promotion_blocked: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeadMansState:
        return cls(
            last_heartbeat=float(data.get("last_heartbeat", time.time())),
            derisk_triggered=bool(data.get("derisk_triggered", False)),
            flatten_triggered=bool(data.get("flatten_triggered", False)),
            promotion_blocked=bool(data.get("promotion_blocked", True)),
        )


class DeadMansSwitch:
    """Operator heartbeat timer — de-risk at 48h, flatten at 72h."""

    def __init__(
        self,
        config: DeadMansConfig | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.config = config or DeadMansConfig()
        self.state_path = state_path or DEFAULT_STATE
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> DeadMansState:
        if self.state_path.exists():
            return DeadMansState.from_dict(
                json.loads(self.state_path.read_text(encoding="utf-8"))
            )
        return DeadMansState(last_heartbeat=time.time())

    def _save(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state.to_dict(), indent=2), encoding="utf-8"
        )

    def heartbeat(self, operator: str = "operator") -> DeadMansState:
        self.state.last_heartbeat = time.time()
        self.state.derisk_triggered = False
        self.state.flatten_triggered = False
        self._save()
        return self.state

    def hours_since_heartbeat(self) -> float:
        return (time.time() - self.state.last_heartbeat) / 3600.0

    def evaluate(self) -> dict[str, Any]:
        hours = self.hours_since_heartbeat()
        action = "none"
        if hours >= self.config.flatten_after_hours:
            action = "flatten"
            self.state.flatten_triggered = True
            self.state.derisk_triggered = True
        elif hours >= self.config.operator_heartbeat_hours:
            action = "derisk"
            self.state.derisk_triggered = True
        self._save()
        return {
            "action": action,
            "hours_since_heartbeat": hours,
            "derisk_triggered": self.state.derisk_triggered,
            "flatten_triggered": self.state.flatten_triggered,
            "promotion_allowed": False if self.config.never_auto_promote else action == "none",
            "never_auto_promote": self.config.never_auto_promote,
        }

    def set_last_heartbeat_hours_ago(self, hours: float) -> None:
        """Test helper — set heartbeat timestamp in the past."""
        self.state.last_heartbeat = time.time() - hours * 3600.0
        self._save()

    def health(self) -> dict[str, Any]:
        ev = self.evaluate()
        return {
            "status": "ok" if ev["action"] == "none" else ev["action"],
            **ev,
        }
