"""Version-fingerprint audit binding with append-only hash chain."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VersionFingerprint:
    model_weights_hash: str
    lora_adapter_hash: str
    prompt_code_version: str
    soul_iron_laws_hash: str

    def composite_hash(self) -> str:
        payload = "|".join(
            [
                self.model_weights_hash,
                self.lora_adapter_hash,
                self.prompt_code_version,
                self.soul_iron_laws_hash,
            ]
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class DecisionLogEntry:
    decision_id: str
    agent_id: str
    action: str
    fingerprint: VersionFingerprint
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def content_hash(self) -> str:
        body = {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "fingerprint": self.fingerprint.to_dict(),
            "fingerprint_composite": self.fingerprint.composite_hash(),
            "payload": self.payload,
            "ts": self.ts,
        }
        canonical = json.dumps(body, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


class AuditChainWriter:
    """Append-only decision log with cryptographic hash chain."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.log_path.exists():
            return ""
        lines = [l for l in self.log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return ""
        return json.loads(lines[-1]).get("chain_hash", "")

    def append(self, entry: DecisionLogEntry) -> dict[str, Any]:
        content_hash = entry.content_hash()
        prev_hash = self._last_hash()
        chain_hash = hashlib.sha256(f"{prev_hash}|{content_hash}".encode()).hexdigest()
        record = {
            "ts": entry.ts,
            "decision_id": entry.decision_id,
            "agent_id": entry.agent_id,
            "action": entry.action,
            "fingerprint": entry.fingerprint.to_dict(),
            "fingerprint_composite": entry.fingerprint.composite_hash(),
            "payload": entry.payload,
            "content_hash": content_hash,
            "prev_hash": prev_hash,
            "chain_hash": chain_hash,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
        return record

    def verify(self) -> tuple[bool, str]:
        if not self.log_path.exists():
            return True, "empty log"
        prev_hash = ""
        for i, line in enumerate(self.log_path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                return False, f"JSON parse error at entry {i + 1}: {exc.msg}"
            stored_chain = record.pop("chain_hash")
            stored_prev = record.pop("prev_hash")
            content_hash = record.pop("content_hash")
            if stored_prev != prev_hash:
                return False, f"prev_hash mismatch at entry {i + 1}"
            body = {
                "decision_id": record["decision_id"],
                "agent_id": record["agent_id"],
                "action": record["action"],
                "fingerprint": record["fingerprint"],
                "fingerprint_composite": record["fingerprint_composite"],
                "payload": record["payload"],
                "ts": record["ts"],
            }
            expected_content = hashlib.sha256(
                json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
            ).hexdigest()
            if expected_content != content_hash:
                return False, f"content_hash mismatch at entry {i + 1}"
            expected_chain = hashlib.sha256(f"{prev_hash}|{content_hash}".encode()).hexdigest()
            if expected_chain != stored_chain:
                return False, f"chain_hash mismatch at entry {i + 1}"
            prev_hash = stored_chain
        return True, "decision log chain valid"


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_fingerprint(
    model_path: Path | None = None,
    lora_path: Path | None = None,
    prompt_version: str = "unknown",
    soul_path: Path | None = None,
) -> VersionFingerprint:
    return VersionFingerprint(
        model_weights_hash=hash_file(model_path) if model_path and model_path.exists() else "0" * 64,
        lora_adapter_hash=hash_file(lora_path) if lora_path and lora_path.exists() else "0" * 64,
        prompt_code_version=prompt_version,
        soul_iron_laws_hash=hash_file(soul_path) if soul_path and soul_path.exists() else "0" * 64,
    )
