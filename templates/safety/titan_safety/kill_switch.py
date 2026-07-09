"""Model-independent global kill switch."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"
KILL_FLAG = "KILL_SWITCH.active"
PIPELINE_HALT_DIR = "pipeline_halts"
HALT_STATE = "HALT_STATE.json"
SECRET_FILE = "kill_switch.secret"
_PIPELINE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_pipeline_id(pipeline_id: str) -> bool:
    return bool(pipeline_id) and bool(_PIPELINE_ID_RE.match(pipeline_id))


@dataclass
class HaltState:
    active: bool = False
    activated_at: float | None = None
    activated_by: str = ""
    reason: str = ""
    flatten_requested: bool = False
    scope: str = "global"  # global | pipeline | portfolio
    pipeline_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HaltState:
        return cls(
            active=bool(data.get("active", False)),
            activated_at=data.get("activated_at"),
            activated_by=str(data.get("activated_by", "")),
            reason=str(data.get("reason", "")),
            flatten_requested=bool(data.get("flatten_requested", False)),
            scope=str(data.get("scope", "global")),
            pipeline_id=str(data.get("pipeline_id", "")),
        )


class KillSwitch:
    """File-flag + optional HMAC-signed command kill switch."""

    def __init__(self, safety_dir: Path | None = None) -> None:
        self.safety_dir = safety_dir or DEFAULT_SAFETY_DIR
        self.safety_dir.mkdir(parents=True, exist_ok=True)

    @property
    def flag_path(self) -> Path:
        return self.safety_dir / KILL_FLAG

    @property
    def state_path(self) -> Path:
        return self.safety_dir / HALT_STATE

    @property
    def secret_path(self) -> Path:
        return self.safety_dir / SECRET_FILE

    def ensure_secret(self) -> bytes:
        if self.secret_path.exists():
            return self.secret_path.read_bytes()
        secret = secrets.token_bytes(32)
        self.secret_path.write_bytes(secret)
        os.chmod(self.secret_path, 0o600)
        return secret

    @property
    def pipeline_halt_dir(self) -> Path:
        d = self.safety_dir / PIPELINE_HALT_DIR
        d.mkdir(parents=True, exist_ok=True)
        return d

    def is_active(self) -> bool:
        return self.flag_path.exists() or self.load_state().active

    def is_pipeline_halted(self, pipeline_id: str) -> bool:
        if not _safe_pipeline_id(pipeline_id):
            return True  # fail-closed on malformed id
        if self.is_active():
            state = self.load_state()
            if state.scope == "global" or state.scope == "portfolio":
                return True
        flag = self.pipeline_halt_dir / f"{pipeline_id}.halt"
        return flag.exists()

    def halted_pipelines(self) -> list[str]:
        if not self.pipeline_halt_dir.exists():
            return []
        return [p.stem for p in self.pipeline_halt_dir.glob("*.halt")]

    def activate_pipeline(self, pipeline_id: str, operator: str, reason: str) -> dict[str, Any]:
        if not _safe_pipeline_id(pipeline_id):
            raise ValueError(f"invalid pipeline_id: {pipeline_id!r}")
        flag = self.pipeline_halt_dir / f"{pipeline_id}.halt"
        # Path-traversal guard
        if not flag.resolve().is_relative_to(self.pipeline_halt_dir.resolve()):
            raise ValueError(f"pipeline halt path escapes directory: {pipeline_id}")
        payload = {
            "ts": time.time(),
            "by": operator,
            "reason": reason,
            "pipeline_id": pipeline_id,
        }
        flag.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def deactivate_pipeline(self, pipeline_id: str) -> bool:
        if not _safe_pipeline_id(pipeline_id):
            return False
        flag = self.pipeline_halt_dir / f"{pipeline_id}.halt"
        if not flag.resolve().is_relative_to(self.pipeline_halt_dir.resolve()):
            return False
        if flag.exists():
            flag.unlink()
            return True
        return False

    def activate_portfolio(self, operator: str, reason: str, flatten: bool = True) -> HaltState:
        """Global portfolio halt — all pipelines, no new entries."""
        return self.activate(operator, reason, flatten=flatten, scope="portfolio")

    def load_state(self) -> HaltState:
        if not self.state_path.exists():
            return HaltState()
        return HaltState.from_dict(json.loads(self.state_path.read_text(encoding="utf-8")))

    def activate(
        self,
        operator: str,
        reason: str,
        flatten: bool = True,
        scope: str = "global",
        pipeline_id: str = "",
    ) -> HaltState:
        state = HaltState(
            active=True,
            activated_at=time.time(),
            activated_by=operator,
            reason=reason,
            flatten_requested=flatten,
            scope=scope,
            pipeline_id=pipeline_id,
        )
        self.flag_path.write_text(
            json.dumps({"ts": state.activated_at, "by": operator, "reason": reason}),
            encoding="utf-8",
        )
        self.state_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        return state

    def deactivate(self, operator: str) -> HaltState:
        if self.flag_path.exists():
            self.flag_path.unlink()
        state = HaltState(active=False, activated_by=operator, reason="cleared")
        self.state_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        return state

    def sign_command(self, command: str, operator: str) -> str:
        secret = self.ensure_secret()
        payload = f"{command}|{operator}|{int(time.time())}"
        sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}|{sig}"

    def verify_signed_command(self, signed: str, max_age_seconds: int = 300) -> tuple[bool, str]:
        parts = signed.split("|")
        if len(parts) != 4:
            return False, "malformed signed command"
        command, operator, ts_str, sig = parts
        try:
            ts = int(ts_str)
        except ValueError:
            return False, "invalid timestamp"
        if time.time() - ts > max_age_seconds:
            return False, "signed command expired"
        if not self.secret_path.exists():
            return False, "no kill switch secret configured"
        secret = self.secret_path.read_bytes()
        payload = f"{command}|{operator}|{ts}"
        expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False, "invalid signature"
        return True, command

    def health(self) -> dict[str, Any]:
        state = self.load_state()
        return {
            "status": "halted" if self.is_active() else "ok",
            "kill_switch_active": self.is_active(),
            "scope": state.scope,
            "halted_pipelines": self.halted_pipelines(),
            "state": state.to_dict(),
            "note": "BusKill/hardware kill is an ops step — see playbooks/kill_switch.yaml",
        }
