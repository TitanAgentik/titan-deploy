"""Dead-man's switch daemon service."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from .dead_mans_switch import DeadMansConfig, DeadMansSwitch
from .flatten_executor import FlattenExecutor
from .http_server import SafetyHTTPServer
from .kill_switch import KillSwitch
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy
from .risk_kernel_service import create_app as create_kernel_app
from .wind_down import WindDownController

logger = setup_logging("dead_mans_switch")


class DeadMansDaemon:
    def __init__(
        self,
        dms: DeadMansSwitch,
        policy_path: Path,
        safety_dir: Path,
        poll_seconds: float = 60.0,
    ) -> None:
        self.dms = dms
        self.policy_path = policy_path
        self.safety_dir = safety_dir
        self.poll_seconds = poll_seconds
        self.ks = KillSwitch(safety_dir)
        self.wind_down = WindDownController(safety_dir)
        self.flatten_exec = FlattenExecutor(safety_dir)

    def tick(self) -> dict[str, Any]:
        result = self.dms.evaluate()
        METRICS.set_gauge("dms_hours_since_heartbeat", result["hours_since_heartbeat"])
        if result["action"] == "derisk":
            METRICS.inc("dms_derisk_total")
            logger.warning("Dead-man's switch: DERISK triggered — entering wind-down")
            self.wind_down.start_derisk(
                "dead_mans_switch",
                f"operator heartbeat missed ({result.get('hours_since_heartbeat')}h)",
            )
            result["wind_down"] = self.wind_down.load_state().to_dict()
        elif result["action"] == "flatten":
            METRICS.inc("dms_flatten_total")
            logger.critical("Dead-man's switch: FLATTEN triggered")
            self.ks.activate("dead_mans_switch", "operator heartbeat exceeded 72h", flatten=True)
            self.wind_down.start_flatten(
                "dead_mans_switch",
                "operator heartbeat exceeded flatten threshold",
            )
            try:
                _server, kernel = create_kernel_app(
                    self.policy_path,
                    self.safety_dir / "kernel_state.json",
                    self.safety_dir,
                )
                flatten_out = self.flatten_exec.execute(
                    kernel,
                    operator="dead_mans_switch",
                    reason="dms_flatten",
                    revoke_keys=True,
                )
                result["flatten_executor"] = flatten_out
            except Exception as exc:
                logger.error(f"Failed to trigger kernel flatten: {exc}")
            result["wind_down"] = self.wind_down.load_state().to_dict()
        return result

    def run_loop(self) -> None:
        while True:
            self.tick()
            time.sleep(self.poll_seconds)


def create_health_server(dms: DeadMansSwitch, port: int) -> SafetyHTTPServer:
    def heartbeat(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        operator = str(body.get("operator", "operator"))
        state = dms.heartbeat(operator)
        METRICS.inc("dms_heartbeat_total")
        return 200, state.to_dict()

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, dms.health()

    routes = {
        "POST /v1/heartbeat": heartbeat,
        "GET /health": health,
        "GET /metrics": lambda _b, _h: (200, METRICS.to_json()),
    }
    return SafetyHTTPServer(
        "127.0.0.1",
        port,
        routes,
        auth_commands={"POST /v1/heartbeat": "HEARTBEAT"},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Dead-Man's Switch Daemon")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    parser.add_argument("--poll", type=float, default=60.0)
    args = parser.parse_args(argv)

    policy_path = expand_path(args.policy)
    policy = load_policy(policy_path)
    dms_cfg = policy.raw.get("dead_mans_switch", {})
    dms = DeadMansSwitch(
        DeadMansConfig(
            operator_heartbeat_hours=float(dms_cfg.get("operator_heartbeat_hours", 48)),
            flatten_after_hours=float(dms_cfg.get("flatten_after_hours", 72)),
            never_auto_promote=bool(dms_cfg.get("never_auto_promote", True)),
        )
    )
    safety_dir = Path.home() / ".openclaw" / "safety"
    daemon = DeadMansDaemon(dms, policy_path, safety_dir, args.poll)

    health_server = create_health_server(dms, policy.service.dead_mans_switch_port)
    health_server.start(background=True)
    logger.info(
        f"Dead-man's switch health on 127.0.0.1:{policy.service.dead_mans_switch_port}"
    )
    daemon.run_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
