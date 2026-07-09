# Security Posture — Stealth + Predatory (Always On)

> Doctrine: **invisible to them, visible to us.** Detect adversaries; profit from their mistakes via shielded execution only.

## Four pillars (default armed)

| Pillar | Owner | Posture |
|--------|-------|---------|
| Impenetrable | SENTINEL | L1–L6 layers armed |
| Evasion | TRENCH-OPS | Ghost — MEV-shield, edge RTT, Nostr, fingerprint rotate |
| Stalking | PREDATOR | hunt_mode — mempool, copy-trade, RPC probes |
| Predatory | PREDATOR | honeypot lattice engaged; poison fills ≤1% equity auto |

## Runtime enforcement

- Policy: `risk_kernel/policy.yaml` → `ghost_evasion` + `security_ops`
- Infra: `infra/ghost_evasion.yaml`
- Gate: execution_gate stage `stealth_evasion` + kernel `STEALTH_*` codes
- CLI: `titan-safety security status`

## Live capital rules (iron-laws §15)

- DENY `public_rpc`, `public_mempool`, unshielded CEX-direct
- Live DEX must use shielded venues (Jito, Flashbots, intent solvers, etc.)
- Stealth pipelines P22/P29/P12/P30 require pipeline-specific routes

## CBs

- `CB_STEALTH_PUBLIC_PATH` · `CB_STEALTH_UNSHIELDED_VENUE`
- `CB_STALK_SEVERITY_HIGH` · `CB_DARKINT_HONEYPOT` · `CB_HYDRA_HONEYPOT`

Refs: `refs/GHOST_detail.md`, `refs/REAPER_detail.md`, `refs/MEV_detail.md`
Skills: `predator_scanner`, `sentinel_security`
