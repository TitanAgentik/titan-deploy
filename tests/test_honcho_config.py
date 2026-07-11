"""Validate Honcho integration templates."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PROJECT_ROOT / "templates"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_honcho_json_template_exists() -> None:
    path = TEMPLATES / "honcho.json"
    assert path.exists(), "templates/honcho.json missing"


def test_honcho_json_required_keys() -> None:
    cfg = _load_json(TEMPLATES / "honcho.json")
    for key in (
        "peerName",
        "recallMode",
        "observationMode",
        "sessionStrategy",
        "pinUserPeer",
    ):
        assert key in cfg, f"honcho.json missing key: {key}"
    assert cfg["peerName"] == "hyperion"
    assert cfg["observationMode"] in ("directional", "unified")
    assert cfg["recallMode"] in ("hybrid", "context", "tools")


def test_honcho_json_profiles() -> None:
    cfg = _load_json(TEMPLATES / "honcho.json")
    profiles = cfg.get("profiles", {})
    assert "herald" in profiles
    assert "hyperion" in profiles
    assert profiles["herald"]["aiPeer"] == "herald-telegram"
    assert profiles["hyperion"]["aiPeer"] == "hyperion-assistant"


def test_config_yaml_honcho_provider() -> None:
    cfg = _load_yaml(TEMPLATES / "config.yaml")
    memory = cfg.get("memory", {})
    assert memory.get("provider") == "honcho"
    assert "honcho_config" in memory
    assert str(memory["honcho_config"]).endswith("honcho.json")


def test_openclaw_json_honcho_block() -> None:
    oc = _load_json(TEMPLATES / "openclaw.json")
    honcho = oc.get("honcho")
    assert honcho is not None
    assert honcho.get("enabled") is True
    assert honcho.get("operatorPeer") == "hyperion"
    agents = honcho.get("agentPeers", {})
    assert "HERALD" in agents
    assert "HYPERION" in agents
    gateway = honcho.get("gatewayIdentity", {})
    assert gateway.get("pinUserPeer") is True


def test_honcho_operator_skill_exists() -> None:
    skill = TEMPLATES / "skills" / "honcho_operator" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "honcho_profile" in text
    assert "directional" in text


def test_honcho_setup_guide_exists() -> None:
    guide = PROJECT_ROOT / "HONCHO_SETUP.md"
    assert guide.exists()
    text = guide.read_text(encoding="utf-8")
    assert "HONCHO_API_KEY" in text
    assert "observationMode" in text


def test_live_env_example_honcho_vars() -> None:
    env = (TEMPLATES / "infra" / "live.env.example").read_text(encoding="utf-8")
    for var in ("HONCHO_API_KEY", "HONCHO_BASE_URL", "HONCHO_PEER_NAME"):
        assert var in env, f"live.env.example missing {var}"


def test_honcho_json_valid_json() -> None:
    raw = (TEMPLATES / "honcho.json").read_text(encoding="utf-8")
    json.loads(raw)  # raises on invalid
