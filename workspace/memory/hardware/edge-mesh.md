# Edge VPS Mesh

**Full 5-PoP mesh** (`mode: full_mesh`) — paper + live use identical routing (`latency_faithful: true`)

| PoP | Status | Role |
|-----|--------|------|
| EDGE-FRA | Active | Erigon archive, Jito FRA, EU DEX, Telegram relay |
| EDGE-TKY | Active | Binance, OKX, Hyperliquid, Jito TKY |
| EDGE-SIN | Active | Bybit, BSC, Sui, APAC failover |
| EDGE-USE | Active | Coinbase, L2 sequencers, Flashbots US |
| EDGE-AMS | Active | Solana gRPC redundancy, Nostr, bridge monitor |

Config: `~/.openclaw/infra/edge_mesh.yaml` + `openclaw.json` → `edgeMesh.mode: full_mesh`.
Bootstrap: `POP=EDGE-TKY bash ~/.openclaw/infra/edge_pop_bootstrap.sh`
Route: `titan-safety edge route --venue jito --strategy P22`
