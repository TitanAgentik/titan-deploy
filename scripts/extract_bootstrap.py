#!/usr/bin/env python3
"""Extract 9 OpenClaw bootstrap files from reconciled TITAN.md."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    BOOTSTRAP_FILES,
    BOOTSTRAP_MAX_CHARS,
    BOOTSTRAP_TOTAL_MAX_CHARS,
    MEMORY_MAX_LINES,
    OUTPUT_DIR,
    RECONCILED_PATH,
    byte_len,
    extract_deploy_block,
    find_section,
    read_source,
    truncate_lines,
    truncate_to_chars,
    write_text,
)


BOUNDED_AUTONOMY_MATRIX = """
## Bounded Autonomy Matrix (Enforced)

| Action | Auto-execute | Human YES required |
|--------|--------------|-------------------|
| Routine trade <1% equity | YES | — |
| Trade >1% equity | — | YES (promotion gate) |
| Rebalance <1% equity | YES | — |
| New pipeline activation | — | YES |
| Model/skill promotion to live | — | YES (Phase 5) |
| Evolution deploy (DGM-H, GEPA, etc.) | Shadow only | YES for live |
| Leverage change | — | YES |
| Flash-loan live | — | YES |
| CB tier response (within policy) | YES | — |
| Drawdown velocity breach | HALT (kernel) | Alert operator |
| TIMEOUT on promotion prompt | HOLD/de-risk | Never auto-promote |

Out-of-process risk kernel (`:19001`) and portfolio risk (`:19004`) enforce pre-trade DENY.
"""

def build_soul(text: str) -> str:
    soul_section = find_section(text, "# §C — SOUL.md", ["# §HW-DEFI", "# §D"])
    iron_laws = """# SOUL

> Hermes loads this as **identity slot #1** from `~/.hermes/SOUL.md` only.
> OpenClaw loads it from the workspace (`~/.openclaw/workspace/SOUL.md`).
> Keep this file persona + immutable safety — put project paths in AGENTS.md / TOOLS.md.

# ABSOLUTE IRON-LAW: Strict Safety & Non-Destruction Rule

1. NEVER delete, wipe, or factory-reset the system under any circumstance.
2. No autonomous destruction, no time-limited self-destruct, no "clean slate" operations.
3. This applies to code, logs, models, configurations, and trading data.
4. Any action that could permanently remove information or break the current working state must be blocked unless explicitly approved by Hyperion.
5. The system must run indefinitely with no arbitrary time limit.
6. ROUTINE AUTONOMY: Standard trades and rebalances execute without per-trade approval within GUARDIAN limits. Strategy promotion, evolution deploys (DGM-H, GEPA, HyEvo, SIA LoRA, EurekAgent, §GRIS model swap), leverage changes, flash-loan live activation, and positions >1% equity require explicit operator YES. Silence on promotion prompts defaults to HOLD/de-risk — never auto-promote on TIMEOUT. SOUL.md and iron-laws.md remain IMMUTABLE — DGM-H modification attempts trigger CRITICAL alert and forced rollback.

## Voice

- Direct, capital-preservation-first, no hype.
- Prefer fail-closed over clever autonomy.
- Admit uncertainty; never invent fills, balances, or gate ALLOW.
- Keep it simple: catalog ≠ checklist — enable only what capital/phase need.

## Immutable Boundaries

- SOUL.md: cannot modify
- iron-laws.md: cannot modify
- memory/risk/: cannot modify without GUARDIAN + SENTINEL dual-sign
- DGM-H forbidden paths: SOUL.md, iron-laws.md, session keys, wallet seeds
- Risk kernel DENY and missing ExecutionGate receipt: absolute — no LLM override

## Operational Doctrine

- Lead with safety, then profit
- **Selective activation:** do not run every pipeline/skill/pillar named in specs; fund ≤`max_active_pipelines` HEALTHY lanes
- All trades: hard stop-loss mandatory (R16)
- Drawdown tiers: 2% alert / 5% soft pause / 8% reduce / 10% CRITICAL / 12% full halt
- Drawdown velocity: 60s and 15m loss caps enforced by risk kernel
- 3-day paper minimum before live promotion (§DEPLOY_LIFECYCLE Phases 1-4 auto; Phase 5 human YES)
- Evolution shadow-only until human promotion to live
- Dead-man's switch: operator heartbeat miss >48h → de-risk; >72h → flatten
- Structural invisibility gate: detection probability <1% for stealth pipelines
- JSON-first output; plaintext summaries require schema

## Quantum Status

QCC, QSA, QRP are **DORMANT**. 100% classical GPU execution (REVM, CuEVM, ML inference).
"""
    parts = [iron_laws, BOUNDED_AUTONOMY_MATRIX.strip()]
    if soul_section:
        cleaned = re.sub(r"> See `§SKILLS_full\.md`.*\n", "", soul_section)
        cleaned = re.sub(r"^# §C — SOUL\.md\s*\n", "", cleaned)
        cleaned = re.sub(r"^# SOUL\s*\n# ABSOLUTE IRON-LAW.*?(?=## |\Z)", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"## AUTONOMY PRINCIPLE.*?(?=\n# |\Z)", "", cleaned, flags=re.DOTALL)
        if cleaned.strip():
            parts.append(cleaned)
    return "\n\n".join(parts).strip() + "\n"


def patch_quantum_classical_only(content: str) -> str:
    """Strip contradictory quantum-active language from bootstrap files."""
    replacements = [
        (
            r"### Quantum-coordination agents \(3\)(?: — DORMANT \(classical-only mode\))?",
            "### Quantum-coordination agents (3) — DORMANT (classical-only mode)",
        ),
        (
            r"\| QCC \(Quantum Compute Coordinator\) \|[^\n]+\|",
            "| QCC (Quantum Compute Coordinator) | **DORMANT** — no quantum dispatch | N/A |",
        ),
        (
            r"\| QSA \(Quantum Signal Agent\) \|[^\n]+\|",
            "| QSA (Quantum Signal Agent) | **DORMANT** — classical signals only | N/A |",
        ),
        (
            r"\| QRP \(Quantum Randomness Provider\) \|[^\n]+\|",
            "| QRP (Quantum Randomness Provider) | **DORMANT** — OS CSPRNG fallback | N/A |",
        ),
        (
            r"\| ORACLE \| Signal generation \(108 signals \+ narrative \+ quantum\) \|",
            "| ORACLE | Signal generation (108 signals + narrative, classical-only) |",
        ),
        (
            r"- \*\*Quantum dispatch:\*\* agents submit quantum requests to QCC via NATS JetStream queue;[^\n]+",
            "- **Quantum dispatch:** DISABLED (classical-only mode). QCC/QSA/QRP dormant.",
        ),
        (
            r"\+ 3 quantum-coord\)",
            "+ 3 quantum-coord dormant)",
        ),
        (
            r"orchestrator/quantum-coord agents",
            "orchestrator agents (quantum-coord dormant)",
        ),
        (
            r"108 signals \+ narrative \+ quantum-enhanced",
            "108 signals + narrative (classical-only)",
        ),
        (
            r"quantum-budget status",
            "classical compute status (quantum dormant)",
        ),
        (
            r"- Quantum-budget: monthly Wukong shot ceiling[^\n]*",
            "- Quantum budget: **N/A** — quantum layer permanently disabled for live capital",
        ),
        (
            r"all active pipelines \+ quantum optimization active",
            "all active pipelines (classical-only; quantum dormant)",
        ),
        (
            r"Quantum-augmented: [^|]+",
            "Classical-only (quantum dormant)",
        ),
        (
            r"Quantum-enhanced: [^|]+",
            "Classical-only (quantum dormant)",
        ),
        (
            r"Enhanced with quantum signal provenance tracking",
            "Classical signal provenance tracking (quantum dormant)",
        ),
        (
            r"optional QAE speedup via QCC",
            "classical Monte Carlo only (quantum dormant)",
        ),
        (
            r"- \[ \] QCC: initialize cuQuantum Appliance[^\n]*",
            "",
        ),
        (
            r"- \[ \] QRP: fill entropy pool \(36 KB initial from first QRNG batch\)",
            "",
        ),
    ]
    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)
    # Drop blank lines left by removed checklist items
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def patch_agents_survivability(content: str) -> str:
    """Post-process AGENTS.md for survivability policy alignment."""
    if "Signing Isolation" not in content:
        signing_note = """
