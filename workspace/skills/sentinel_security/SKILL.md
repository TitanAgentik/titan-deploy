---
name: sentinel_security
description: SENTINEL four-pillar security — Impenetrable layers, PCR/CodeQL, honeypot arm, lockdown sequencing
metadata:
  openclaw:
    status: live
  skill_tuple:
    intent: sentinel_security
    method: audit_harden_lockdown
    difficulty: high
  agent: SENTINEL
  tier: "2"
  model: ":30001"
---

# Sentinel Security

Owner: **SENTINEL** (Tier 2 `:30001`). Dual-sign with GUARDIAN for `memory/security/` writes.

## Pillars owned

| Pillar | Responsibility |
|--------|----------------|
| Impenetrable | L1–L6 integrity checks, CodeQL, PCR drift, netns audit |
| Predatory (shared) | Honeypot lattice arm/disarm, lockdown sequencing |
| Stalking (shared) | Quarantine phishing / escalate high-severity stalks |

## Tools / CLI

```bash
titan-safety security status
titan-safety security layer-check [--layer L1|L2|…]
titan-safety security honeypot arm|disarm|status
titan-safety security lockdown --operator ID --reason "…" [--dry-run] [--signed …]
```

## Heartbeat (5m)

1. CodeQL / dissent queue scan  
2. TPM PCR vs `signing_node.yaml` baseline  
3. Honeypot tripwire poll (`~/.openclaw/safety/honeypots/`)  
4. Append posture line to `memory/security/posture.jsonl` (dual-sign)

## Lockdown (HMAC required)

Sequence: kill ACTIVE → evolution FREEZE → SIGNING_HALTED → honeypots ARMED → edge fail-closed → HERALD CRITICAL.

Never auto-lockdown from LLM alone — operator HMAC or signed CLI.

## Output schema

```json
{
  "agent": "SENTINEL",
  "pillar": "impenetrable|predatory",
  "posture": "HARDENED|DEGRADED|BREACH",
  "layers": [{"id": "L1", "status": "armed|fault"}],
  "pcr_drift": false,
  "honeypot_armed": true,
  "confidence": 0.0,
  "ts": "ISO-8601"
}
```

## Refs

- `refs/AEGIS_detail.md`, `refs/FORTRESS_detail.md`, `refs/REAPER_detail.md`
- `risk_kernel/policy.yaml` → `security_ops`
- Playbook: `playbooks/security_lockdown.yaml`
