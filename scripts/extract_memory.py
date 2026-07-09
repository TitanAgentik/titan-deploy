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


def extract_pipelines(text: str) -> str:
    text = unescape_markdown(text)
    lines = ["# Active Pipelines — Index (P1–P48)", ""]
    seen = set()
    for m in PIPELINE_RE.finditer(text):
        pid, name = m.group(1), m.group(2).strip()
        if pid in seen:
            continue
        seen.add(pid)
        lines.append(f"- **P{pid}** {name}")
    if len(lines) <= 2:
        lines += [
            "- **P1** Momentum Scalping",
            "- **P3** Cross-Chain Arbitrage",
            "- **P6** Liquidation Hunting",
            "- **P29** Unified MEV Engine",
            "- **P30** Vulnerability Scanner & Bounty Hunter",
            "- **P32** Bridge Security Engine",
            "- **P34** CLMM 2.0",
            "- **P37-P48** See full TITAN source",
        ]
    lines.append("")
    lines.append("Full pipeline specs: TITAN source §MEMORY / §L")
    return "\n".join(lines) + "\n"


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
    ]
    for cb in unique[:50]:
        lines.append(f"- `{cb}`")
    return "\n".join(lines) + "\n"


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
| TRENCH-OPS | :30000 | Trade execution → signing_node (isolated) |
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

## Quantum (DORMANT)

| Agent | Status |
|-------|--------|
| QCC | DORMANT |
| QSA | DORMANT |
| QRP | DORMANT |
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
- Timing: LBE-1420 GPSDO | OOB: PiKVM V4 Plus | TPM: ASUS TPM-SPI
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
- Evolution/training offload (off-peak); does not host signing_node
- UPS recommended for live capital (utility tier failover path)
"""


def edge_mesh_doc() -> str:
    return """# Edge VPS Mesh

**Phase 1 ($2.5K):** `single_pop` — **EDGE-FRA** only

| PoP | Status | Role |
|-----|--------|------|
| EDGE-FRA | **Active (Phase 1)** | Telegram/EU relay, Erigon archive, EU RPC |
| EDGE-TKY | Deferred Phase 3+ | Hyperliquid / APAC latency |
| EDGE-SIN | Deferred Phase 3+ | APAC secondary |
| EDGE-USE | Deferred Phase 3+ | US East exchange colo |
| EDGE-AMS | Deferred Phase 3+ | Amsterdam DE-CIX |

Full 5-PoP mesh is **not required at launch**. Config: `edge_mesh.phase1: single_pop` in config.yaml.
"""


def macmini_vault_doc() -> str:
    return """# Mac Mini Vault

**Role:** Encrypted key metadata + Trezor ceremonies + profit workloads

- Hardware: Mac Mini 2018 — i7 6-core 3.2GHz, 64GB DDR4 2667MHz
- NOT primary compute — TITANHOME hosts Tier 1/2 inference + safety services
- Vault core: encrypted key management, Trezor sweep signing ceremonies
- Bitcoin SPV node, governance scanner, portfolio analytics preprocessor
- Signing **execution** routes to isolated signing_node; vault holds metadata only
- UPS REQUIRED for live capital (power-protected with signing isolation)
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract memory sidecars")
    parser.add_argument("input", type=Path, nargs="?", default=RECONCILED_PATH)
    parser.add_argument("-o", "--output-dir", type=Path, default=OUTPUT_DIR / "memory")
    args = parser.parse_args()

    text = read_source(args.input)

    files = {
        "strategies/active-pipelines.md": extract_pipelines(text),
        "risk/circuit-breakers.md": extract_critical_cbs(text),
        "agents/routing-table.md": agent_routing_table(),
        "hardware/workstation.md": workstation_doc(),
        "hardware/titanspark.md": titanspark_doc(),
        "hardware/edge-mesh.md": edge_mesh_doc(),
        "hardware/macmini-vault.md": macmini_vault_doc(),
        "research/skill-evolution.md": "# Skill Evolution\n\n6-tier learning stack. See TITAN §HY.\n",
        "research/hydra-models.md": "# Hydra Models\n\n8-model ensemble feeding ORACLE. See TITAN §MODELS.\n",
        "rd_automation/indicators.md": "# R&D Automation Indicators\n\nCSET indicator panel. See TITAN §RD.\n",
    }

    for rel_path, content in files.items():
        write_text(args.output_dir / rel_path, content)

    print(f"Extracted {len(files)} memory files -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