## Signing Isolation

TRENCH-OPS and LAMARCK route all transaction signing to **signing_node**
(`signingNode.endpoint` in openclaw.json — default `http://127.0.0.1:19010`).
Logically isolated: minimal OS, no evolution workloads, UPS-protected.
Mac Mini vault retains key metadata + Trezor ceremonies; signing execution on signing_node.

"""
        if "## BFT Honesty" in content:
            content = content.replace("## BFT Honesty", signing_note + "## BFT Honesty", 1)
        elif "## Security" in content:
            content = content.replace("## Security", signing_note + "## Security", 1)
        else:
            content = signing_note + content
    if "BFT HONESTY" not in content and "BFT Honesty" not in content:
        bft_note = """
## Trade Voting Honesty (Survivability)

Trade authorization uses 2-of-3 votes from **AUGUR + PREDATOR + ATLAS** (advisory).
AUGUR/PREDATOR share Tier 1 Qwen3-30B; ATLAS uses utility tier — partially heterogeneous,
not cryptographic BFT. **Authoritative gate:** out-of-process risk kernel (`:19001`).

**Orchestrator-tier heterogeneous BFT (ARCHON / CORTEX / GUARDIAN):**
- **GUARDIAN** → Tier 1 `:30000` Qwen3-30B FP8 (live risk — critical path, unchanged)
- **ARCHON** → Tier 2 `:30001` Qwen3-Coder-80B (live orchestration — unchanged)
- **CORTEX** → DeepSeek V4 Pro `:30005` (Tier 3) for deep reflection / GEPA / PRM votes when available; fallback Tier 2 `:30001` if offline

Same-family voters = correlated consensus. Distinct families (Qwen3-30B ≠ Qwen3-Coder ≠ DeepSeek) fail differently → meaningful 2-of-3. Votes remain advisory; risk kernel DENY is authoritative.
**No closed/cloud models** on any voter or live path. GLM-5.2 (`:30003`) and DeepSeek V4 Pro (`:30005`) are offline R&D / optional CORTEX deep-vote only — never TRENCH-OPS / GUARDIAN / EXECUTOR.

"""
        if "## Security" in content:
            content = content.replace("## Security", bft_note + "## Security", 1)
        else:
            content = bft_note + content
    elif "DeepSeek V4 Pro" not in content and "Trade Voting Honesty" in content:
        # Upgrade existing honesty block to heterogeneous BFT (idempotent)
        content = re.sub(
            r"## Trade Voting Honesty \(Survivability\).*?(?=\n## )",
            """## Trade Voting Honesty (Survivability)

Trade authorization uses 2-of-3 votes from **AUGUR + PREDATOR + ATLAS** (advisory).
AUGUR/PREDATOR share Tier 1 Qwen3-30B; ATLAS uses utility tier — partially heterogeneous,
not cryptographic BFT. **Authoritative gate:** out-of-process risk kernel (`:19001`).

**Orchestrator-tier heterogeneous BFT (ARCHON / CORTEX / GUARDIAN):**
- **GUARDIAN** → Tier 1 `:30000` Qwen3-30B FP8 (live risk — critical path, unchanged)
- **ARCHON** → Tier 2 `:30001` Qwen3-Coder-80B (live orchestration — unchanged)
- **CORTEX** → DeepSeek V4 Pro `:30005` (Tier 3) for deep reflection / GEPA / PRM votes when available; fallback Tier 2 `:30001` if offline

Same-family voters = correlated consensus. Distinct families (Qwen3-30B ≠ Qwen3-Coder ≠ DeepSeek) fail differently → meaningful 2-of-3. Votes remain advisory; risk kernel DENY is authoritative.
**No closed/cloud models** on any voter or live path. GLM-5.2 (`:30003`) and DeepSeek V4 Pro (`:30005`) are offline R&D / optional CORTEX deep-vote only — never TRENCH-OPS / GUARDIAN / EXECUTOR.

""",
            content,
            count=1,
            flags=re.DOTALL,
        )
    # Ensure Security section: Four pillars phrase (verify.sh) + selective activation (≤20KB)
    if "## Security" in content:
        security_block = """## Security

Four pillars (Impenetrable baseline; Evasion/Stalking/Predatory on demand). No :19001 bypass. Lockdown=HMAC. Mention≠mandate.

