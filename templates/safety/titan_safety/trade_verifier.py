"""Agent authorization for autonomous sign/verify — replaces human approval on trade path.

Safe defaults:
  - confidence gate (≥0.50 reduced, ≥0.70 full size)
  - 2-of-3 BFT advisory votes (AUGUR/PREDATOR/ATLAS) above equity threshold
  - risk kernel + gate receipt still mandatory (signing node enforces)
  - blind-sign rejected on live venues (typed_data or calldata required)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .auth import ensure_control_secret
from .kernel import TradeRequest


VOTE_PREFIX = "BFT_VOTE"
DEFAULT_VOTERS = ("AUGUR", "PREDATOR", "ATLAS")


@dataclass
class VerificationResult:
    ok: bool
    reason: str
    code: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "code": self.code,
            "details": self.details,
        }


def autonomous_signing_cfg(policy_raw: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enabled": True,
        "min_confidence_reduced": 0.50,
        "min_confidence_full": 0.70,
        "bft_required_above_equity_pct": 1.0,
        "bft_voters": list(DEFAULT_VOTERS),
        "bft_threshold": 2,
        "require_typed_data_live": True,
        "paper_min_confidence": 0.30,
    }
    cfg = dict(defaults)
    cfg.update((policy_raw or {}).get("autonomous_signing") or {})
    return cfg


def _vote_payload(voter: str, trade_id: str, decision: str, confidence: float, ts: int) -> str:
    return f"{VOTE_PREFIX}|{voter}|{trade_id}|{decision.upper()}|{confidence:.4f}|{ts}"


def sign_bft_vote(
    voter: str,
    trade_id: str,
    decision: str,
    confidence: float,
    safety_dir: Path | None = None,
    ts: int | None = None,
) -> dict[str, Any]:
    """Issue an HMAC-signed BFT vote blob for TRENCH-OPS to attach to trades."""
    timestamp = int(time.time()) if ts is None else int(ts)
    secret = ensure_control_secret(safety_dir)
    payload = _vote_payload(voter, trade_id, decision, confidence, timestamp)
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return {
        "voter": voter.upper(),
        "trade_id": trade_id,
        "decision": decision.upper(),
        "confidence": confidence,
        "ts": timestamp,
        "token": f"{payload}|{sig}",
    }


def verify_bft_vote(vote: dict[str, Any], safety_dir: Path | None = None) -> tuple[bool, str]:
    token = str(vote.get("token") or "").strip()
    if not token:
        return False, "missing vote token"
    parts = token.split("|")
    if len(parts) != 7 or parts[0] != VOTE_PREFIX:
        return False, "malformed vote token"
    voter, trade_id, decision, conf_s, ts_s, sig = (
        parts[1],
        parts[2],
        parts[3],
        parts[4],
        parts[5],
        parts[6],
    )
    payload = "|".join(parts[:6])
    secret = ensure_control_secret(safety_dir)
    expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "invalid vote signature"
    if decision != "ALLOW":
        return False, f"vote DENY from {voter}"
    age = time.time() - int(ts_s)
    if age > 300 or age < -30:
        return False, "vote expired"
    if vote.get("voter") and str(vote.get("voter")).upper() != voter.upper():
        return False, "voter mismatch"
    return True, "ok"


def verify_agent_authorization(
    trade: TradeRequest,
    policy_raw: dict[str, Any],
    equity_usd: float,
    safety_dir: Path | None = None,
) -> VerificationResult:
    """Deterministic agent verification — no human in the loop."""
    cfg = autonomous_signing_cfg(policy_raw)
    if not cfg.get("enabled", True):
        return VerificationResult(
            ok=False,
            reason="autonomous_signing disabled — human approval required",
            code="AUTONOMOUS_SIGNING_OFF",
        )

    pct = (abs(trade.notional_usd) / equity_usd * 100.0) if equity_usd else 100.0
    is_paper = trade.venue.lower() == "paper"
    confidence = float(trade.confidence or 0.0)

    min_reduced = float(cfg["min_confidence_reduced"])
    min_full = float(cfg["min_confidence_full"])
    paper_min = float(cfg.get("paper_min_confidence", 0.30))

    max_pct = float(
        (policy_raw.get("position_limits") or {}).get("max_equity_pct_per_trade", 2.0)
    )
    if is_paper:
        required_conf = paper_min
    else:
        needs_full_conf = pct >= max_pct * 0.5 or pct > 0.5
        required_conf = min_full if needs_full_conf else min_reduced

    if confidence < required_conf:
        return VerificationResult(
            ok=False,
            reason=f"confidence {confidence:.2f} below required {required_conf:.2f}",
            code="CONFIDENCE_TOO_LOW",
            details={"confidence": confidence, "required": required_conf, "pct_equity": pct},
        )

    bft_pct = float(cfg.get("bft_required_above_equity_pct", 1.0))
    if not is_paper and pct > bft_pct:
        voters = [str(v).upper() for v in cfg.get("bft_voters", DEFAULT_VOTERS)]
        threshold = int(cfg.get("bft_threshold", 2))
        votes = trade.bft_votes or []
        allow_voters: set[str] = set()
        for v in votes:
            ok, msg = verify_bft_vote(v, safety_dir)
            if not ok:
                continue
            voter = str(v.get("voter", "")).upper()
            if voter in voters and v.get("trade_id") == trade.trade_id:
                allow_voters.add(voter)
        if len(allow_voters) < threshold:
            return VerificationResult(
                ok=False,
                reason=(
                    f"BFT {len(allow_voters)}/{threshold} ALLOW votes "
                    f"(need {threshold}-of-{len(voters)} above {bft_pct}% equity)"
                ),
                code="BFT_INSUFFICIENT",
                details={
                    "allow_voters": sorted(allow_voters),
                    "required": threshold,
                    "pct_equity": pct,
                },
            )

    return VerificationResult(
        ok=True,
        reason="agent verified (confidence + BFT)",
        code="AGENT_VERIFIED",
        details={"confidence": confidence, "pct_equity": pct, "paper": is_paper},
    )


def verify_sign_payload(
    trade: TradeRequest,
    body: dict[str, Any],
    policy_raw: dict[str, Any],
) -> tuple[bool, str]:
    """Reject blind-sign on live venues; enforce session envelope."""
    cfg = autonomous_signing_cfg(policy_raw)
    if trade.venue.lower() == "paper":
        return True, "paper lane"
    if not cfg.get("require_typed_data_live", True):
        if body.get("typed_data") or body.get("calldata"):
            return True, "calldata present"
        return False, "BLIND_SIGN_REJECTED — typed_data or calldata required on live venues"

    typed_data = body.get("typed_data")
    calldata = body.get("calldata")
    if not typed_data and not calldata:
        return False, "BLIND_SIGN_REJECTED — typed_data or calldata required on live venues"

    ok_env, env_reason = _check_session_envelope(trade, body, policy_raw)
    if not ok_env:
        return False, env_reason

    return True, "calldata present"


def compute_payload_hash(body: dict[str, Any]) -> str:
    """Deterministic SHA-256 over calldata + typed_data for receipt binding."""
    material = {
        "calldata": body.get("calldata"),
        "typed_data": body.get("typed_data"),
        "reduce_only": body.get("reduce_only", False),
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_receipt_payload_binding(
    receipt_token: str,
    trade: TradeRequest,
    body: dict[str, Any],
    policy_raw: dict[str, Any],
) -> tuple[bool, str]:
    """Verify receipt payload_hash field matches body calldata/typed_data."""
    tier0 = (policy_raw or {}).get("tier0_money_path") or {}
    if not tier0.get("require_payload_hash_binding", True):
        return True, "binding not required"
    if trade.venue.lower() == "paper":
        return True, "paper lane"

    parts = receipt_token.strip().split("|")
    if len(parts) == 8:
        return True, "legacy receipt without payload hash"
    if len(parts) != 9:
        return False, "malformed receipt for payload binding"

    receipt_hash = parts[7]
    if not receipt_hash:
        # Gate-time receipt without hash — require hash at submit via body
        body_hash = compute_payload_hash(body)
        if not body.get("calldata") and not body.get("typed_data"):
            return False, "payload hash binding required but no calldata"
        return True, "ok"

    expected = compute_payload_hash(body)
    if not hmac.compare_digest(receipt_hash, expected):
        return False, "payload hash mismatch — calldata does not match gate receipt"
    return True, "ok"


def _check_session_envelope(
    trade: TradeRequest,
    body: dict[str, Any],
    policy_raw: dict[str, Any],
) -> tuple[bool, str]:
    """Hot-path session keys may only sign within pre-approved notional envelopes."""
    tier0 = (policy_raw or {}).get("tier0_money_path") or {}
    envelope = tier0.get("session_envelope") or {}
    if not envelope.get("enabled", False):
        return True, "envelope not enabled"

    max_notional = float(envelope.get("max_notional_usd", 0) or 0)
    if max_notional > 0 and abs(trade.notional_usd) > max_notional:
        return (
            False,
            f"SESSION_ENVELOPE_EXCEEDED — {trade.notional_usd:.2f} > {max_notional:.2f} USD",
        )

    allowed_venues = {str(v).lower() for v in envelope.get("allowed_venues", [])}
    if allowed_venues and trade.venue.lower() not in allowed_venues:
        return False, f"venue {trade.venue!r} outside session envelope"

    if envelope.get("require_typed_data", True) and not body.get("typed_data"):
        return False, "session envelope requires typed_data"

    return True, "ok"
