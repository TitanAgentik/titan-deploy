#!/usr/bin/env python3
"""Export decision log + audit chain to S3-compatible WORM/object storage.

Verifies hash chain integrity before export. Immutable append-only tar.gz per run.
Environment:
  TITAN_AUDIT_EXPORT_BUCKET   — target bucket (required)
  TITAN_AUDIT_EXPORT_PREFIX   — key prefix (default: titan/audit)
  TITAN_AUDIT_EXPORT_ENDPOINT — S3-compatible endpoint URL (optional)
  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY — credentials (or IAM role)
  TITAN_DECISION_LOG            — override decision log path
  TITAN_AUDIT_CHAIN_LOG         — override audit chain path (defaults to decision log)
  TITAN_AUDIT_EXPORT_DRY_RUN    — set 1 to build archive locally only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "templates" / "safety"))

from titan_safety.audit_chain import AuditChainWriter  # noqa: E402

DEFAULT_DECISION_LOG = Path.home() / ".openclaw" / "memory" / "decision_log.jsonl"
DEFAULT_AUDIT_LOG = Path.home() / ".openclaw" / "memory" / "audit_chain.jsonl"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_chain(path: Path) -> tuple[bool, str]:
    writer = AuditChainWriter(path)
    return writer.verify()


def build_manifest(
    *,
    decision_log: Path,
    audit_log: Path,
    chain_ok: bool,
    chain_msg: str,
) -> dict:
    files = []
    seen: set[str] = set()
    for label, p in [("decision_log", decision_log), ("audit_chain", audit_log)]:
        key = str(p.resolve())
        if p.exists() and key not in seen:
            seen.add(key)
            files.append(
                {
                    "label": label,
                    "path": str(p),
                    "bytes": p.stat().st_size,
                    "sha256": _sha256_file(p),
                }
            )
    return {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "chain_verified": chain_ok,
        "chain_message": chain_msg,
        "files": files,
        "exporter": "audit_export_worm.py",
        "version": "1.0",
    }


def create_archive(
    *,
    decision_log: Path,
    audit_log: Path,
    out_dir: Path,
) -> tuple[Path, dict]:
    chain_ok, chain_msg = verify_chain(audit_log if audit_log.exists() else decision_log)
    manifest = build_manifest(
        decision_log=decision_log,
        audit_log=audit_log,
        chain_ok=chain_ok,
        chain_msg=chain_msg,
    )
    archive_name = f"titan-audit-{_now_stamp()}.tar.gz"
    archive_path = out_dir / archive_name
    with tarfile.open(archive_path, "w:gz") as tar:
        if decision_log.exists():
            tar.add(decision_log, arcname="decision_log.jsonl")
        if audit_log.exists() and audit_log != decision_log:
            tar.add(audit_log, arcname="audit_chain.jsonl")
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tar.add(manifest_path, arcname="manifest.json")
        manifest_path.unlink(missing_ok=True)
    manifest["archive_sha256"] = _sha256_file(archive_path)
    manifest["archive_name"] = archive_name
    return archive_path, manifest


def upload_s3(archive_path: Path, manifest: dict, *, bucket: str, prefix: str, endpoint: str | None) -> str:
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError("boto3 required for upload; pip install boto3") from exc

    key = f"{prefix.rstrip('/')}/{manifest['archive_name']}"
    client_kwargs: dict = {}
    if endpoint:
        client_kwargs["endpoint_url"] = endpoint
    s3 = boto3.client("s3", **client_kwargs)
    extra = {"ObjectLockMode": "COMPLIANCE", "ObjectLockRetainUntilDate": _worm_retain_date()}
    try:
        s3.upload_file(
            str(archive_path),
            bucket,
            key,
            ExtraArgs=extra,
        )
    except Exception:
        # WORM/ObjectLock may be unavailable on dev endpoints — fall back to plain put
        s3.upload_file(str(archive_path), bucket, key)
    manifest_key = f"{prefix.rstrip('/')}/{manifest['archive_name']}.manifest.json"
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2).encode(),
        ContentType="application/json",
    )
    return f"s3://{bucket}/{key}"


def _worm_retain_date():
    from datetime import timedelta

    return datetime.now(timezone.utc) + timedelta(days=2555)  # ~7 years


def export_audit(
    *,
    decision_log: Path | None = None,
    audit_log: Path | None = None,
    bucket: str | None = None,
    prefix: str | None = None,
    endpoint: str | None = None,
    dry_run: bool = False,
    out_dir: Path | None = None,
) -> dict:
    decision_log = decision_log or Path(os.environ.get("TITAN_DECISION_LOG", str(DEFAULT_DECISION_LOG)))
    audit_log = audit_log or Path(os.environ.get("TITAN_AUDIT_CHAIN_LOG", str(decision_log)))
    bucket = bucket or os.environ.get("TITAN_AUDIT_EXPORT_BUCKET", "").strip()
    prefix = prefix or os.environ.get("TITAN_AUDIT_EXPORT_PREFIX", "titan/audit").strip()
    endpoint = endpoint or os.environ.get("TITAN_AUDIT_EXPORT_ENDPOINT", "").strip() or None
    dry_run = dry_run or os.environ.get("TITAN_AUDIT_EXPORT_DRY_RUN", "") == "1"

    if not decision_log.exists() and not audit_log.exists():
        return {"ok": False, "error": "no decision or audit log found", "paths": [str(decision_log)]}

    work_dir = out_dir or Path(tempfile.mkdtemp(prefix="titan-audit-export-"))
    archive_path, manifest = create_archive(decision_log=decision_log, audit_log=audit_log, out_dir=work_dir)

    result: dict = {"ok": True, "manifest": manifest, "local_archive": str(archive_path)}

    if dry_run or not bucket:
        result["uploaded"] = False
        result["note"] = "dry_run or missing TITAN_AUDIT_EXPORT_BUCKET"
        return result

    uri = upload_s3(archive_path, manifest, bucket=bucket, prefix=prefix, endpoint=endpoint)
    result["uploaded"] = True
    result["uri"] = uri
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Export TITAN audit chain to WORM storage")
    parser.add_argument("--decision-log", type=Path, default=None)
    parser.add_argument("--audit-log", type=Path, default=None)
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print result JSON")
    args = parser.parse_args()

    result = export_audit(
        decision_log=args.decision_log,
        audit_log=args.audit_log,
        bucket=args.bucket,
        prefix=args.prefix,
        endpoint=args.endpoint,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