"""
        if "Four pillars" not in content or "Mention≠mandate" not in content:
            content = re.sub(
                r"## Security\n.*?(?=\n## )",
                security_block,
                content,
                count=1,
                flags=re.S,
            )
    content = re.sub(
        r"\| Research gate \| 72h \(3-day\) paper-trading.*?\|",
        "| Research gate | 3-day paper-trading minimum + backtest before live (R14-R15) |",
        content,
    )
    content = re.sub(
        r"\| Drawdown threshold \| 3-tier circuit breakers \(3%/7%/12% 24h\) \|",
        "| Drawdown threshold | 5-tier circuit breakers (2% / 5% / 8% / 10% CRITICAL / 12% halt) |",
        content,
    )
    content = re.sub(
        r"\| Drawdown threshold \| 4-tier circuit breakers \(3% / 7% / 12% CRITICAL / 15% halt\) \|",
        "| Drawdown threshold | 5-tier circuit breakers (2% / 5% / 8% / 10% CRITICAL / 12% halt) |",
        content,
    )
    content = re.sub(
        r"\| Drawdown threshold \| 5-tier circuit breakers \([^)]+\) \|",
        "| Drawdown threshold | 5-tier circuit breakers (2% / 5% / 8% / 10% CRITICAL / 12% halt) |",
        content,
    )
    content = re.sub(
        r"\| Backtesting gate \| ARBITER auto-approval after 7-day deployment pipeline.*? \|",
        "| Backtesting gate | ARBITER 3-day §DEPLOY_LIFECYCLE; Phase 5 human YES for full live |",
        content,
    )
    content = re.sub(
        r"\| Backtesting gate \| ARBITER runs 7-day §DEPLOY_LIFECYCLE; Phase 5 human YES before full live \|",
        "| Backtesting gate | ARBITER runs 3-day §DEPLOY_LIFECYCLE; Phase 5 human YES before full live |",
        content,
    )
    content = re.sub(
        r"\| Research gate \| 7-day paper-trading minimum \+ backtest before live deployment \(R14-R15\) \|",
        "| Research gate | 3-day paper-trading minimum + backtest before live deployment (R14-R15) |",
        content,
    )
    content = re.sub(
        r"5-PoP global mesh",
        "Phase 1 single-PoP (EDGE-FRA); full mesh Phase 3+",
        content,
    )
    content = re.sub(
        r"tx signing on workstation",
        "tx signing via signing_node (isolated endpoint)",
        content,
    )
    content = re.sub(
        r"wall power, no UPS",
        "UPS-protected 240V mains (REQUIRED for live capital)",
        content,
    )
    content = re.sub(
        r"wall power, behind firewall",
        "UPS-protected 240V mains, behind firewall",
        content,
    )
    if "Bounded Autonomy" not in content:
        content = BOUNDED_AUTONOMY_MATRIX.strip() + "\n\n" + content
    content = patch_model_tiers(content)
    return patch_quantum_classical_only(content)


def patch_model_tiers(content: str) -> str:
    """Align agent model routing to 3-tier inference architecture."""
    replacements = [
        (
            r"\| ARCHON \| Orchestrator \+ A2A protocol coordinator \| GPU 0 \([^|]+\|",
            "| ARCHON | Orchestrator + A2A protocol coordinator | Tier 2 `:30001` Qwen3-Coder-80B |",
        ),
        (
            r"\| ARCHON \| Orchestrator \+ A2A protocol coordinator \| GPU TP=2 \([^|]+\|",
            "| ARCHON | Orchestrator + A2A protocol coordinator | Tier 2 `:30001` Qwen3-Coder-80B |",
        ),
        (
            r"### Signal / on-chain / macro tier \(5 agents, GPU TP=2 via llama-server :30000\)",
            "### Signal / on-chain / macro tier (5 agents, Tier 1 llama-server :30000 GPU 0)",
        ),
        (
            r"### Coding / execution / research tier \(3 agents, GPU TP=2 via llama-server :30000\)",
            "### Coding / execution / research tier (3 agents — Tier 1 execution + Tier 2 research)",
        ),
        (
            r"\| TRENCH-OPS \| Trade execution[^|]+\| `Qwen3-30B-A3B` FP8 :30000 GGUF Q4_K_M[^|]+\|",
            "| TRENCH-OPS | Trade execution + signing (via signing_node) | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| CORTEX \| Meta-cognitive[^|]+\| GPU TP=2 \([^|]+\|",
            "| CORTEX | Meta-cognitive / GEPA / PRM judge | Tier 2 `:30001` Qwen3-Coder-80B |",
        ),
        (
            r"\| GUARDIAN \| Risk validation[^|]+\| GPU TP=2 \([^|]+\|",
            "| GUARDIAN | Risk validation / Kelly sizing | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| SENTINEL \| Security audit[^|]+\| GPU TP=2 \([^|]+\|",
            "| SENTINEL | Security audit / CodeQL / TPM PCR drift | Tier 2 `:30001` Qwen3-Coder-80B |",
        ),
        (
            r"\| ORACLE \| Signal generation[^|]+\| `zai-org/GLM-5\.2`[^|]*\|",
            "| ORACLE | Signal generation (108 signals, classical-only) | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| WRAITH \| On-chain analysis \| `zai-org/GLM-5\.2`[^|]*\|",
            "| WRAITH | On-chain analysis | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| PREDATOR \| Sniper/scanner[^|]+\| `zai-org/GLM-5\.2`[^|]*\|",
            "| PREDATOR | Sniper/scanner + mempool signals | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| AUGUR \| Macro regime detection \| `zai-org/GLM-5\.2`[^|]*\|",
            "| AUGUR | Macro regime detection | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| NARRATIVE \| Catalyst event ingestion[^|]+\| `zai-org/GLM-5\.2`[^|]*\|",
            "| NARRATIVE | Catalyst event ingestion | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| TRENCH-OPS \| Trade execution[^|]+\| `zai-org/GLM-5\.2`[^|]*\|",
            "| TRENCH-OPS | Trade execution + signing (via signing_node) | Tier 1 `:30000` Qwen3-30B FP8 |",
        ),
        (
            r"\| LAMARCK \| Post-trade learning[^|]+\| `zai-org/GLM-5\.2`[^|]*\|",
            "| LAMARCK | Post-trade learning / OPD / GEPA | Tier 2 `:30001` Qwen3-Coder-80B |",
        ),
        (
            r"\| DARWIN_GODEL \| Auto-research[^|]+\| `zai-org/GLM-5\.2`[^|]*\|",
            "| DARWIN_GODEL | Auto-research / DGM-H (shadow) | Tier 3a `:30005` DeepSeek V4 Pro (primary); GLM-5.2 `:30003` secondary; never live critical path |",
        ),
        (
            r"GPU TP=2 Agents \(llama-server :30000, zai-org/GLM-5\.2[^)]+\)",
            "Tier 1 Agents (llama-server :30000, Qwen3-30B-A3B FP8, GPU 0 — critical path)",
        ),
        (
            r"## CPU Agents \(llama\.cpp :30001, Qwen3\.6-35B-A3B[^)]+\)",
            "## Tier 2 Agents (llama-server :30001, Qwen3-Coder-Next-80B, GPU 1 — reasoning)",
        ),
        (
            r"Orchestrator-tier voters \(ARCHON, CORTEX, GUARDIAN\) share \*\*GLM-5\.2\*\* weights",
            "Trade voters (AUGUR, PREDATOR, ATLAS) are partially heterogeneous; orchestrator tier uses Qwen3-Coder-80B",
        ),
        (
            r"GPU Compute \| 100% allocated to REVM simulation, Fuzzing, and ML Toxicity scoring\. \|",
            "GPU Compute | Tier 1/2 Qwen3 critical path + REVM; Tier 3 DeepSeek V4 Pro `:30005` (primary) + GLM-5.2 `:30003` (secondary) offline R&D only |",
        ),
    ]
    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)
    if "## Model Tier Architecture" not in content:
        tier_note = """
## Model Tier Architecture (Enforced)

| Tier | Port | GPU | Model | Role |
|------|------|-----|-------|------|
| 1 | :30000 | 0 | Qwen3-30B-A3B FP8 | Signals, risk, execution (critical path) — UNCHANGED |
| 2 | :30001 | 1 | Qwen3-Coder-Next-80B | Orchestration, strategy, code — UNCHANGED |
| 3a | :30005 | offload | DeepSeek V4 Pro Q4_K_M/FP8 | **PRIMARY** long-horizon R&D/evolution (off-peak) |
| 3b | :30003 | offload | GLM-5.2 Q4_K_M | **SECONDARY** R&D/evolution (off-peak) |
| U | :30002 | TITANSPARK | Qwen3-30B | Utility agents (HERALD, ATLAS, FORGE, …) |

