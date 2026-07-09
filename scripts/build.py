#!/usr/bin/env python3
"""Main build orchestrator for TITAN deploy bundle."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
OUTPUT = PROJECT_ROOT / "output"
TEMPLATES = PROJECT_ROOT / "templates"


def run_script(name: str, *args: str) -> None:
    cmd = [sys.executable, str(SCRIPTS / name), *args]
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def copy_templates() -> None:
    shutil.copy(TEMPLATES / "openclaw.json", OUTPUT / "openclaw.json")
    shutil.copy(TEMPLATES / "config.yaml", OUTPUT / "config.yaml")
    systemd_out = OUTPUT / "systemd"
    systemd_out.mkdir(parents=True, exist_ok=True)
    for svc in (TEMPLATES / "systemd").glob("*.service"):
        shutil.copy(svc, systemd_out / svc.name)
    # Infra specs (power, signing, GPU schedule)
    infra_src = TEMPLATES / "infra"
    if infra_src.exists():
        infra_dest = OUTPUT / "infra"
        infra_dest.mkdir(parents=True, exist_ok=True)
        for f in infra_src.iterdir():
            if f.is_file():
                shutil.copy(f, infra_dest / f.name)
        print(f"Copied infra specs -> {infra_dest}")
    # Risk kernel policy
    rk_src = TEMPLATES / "risk_kernel"
    if rk_src.exists():
        rk_dest = OUTPUT / "risk_kernel"
        rk_dest.mkdir(parents=True, exist_ok=True)
        for f in rk_src.iterdir():
            if f.is_file():
                shutil.copy(f, rk_dest / f.name)
        print(f"Copied risk_kernel -> {rk_dest}")
    copy_safety_package()
    copy_playbooks()
    copy_capital_stubs()


def copy_playbooks() -> None:
    src = TEMPLATES / "playbooks"
    if not src.exists():
        return
    dest = OUTPUT / "playbooks"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"Copied playbooks -> {dest}")


def copy_capital_stubs() -> None:
    src = TEMPLATES / "capital"
    if not src.exists():
        return
    dest = OUTPUT / "capital"
    dest.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file():
            shutil.copy(f, dest / f.name)
    print(f"Copied capital stubs -> {dest}")


def copy_safety_package() -> None:
    """Copy out-of-process safety services (deterministic risk kernel, etc.)."""
    src = TEMPLATES / "safety"
    if not src.exists():
        return
    dest = OUTPUT / "safety"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    # Ship requirements alongside safety bundle
    req = PROJECT_ROOT / "requirements.txt"
    if req.exists():
        shutil.copy(req, dest / "requirements.txt")
    print(f"Copied safety package -> {dest}")


def copy_telegram_assets() -> None:
    """Copy institutional Telegram templates to output/workspace/telegram/."""
    src = TEMPLATES / "telegram"
    if not src.exists():
        return
    dest = OUTPUT / "workspace" / "telegram"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"Copied telegram assets -> {dest}")


def overlay_herald_skill() -> None:
    """Replace stub herald_notify with full institutional skill."""
    src = TEMPLATES / "skills" / "herald_notify"
    if not src.exists():
        return
    dest = OUTPUT / "workspace" / "skills" / "herald_notify"
    dest.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file():
            shutil.copy(f, dest / f.name)
    print(f"Overlay herald_notify skill -> {dest}")


def overlay_infra_skills() -> None:
    """Overlay infra-related skill stubs with advisory content."""
    for skill_name in ("trench_ops_execution", "forge_infra"):
        src = TEMPLATES / "skills" / skill_name
        if not src.exists():
            continue
        dest = OUTPUT / "workspace" / "skills" / skill_name
        dest.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                shutil.copy(f, dest / f.name)
        print(f"Overlay {skill_name} skill -> {dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build TITAN deploy bundle")
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "source" / "TITAN.md",
        help="Source TITAN.md path",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"ERROR: source not found: {args.source}", file=sys.stderr)
        return 1

    OUTPUT.mkdir(parents=True, exist_ok=True)

    run_script("normalize.py", str(args.source))
    run_script("reconcile.py")
    run_script("extract_bootstrap.py")
    run_script("extract_skills.py")
    run_script("extract_memory.py")
    copy_templates()
    copy_telegram_assets()
    overlay_herald_skill()
    overlay_infra_skills()

    print(f"\nBuild complete -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
