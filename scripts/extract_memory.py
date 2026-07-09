#!/usr/bin/env python3
"""Extract memory sidecar files from §L and bootstrap pointers."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT_DIR, RECONCILED_PATH, read_source, unescape_markdown, write_text

PIPELINE_RE = re.compile(r"^- \*\*P(\d+)\s+([^*]+)\*\*", re.MULTILINE)


def selective_activation_doc() -> str:
    return """# Selective activation — keep it simple

TITAN source and companions list many pipelines, skills, agents, and security modules.
That is a **catalog**, not a requirement to run everything.

## Rules

1. Enable only what current capital, phase, and operator intent need.
2. Allocator `max_active_pipelines` (default **4**) is the hard concentration cap.
3. Security: **Impenetrable always**; **Evasion + Stalking + Predatory armed by default** (`ghost_evasion` + `security_ops`). Live DEX only via shielded routes — public RPC forbidden.
4. New pipeline / skill / PoP = human YES (or promotion gate) — never auto-expand the set.
5. Prefer fewer HEALTHY lanes over many marginal ones.
6. **P22 Memecoin Trench** requires human YES + live profile + `memecoinTrench.enabled` — never auto-activate from catalog mention.

## See

- SOUL.md — Voice + Operational Doctrine
- iron-laws.md §14
- USER.md Preferences
- `risk_kernel/policy.yaml` allocator.selective_activation
- `openclaw.json` autonomy.selectiveActivation
- `memory/strategies/memecoin-trench.md`
"""


def signal_catalog_doc() -> str:
    return """# Signal Catalog — Index (classical-only)

> Catalog of available signal families for ORACLE / PREDATOR / AUGUR / NARRATIVE.
> **Mention ≠ mandate** — subscribe only to feeds needed for funded lanes.

## Families (enable as needed)

- **Price / microstructure** — CEX/DEX mid, spread, depth, trade prints
- **Funding / OI** — perpetual funding rates, open interest, basis
- **On-chain flow** — whale wallets, exchange inflow/outflow, bridge volume
- **Mempool / MEV** — pending txs, bundle competition (PREDATOR; edge PoP)
- **Pump.fun / trench (P22)** — mint create, curve buy velocity, graduation/migration, smart-money wallet copy (Geyser)
- **Macro / regime** — AUGUR risk_on / neutral / risk_off (file or HTTP feed)
- **Catalyst / news** — NARRATIVE listings, governance, regulatory events
- **Sentiment (grounded)** — cited social posts with timestamps only

## Rules

1. Min 3 independent sources before trade entry (R17).
2. No quantum signal paths (classical-only; quantum agents removed).
3. Full 108-signal list lives in TITAN source §ORACLE — do not enable all by default.