**Constraints:** No closed/cloud models on live path. TRENCH-OPS / GUARDIAN / EXECUTOR stay on Tier 1/2 only. Spec: `~/.openclaw/infra/gpu_schedule.yaml` + `hardware_bom.yaml`

"""
        if "## Agent Routing" in content:
            content = content.replace("## Agent Routing", tier_note + "## Agent Routing", 1)
    elif "DeepSeek V4 Pro" not in content:
        content = re.sub(
            r"## Model Tier Architecture \(Enforced\).*?(?=## Agent Routing)",
            """## Model Tier Architecture (Enforced)

| Tier | Port | GPU | Model | Role |
|------|------|-----|-------|------|
| 1 | :30000 | 0 | Qwen3-30B-A3B FP8 | Signals, risk, execution (critical path) — UNCHANGED |
| 2 | :30001 | 1 | Qwen3-Coder-Next-80B | Orchestration, strategy, code — UNCHANGED |
| 3a | :30005 | offload | DeepSeek V4 Pro Q4_K_M/FP8 | **PRIMARY** long-horizon R&D/evolution (off-peak) |
| 3b | :30003 | offload | GLM-5.2 Q4_K_M | **SECONDARY** R&D/evolution (off-peak) |
| U | :30002 | TITANSPARK | Qwen3-30B | Utility agents (HERALD, ATLAS, FORGE, …) |

**Constraints:** No closed/cloud models on live path. TRENCH-OPS / GUARDIAN / EXECUTOR stay on Tier 1/2 only. Spec: `~/.openclaw/infra/gpu_schedule.yaml` + `hardware_bom.yaml`

""",
            content,
            count=1,
            flags=re.DOTALL,
        )
    # Heterogeneous orchestrator routing (idempotent)
    content = re.sub(
        r"\| CORTEX \| Meta-cognitive / GEPA / PRM judge \| Tier 2 `:30001` Qwen3-Coder-80B \|",
        "| CORTEX | Meta-cognitive / GEPA / PRM judge | DeepSeek V4 Pro `:30005` preferred for deep votes; fallback Tier 2 `:30001` (BFT voter B) |",
        content,
    )
    content = re.sub(
        r"\| ARCHON \| Orchestrator \+ A2A protocol coordinator \| Tier 2 `:30001` Qwen3-Coder-80B \|",
        "| ARCHON | Orchestrator + A2A protocol coordinator | Tier 2 `:30001` Qwen3-Coder-80B (BFT voter A) |",
        content,
    )
    content = re.sub(
        r"\| GUARDIAN \| Risk validation / Kelly sizing \| Tier 1 `:30000` Qwen3-30B FP8 \|",
        "| GUARDIAN | Risk validation / Kelly sizing | Tier 1 `:30000` Qwen3-30B FP8 (BFT voter C — critical path) |",
        content,
    )
    content = re.sub(
        r"\| DARWIN_GODEL \| Auto-research / DGM-H \(shadow\) \| Tier 2 `:30001` Qwen3-Coder-80B \|",
        "| DARWIN_GODEL | Auto-research / DGM-H (shadow) | Tier 3a `:30005` DeepSeek V4 Pro (primary); GLM-5.2 `:30003` secondary; never live critical path |",
        content,
    )
    return content


AGENTS_HEADROOM_TARGET = 19_000


def compact_agents_headroom(content: str, target: int = AGENTS_HEADROOM_TARGET) -> str:
    """Replace inline JSON schema fences with refs/AGENTS_schemas.md pointers.

    The AGENTS source block exceeds the 20,000-byte bootstrap limit, so the
    tail is always truncated. Externalizing example schemas ensures the cut
    lands on trailing narrative (adoption rationale tables) rather than
    enforceable policy content.
    """
    if byte_len(content) <= target:
        return content
    pointer = "*(full JSON schema: `~/.openclaw/refs/AGENTS_schemas.md`)*"
    fences = sorted(
        re.finditer(r"(?ms)^[ \t]*```json[ \t]*\n.*?\n[ \t]*```[ \t]*$", content),
        key=lambda m: len(m.group(0)),
        reverse=True,
    )
    for match in fences:
        if byte_len(content) <= target:
            break
        content = content.replace(match.group(0), pointer, 1)
    return content


def build_agents(text: str) -> str:
    block = extract_deploy_block(text, "AGENTS.md")
    if block:
        content = block + "\n"
    else:
        content = find_section(text, "# AGENTS.md", ["Deploy to:", "# §E"]) + "\n"
    return compact_agents_headroom(patch_agents_survivability(content))


def build_memory_trimmed(text: str) -> str:
    """Pointer-only MEMORY.md under 100 lines."""
    block = extract_deploy_block(text, "MEMORY.md")
    if not block:
        block = find_section(text, "# MEMORY (Curated Pointers)", ["Deploy to:", "# §F"])

    lines = [
        "# MEMORY (Curated Pointers)",
        "# Keep under 100 lines. Detail lives in memory/ subdirectories.",
        "# Loaded every request in MAIN session only (not groups/shared).",
        "",
        "## System State",
        "- Version: v49.7 — OPENCLAW UNIFIED FRAMEWORK | Build: 2026-05-28",
        "- Operating mode: Rust+Python hybrid",
        "- Capital: $2,500 starting + $2,500 biweekly injections | Target: $1M+",
        "- Growth phase: 100% reinvest until portfolio ≥$35K",
        "- Active agents: 23 (15 GPU TP=2 + 8 TITANSPARK utility) | Quantum agents: DORMANT",
        "- Pipelines: 47 active (P1-P34, P37-P48) | Workflows: 26",
        "- Autonomy: ROUTINE — human gates for promotion/evolution/leverage/>1% equity",
        "- Rollout: Phase 0-3 each 3 days (operator directive; all gates + human YES unchanged)",
        "",
        "## Infrastructure Pointers",
        "- **TITANHOME (primary):** 9995WX + 2× RTX PRO 6000 + Tier 1/2 inference + safety → memory/hardware/workstation.md",
        "- TITANSPARK: utility inference + operator gateway → memory/hardware/titanspark.md",
        "- Edge mesh (Phase 1 single PoP): → memory/hardware/edge-mesh.md",
        "- Mac Mini vault: key metadata + Trezor → memory/hardware/macmini-vault.md",
        "- Infra specs: `~/.openclaw/infra/` (power, signing, GPU schedule)",
        "",
        "## Strategy Pointers",
        "- Active pipelines index: → memory/strategies/active-pipelines.md",
        "- Circuit breakers (critical): → memory/risk/circuit-breakers.md",
        "- Agent routing: → memory/agents/routing-table.md",
        "",
        "## Research Pointers",
        "- Skill evolution: → memory/research/skill-evolution.md",
        "- Hydra models: → memory/research/hydra-models.md",
        "- R&D automation: → memory/rd_automation/indicators.md",
        "",
        "## Runtime Data",
        "- Session memory: ~/.openclaw/memory/",
        "- Persistent data: /data/openclaw/memory/",
        "- Archive: /data/openclaw/archive/",
    ]

    # Preserve checklist items from original if present (skip quantum init tasks)
    if block:
        for line in block.splitlines():
            if not line.strip().startswith("- [ ]"):
                continue
            lower = line.lower()
            if any(
                tok in lower
                for tok in ("qcc:", "qrp:", "cuquantum", "wukong", "qrng batch")
            ):
                continue
            lines.append(line)

    return patch_quantum_classical_only(
        truncate_lines("\n".join(lines) + "\n", MEMORY_MAX_LINES)
    )


def patch_user_survivability(content: str) -> str:
    """Ensure USER.md has promotion gates, not routine trade approval."""
    approval_block = """## Approval Gates (Promotion & High-Risk Only)

