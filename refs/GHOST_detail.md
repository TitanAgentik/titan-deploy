# §GHOST_detail.md — Evasion / OPSEC

> Ghost Protocol / structural invisibility. Runtime: TRENCH-OPS intents, edge mesh,
> adversarial harness under `tests/adversarial/`.

## Pillar: Evasion

Reduce detection surface and adversarial fingerprinting of TITAN execution.

### Controls

| ID | Control | Mode |
|----|---------|------|
| ev-1 | MEV-shielded intent solvers (no public RPC pool for DEX) | active |
| ev-2 | Edge RTT routing (lowest live p50 to target chain) | active |
| ev-3 | Nostr NIP-44 Kind 1059 edge dispatch | active |
| ev-4 | Hot wallet / session fingerprint rotation | scheduled |
| ev-5 | Traffic pattern obfuscation (jittered heartbeats, decoy probes) | active |
| ev-6 | Signing ceremony air-gap (Trezor Safe 7 / Mac Mini metadata) | active |

### Rules

- **Always on:** evasion controls active for all live DEX; stalking hunt_mode default; structural invisibility gate enforced at kernel + execution gate
- Structural invisibility gate: detection probability &lt;1% for stealth pipelines (SOUL)
- Live capital DENY on `public_rpc`, `public_mempool`, and unshielded CEX-direct venues (`STEALTH_PUBLIC_PATH`, `STEALTH_UNSHIELDED_VENUE`)
- Stealth pipelines (P22/P29/P12/P30) require pipeline-specific shielded routes (Jito, Flashbots, intent solvers)
- R44 Full-Spectrum Stealth (Ghost Protocol v2) — see TITAN.reconciled §GHOST
- Quantum dispatch DISABLED — classical-only (no quantum fingerprint channel)
- Never log raw seeds / session keys to agent memory

### Verification

```bash
titan-safety security status   # evasion section
# Edge health via Titan Agentik /edge or FORGE heartbeat
```

### See also

- `refs/MEV_detail.md`
- `tests/adversarial/adversarial_harness.py`
- TITAN.reconciled.md §GHOST.14–21
