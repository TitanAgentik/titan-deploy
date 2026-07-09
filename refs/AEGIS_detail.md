# §AEGIS_detail.md — Impenetrable Defense

> Companion for OpenClaw + Hermes. Runtime truth: `risk_kernel/policy.yaml`,
> `infra/signing_node.yaml`, `titan_safety`, Cockpit `/security`.

## Pillar: Impenetrable

Defense-in-depth that agents cannot bypass. LLM votes are advisory; out-of-process
DENY is authoritative.

### Layers (L1–L6)

| ID | Layer | Endpoint | Failure mode |
|----|-------|----------|--------------|
| L1 | Risk kernel | `:19001` | Fail-closed DENY if unreachable |
| L2 | Signing node | `:19010` | Blind sign rejected; gate receipt required |
| L3 | Network namespace / policy engine | host netns | Egress blocked without policy allow |
| L4 | SENTINEL CodeQL + TPM PCR | Tier 2 | PCR drift → alert + hold |
| L5 | Dead-man's switch | `:19005` | 48h derisk / 72h flatten |
| L6 | Closed-model ban (live path) | policy | No Claude/GPT/Gemini on critical path |

### Circuit breakers

- `CB_TPM_PCR_DRIFT` — PCR mismatch vs baseline → halt new risk + CRITICAL
- `CB_KEYS_SIGNING_ENV_COMPROMISED` — signing env integrity fail → `SIGNING_HALTED`
- `CB_NETNS_POLICY_BYPASS` — attempted egress outside allowlist → kill pipeline
- `CB_RISK_KERNEL_UNREACHABLE` — fail-closed DENY all trades

### Operator commands

```bash
titan-safety security status
titan-safety security layer-check --layer L1
titan-safety gate check --trade-json …
curl -s http://127.0.0.1:19001/health
curl -s http://127.0.0.1:19010/health
```

### Operator note

**Mention ≠ mandate.** These companions describe optional capabilities. Enable Impenetrable baseline always; use Evasion / Stalking / Predatory modules only when threat model or strategy requires them. Do not run every control in this file by default.

## See also

- `refs/FORTRESS_detail.md` (perimeter)
- `refs/KEYS_detail.md` (signing ceremony)
- Skill: `sentinel_security`
- Playbook: `security_lockdown.yaml`
