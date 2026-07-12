# Runbook — Host Compromise Suspected

> **Severity:** CRITICAL  
> **Agents:** SENTINEL, FORGE, GUARDIAN  
> **Principle:** Assume signing keys and control-plane secrets are exposed until proven otherwise.

## Detection signals

- Unexpected `security_ops` posture change on `:19008`
- SENTINEL CodeQL / PCR drift alerts
- Unauthorized `titan-safety gate sign` in audit chain
- Novel outbound connections from agent UID
- BusKill triggered (physical disconnect)

## Immediate actions (0–2 min)

1. **BusKill** if installed — yank cable; host locks.
2. Software kill: `titan-safety kill activate --operator YOU --reason "compromise suspected"`
3. **Revoke signing:** key revoke path per `flatten_executor` / `LiveKeyRevoker`
4. Isolate network: disconnect Ethernet or security group deny-all (cloud edges unaffected).

## Containment (2–30 min)

```bash
# Verify signing halted
curl -s http://127.0.0.1:19008/v1/status | jq .signing_halted

# Export audit chain BEFORE wipe (off-host WORM)
TITAN_AUDIT_EXPORT_DRY_RUN=1 python3 scripts/audit_export_worm.py --dry-run
# Then upload with bucket configured
```

5. Do **not** restart agents on compromised host for "quick fix."
6. Snapshot disk for forensics if legal counsel advises; otherwise wipe.

## Recovery (clean host)

1. Reimage TITANHOME from known-good baseline (`scripts/titanhome-postinstall.sh`).
2. Rotate **all** secrets: Telegram, NATS, RPC, API keys — never copy from old host.
3. Restore `policy.yaml` from git; Trezor ceremonies for signing metadata on Mac Mini vault.
4. `./verify.sh` must pass; reconciliation clean; Phase 5 not auto-restored.
5. Post-incident: update `docs/AGENT_HOST_SECURITY.md` capability audit.

## What agents cannot do

- Agents **never** override kernel DENY.
- LLM runtime cannot read signing material (see FS isolation doc).

## References

- `docs/AGENT_HOST_SECURITY.md`
- `templates/playbooks/security_lockdown.yaml`
