# P22 — Solana Memecoin Trench (Pump.fun Lifecycle)

> **Catalog until promotion YES.** Real SOL requires live profile, six-gate filter, and Phase 5 approval.
> **Excluded:** §5.5.6 launch bundler dumps, honeypot/rug offensive tooling.

## Strategies (default playbook)

| Strategy | Trigger | Max size |
|----------|---------|----------|
| first_block_snipe | Mint create, G1–G6 pass | 0.1–0.5% equity |
| curve_climb | 15–85% bonding curve | 0.5% equity |
| graduation | ~$69k migration | 0.5% equity |
| post_grad_pullback | Post-PumpSwap | 1.0% equity |
| smart_money_mirror | Tracked wallet buy | 0.5% equity |

## Six-gate filter

1. Mint authority revoked  
2. Freeze authority revoked  
3. Holder concentration caps  
4. No cabal fast-fill  
5. Curve alive  
6. Sell sim OK  

CLI: `titan-safety memecoin filter --mint-json '…'`

## Real Solana wiring

- Infra: `infra/solana_memecoin.yaml` (Geyser + Jito + EDGE-FRA)  
- Config: `openclaw.json` → `memecoinTrench.enabled` (default false)  
- Policy: `memecoin_trench:` block + live venues when ready  
- Agents: PREDATOR (scan) → GUARDIAN/kernel → TRENCH-OPS (Jito) → signing_node  

## Capital envelope

$100–$2,000 lane; daily SOL cap (default 2 SOL); correlation group `memecoin_trench`.

Playbook: `playbooks/memecoin_trench.yaml`
Skill: `memecoin_trench`