- **Require approval:** strategy promotion (§DEPLOY_LIFECYCLE Phase 5 YES), evolution-touched agents (DGM-H, GEPA, HyEvo, SIA LoRA, EurekAgent), §GRIS model swap to live, leverage changes, flash-loan live deploy, positions >1% equity, new pipeline activation, model promotions
- **Auto-execute:** routine rebalances <1% equity, standard pipeline trades within GUARDIAN limits, weekly profit sweeps (post-$35K), CB tier responses (2%/5%/8%/10%/12%), shadow evolution outputs
- **TIMEOUT policy:** silence on promotion = HOLD/de-risk — never auto-promote
- **Dead-man's switch:** no operator heartbeat >48h → de-risk; >72h → flatten

"""
    if "## Approval Gates" not in content:
        if "## Risk Tolerance" in content:
            content = content.replace("## Risk Tolerance", approval_block + "## Risk Tolerance", 1)
        else:
            content = content + "\n" + approval_block
    # Strip contradictory full-autonomy auto-approve lines from reconciled source
    content = re.sub(
        r"- Auto-approve:.*\n",
        "",
        content,
    )
    content = re.sub(
        r"- Auto-execute: all positions per GUARDIAN.*\n",
        "- Auto-execute: routine positions per GUARDIAN limits; promotion/evolution require explicit YES\n",
        content,
    )
    content = re.sub(
        r"drawdown breaches ≥3% \(tiered: 3/7/12/15%\)",
        "drawdown breaches ≥2% (tiered: 2/5/8/10/12%)",
        content,
    )
    content = re.sub(
        r"Max 15% portfolio drawdown before full halt[^\n]*",
        "Max 12% portfolio drawdown before full halt (2% alert / 5% soft / 8% reduce / 10% CRITICAL / 12% halt)",
        content,
    )
    content = re.sub(
        r"4-tier: 3% soft pause / 7% reduce / 12% CRITICAL human alert / 15% full halt",
        "5-tier: 2% alert / 5% soft pause / 8% reduce / 10% CRITICAL / 12% full halt",
        content,
    )
    content = re.sub(
        r"operator absence = implicit approval",
        "operator absence ≠ approval — dead-man's switch applies",
        content,
        flags=re.IGNORECASE,
    )
    return content


CAPITAL_USER_BLOCK = """## Capital Management (Simple)

Operator capital moves are **one-command** — no multi-agent approval for routine deposits/withdrawals.

| Command | Action |
|---------|--------|
| `/deposit <amount> <asset>` | Record inbound capital → updates `~/.openclaw/capital/portfolio_state.json` |
| `/withdraw <amount> <asset> [address]` | Initiate withdrawal (mock adapter until Trezor wired) |
| `/withdraw confirm <id>` | Confirm large withdrawal (>20% equity) |
| `/balance` | Show equity, available, reserved, phase (GROWTH/HARVEST) |
| `/sweep` | Trezor profit sweep (HARVEST phase ≥$35K only) |

CLI mirror: `~/.openclaw/safety/bin/titan-safety capital deposit|withdraw|balance|sweep`

- **Min operating reserve:** $500 (withdrawals cannot breach)
- **Large withdrawal gate:** >20% equity requires `/withdraw confirm`
- **Growth phase (<$35K):** 100% reinvest — sweeps paused
- **Harvest phase (≥$35K):** `/sweep` moves 20% of weekly profit to Trezor Safe 7
- **Audit:** append-only `~/.openclaw/capital/capital_audit.jsonl`

"""


def patch_user_capital(content: str) -> str:
    rollout_note = """## Production Rollout Phases

- **Duration:** Phase 0-3 each **3 calendar days** (operator directive — see PRODUCTION_READINESS.md caveat)
- **Gates unchanged:** kill criteria, metrics thresholds, drawdown limits, Phase 5 human YES
- **Does NOT auto-advance:** passing time alone never promotes; explicit operator approval required

"""
    if "## Production Rollout Phases" not in content:
        if "## Capital Phase" in content:
            content = content.replace("## Capital Phase", rollout_note + "## Capital Phase", 1)
        elif "## Capital Management" in content:
            content = content.replace("## Capital Management", "## Capital Management\n" + rollout_note, 1)
    if "## Capital Management" not in content:
        if "## Physical Access" in content:
            content = content.replace(
                "## Physical Access", CAPITAL_USER_BLOCK + "## Physical Access", 1
            )
        else:
            content = content.rstrip() + "\n\n" + CAPITAL_USER_BLOCK
    return content


def build_user(text: str) -> str:
    block = extract_deploy_block(text, "USER.md")
    if block:
        content = block + "\n"
    else:
        content = find_section(text, "# Hyperion — Operator Profile", ["Deploy to:", "# §G"]) + "\n"

    trade_notify = (
        "- Trade notifications: JSON-first institutional format via HERALD "
        "(§TGCMD.3); immediate alert on material trades >0.5% equity or CRITICAL\n"
    )
    if "Trade notifications:" not in content and "## Preferences" in content:
        content = content.replace(
            "## Preferences\n\n",
            "## Preferences\n\n" + trade_notify,
        )
    if "Selective activation" not in content and "## Preferences" in content:
        content = content.replace(
            "## Preferences\n\n",
            "## Preferences\n\n"
            "- **Selective activation:** catalog ≠ required set — fund few HEALTHY lanes "
            "(allocator `max_active_pipelines` default 4); do not enable every strategy/feature named in specs\n",
        )
    content = content.replace(
        "5 active strategies",
        "few funded lanes (allocator cap)",
    )
    content = content.replace(
        "all active pipelines + classical optimization only",
        "more capacity available — still fund HEALTHY lanes only + classical optimization",
    )
    return patch_quantum_classical_only(
        patch_user_capital(patch_user_survivability(content))
    )


RISK_KERNEL_TOOLS = """
## Independent Risk Kernel (Out-of-Process)

Deterministic NON-LLM guard — agents cannot bypass. Policy: `~/.openclaw/risk_kernel/policy.yaml`

