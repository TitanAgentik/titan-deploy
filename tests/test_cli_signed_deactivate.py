"""CLI: deactivate requires signed RESUME."""

from __future__ import annotations

import json
from pathlib import Path

from titan_safety.cli import main
from titan_safety.kill_switch import KillSwitch


def test_deactivate_requires_signed(tmp_path: Path, capsys) -> None:
    ks = KillSwitch(tmp_path)
    ks.activate("op", "test")
    rc = main(["--safety-dir", str(tmp_path), "kill", "deactivate", "--operator", "op"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert "signed RESUME required" in out["error"]
    assert ks.is_active()


def test_deactivate_with_signed_resume(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    ks.activate("op", "test")
    signed = ks.sign_command("RESUME", "op")
    rc = main(
        [
            "--safety-dir",
            str(tmp_path),
            "kill",
            "deactivate",
            "--operator",
            "op",
            "--signed",
            signed,
        ]
    )
    assert rc == 0
    assert not ks.is_active()