See: `memory/strategies/selective-activation.md`, `memory/strategies/active-pipelines.md`
"""


def extract_pipelines(text: str) -> str:
    text = unescape_markdown(text)
    lines = [
        "# Pipeline Catalog Index (P1–P48)",
        "",
        "> **Mention ≠ mandate.** This is a catalog of *available* strategies, not a list of",
        "> required live lanes. Allocator `max_active_pipelines` (default **4**) caps what",
        "> may be funded. Prefer few HEALTHY lanes over many marginal ones.",
        ">",
        "> See also: `memory/strategies/selective-activation.md`",
        "",
        "## Currently relevant (Phase 1 paper / small capital)",
        "",
        "Typical starters when capital allows — still subject to promotion gates:",
        "",
        "- **P1** DEX Cross-Venue Arb (when funded)",
        "- **P5** DEX Funding Carry (when funded)",
        "- **P11** Prediction Market Arbitrage (micro-live path)",
        "- **P12** Intent Solver Network (when funded)",
        "",
        "## Phase 2+ optional (high toxicity — promotion YES required)",
        "",
        "- **P22** Solana Memecoin Trench / Pump.fun lifecycle (catalog — real SOL gated)",
        "",
        "## Catalog (not all active)",
        "",
    ]
    seen = set()
    for m in PIPELINE_RE.finditer(text):
        pid, name = m.group(1), m.group(2).strip()
        if pid in seen:
            continue
        seen.add(pid)
        lines.append(f"- **P{pid}** {name}")
    if len(seen) == 0:
        lines += [
            "- **P9** NFT / RWA Market Making",
            "- **P10** Restaking / AVS Optimization",
            "- **P18** Perpetual Funding Rate Harvest",
            "- **P29** Unified MEV Arbitrage Engine",
            "- **P30** Automated Vulnerability Scanner & Bounty Hunter",
            "- **P34** Concentrated Liquidity Provision (CLMM) 2.0",
            "- **P22** Solana Memecoin Trench (Pump.fun lifecycle)",
            "- **P37-P48** See full TITAN source",
        ]
    lines.append("")
    lines.append(
        "Full pipeline specs: TITAN source §MEMORY / §L — read for research; "
        "activate only via promotion + allocator."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


ENDGAME_CBS = [
    "CB_FUNDING_FLIP",
    "CB_RESTAKING_SLASH",
    "CB_RESTAKING_DEPEG",
    "CB_PRED_MARKET_RESOLVE_RISK",
    "CB_VOL_HARVEST_GAP",
    "CB_NEW_CHAIN_MEV_HALT",
    "CB_AIRDROP_SYBIL",
    "CB_RATE_ARB_LIQUIDITY",
    "CB_CLMM_IL_SPIKE",
    "CB_ENDGAME_PHASE_GATE",
]

MEMECOIN_CBS = [
    "CB_MEMECOIN_DAILY_SOL_CAP",
    "CB_MEMECOIN_FILTER_BYPASS",
    "CB_MEMECOIN_HONEYPOT",
    "CB_MEMECOIN_GRAD_FAIL",
    "CB_MEMECOIN_TIP_BLEED",
]

STEALTH_CBS = [
    "CB_STEALTH_PUBLIC_PATH",
    "CB_STEALTH_UNSHIELDED_VENUE",
    "CB_STALK_SEVERITY_HIGH",
]


def extract_critical_cbs(text: str) -> str:
    text = unescape_markdown(text)
    cbs = re.findall(r"`(CB_[A-Z0-9_]+)`", text)
    unique = []
    seen = set()
    for cb in cbs:
        if cb not in seen:
            seen.add(cb)
            unique.append(cb)
    lines = [
        "# Circuit Breakers — Critical Catalog (top 50)",
        "",
        "Full catalog: 775+ CBs in TITAN source.",
        "",
        "## ENDGAME (Phase 3+ unlock — documented in policy.yaml)",
        "",
    ]
    for cb in ENDGAME_CBS:
        lines.append(f"- `{cb}`")
        seen.add(cb)
    lines.append("")
    lines.append("## P22 Memecoin trench")
    lines.append("")
    for cb in MEMECOIN_CBS:
        lines.append(f"- `{cb}`")
        seen.add(cb)
    lines.append("")
    lines.append("## Stealth / predatory")
    lines.append("")
    for cb in STEALTH_CBS:
        lines.append(f"- `{cb}`")
        seen.add(cb)
    lines.append("")
    lines.append("## From source (sample)")
    lines.append("")
    for cb in unique[:40]:
        if cb not in ENDGAME_CBS:
            lines.append(f"- `{cb}`")
    return "\n".join(lines) + "\n"


def endgame_strategies_doc() -> str:
    return """# ENDGAME Strategies — Phase 3+ Catalog

> From TITAN §ENDGAME. **Not auto-funded.** Requires `capital.endgame_phase_unlock` (≥3),
> statistical promotion, human YES, and allocator headroom (`max_active_pipelines`).

| Strategy | Overlaps | Circuit breaker |
|----------|----------|-----------------|
| Funding rate harvest | P18 | `CB_FUNDING_FLIP` |
| Restaking engine | P10 / P15 | `CB_RESTAKING_SLASH`, `CB_RESTAKING_DEPEG` |
| Prediction market arb | P11 | `CB_PRED_MARKET_RESOLVE_RISK` |
| Vol harvest | — | `CB_VOL_HARVEST_GAP` |
| New-chain MEV | — | `CB_NEW_CHAIN_MEV_HALT` |
| Airdrop positioning | — | `CB_AIRDROP_SYBIL` |
| Rate arb / yield | — | `CB_RATE_ARB_LIQUIDITY` |
| Concentrated LP | P34 | `CB_CLMM_IL_SPIKE` |