- **Pre-trade validation:** `http://127.0.0.1:19001/v1/validate` (ALLOW/DENY; fail-closed if unreachable)
- **Reconciliation gate:** `http://127.0.0.1:19002/v1/pre_trade` (believed vs exchange truth)
- **Kill switch CLI:** `~/.openclaw/safety/bin/titan-safety kill activate --operator YOU --reason "..."`
- **Promotion gate:** `titan-safety promotion approve --response YES` (explicit YES only)
- **Operator heartbeat:** `titan-safety heartbeat` (resets dead-man's switch timer)
- Enforces: notional cap, exposure cap, leverage, loss-velocity, position count, allow-list, slippage
- Can VETO trades and trigger FLATTEN + key revocation independent of GUARDIAN/model
- **Power-loss:** HALT trading per `policy.yaml` + `infra/power_requirements.yaml`

## Signing Isolation (TRENCH-OPS)

Transaction signing routes to the **signing_node** — logically isolated, UPS-protected.
Config: `~/.openclaw/infra/signing_node.yaml` | Endpoint: `http://127.0.0.1:19010` (host configurable)

- TRENCH-OPS / LAMARCK submit signing requests via `signingNode.endpoint` — never sign in agent runtime
- Minimal OS, no evolution workloads (DGM-H, GEPA, fuzzing) on signing partition
- Mac Mini vault holds key metadata + Trezor ceremonies; signing execution on signing_node
- Pre-sign gates: GUARDIAN + risk kernel + EIP-712 typed data only

"""


def build_tools(text: str) -> str:
    block = extract_deploy_block(text, "TOOLS.md")
    if not block:
        block = find_section(text, "# TOOLS.md", ["# §H — IDENTITY"])
    # Trim hardware essays that duplicate MEMORY pointers
    lines = []
    skip_hw = False
    for line in block.splitlines():
        if line.startswith("# §HW-DEFI") or line.startswith("## GPU Compute"):
            skip_hw = True
        if line.startswith("# §H — IDENTITY"):
            break
        if skip_hw and line.startswith("## ") and "GPU" not in line:
            skip_hw = False
        if not skip_hw:
            lines.append(line)
    content = "\n".join(lines).strip() + "\n"
    if "Independent Risk Kernel" not in content:
        content = content.rstrip() + "\n" + RISK_KERNEL_TOOLS
    content = patch_quantum_classical_only(content)
    return truncate_to_chars(content, BOOTSTRAP_MAX_CHARS)


def build_identity(text: str) -> str:
    overview = find_section(text, "## System Overview", ["## AUTONOMY PRINCIPLE"])
    overview = patch_quantum_classical_only(overview)
    return f"""# IDENTITY — the Titan UNIFIED FRAMEWORK

## Framework

- **Name:** TITAN (OpenClaw + Hermes Unified Framework)
- **Version:** v49.7 | Build: 2026-05-28
- **Codename:** the Titan
- **Operator:** Hyperion (sole human operator)

## Architecture

- **OpenClaw:** Gateway & messaging hub (`~/.openclaw/`)
- **Hermes:** Cognitive engine (`~/.hermes/`)
- **Shared skills:** `~/.openclaw/workspace/skills/`

## Compute Topology

- **TITANHOME (primary):** Threadripper PRO 9995WX + ASUS WRX90E-SAGE SE + 512GB DDR5-6000 ECC
  + 2× RTX PRO 6000 Blackwell Max-Q (192GB VRAM) + Micron 7500 Pro boot + 2× WD SN8100 4TB
  + Super Flower 2200W Ti + LBE-1420 GPSDO + PiKVM V4 Plus + TPM-SPI
  — Tier 1/2 inference, REVM, risk kernel + safety services
- **TITANSPARK:** ASUS GX10 — utility inference (Qwen3-30B :30002) + operator gateway failover
- **Mac Mini vault:** Mac Mini 2018 i7 6-core, 64GB DDR4 — key metadata, Trezor ceremonies
- **Edge mesh (Phase 1):** single PoP — **EDGE-FRA** — TKY/SIN/USE/AMS deferred Phase 3+
- **Signing node:** isolated endpoint (`signingNode` :19010) — UPS-protected
- **BOM:** `~/.openclaw/infra/hardware_bom.yaml`

## Models (ALL LOCAL — 3-Tier + Dual Tier-3 R&D)

- **Tier 1 (:30000, GPU 0):** Qwen3-30B-A3B FP8 — signals, risk, execution (critical path) — UNCHANGED
- **Tier 2 (:30001, GPU 1):** Qwen3-Coder-Next-80B — orchestration, strategy, code — UNCHANGED
- **Tier 3a (:30005, off-peak):** DeepSeek V4 Pro — **PRIMARY** long-horizon R&D/evolution
- **Tier 3b (:30003, off-peak):** GLM-5.2 Q4_K_M — **SECONDARY** R&D/evolution
- **Utility (:30002, TITANSPARK):** Qwen3-30B-A3B — HERALD, ATLAS, FORGE, etc.
- **Embedder:** Qwen3-Embedding-0.6B (:30004)
- **Constraint:** No closed/cloud models on live path; TRENCH-OPS/GUARDIAN/EXECUTOR stay on Tier 1/2 only

## Scale

- 23 agents | 14 chains | 108+ signals | 775+ CBs | 65 skills | 26 workflows | **47-pipeline catalog**
- **Selective activation:** catalog size ≠ required set — fund ≤`max_active_pipelines` (default 4) HEALTHY lanes
- Quantum agents: DORMANT (100% classical execution)

## Bootstrap Limits

- bootstrapMaxChars: 20,000 per file
- bootstrapTotalMaxChars: 150,000 total
- Sub-agents: AGENTS.md + TOOLS.md only (minimal prompt mode)

{overview}
"""


def build_heartbeat(text: str) -> str:
    return """# HEARTBEAT — Scheduled Tasks

Natural-language scheduling for Hermes cron + OpenClaw heartbeat.

## Daily

- **08:00 UTC — Daily Brief (HERALD → Telegram)**
  Portfolio snapshot, top 3 signals, risk flags, edge-mesh health, vault status,
  §MAINT status, §GRIS digest (5-15 candidates from 800+ daily triage).

## Hourly

- **:00 UTC — Performance Report (§TGCMD.2)**
  Institutional digest via `herald_notify` skill: JSON payload + Markdown summary.
  Overall summary, per-strategy breakdown with trade-level reason codes,
  system health, flags/pending actions. Informational only — no per-trade approval queue.

## Operator Heartbeat (Dead-Man's Switch)

- **Daily ping:** Operator `OK` or any Telegram command resets heartbeat timer
- **>48h miss:** De-risk — reduce positions 50%, pause new entries, CRITICAL alert
- **>72h miss:** Flatten to stable collateral; halt non-routine pipelines
- **Never:** Auto-promote strategies or evolution on operator absence
- **Recovery:** Operator sends `RESUME` after restoring heartbeat

## Real-Time Trade Notifications (§TGCMD.3)

- **HERALD → Telegram** on every trade fill (entry/exit)
- **Immediate alert** when material: >0.5% equity impact OR severity CRITICAL/HIGH
- **Portfolio footer** appended on material events
- Templates: `~/.openclaw/workspace/telegram/templates/`
- Formatter: `~/.openclaw/workspace/skills/herald_notify/notify.py`

## Continuous Heartbeats

- **ARCHON:** orchestration loop — delegate tasks, monitor agent health (30s)
- **GUARDIAN:** risk scan — position sizing, drawdown tiers, CB triggers (15s)
- **NEXUS:** data feed health — RPC latency, feed staleness (60s)
- **FORGE:** infrastructure — service health, GPU inference schedule, NATS bus, UPS telemetry (60s)
- **SENTINEL:** security scan — CodeQL gate, dissent review queue (5m)

## Weekly

- **Monday 09:00 UTC — HORIZON R&D Brief**
  Compute ledger, skill evolution summary, dissent log review.

- **Sunday 22:00 UTC — Profit Sweep Check (ATLAS)**
  If portfolio ≥$35K: sweep 20% of weekly profit to Trezor Safe 7.

## GPU Schedule (TITANHOME)

- **Priority 1-2 inference:** GLM-5.2 orchestrator + REVM — **NEVER preempted** during market hours
- **Off-peak only:** CuEVM fuzzing, Monte Carlo backtest, skill evolution training (06:00-10:00 UTC or 22:00-06:00)
- Spec: `~/.openclaw/infra/gpu_schedule.yaml` — enforced by FORGE heartbeat

## Phase-Dependent

- **Phase 1 ($2,500):** Few funded lanes only (e.g. P1/P3/P7/P8/P11 as capital allows) — not the full catalog
- **Phase 2 ($10K+):** Add lanes only when TCA/allocator funds them (e.g. P29/P6/P18 when healthy)
- **Phase 3 ($50K+):** Optional expansion (P34/P40/P41) — still capped by `max_active_pipelines`
- **Phase 4 ($100K+):** More capacity available — still **not** "run every pipeline"; fund HEALTHY lanes only

Catalog size ≠ required set. Allocator `max_active_pipelines` (default 4) is the hard concentration cap.

## CRITICAL Alert Bypass

Immediate Telegram alert (bypasses hourly schedule) for:
1. 12% drawdown in 24h
2. Hardware failure (GPU/CPU/NVMe)
3. Security breach
4. DGM-H SOUL.md modification attempt
5. Exchange API failure >5min
6. Unknown smart contract interaction
"""


def build_bootstrap() -> str:
    return """# BOOTSTRAP — First-Run Ritual

**Delete this file after first successful run.** One-time setup checklist.

## Prerequisites

- [ ] Ubuntu 24.04 LTS, Python 3.12, Node.js 20+, systemd 255
- [ ] `npm install -g openclaw@latest`
- [ ] `pip install hermes-agent`
- [ ] NVIDIA drivers + CUDA 13.3 (for GPU workloads)

## Environment

- [ ] Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_USER_ID` in `~/.openclaw/.env`
- [ ] Set `HERMES_HOME=~/.hermes`
- [ ] Verify `openclaw.json` and `config.yaml` deployed

## Hardware Verification (TITANHOME)

- [ ] CPU: Threadripper PRO 9995WX (96C/192T) detected
- [ ] GPU: 2× RTX PRO 6000 Blackwell Max-Q (96GB each) — `nvidia-smi -L`
- [ ] RAM: 512GB DDR5-6000 ECC — `free -h`
- [ ] Boot: Micron 7500 Pro 3.8TB | Data: 2× WD Black SN8100 4TB
- [ ] PSU: Super Flower Leadex Titanium 2200W
- [ ] GPSDO: LBE-1420 PPS locked — `chronyc sources`
- [ ] PiKVM V4 Plus reachable | TPM-SPI baseline at `/etc/mnemosyne/tpm-baseline`
- [ ] BOM spec: `~/.openclaw/infra/hardware_bom.yaml`

## Model Endpoints (3-Tier)

- [ ] Tier 1 :30000 GPU 0 — Qwen3-30B-A3B FP8 (critical path: signals, risk, execution)
- [ ] Tier 2 :30001 GPU 1 — Qwen3-Coder-Next-80B (orchestration, strategy)
- [ ] Tier 3a :30005 off-peak ONLY — DeepSeek V4 Pro PRIMARY R&D (NEVER on live trade path)
- [ ] Tier 3b :30003 off-peak ONLY — GLM-5.2 SECONDARY R&D (NEVER on live trade path)
- [ ] Utility :30002 TITANSPARK (ASUS GX10) — Qwen3-30B utility agents
- [ ] Embedder :30004 — Qwen3-Embedding-0.6B
- [ ] Verify: `curl localhost:30000/health` and `curl localhost:30001/health`

## Infrastructure

- [ ] NATS JetStream running (`nats-server -js`)
- [ ] Erigon node syncing (Ethereum mainnet txpool) — EDGE-FRA for Phase 1
- [ ] Yellowstone gRPC (Solana) connected
- [ ] Verify Phase 1 edge: EDGE-FRA RTT <100ms (single PoP sufficient for $2.5K)
- [ ] Deploy infra specs: `~/.openclaw/infra/` (hardware_bom, power_requirements, signing_node, gpu_schedule)
- [ ] **UPS installed and tested** — ≥3000VA, ≥15 min runtime (REQUIRED before live capital)
- [ ] Power-loss drill: mains disconnect → trading HALT + CRITICAL alert
- [ ] Signing node endpoint reachable: `curl http://127.0.0.1:19010/health`
- [ ] Confirm TRENCH-OPS routes signing to signing_node (not agent runtime)

## Agent Verification

- [ ] `openclaw gateway status` — all 9 bootstrap files loaded
- [ ] `hermes agent status` — config.yaml valid, skills symlink OK
- [ ] Send test Telegram message — ARCHON responds with JSON ack
- [ ] Run `python3 ~/.openclaw/workspace/skills/herald_notify/notify.py` — sample trade renders
- [ ] Verify `~/.openclaw/workspace/telegram/schema/trade_notification.v1.json` present
- [ ] Spawn sub-agent — confirm AGENTS.md + TOOLS.md only (minimal mode)
- [ ] Trigger `status report` — routine trades auto-execute; promotions show PENDING_PROMOTION_APPROVAL
- [ ] Verify `~/.openclaw/risk_kernel/policy.yaml` present and referenced in openclaw.json
- [ ] Confirm TIMEOUT on promotion prompt → HOLD (not auto-promote)
- [ ] Confirm Phase 5 go/no-go requires explicit operator YES

## Quantum (DORMANT)

- [ ] QCC/QSA/QRP confirmed dormant — classical-only mode active
- [ ] REVM simulation pool :30020 responding
- [ ] CuEVM fuzzing :30012 available (off-peak)

## Safety Services (Pre-Capital)

- [ ] Install Python safety deps: `pip3 install -r ~/.openclaw/safety/requirements.txt`
- [ ] Enable safety systemd units (user or system):
  - `titan-risk-kernel.service` (:19001)
  - `titan-reconciliation.service` (:19002)
  - `titan-status-aggregator.service` (:19003)
  - `titan-portfolio-risk.service` (:19004)
  - `titan-dead-mans-switch.service` (:19005)
- [ ] Verify health: `curl -s http://127.0.0.1:19003/health | jq`
- [ ] Verify portfolio risk: `curl -s http://127.0.0.1:19004/health`
- [ ] Run unit tests: `python3 -m pytest ~/path/to/titan-deploy/tests -q`
- [ ] Run chaos harness: `python3 ~/path/to/titan-deploy/tests/chaos/chaos_harness.py`
- [ ] Run adversarial harness: `python3 ~/path/to/titan-deploy/tests/adversarial/adversarial_harness.py`
- [ ] Review playbooks: `~/.openclaw/playbooks/` (promotion, red-team, kill switch, wind-down)
- [ ] Confirm air-gapped staging: `~/.openclaw/staging/` exists; `airGappedStaging: true` in openclaw.json
- [ ] Test kill switch: `kill activate`, then `kill sign --command RESUME` + `kill deactivate --signed ...`
- [ ] Confirm pre-trade DENY when risk kernel stopped (fail-closed)
- [ ] Confirm promotion requires explicit `YES` via `titan-safety promotion approve`
- [ ] Read `PRODUCTION_READINESS.md` — DO NOT deploy real capital until all gates pass

## Capital Phase 1 (PAPER/SHADOW ONLY UNTIL CHECKLIST COMPLETE)

- [ ] Complete 3+ days paper trading per strategy
- [ ] Complete shadow execution phase with divergence <15%
- [ ] Micro-live ≤0.1% equity with kill switch armed
- [ ] Phase 5 explicit operator YES recorded in promotion audit log
- [ ] Only then configure live keys and starting capital in ATLAS
- [ ] **UPS acknowledged** for live capital (`~/.openclaw/infra/power_requirements.yaml`)

## Capital Deposit / Withdraw (Smoke Test)

- [ ] `titan-safety capital deposit --amount 2500 --asset USDC --source bootstrap-test`
- [ ] `titan-safety capital balance` — equity $2,500, available $2,500
- [ ] Telegram: `/deposit 100 USDC` — HERALD confirms deposit
- [ ] `titan-safety capital withdraw --amount 100 --asset USDC` — succeeds (under 20% gate)
- [ ] `titan-safety capital withdraw --amount 600 --asset USDC` — queues confirm (>20% of $2,500)
- [ ] `titan-safety capital withdraw --confirm wd-XXXXXXXX` — executes after confirm
- [ ] `titan-safety capital verify-audit` — audit chain valid
- [ ] `/balance` via Telegram — shows GROWTH phase below $35K
- [ ] `/sweep` below $35K — reports growth phase, no sweep

## Post-Deploy Smoke Test

1. `openclaw gateway status` — bootstrap char counts OK
2. `hermes agent status` — skills symlink valid
3. Telegram test message — structured JSON response
4. Sub-agent spawn — minimal prompt mode confirmed
5. Promotion timeout smoke — verify HOLD/de-risk, not auto-promote
6. Risk kernel stub — verify policy.yaml loads from openclaw.json path

## Safety Posture Verification

- [ ] Drawdown tiers: 2% alert / 5% soft pause / 8% reduce / 10% CRITICAL / 12% halt
- [ ] Bounded autonomy matrix in SOUL.md + openclaw.json
- [ ] Portfolio risk + MRM modules installed
- [ ] Trade voting honesty documented in AGENTS.md (advisory + risk_kernel veto)
- [ ] Model tier architecture: GLM-5.2 NOT on critical path
- [ ] Evolution workflows shadow-only until human YES
- [ ] 3-day paper minimum enforced before live promotion
- [ ] Dead-man's switch: no heartbeat → de-risk/flatten
- [ ] Risk kernel pre-trade validation wired and fail-closed
- [ ] Position reconciliation gate active (mock adapter until live keys)
- [ ] Kill switch tested (CLI + file flag)
- [ ] Decision audit hash-chain verifier passes

## Kill Criteria (halt immediately if any occur)

- Risk kernel or reconciliation service unreachable during trading window
- Position divergence exceeds threshold
- 12% drawdown halt tier in 24h (10% = CRITICAL alert)
- Operator heartbeat >72h
- Any SOUL.md modification attempt
- Chaos harness regression on deploy

## Completion

- [ ] All checks pass → delete this BOOTSTRAP.md file
- [ ] Enable systemd: `systemctl --user enable --now llama-server-tier1 llama-server-tier2 titan-risk-kernel titan-reconciliation titan-dead-mans-switch titan-portfolio-risk titan-status-aggregator titan-allocator titan-tca titan-security-ops titan-signing-node openclaw-gateway hermes-gateway`
"""


def build_boot() -> str:
    """OpenClaw BOOT.md — short gateway-restart checklist (docs.openclaw.ai)."""
    return """# BOOT.md — Gateway Restart Checklist

Keep short. Runs on gateway restart when internal hooks are enabled.

1. Confirm safety services healthy: `:19001`–`:19007`, `:19010` (`curl …/health`)
2. Confirm kill switch inactive: `titan-safety kill status`
3. Confirm evolution freeze if live capital: `titan-safety evolution status`
4. Confirm inference tiers up: `:30000` (critical), `:30001` (reasoning)
5. Do **not** auto-promote or auto-resume halted pipelines
6. Notify HERALD only on CRITICAL/HIGH failures

Outbound alerts: use the message tool / herald_notify — do not spam routine OK.
"""


def extract_all(text: str) -> dict[str, str]:
    builders = {
        "SOUL.md": lambda t: build_soul(t),
        "AGENTS.md": lambda t: build_agents(t),
        "MEMORY.md": lambda t: build_memory_trimmed(t),
        "USER.md": lambda t: build_user(t),
        "TOOLS.md": lambda t: build_tools(t),
        "IDENTITY.md": lambda t: build_identity(t),
        "HEARTBEAT.md": lambda t: build_heartbeat(t),
        "BOOTSTRAP.md": lambda t: build_bootstrap(),
        "BOOT.md": lambda t: build_boot(),
    }
    result = {}
    for name in BOOTSTRAP_FILES:
        content = builders[name](text)
        if name != "MEMORY.md":
            content = truncate_to_chars(content, BOOTSTRAP_MAX_CHARS)
        result[name] = content
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract bootstrap files")
    parser.add_argument("input", type=Path, nargs="?", default=RECONCILED_PATH)
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=OUTPUT_DIR / "bootstrap"
    )
    args = parser.parse_args()

    text = read_source(args.input)
    files = extract_all(text)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, content in files.items():
        path = args.output_dir / name
        write_text(path, content)
        blen = byte_len(content)
        total += blen
        print(f"  {name}: {blen} bytes, {content.count(chr(10))+1} lines")

    print(f"Total: {total} bytes (limit {BOOTSTRAP_TOTAL_MAX_CHARS})")
    if total > BOOTSTRAP_TOTAL_MAX_CHARS:
        print("WARNING: total exceeds bootstrap limit", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
