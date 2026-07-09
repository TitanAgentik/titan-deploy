"""Live signer / flatten adapter wiring — mock ban + pluggable components."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from titan_safety.flatten_executor import (
    FlattenExecutor,
    MockPositionCloser,
    SigningNodeCloser,
    validate_flatten_config_for_live,
)
from titan_safety.policy_loader import load_component, load_policy
from titan_safety.signing_service import create_app as create_signing_app
from titan_safety.signing_service import mock_signer


def _write_policy(tmp_path: Path, **overrides) -> Path:
    data = {
        "version": "2.0",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 10000},
        "allowed_venues": ["paper"],
        "reconciliation": {"adapter": "mock", "divergence_threshold_usd": 10.0},
        "service": {"signing_node_port": 19010},
    }
    data.update(overrides)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_load_component_valid() -> None:
    fn = load_component("titan_safety.signing_service:mock_signer")
    assert fn is mock_signer


def test_load_component_bad_spec() -> None:
    with pytest.raises(ValueError, match="module.path:attr"):
        load_component("no_colon_here")
    with pytest.raises(ValueError, match="no attribute"):
        load_component("titan_safety.signing_service:does_not_exist")


def test_signing_live_profile_refuses_mock_signer(tmp_path: Path) -> None:
    policy_path = _write_policy(tmp_path, capital_profile="live")
    with pytest.raises(ValueError, match="mock signer banned"):
        create_signing_app(policy_path, safety_dir=tmp_path)


def test_signing_live_profile_starts_with_signer_module(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path,
        capital_profile="live",
        signing={"signer_module": "titan_safety.signing_service:mock_signer"},
    )
    server = create_signing_app(policy_path, safety_dir=tmp_path)
    assert server is not None


def test_signing_paper_profile_allows_default_mock(tmp_path: Path) -> None:
    policy_path = _write_policy(tmp_path, capital_profile="paper")
    server = create_signing_app(policy_path, safety_dir=tmp_path)
    assert server is not None


def test_flatten_live_refuses_mock_closer(tmp_path: Path) -> None:
    policy = load_policy(_write_policy(tmp_path, capital_profile="live"))
    with pytest.raises(ValueError, match="mock closer banned"):
        validate_flatten_config_for_live(policy)


def test_flatten_live_refuses_mock_revoker(tmp_path: Path) -> None:
    policy = load_policy(
        _write_policy(
            tmp_path,
            capital_profile="live",
            flatten={"closer": "signing_node"},
        )
    )
    with pytest.raises(ValueError, match="mock revoker banned"):
        validate_flatten_config_for_live(policy)


def test_flatten_paper_allows_mock(tmp_path: Path) -> None:
    policy = load_policy(_write_policy(tmp_path, capital_profile="paper"))
    validate_flatten_config_for_live(policy)  # no raise


def test_flatten_from_policy_builds_signing_node_closer(tmp_path: Path) -> None:
    policy = load_policy(
        _write_policy(
            tmp_path,
            flatten={"closer": "signing_node", "signing_endpoint": "http://127.0.0.1:19010"},
        )
    )
    executor = FlattenExecutor.from_policy(policy, tmp_path)
    assert isinstance(executor.closer, SigningNodeCloser)


def test_flatten_from_policy_defaults_to_mock(tmp_path: Path) -> None:
    policy = load_policy(_write_policy(tmp_path))
    executor = FlattenExecutor.from_policy(policy, tmp_path)
    assert isinstance(executor.closer, MockPositionCloser)