Playbook: `playbooks/endgame_phase_gate.yaml`
Gate: `CB_ENDGAME_PHASE_GATE`
"""


def security_posture_doc() -> str:
    return """# Security Posture — Stealth + Predatory (Always On)

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
"""


def memecoin_trench_doc() -> str:
    return """# P22 — Solana Memecoin Trench (Pump.fun Lifecycle)

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

CLI: `titan-safety memecoin filter|evaluate --mint-json '…'` · `memecoin sim --count N`

## Real Solana wiring

- Infra: `infra/solana_memecoin.yaml` (Geyser + PumpSwap migration + Jito + EDGE-FRA)  
- Config: `openclaw.json` → `memecoinTrench.enabled` (default false)  
- Policy: `memecoin_trench:` block + live venues when ready  
- Agents: PREDATOR (scan) → GUARDIAN/kernel → TRENCH-OPS (Jito) → in-process SigningNode  
- Adapters: `solana_recon.py`, `jito_submit.py` (NotConfigured until live)

## Capital envelope

$100–$2,000 lane; daily SOL cap (default 2 SOL); correlation group `memecoin_trench`.
**Requires human YES** — see `selective-activation.md` rule 6.

Playbook: `playbooks/memecoin_trench.yaml`
Skill: `memecoin_trench`
"""


def agent_routing_table() -> str:
    return """# Agent Routing — 23 Agents

## Orchestrator / Risk / Security

| Agent | Tier | Role |
|-------|------|------|
| ARCHON | :30001 | Orchestrator + A2A coordinator |
| CORTEX | :30001 | Meta-cognitive / GEPA / PRM judge |
| GUARDIAN | :30000 | Risk validation / Kelly sizing |
| SENTINEL | :30001 | Security audit / CodeQL gate |

## Signal / On-Chain / Macro (Tier 1 :30000)

| Agent | Role |
|-------|------|
| ORACLE | Signal generation (108 signals) |
| WRAITH | On-chain analysis |
| PREDATOR | Sniper/scanner + mempool |
| AUGUR | Macro regime detection |
| NARRATIVE | Catalyst event ingestion |

## Execution / Research

| Agent | Tier | Role |
|-------|------|------|
| TRENCH-OPS | :30000 | Trade execution → in-process SigningNode |
| LAMARCK | :30001 | Post-trade learning / MGPO |
| DARWIN_GODEL | :30001 | Auto-research / HyEvo / DGM-H (shadow) |

## Utility (TITANSPARK SGLang :30002)

| Agent | Role |
|-------|------|
| HERALD | Notifications (Telegram) |
| NEXUS | Data feeds |
| FORGE | Infrastructure health |
| ALCHEMY | DeFi operations |
| ATLAS | Portfolio management |
| QUANT | Statistical analysis |
| ARBITER | Backtest validation |
| HORIZON | R&D metrology |

## Quantum

Quantum-coordination agents removed. Classical-only posture; OS CSPRNG for entropy.
"""


def workstation_doc() -> str:
    return """# TITANHOME Workstation

**Role:** Primary compute + Tier 1/2 inference + safety services

- CPU: AMD Ryzen Threadripper PRO 9995WX (96C/192T)
- Board: ASUS Pro WS WRX90E-SAGE SE (128 PCIe 5.0 lanes)
- RAM: 512GB DDR5-6000 ECC R-DIMM (8×64GB)
- GPU: 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96GB each, 192GB total)
- Storage: Micron 7500 Pro 3.8TB (boot) + 2× WD Black SN8100 4TB
- PSU: Super Flower Leadex Titanium 2200W
- Cooling: Silverstone XE360-TR5 360mm AIO + Noctua iPPC fans
- Timing: LBE-1425 GPSDO → E810-XXVDA4T | UPS: Eaton 9SX 3000VA | OOB: AST2600 BMC (no PiKVM) | TPM: ASUS TPM-SPI
- NIC: Intel E810-XXVDA4T (4×25GbE PTP/SyncE)
- Chassis: Phanteks Enthoo Pro 2 Server Edition

## Inference Services

- Tier 1 :30000 (GPU 0): Qwen3-30B-A3B FP8 — critical path
- Tier 2 :30001 (GPU 1): Qwen3-Coder-Next-80B — reasoning
- Tier 3a :30005 (off-peak): DeepSeek V4 Pro — PRIMARY R&D/evolution
- Tier 3b :30003 (off-peak): GLM-5.2 — SECONDARY R&D only
- REVM :30020 | Embedder :30004
- Safety: risk kernel + reconciliation + dead-man's switch (:19001-19005)

