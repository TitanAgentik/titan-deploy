"""Four-pillar security ops — posture, honeypots, lockdown sequencing."""

from __future__ import annotations

import json
import socket
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .evolution_freeze import EvolutionFreeze
from .kill_switch import KillSwitch
from .stealth_predatory import predatory_posture, stealth_posture

DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"
HONEYPOT_DIR = "honeypots"
HONEYPOT_ARMED = "HONEYPOT.armed"
HONEYPOT_DISARMED = "HONEYPOT.disarmed"
# Must match signing_service.is_halted() / flatten_executor revoke flag
SIGNING_HALT_FLAG = "SIGNING_HALTED"
EDGE_FAIL_CLOSED_FLAG = "EDGE_FAIL_CLOSED"
HERALD_QUEUE = "herald_queue.jsonl"
PCR_DRIFT_FILE = "pcr_drift.json"
POSTURE_FILE = "security_posture.json"
LOCKDOWN_AUDIT = "security_lockdown.jsonl"
LAYER_PROBE_TIMEOUT_S = 0.2

LAYERS = [
    {"id": "L1", "name": "risk_kernel", "port": ":19001"},
    {"id": "L2", "name": "signing_node", "port": ":19010"},
    {"id": "L3", "name": "netns_policy", "port": "netns"},
    {"id": "L4", "name": "pcr_codeql", "port": "T2"},
    {"id": "L5", "name": "dead_mans_switch", "port": ":19005"},
    {"id": "L6", "name": "closed_model_ban", "port": "policy"},
]


@dataclass
class SecurityPosture:
    overall: str = "HARDENED"
    threat_level: str = "ELEVATED"
    hunt_mode: bool = True
    honeypot_armed: bool = True
    pcr_drift: bool = False
    signing_halted: bool = False
    edge_fail_closed: bool = False
    kill_active: bool = False
    evolution_frozen: bool = False
    layers: list[dict[str, Any]] = field(default_factory=list)
    ts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_localhost_port(port_field: str) -> int | None:
    """Return int port for ':NNNN' style fields; None for non-socket layers."""
    if not port_field.startswith(":"):
        return None
    try:
        return int(port_field[1:])
    except ValueError:
        return None


def _probe_localhost(port: int, timeout_s: float = LAYER_PROBE_TIMEOUT_S) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout_s):
            return True
    except OSError:
        return False


