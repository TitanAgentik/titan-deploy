# §REAPER_detail.md — Predatory Countermeasures & Kill-Chain

> Offensive security posture: honeypots, Red Team, counter-copy, lockdown sequencing.

## Pillar: Predatory

| Module | Agent | Posture |
|--------|-------|---------|
| PREDATOR sniper / mempool | PREDATOR | hunt |
| Honeypot wallet lattice | SENTINEL | lure |
| Red Team gauntlet | ARBITER | simulate |
| Graph-R1 fraud hypergraph | GUARDIAN | isolate |
| Counter-copy poison fills | TRENCH-OPS | disrupt (&lt;1% equity auto) |
| Kill-chain auto-response | ARCHON | contain (HMAC for full lockdown) |

## Stalking feed (PREDATOR)

Track and classify — do not auto-engage capital &gt;1% without YES:

- Mempool sandwich / predator clusters
- RPC fingerprint probes on signing/health endpoints
- Competitor copy-trade wallets (lag 180–400ms)
- Telegram phishing lures (HERALD quarantine)

## Lockdown sequence (operator HMAC)

1. Global kill switch ACTIVE  
2. Evolution FREEZE (shadow-only)  
3. Signing node SIGNING_HALTED  
4. Honeypot lattice ARMED  
5. Edge routing fail-closed to known-good PoPs  
6. HERALD CRITICAL alert  

```bash
titan-safety security lockdown --operator YOU --reason "…"
# or dry-run:
titan-safety security lockdown --dry-run --operator YOU --reason "drill"
```

## Circuit breakers

- `CB_DARKINT_HONEYPOT` / `CB_HYDRA_HONEYPOT` — tripwire touch → CRITICAL + optional pipeline halt
- `CB_STALK_SEVERITY_HIGH` — escalate to ARCHON + operator
- `CB_SECURITY_LOCKDOWN` — full sequence above

## Operator note

**Core posture is always on:** Evasion (Ghost), Stalking (hunt_mode), and Predatory (honeypot lattice) default armed per `security_ops` + `ghost_evasion` policy. PREDATOR classifies adversaries continuously; TRENCH-OPS routes live capital only through shielded venues. Escalation modules (full lockdown, poison fills >1% equity) still require operator YES or kernel gates.

**Mention ≠ mandate** for *optional* catalog modules beyond the core four pillars.

## P22 Memecoin trench (defensive)

PREDATOR six-gate filter + lifecycle classifier for Pump.fun / PumpSwap. **Defensive only** — no launch bundler dumps, honeypot construction, or rug tooling.

- Filter/sim: `titan-safety memecoin filter|evaluate|sim`
- Infra: `infra/solana_memecoin.yaml` · skill `memecoin_trench` · playbook `memecoin_trench.yaml`
- Live: promotion YES + `memecoinTrench.enabled` + `capital_profile: live`
- CBs: `CB_MEMECOIN_*` in policy `memecoin_circuit_breakers`

## See also

- Skill: `predator_scanner`, `sentinel_security`, `memecoin_trench`
- Playbook: `security_lockdown.yaml`, `memecoin_trench.yaml`
- Titan Agentik: `/security`, `/memecoin`
- P44 AGENT_HUNT (TITAN.reconciled)
