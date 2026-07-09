# §AU_audit.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `AU_audit.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Audit / decision-log pointers for TITAN safety services.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Append-only logs (runtime)

| Log | Path |
|-----|------|
| Promotion audit | `~/.openclaw/safety/promotion_audit.jsonl` |
| Capital audit | `~/.openclaw/capital/capital_audit.jsonl` |
| Signing audit | `~/.openclaw/safety/signing_audit.jsonl` |
| Defund ledger | `~/.openclaw/safety/defund_ledger.jsonl` |
| Decision hash chain | `titan_safety.audit_chain` |

## Verify

```bash
titan-safety promotion verify-audit
titan-safety capital audit  # if exposed
```

Constitutional blocks prevent agents from rewriting `risk_kernel/` or `SOUL.md`.