class SecurityOps:
    """Impenetrable / Evasion / Stalking / Predatory control surface."""

    def __init__(self, safety_dir: Path | None = None) -> None:
        self.safety_dir = safety_dir or DEFAULT_SAFETY_DIR
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.honeypot_dir = self.safety_dir / HONEYPOT_DIR
        self.honeypot_dir.mkdir(parents=True, exist_ok=True)
        self._ks = KillSwitch(self.safety_dir)
        self._evo = EvolutionFreeze(self.safety_dir)

    def _armed_flag(self) -> Path:
        return self.honeypot_dir / HONEYPOT_ARMED

    def _disarmed_flag(self) -> Path:
        return self.honeypot_dir / HONEYPOT_DISARMED

    def honeypot_armed(self) -> bool:
        if self._disarmed_flag().exists():
            return False
        if self._armed_flag().exists():
            return True
        return True  # default armed until explicitly disarmed

    def honeypot_arm(self, operator: str = "SENTINEL") -> dict[str, Any]:
        dis = self._disarmed_flag()
        if dis.exists():
            dis.unlink()
        flag = self._armed_flag()
        flag.write_text(
            json.dumps({"armed_at": time.time(), "operator": operator}) + "\n",
            encoding="utf-8",
        )
        flag.chmod(0o600)
        return {"honeypot_armed": True, "operator": operator}

    def honeypot_disarm(self, operator: str = "SENTINEL") -> dict[str, Any]:
        armed = self._armed_flag()
        if armed.exists():
            armed.unlink()
        flag = self._disarmed_flag()
        flag.write_text(
            json.dumps({"disarmed_at": time.time(), "operator": operator}) + "\n",
            encoding="utf-8",
        )
        flag.chmod(0o600)
        return {"honeypot_armed": False, "operator": operator}

    def honeypot_status(self) -> dict[str, Any]:
        return {"honeypot_armed": self.honeypot_armed()}

    def signing_halted(self) -> bool:
        return (self.safety_dir / SIGNING_HALT_FLAG).exists()

    def edge_fail_closed(self) -> bool:
        return (self.safety_dir / EDGE_FAIL_CLOSED_FLAG).exists()

    def set_edge_fail_closed(self, operator: str, reason: str) -> dict[str, Any]:
        path = self.safety_dir / EDGE_FAIL_CLOSED_FLAG
        payload = {
            "armed": True,
            "operator": operator,
            "reason": reason,
            "ts": time.time(),
        }
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        path.chmod(0o600)
        return payload

    def herald_critical(self, operator: str, reason: str) -> dict[str, Any]:
        path = self.safety_dir / HERALD_QUEUE
        event = {
            "level": "CRITICAL",
            "event": "security_lockdown",
            "operator": operator,
            "reason": reason,
            "ts": time.time(),
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return event

    def pcr_drift(self) -> bool:
        """True only when an explicit PCR drift file exists under safety_dir."""
        return (self.safety_dir / PCR_DRIFT_FILE).exists()

    def set_signing_halt(self, halted: bool, operator: str, reason: str) -> None:
        path = self.safety_dir / SIGNING_HALT_FLAG
        if halted:
            path.write_text(
                json.dumps(
                    {
                        "halted_at": time.time(),
                        "operator": operator,
                        "reason": reason,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            path.chmod(0o600)
        elif path.exists():
            path.unlink()

    def layer_check(self, layer_id: str | None = None) -> dict[str, Any]:
        layers = []
        for layer in LAYERS:
            if layer_id and layer["id"] != layer_id:
                continue
            entry = {**layer}
            port_num = _parse_localhost_port(str(layer["port"]))
            if layer["id"] == "L2" and self.signing_halted():
                entry["status"] = "halted"
                entry["reachability"] = "halted"
            elif port_num is not None:
                up = _probe_localhost(port_num)
                entry["status"] = "UP" if up else "DOWN"
                entry["reachability"] = entry["status"]
            else:
                entry["status"] = "armed"
                entry["reachability"] = "n/a"
            if layer["id"] == "L4":
                entry["pcr_drift"] = self.pcr_drift()
            layers.append(entry)
        return {
            "layers": layers,
            "ok": all(
                l["status"] in ("armed", "halted", "UP", "DOWN") for l in layers
            ),
        }

    def status(self) -> dict[str, Any]:
        ks = self._ks.health()
        evo = self._evo.status()
        layers = self.layer_check()["layers"]
        kill_active = bool(ks.get("kill_switch_active") or ks.get("active"))
        posture = SecurityPosture(
            overall="LOCKDOWN" if kill_active else "HARDENED",
            threat_level="CRITICAL" if kill_active else "ELEVATED",
            hunt_mode=True,
            honeypot_armed=self.honeypot_armed(),
            pcr_drift=self.pcr_drift(),
            signing_halted=self.signing_halted(),
            edge_fail_closed=self.edge_fail_closed(),
            kill_active=kill_active,
            evolution_frozen=bool(evo.get("frozen")),
            layers=layers,
            ts=time.time(),
        )
        policy = self._load_policy_optional()
        out = posture.to_dict()
        out["pillars"] = {
            "impenetrable": "armed",
            "evasion": "active",
            "stalking": "hunt" if posture.hunt_mode else "idle",
            "predatory": "engaged" if posture.honeypot_armed else "idle",
        }
        out["ghost_evasion"] = stealth_posture(policy)
        out["predatory_ops"] = predatory_posture(
            hunt_mode=posture.hunt_mode,
            honeypot_armed=posture.honeypot_armed,
        )
        out["doctrine"] = "invisible_to_them_visible_to_us"
        out["refs"] = ["AEGIS", "FORTRESS", "GHOST", "MEV", "REAPER"]
        return out

    def _load_policy_optional(self) -> Any:
        try:
            from .policy_loader import expand_path, load_policy

            path = expand_path("~/.openclaw/risk_kernel/policy.yaml")
            if path.exists():
                return load_policy(path)
        except Exception:
            pass
        return None

    def _audit(self, event: dict[str, Any]) -> None:
        path = self.safety_dir / LOCKDOWN_AUDIT
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def lockdown(
        self,
        operator: str,
        reason: str,
        *,
        dry_run: bool = False,
        signed: str | None = None,
    ) -> dict[str, Any]:
        """Sequence: kill → evolution freeze → signing halt → honeypot arm."""
        if signed:
            ok, msg = self._ks.verify_signed_command(signed)
            if not ok:
                return {"error": msg, "ok": False}
            if msg not in ("HALT", "LOCKDOWN"):
                return {"error": f"unexpected command: {msg}", "ok": False}

        steps = [
            "kill_switch_activate",
            "evolution_freeze",
            "signing_halt",
            "honeypot_arm",
            "edge_fail_closed",
            "herald_critical",
        ]
        result: dict[str, Any] = {
            "ok": True,
            "dry_run": dry_run,
            "operator": operator,
            "reason": reason,
            "sequence": steps,
            "executed": [],
        }
        if dry_run:
            result["executed"] = [{"step": s, "status": "planned"} for s in steps]
            self._audit({**result, "ts": time.time()})
            return result

        state = self._ks.activate(operator, f"security lockdown: {reason}", flatten=True)
        result["executed"].append(
            {"step": "kill_switch_activate", "status": "ok", "state": state.to_dict()}
        )

        self._evo.freeze(operator, f"security lockdown: {reason}")
        result["executed"].append({"step": "evolution_freeze", "status": "ok"})

        self.set_signing_halt(True, operator, reason)
        result["executed"].append({"step": "signing_halt", "status": "ok"})

        hp = self.honeypot_arm(operator)
        result["executed"].append({"step": "honeypot_arm", "status": "ok", **hp})

        edge = self.set_edge_fail_closed(operator, reason)
        result["executed"].append({"step": "edge_fail_closed", "status": "ok", **edge})

        herald = self.herald_critical(operator, reason)
        result["executed"].append({"step": "herald_critical", "status": "ok", **herald})

        self._audit({**result, "ts": time.time()})
        (self.safety_dir / POSTURE_FILE).write_text(
            json.dumps(self.status(), indent=2) + "\n", encoding="utf-8"
        )
        return result
