"""Exit ramp / safe mode — gradual position reduction procedure."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


SAFE_MODE_FLAG = "SAFE_MODE.active"
WIND_DOWN_STATE = "wind_down_state.json"


class WindDownPhase(str, Enum):
    NORMAL = "normal"
    SAFE_MODE = "safe_mode"
    DERISK = "derisk"
    FLATTEN = "flatten"
    COMPLETE = "complete"


@dataclass
class WindDownConfig:
    safe_mode_max_equity_pct: float = 50.0
    derisk_target_pct: float = 25.0
    flatten_target_pct: float = 0.0
    step_interval_seconds: float = 300.0
    max_reduction_pct_per_step: float = 10.0


@dataclass
class WindDownState:
    phase: str = WindDownPhase.NORMAL.value
    started_at: float | None = None
    operator: str = ""
    reason: str = ""
    current_exposure_pct: float = 100.0
    target_exposure_pct: float = 100.0
    steps_completed: int = 0
    safe_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WindDownState:
        return cls(
            phase=str(data.get("phase", WindDownPhase.NORMAL.value)),
            started_at=data.get("started_at"),
            operator=str(data.get("operator", "")),
            reason=str(data.get("reason", "")),
            current_exposure_pct=float(data.get("current_exposure_pct", 100.0)),
            target_exposure_pct=float(data.get("target_exposure_pct", 100.0)),
            steps_completed=int(data.get("steps_completed", 0)),
            safe_mode=bool(data.get("safe_mode", False)),
        )


class WindDownController:
    """Gradual position reduction with safe_mode flag."""

    def __init__(
        self,
        safety_dir: Path | None = None,
        config: WindDownConfig | None = None,
    ) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or WindDownConfig()
        self.state_path = self.safety_dir / WIND_DOWN_STATE
        self.flag_path = self.safety_dir / SAFE_MODE_FLAG

    def load_state(self) -> WindDownState:
        if not self.state_path.exists():
            return WindDownState()
        return WindDownState.from_dict(
            json.loads(self.state_path.read_text(encoding="utf-8"))
        )

    def _save(self, state: WindDownState) -> None:
        self.state_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        if state.safe_mode:
            self.flag_path.write_text(
                json.dumps({"ts": time.time(), "phase": state.phase}),
                encoding="utf-8",
            )
        elif self.flag_path.exists():
            self.flag_path.unlink()

    def is_safe_mode(self) -> bool:
        return self.flag_path.exists() or self.load_state().safe_mode

    def enter_safe_mode(self, operator: str, reason: str) -> WindDownState:
        state = WindDownState(
            phase=WindDownPhase.SAFE_MODE.value,
            started_at=time.time(),
            operator=operator,
            reason=reason,
            current_exposure_pct=100.0,
            target_exposure_pct=self.config.safe_mode_max_equity_pct,
            safe_mode=True,
        )
        self._save(state)
        return state

    def start_derisk(self, operator: str, reason: str, current_pct: float = 100.0) -> WindDownState:
        state = WindDownState(
            phase=WindDownPhase.DERISK.value,
            started_at=time.time(),
            operator=operator,
            reason=reason,
            current_exposure_pct=current_pct,
            target_exposure_pct=self.config.derisk_target_pct,
            safe_mode=True,
        )
        self._save(state)
        return state

    def start_flatten(self, operator: str, reason: str, current_pct: float = 100.0) -> WindDownState:
        state = WindDownState(
            phase=WindDownPhase.FLATTEN.value,
            started_at=time.time(),
            operator=operator,
            reason=reason,
            current_exposure_pct=current_pct,
            target_exposure_pct=self.config.flatten_target_pct,
            safe_mode=True,
        )
        self._save(state)
        return state

    def step(self, current_exposure_pct: float | None = None) -> dict[str, Any]:
        state = self.load_state()
        if state.phase in (WindDownPhase.NORMAL.value, WindDownPhase.COMPLETE.value):
            return {"action": "none", "state": state.to_dict()}

        if current_exposure_pct is not None:
            state.current_exposure_pct = current_exposure_pct

        if state.current_exposure_pct <= state.target_exposure_pct:
            state.phase = WindDownPhase.COMPLETE.value
            state.safe_mode = False
            self._save(state)
            return {"action": "complete", "state": state.to_dict()}

        reduction = min(
            self.config.max_reduction_pct_per_step,
            state.current_exposure_pct - state.target_exposure_pct,
        )
        state.current_exposure_pct -= reduction
        state.steps_completed += 1
        self._save(state)
        return {
            "action": "reduce",
            "reduce_pct": reduction,
            "new_exposure_pct": state.current_exposure_pct,
            "target_pct": state.target_exposure_pct,
            "state": state.to_dict(),
        }

    def resume_normal(self, operator: str) -> WindDownState:
        state = WindDownState(
            phase=WindDownPhase.NORMAL.value,
            operator=operator,
            reason="operator resume",
            safe_mode=False,
        )
        self._save(state)
        return state

    def health(self) -> dict[str, Any]:
        state = self.load_state()
        return {
            "status": "safe_mode" if state.safe_mode else "ok",
            "safe_mode": state.safe_mode,
            "phase": state.phase,
            "exposure_pct": state.current_exposure_pct,
        }
