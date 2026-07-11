"""Decision log lifecycle — rotation, corruption repair, memory-write validation.

Implements AGENTS.md circuit breakers:
- CB_DECISION_LOG_CORRUPT → repair from backup
- CB_DECISION_LOG_FULL → force rotation when resolved entries exceed cap
- CB_REFLECTION_DRIFT → disable pipeline for asset after systematic errors
- CB_CHECKPOINT_STALE → abandon checkpoint idle >1h
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .audit_chain import AuditChainWriter

DEFAULT_MAX_RESOLVED = 500
DEFAULT_REFLECTION_DRIFT_THRESHOLD = 5
DEFAULT_CHECKPOINT_STALE_SECONDS = 3600
RESOLVED_STATUSES = frozenset({"resolved", "rejected", "cancelled", "closed"})
PENDING_STATUSES = frozenset({"pending", "open", "in_progress", "checkpoint"})


@dataclass
class CircuitBreakerResult:
    triggered: bool
    code: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RotationResult:
    rotated: bool
    removed: int
    kept_resolved: int
    kept_pending: int
    total_before: int
    total_after: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepairResult:
    repaired: bool
    reason: str
    backup_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _entry_status(entry: dict[str, Any]) -> str:
    raw = entry.get("status")
    if raw is None and isinstance(entry.get("payload"), dict):
        raw = entry["payload"].get("status")
    return str(raw or "").strip().lower()


def is_pending(entry: dict[str, Any]) -> bool:
    status = _entry_status(entry)
    if status in PENDING_STATUSES:
        return True
    if status in RESOLVED_STATUSES:
        return False
    if entry.get("resolved") is True:
        return False
    if entry.get("resolved") is False:
        return True
    # Unknown status: treat as pending (fail-closed — never prune ambiguous rows)
    return True


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    """Load JSONL; return (records, error_message). Fail-closed on parse errors."""
    if not path.exists():
        return [], None
    records: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            return records, f"JSON parse error at line {i}: {exc.msg}"
    return records, None


def validate_memory_write(record: dict[str, Any]) -> tuple[bool, str]:
    """Enforce AGENTS.md memory write contract: ts + agent_id + rationale."""
    agent_id = record.get("agent_id")
    if not agent_id or not str(agent_id).strip():
        return False, "agent_id required on memory write"
    rationale = record.get("rationale")
    if rationale is None or not str(rationale).strip():
        return False, "rationale required on memory write"
    ts = record.get("ts", record.get("timestamp"))
    if ts is None:
        return False, "timestamp (ts) required on memory write"
    if isinstance(ts, (int, float)) and ts <= 0:
        return False, "timestamp must be positive"
    if isinstance(ts, str) and not ts.strip():
        return False, "timestamp must be non-empty ISO 8601 string"
    return True, "valid memory write"


def backup_path_for(log_path: Path) -> Path:
    return log_path.with_suffix(log_path.suffix + ".bak")


def write_backup(log_path: Path, dest: Path | None = None) -> Path:
    """Copy log to .bak sibling before destructive operations."""
    if not log_path.exists():
        raise FileNotFoundError(f"log not found: {log_path}")
    target = dest or backup_path_for(log_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(log_path, target)
    return target


def rotate_decision_log(
    log_path: Path,
    max_resolved: int = DEFAULT_MAX_RESOLVED,
    *,
    backup: bool = True,
) -> RotationResult:
    """Prune oldest resolved entries when resolved count exceeds max_resolved.

    Pending / ambiguous entries are never removed (fail-closed).
    """
    records, parse_err = load_jsonl(log_path)
    if parse_err:
        return RotationResult(
            rotated=False,
            removed=0,
            kept_resolved=0,
            kept_pending=0,
            total_before=len(records),
            total_after=len(records),
            message=f"rotation aborted: {parse_err}",
        )

    pending = [r for r in records if is_pending(r)]
    resolved = [r for r in records if not is_pending(r)]

    if len(resolved) <= max_resolved:
        return RotationResult(
            rotated=False,
            removed=0,
            kept_resolved=len(resolved),
            kept_pending=len(pending),
            total_before=len(records),
            total_after=len(records),
            message=f"within cap ({len(resolved)}/{max_resolved} resolved)",
        )

    excess = len(resolved) - max_resolved
    kept_resolved = resolved[excess:]
    removed = resolved[:excess]
    new_records = kept_resolved + pending

    if backup and log_path.exists():
        write_backup(log_path)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        for rec in new_records:
            f.write(json.dumps(rec, separators=(",", ":"), sort_keys=True) + "\n")

    return RotationResult(
        rotated=True,
        removed=len(removed),
        kept_resolved=len(kept_resolved),
        kept_pending=len(pending),
        total_before=len(records),
        total_after=len(new_records),
        message=f"removed {len(removed)} oldest resolved entries",
    )


def repair_decision_log(
    log_path: Path,
    backup_path: Path | None = None,
) -> RepairResult:
    """On corrupt log, restore from verified backup (CB_DECISION_LOG_CORRUPT)."""
    writer = AuditChainWriter(log_path)
    ok, msg = writer.verify()
    if ok:
        return RepairResult(repaired=False, reason="log valid, no repair needed")

    candidate = backup_path or backup_path_for(log_path)
    if not candidate.exists():
        return RepairResult(
            repaired=False,
            reason=f"corrupt log ({msg}); no backup at {candidate}",
        )

    bak_writer = AuditChainWriter(candidate)
    ok_bak, msg_bak = bak_writer.verify()
    if not ok_bak:
        return RepairResult(
            repaired=False,
            reason=f"corrupt log ({msg}); backup invalid ({msg_bak})",
            backup_path=str(candidate),
        )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate, log_path)
    return RepairResult(
        repaired=True,
        reason=f"restored from backup after: {msg}",
        backup_path=str(candidate),
    )


def ensure_decision_log_healthy(
    log_path: Path,
    max_resolved: int = DEFAULT_MAX_RESOLVED,
) -> dict[str, Any]:
    """Verify chain; repair from backup if corrupt; rotate if over cap."""
    writer = AuditChainWriter(log_path)
    ok, verify_msg = writer.verify()
    result: dict[str, Any] = {
        "ts": time.time(),
        "path": str(log_path),
        "verify_ok": ok,
        "verify_message": verify_msg,
    }
    if not ok:
        repair = repair_decision_log(log_path)
        result["repair"] = repair.to_dict()
        if not repair.repaired:
            result["healthy"] = False
            return result
        ok, verify_msg = AuditChainWriter(log_path).verify()
        result["verify_ok"] = ok
        result["verify_message"] = verify_msg
        if not ok:
            result["healthy"] = False
            return result

    rotation = rotate_decision_log(log_path, max_resolved=max_resolved)
    result["rotation"] = rotation.to_dict()
    result["healthy"] = True
    return result


def _reflection_alpha(entry: dict[str, Any]) -> float | None:
    reflection = entry.get("reflection")
    if not isinstance(reflection, dict):
        payload = entry.get("payload")
        if isinstance(payload, dict):
            reflection = payload.get("reflection")
    if not isinstance(reflection, dict):
        return None
    alpha = reflection.get("alpha_pct", reflection.get("alpha"))
    if alpha is None:
        return None
    try:
        return float(alpha)
    except (TypeError, ValueError):
        return None


def _entry_asset(entry: dict[str, Any]) -> str:
    for key in ("asset", "symbol"):
        val = entry.get(key)
        if val:
            return str(val).strip().upper()
    payload = entry.get("payload")
    if isinstance(payload, dict):
        for key in ("asset", "symbol"):
            val = payload.get(key)
            if val:
                return str(val).strip().upper()
    return ""


def check_reflection_drift(
    records: list[dict[str, Any]],
    *,
    asset: str | None = None,
    threshold: int = DEFAULT_REFLECTION_DRIFT_THRESHOLD,
    notable_alpha_pct: float = 5.0,
) -> CircuitBreakerResult:
    """CB_REFLECTION_DRIFT — >threshold same-asset reflections with notable error."""
    target = (asset or "").strip().upper()
    streak = 0
    for entry in reversed(records):
        entry_asset = _entry_asset(entry)
        if target and entry_asset != target:
            continue
        alpha = _reflection_alpha(entry)
        if alpha is None:
            break
        if abs(alpha) >= notable_alpha_pct:
            streak += 1
        else:
            break
    if streak >= threshold:
        return CircuitBreakerResult(
            triggered=True,
            code="CB_REFLECTION_DRIFT",
            message=(
                f"{streak} consecutive notable reflections for {target or 'asset'} "
                f"(threshold {threshold})"
            ),
            details={"asset": target, "streak": streak, "threshold": threshold},
        )
    return CircuitBreakerResult(
        triggered=False,
        code="CB_REFLECTION_DRIFT",
        message="within reflection drift threshold",
        details={"asset": target, "streak": streak, "threshold": threshold},
    )


def check_checkpoint_stale(
    checkpoint_path: Path,
    *,
    max_idle_seconds: float = DEFAULT_CHECKPOINT_STALE_SECONDS,
    now: float | None = None,
) -> CircuitBreakerResult:
    """CB_CHECKPOINT_STALE — abandon checkpoint when idle longer than max_idle_seconds."""
    ts_now = time.time() if now is None else float(now)
    if not checkpoint_path.exists():
        return CircuitBreakerResult(
            triggered=False,
            code="CB_CHECKPOINT_STALE",
            message="no checkpoint file",
            details={"path": str(checkpoint_path)},
        )
    try:
        raw = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return CircuitBreakerResult(
            triggered=True,
            code="CB_CHECKPOINT_STALE",
            message=f"checkpoint unreadable: {exc}",
            details={"path": str(checkpoint_path)},
        )
    if not isinstance(raw, dict):
        return CircuitBreakerResult(
            triggered=True,
            code="CB_CHECKPOINT_STALE",
            message="checkpoint payload not an object",
            details={"path": str(checkpoint_path)},
        )
    updated = raw.get("updated_at", raw.get("ts", raw.get("timestamp")))
    try:
        updated_ts = float(updated)
    except (TypeError, ValueError):
        return CircuitBreakerResult(
            triggered=True,
            code="CB_CHECKPOINT_STALE",
            message="checkpoint missing updated_at/ts",
            details={"path": str(checkpoint_path)},
        )
    idle = ts_now - updated_ts
    if idle > max_idle_seconds:
        return CircuitBreakerResult(
            triggered=True,
            code="CB_CHECKPOINT_STALE",
            message=f"checkpoint idle {idle:.0f}s > {max_idle_seconds:.0f}s",
            details={
                "path": str(checkpoint_path),
                "idle_seconds": idle,
                "max_idle_seconds": max_idle_seconds,
            },
        )
    return CircuitBreakerResult(
        triggered=False,
        code="CB_CHECKPOINT_STALE",
        message="checkpoint fresh",
        details={
            "path": str(checkpoint_path),
            "idle_seconds": idle,
            "max_idle_seconds": max_idle_seconds,
        },
    )