## Power

- 240V dedicated circuit + **UPS REQUIRED for live capital** (≥15 min runtime)
- On power-loss: HALT trading per `risk_kernel/policy.yaml`

BOM: `~/.openclaw/infra/hardware_bom.yaml` | Schedule: `gpu_schedule.yaml`
"""


def titanspark_doc() -> str:
    return """# TITANSPARK GX10

**Role:** Utility inference + operator gateway failover (not primary compute)

- ASUS GX10 — Qwen3-30B utility (:30002)
- Telegram gateway failover when Mac Mini unavailable
- Evolution/training offload (off-peak); does not host signing
- UPS recommended for live capital (utility tier failover path)
"""


def edge_mesh_doc() -> str:
    return """# Edge VPS Mesh

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
"""


def macmini_vault_doc() -> str:
    return """# Mac Mini Vault

**Role:** Encrypted key metadata + Trezor ceremonies + profit workloads

- Hardware: Mac Mini 2018 — i7 6-core 3.2GHz, 64GB DDR4 2667MHz
- NOT primary compute — TITANHOME hosts Tier 1/2 inference + safety services
- Vault core: encrypted key management, Trezor sweep signing ceremonies
- Bitcoin SPV node, governance scanner, portfolio analytics preprocessor
- Signing **execution** is in-process on TITANHOME (`titan-safety`); vault holds metadata only
- UPS REQUIRED for live capital (power-protected with signing isolation)
"""


def quantum_inspired_doc() -> str:
    return """# Quantum-Inspired Lane Selection (Offline)

**Status:** advisory only — `live_path: false`, `backend: classical_sa`

Classical QUBO + simulated annealing for pipeline/lane subset selection.
Compares against fractional-Kelly `CapitalAllocator` for R&D; **not wired to live gates**.

## Constraints

- No cloud QPU, no `quantum.enabled` policy changes
- Stdlib-only module: `titan_safety/quantum_inspired.py`
- Quantum agents removed from catalog; QI is classical SA only

## CLI

```bash
titan-safety qi demo --seed 42 --k 4
titan-safety qi optimize --lanes-json '[{...}]' --k 4 --compare-kelly
```

## QUBO objective

- Reward: normalized edge/variance per lane (Kelly-like signal)
- Penalty: variance (`risk_lambda`), same-cluster pairs (`cluster_penalty`)
- Cardinality: soft constraint toward `k` active lanes

See: `refs/RESEARCH_detail.md`, `titan-safety allocator plan`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract memory sidecars")
    parser.add_argument("input", type=Path, nargs="?", default=RECONCILED_PATH)
    parser.add_argument("-o", "--output-dir", type=Path, default=OUTPUT_DIR / "memory")
    args = parser.parse_args()

    text = read_source(args.input)

    files = {
        "strategies/active-pipelines.md": extract_pipelines(text),
        "strategies/selective-activation.md": selective_activation_doc(),
        "strategies/signal-catalog.md": signal_catalog_doc(),
        "strategies/endgame.md": endgame_strategies_doc(),
        "strategies/memecoin-trench.md": memecoin_trench_doc(),
        "security/posture.md": security_posture_doc(),
        "risk/circuit-breakers.md": extract_critical_cbs(text),
        "agents/routing-table.md": agent_routing_table(),
        "hardware/workstation.md": workstation_doc(),
        "hardware/titanspark.md": titanspark_doc(),
        "hardware/edge-mesh.md": edge_mesh_doc(),
        "hardware/macmini-vault.md": macmini_vault_doc(),
        "research/skill-evolution.md": "# Skill Evolution\n\n6-tier learning stack. See TITAN §HY.\n",
        "research/hydra-models.md": "# Hydra Models\n\n8-model ensemble feeding ORACLE. See TITAN §MODELS.\n",
        "research/quantum-inspired.md": quantum_inspired_doc(),
        "rd_automation/indicators.md": "# R&D Automation Indicators\n\nCSET indicator panel. See TITAN §RD.\n",
    }

    for rel_path, content in files.items():
        write_text(args.output_dir / rel_path, content)

    print(f"Extracted {len(files)} memory files -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
