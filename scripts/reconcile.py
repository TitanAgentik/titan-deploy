#!/usr/bin/env python3
"""Reconcile policy contradictions for survivability-hardened deploy bundle."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NORMALIZED_PATH, RECONCILED_PATH, OUTPUT_DIR, read_source, write_text


def reconcile_counts(text: str) -> str:
    text = text.replace("27 workflows", "26 workflows")
    # Catalog size is 47 — never imply all must run. Prefer selective-activation wording.
    text = re.sub(
        r"Routine trade execution \(all 4[67] pipelines\)",
        "Routine trade execution (funded lanes only — catalog has 47; allocator caps active set)",
        text,
    )
    text = re.sub(
        r"Active Strategies \(4[67] pipelines",
        "Active Strategies (catalog: 47 pipelines",
        text,
    )
    # Longer phrase first — otherwise "all 47 pipelines" swallows "...active".
    text = text.replace(
        "all 47 pipelines active",
        "more capacity available — still fund HEALTHY lanes only (not every pipeline)",
    )
    text = text.replace("all 46 pipelines", "funded lanes from the 47-pipeline catalog")
    text = text.replace("all 47 pipelines", "funded lanes from the 47-pipeline catalog")
    # Agent/pipeline totals drift throughout the doc — normalize to 20 agents.
    text = re.sub(r"\bALL 2[34] agents\b", "ALL 20 agents", text)
    text = re.sub(r"\ball 2[34] agents\b", "all 20 agents", text)
    text = re.sub(r"\b2[34] agents communicate\b", "20 agents communicate", text)
    text = re.sub(r"\b23 agents\b", "20 agents", text)
    return text


def reconcile_quantum(text: str) -> str:
    """Remove/neutralize quantum agents; align with 100% classical execution."""
    if "QUANTUM STATUS (reconciled)" not in text:
        text = text.replace(
            "100% Classical Execution (Quantum simulators removed",
            "100% Classical Execution — quantum agents removed (Quantum simulators removed",
            1,
        )
        quantum_status = """
> **QUANTUM STATUS (reconciled):** Quantum-coordination agents (QCC/QSA/QRP) **removed** from the catalog.
> No cuQuantum, Wukong, or Tier 3 cloud QPU dispatch. 100% classical GPU execution (REVM, CuEVM, ML inference).
> OS CSPRNG for all cryptographic entropy. Quantum skills archived — not loaded at runtime.
> QI Optimizer (`quantum_inspired.py`) is classical SA only — not a quantum agent.

"""
        anchor = "## AUTONOMY PRINCIPLE"
        if anchor in text and "QUANTUM STATUS (reconciled)" not in text:
            text = text.replace(anchor, quantum_status + anchor, 1)

    # Strip quantum-coordination agent table from routing (agents removed from catalog)
    text = re.sub(
        r"### Quantum-coordination agents \(3\)[^\n]*\n(?:\|[^\n]*\n)+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"\| QCC \|[^\n]*\|\n",
        "",
        text,
    )
    text = re.sub(
        r"\| QSA \|[^\n]*\|\n",
        "",
        text,
    )
    text = re.sub(
        r"\| QRP \|[^\n]*\|\n",
        "",
        text,
    )
    text = re.sub(
        r"\| QCC \(Quantum Compute Coordinator\) \|[^\n]+\|\n",
        "",
        text,
    )
    text = re.sub(
        r"\| QSA \(Quantum Signal Agent\) \|[^\n]+\|\n",
        "",
        text,
    )
    text = re.sub(
        r"\| QRP \(Quantum Randomness Provider\) \|[^\n]+\|\n",
        "",
        text,
    )

    # Dispatch, routing, and active-path language
    text = re.sub(
        r"- \*\*Quantum dispatch:\*\* Fully automated via QCC → NATS JetStream\.",
        "- **Quantum dispatch:** DISABLED (classical-only mode).",
        text,
    )
    text = re.sub(
        r"- \*\*Quantum dispatch:\*\* agents submit quantum requests to QCC via NATS JetStream queue;[^\n]+",
        "- **Quantum dispatch:** REMOVED (classical-only mode). No quantum agents; no NATS quantum queue.",
        text,
    )
    text = re.sub(
        r"- Quantum compute routing",
        "- Classical GPU compute routing (REVM, CuEVM)",
        text,
        count=1,
    )
    text = re.sub(
        r"OriginQ: Wukong-180 QPU via qcloud\.originqc\.com\.cn \(PQC-encrypted, Tier 2 — active by default for 35-180q circuits\)",
        "OriginQ Wukong-180: **DORMANT** — not connected for live capital (classical-only mode)",
        text,
    )
    text = re.sub(
        r"only when Tier 3 active",
        "disabled — quantum dormant",
        text,
    )
    text = re.sub(
        r"if Wukong Tier 3 active",
        "disabled — quantum dormant",
        text,
    )
    text = re.sub(
        r"quantum optimization active",
        "classical optimization only (quantum dormant)",
        text,
    )
    text = re.sub(
        r"quantum-budget status",
        "classical compute status (quantum dormant)",
        text,
    )
    text = re.sub(
        r"- Quantum-budget: monthly Wukong shot ceiling[^\n]*",
        "- Quantum budget: **N/A** — quantum layer permanently disabled for live capital",
        text,
    )
    text = re.sub(
        r"\| ORACLE \| Signal generation \(108 signals \+ narrative \+ quantum\) \|",
        "| ORACLE | Signal generation (108 signals + narrative, classical-only) |",
        text,
        count=1,
    )
    text = re.sub(
        r"108 signals \+ narrative \+ quantum-enhanced",
        "108 signals + narrative (classical-only; quantum dormant)",
        text,
    )
    text = re.sub(
        r" \+ 3 quantum-coord(?: dormant)?\)",
        ")",
        text,
    )
    text = re.sub(
        r"orchestrator/quantum-coord agents",
        "orchestrator agents",
        text,
    )
    text = re.sub(
        r"orchestrator agents \(quantum-coord dormant\)",
        "orchestrator agents",
        text,
    )
    text = re.sub(
        r"## Agent Routing \(23 agents\)",
        "## Agent Routing (20 agents)",
        text,
    )
    text = re.sub(
        r"\*\*Total: 23 agents",
        "**Total: 20 agents",
        text,
    )
    text = re.sub(
        r"Quantum-augmented: QC\.\d+ [^|]+",
        "Classical-only (quantum dormant)",
        text,
    )
    text = re.sub(
        r"Quantum-enhanced: QC\.\d+ [^|]+",
        "Classical-only (quantum dormant)",
        text,
    )
    text = re.sub(
        r"Enhanced with quantum signal provenance tracking",
        "Classical signal provenance tracking only (quantum dormant)",
        text,
    )
    text = re.sub(
        r"\(— OpenClaw framework \+ quantum augmentation \+ operator-locked BOM\)",
        "(— OpenClaw framework, classical-only compute + operator-locked BOM)",
        text,
    )
    text = re.sub(
        r"- Quantum \(4-tier hybrid, async\):[^\n]+",
        "- Quantum: **DORMANT** — 4-tier hybrid stack not active; classical GPU only",
        text,
    )
    text = re.sub(
        r"- \[ \] QCC: initialize cuQuantum Appliance[^\n]+",
        "- [x] Quantum agents: **removed** — classical-only mode",
        text,
    )
    text = re.sub(
        r"- \[ \] QRP: fill entropy pool \(36 KB initial from first QRNG batch\)",
        "- [x] Entropy: OS CSPRNG (quantum agents removed)",
        text,
    )
    text = re.sub(
        r"optional QAE speedup via QCC",
        "classical Monte Carlo only (quantum dormant)",
        text,
    )
    text = re.sub(
        r"Wukong monthly shot budget tracked separately \(disabled — quantum dormant; local compute = unlimited\)",
        "Wukong budget: **disabled** — quantum dormant; no cloud QPU spend",
        text,
    )
    text = re.sub(
        r"\*\*Wukong Tier 3 unavailable\*\*: QCC continues on Tier 1/2 \(local GPU\)\. No impact on trading operations\. No impact on trading operations\.",
        "**Quantum layer dormant**: classical execution only. No cuQuantum/Wukong paths active.",
        text,
    )
    return text


def reconcile_autonomy_scope(text: str) -> str:
    """Routine trades autonomous; human gates for promotion/evolution/high-risk."""
    text = text.replace(
        "All authorization flows are FULLY AUTOMATED. No human review required for standard operations.",
        "ROUTINE trades execute autonomously within GUARDIAN risk limits. "
        "Human gates apply to strategy promotion, evolution-touched agents, leverage changes, "
        "flash-loan live deployment, and positions >1% equity.",
    )
    text = re.sub(
        r"\| ARBITER \| Backtest validation \| Auto-approve strategies \|",
        "| ARBITER | Backtest validation | Auto-run gates; Phase 5 human YES required for live |",
        text,
        count=1,
    )
    text = re.sub(
        r"\| sia_self_improvement_loop \| Auto-evolve, auto-promote, auto-rollback \|",
        "| sia_self_improvement_loop | Shadow evolve; human promotion to live |",
        text,
    )
    text = re.sub(
        r"\| deploy_lifecycle_pipeline \| Auto-promote on Phase 1-4 pass \(Phase 5 REMOVED\) \|",
        "| deploy_lifecycle_pipeline | Phases 1-4 auto; Phase 5 explicit human YES for full live |",
        text,
    )
    text = re.sub(
        r"\| eurekagent_strategy_discovery \| Auto-discover, auto-implement, auto-deploy \|",
        "| eurekagent_strategy_discovery | Shadow discover/implement; human promotion to live |",
        text,
    )
    # Title + header autonomy claims: replace "zero human gates" with the
    # bounded-autonomy matrix summary so the doc never contradicts AGENTS.md.
    text = re.sub(
        r"AUTONOMOUS OPERATION MODE — ZERO HUMAN GATES FOR STANDARD OPERATIONS",
        "AUTONOMOUS OPERATION MODE — BOUNDED AUTONOMY (routine ops auto; "
        "promotion/evolution/leverage/>1% equity require human YES)",
        text,
    )
    text = re.sub(
        r"- \*\*Autonomy\*\*: FULLY AUTONOMOUS — zero human gates for standard operations;[^\n]*",
        "- **Autonomy**: BOUNDED — routine trades <1% equity auto-execute within GUARDIAN "
        "limits; human YES required for promotion to live, evolution deploys, leverage "
        "changes, flash-loan live, and trades >1% equity; operator receives informational "
        "notifications plus CRITICAL alerts for 6 emergency conditions",
        text,
    )
    text = re.sub(
        r"#### Signal / on-chain / macro tier \(5 agents\) — FULL AUTONOMY",
        "#### Signal / on-chain / macro tier (5 agents) — autonomous within GUARDIAN limits",
        text,
    )
    text = text.replace(
        "**ABSOLUTE CONTROL PROTOCOL INTEGRATION**:",
        "**OPERATOR DASHBOARD INTEGRATION (informational + promotion gates)**:",
    )
    # Routine trades: no PENDING_HUMAN_APPROVAL; promotions use PENDING_PROMOTION_APPROVAL
    text = re.sub(
        r"All system actions and trade proposals halt in a `PENDING_HUMAN_APPROVAL`\s*"
        r"state\. Approving a trade via the GUI instantly clears the Telegram\s*"
        r"prompt, and vice-versa, utilizing the shared NATS event bus\.",
        "Routine trades execute autonomously (no per-trade approval queue). "
        "Strategy promotions, evolution deploys, and high-risk actions enter "
        "`PENDING_PROMOTION_APPROVAL` until operator explicit YES via Telegram/GUI.",
        text,
        flags=re.DOTALL,
    )
    return text


def reconcile_phase5_and_timeout(text: str) -> str:
    """Restore Phase 5 human gate; silence defaults to HOLD/de-risk."""
    text = re.sub(
        r"- \*\*Phase 5 \(Go/No-Go\):\*\* \*\*REMOVED\.\*\* Human approval BYPASSED\. Auto-promote on Phase 1-4 pass\.",
        "- **Phase 5 (Go/No-Go):** **ACTIVE.** Explicit operator YES required before full live promotion.",
        text,
    )
    text = re.sub(
        r"\| TIMEOUT \| \*\*Auto-promote\*\* \(default — operator absence \\?= implicit approval\) \|",
        "| TIMEOUT | **HOLD / de-risk** (default — silence never promotes; flatten exposure) |",
        text,
    )
    text = re.sub(
        r"\| YES \| Auto-promote \|",
        "| YES | Promote to live (explicit operator consent) |",
        text,
    )
    text = re.sub(
        r"timeout_policy: \"No timeout — system never waits for operator\. Auto-promote is default\. Operator commands are processed when received but never block operations\.\"",
        'timeout_policy: "Silence defaults to HOLD/de-risk. Never auto-promote on timeout. '
        'Phase 5 awaits explicit YES; pending promotions defer indefinitely."',
        text,
    )
    text = re.sub(
        r"\*\*Phase 5 Go/No-Go human confirmation has been REMOVED per §AUTONOMY PRINCIPLE\.\*\*",
        "**Phase 5 Go/No-Go requires explicit operator YES before full live promotion.**",
        text,
    )
    text = re.sub(
        r"proceed_to: \"Phase 5 — Auto-Promotion \(HUMAN GATE REMOVED\)\"",
        'proceed_to: "Phase 5 — Go/No-Go (explicit operator YES required)"',
        text,
    )
    text = re.sub(
        r"# §DEPLOY_LIFECYCLE\.5 — Phase 5: Auto-Promotion \(HUMAN GATE REMOVED\)",
        "# §DEPLOY_LIFECYCLE.5 — Phase 5: Go/No-Go (Human Gate REQUIRED)",
        text,
    )
    text = re.sub(
        r"Phase 5 \(AUTO-PROMOTE — human gate REMOVED per §AUTONOMY PRINCIPLE\)",
        "Phase 5 (explicit operator YES required before full live)",
        text,
    )
    text = re.sub(
        r"✅ Auto-promoted to full live \(Phase 5 — auto-promotion, no human gate\)",
        "✅ Promoted to full live (Phase 5 — operator YES received)",
        text,
    )
    text = re.sub(
        r"Phase 6: Promotion Decision \(end of Tier 3 — approval or auto-promote\)",
        "Phase 6: Promotion Decision (end of Tier 3 — human YES required for live)",
        text,
    )

    # Phase 5 body still contradicted its (already-fixed) header — the strategy
    # is held pending explicit YES, not auto-promoted.
    text = text.replace(
        "Strategies that pass Phases 1-4 are AUTO-PROMOTED to full live deployment.  \n"
        "No Telegram confirmation required. Pre-authorized by default.",
        "Strategies that pass Phases 1-4 enter PENDING_PROMOTION_APPROVAL and wait "
        "for explicit operator YES via Telegram/GUI.  \n"
        "Silence = HOLD/de-risk. Never auto-promote on timeout.",
    )
    text = re.sub(
        r"phase_5_auto_promote:\s*\n"
        r"\s*confirmation_required: false  # WAS: true — REMOVED per §AUTONOMY PRINCIPLE\s*\n"
        r"\s*auto_promote: true\s*\n"
        r'\s*notification_mode: "informational_only"',
        'phase_5_go_no_go:\n'
        '  confirmation_required: true   # explicit operator YES before full live\n'
        '  auto_promote: false\n'
        '  timeout_policy: "hold_derisk"  # silence never promotes\n'
        '  notification_mode: "approval_required"',
        text,
    )
    text = text.replace(
        "    ⚡ DEPLOY PIPELINE — AUTO-PROMOTED",
        "    ⏸ DEPLOY PIPELINE — AWAITING OPERATOR YES",
    )
    text = text.replace(
        "    Phase:       5/6 — Auto-Promotion (No Human Gate)",
        "    Phase:       5/6 — Go/No-Go (operator YES required)",
    )
    text = text.replace(
        "    ⚡ AUTO-PROMOTED to full live trading.  \n"
        "    Watch mode: 24h active monitoring enabled.",
        "    ⏸ HELD pending operator YES before full live.  \n"
        "    Reply YES to promote; watch mode arms on promotion.",
    )
    # Freeform auto-promote narrative line (runs before 7-day→3-day rewrite,
    # so match only the stable tail).
    text = text.replace(
        "(§DEPLOY_LIFECYCLE) → auto-promote → deploy",
        "(§DEPLOY_LIFECYCLE) → Phase 5 operator YES → deploy",
    )
    text = text.replace(
        "# The system auto-archives on failure, auto-promotes on success, auto-rollbacks on breach.",
        "# The system auto-archives on failure and auto-rollbacks on breach; "
        "promotion to live requires explicit operator YES.",
    )
    return text


def reconcile_paper_minimum(text: str) -> str:
    """Align research gate and deploy lifecycle to 3-day paper minimum (operator directive)."""
    text = re.sub(
        r"\| Research gate \| 72h \(3-day\) paper-trading \+ backtest before live deployment \(R14-R15\) \|",
        "| Research gate | 3-day paper-trading minimum + backtest before live deployment (R14-R15) |",
        text,
    )
    text = re.sub(
        r"\| Research gate \| 7-day paper-trading minimum \+ backtest before live deployment \(R14-R15\) \|",
        "| Research gate | 3-day paper-trading minimum + backtest before live deployment (R14-R15) |",
        text,
    )
    text = re.sub(
        r"\| Backtesting gate \| ARBITER auto-approval after 7-day deployment pipeline \(§DEPLOY_LIFECYCLE\) before live execution — no human gate per §AUTONOMY PRINCIPLE \|",
        "| Backtesting gate | ARBITER runs 3-day §DEPLOY_LIFECYCLE; Phase 5 human YES before full live |",
        text,
    )
    text = re.sub(
        r"\| Backtesting gate \| ARBITER runs 7-day §DEPLOY_LIFECYCLE; Phase 5 human YES before full live \|",
        "| Backtesting gate | ARBITER runs 3-day §DEPLOY_LIFECYCLE; Phase 5 human YES before full live |",
        text,
    )
    text = re.sub(
        r"Research gate \| 72h \(3-day\) paper-trading",
        "Research gate | 3-day paper-trading minimum",
        text,
    )
    text = re.sub(
        r"Research gate \| 7-day paper-trading minimum",
        "Research gate | 3-day paper-trading minimum",
        text,
    )
    text = re.sub(
        r"shadow 24-72h",
        "shadow minimum 3-day paper",
        text,
    )
    text = re.sub(
        r"shadow minimum 7-day paper",
        "shadow minimum 3-day paper",
        text,
    )
    text = re.sub(
        r"\| `CB_EVERGREEN_APPROVAL_TIMEOUT` \| Pending approval not acted on within 72h \| MEDIUM \| Re-send Telegram reminder; if still no response after 7d → auto-defer candidate to next review cycle\. \|",
        "| `CB_EVERGREEN_APPROVAL_TIMEOUT` | Pending approval not acted on within 72h | MEDIUM | Re-send Telegram reminder; if still no response → HOLD/de-risk (never auto-promote) |",
        text,
    )
    # §DEPLOY_LIFECYCLE duration: 7-day → 3-day (gates unchanged)
    deploy_duration_replacements = [
        (r"ARBITER runs 7-day backtest", "ARBITER runs 3-day backtest"),
        (r"7-day deployment pipeline", "3-day deployment pipeline"),
        (r"7-day §DEPLOY_LIFECYCLE", "3-day §DEPLOY_LIFECYCLE"),
        (r"6-phase, 7-day deployment pipeline", "6-phase, 3-day deployment pipeline"),
        (r"backtest \(7 trading days\)", "backtest (3 trading days)"),
        (r"7-day paper-trading telemetry", "3-day paper-trading telemetry"),
        (r"Phase 1: 7-day tick-level backtest", "Phase 1: 3-day tick-level backtest"),
        (r"Phase 1 \(7-day backtest\)", "Phase 1 (3-day backtest)"),
        (r"last 2h of Day 7", "last 2h of Day 3"),
        (r"Last 2h of Day 7", "Last 2h of Day 3"),
        (r"Final 2 hours of Day 7", "Final 2 hours of Day 3"),
        (r"spanning 7 calendar days", "spanning 3 calendar days"),
        (r"7 calendar days, concurrent", "3 calendar days, concurrent"),
        (r"during 7-day pipeline", "during 3-day pipeline"),
        (r"entire 7-day pipeline", "entire 3-day pipeline"),
        (r"full 7-day pipeline", "full 3-day pipeline"),
        (r"7-day validation", "3-day validation"),
        (r"7-day post-deployment monitoring", "3-day post-deployment monitoring"),
        (r"7-day deployment pipeline enforcer", "3-day deployment pipeline enforcer"),
        (r"skip the 7-day deployment pipeline minimum", "skip the 3-day deployment pipeline minimum"),
        (r"Paper Trade \(7 calendar days", "Paper Trade (3 calendar days"),
        (r"≥5 of 7 days", "≥2 of 3 days"),
        (r"minimum 5 of 7 days profitable", "minimum 2 of 3 days profitable"),
        (r"Seven-Day Backtesting \(Days 1–7\)", "Three-Day Backtesting (Days 1–3)"),
        (r"Concurrent Paper-Trading \(Days 1–7\)", "Concurrent Paper-Trading (Days 1–3)"),
        (r"Micro-live test will activate in last 2h of Day 7", "Micro-live test will activate in last 2h of Day 3"),
    ]
    for pattern, repl in deploy_duration_replacements:
        text = re.sub(pattern, repl, text)
    return text


def reconcile_shadow_evolution(text: str) -> str:
    """Evolution and model swap paths are shadow-only until human promotion."""
    replacements = [
        (
            r"Auto-promote \(ML models passing gate\)",
            "Shadow-only; human YES for live (ML models passing gate)",
        ),
        (
            r"\| All 5 gates PASS \+ ML model \| \*\*Auto-promote\*\* via atomic swap \|",
            "| All 5 gates PASS + ML model | **Shadow hold** — human YES for atomic swap to live |",
        ),
        (
            r"Approval: Auto-promote \(LOW risk\); Telegram confirmation \(MEDIUM/HIGH risk\)",
            "Approval: Shadow-only for all evolution; Telegram YES required for live (all risk tiers)",
        ),
        (
            r"Hyperion can grant one-time auto-promote",
            "No auto-promote on timeout; explicit YES required",
        ),
        (
            r"Safety: 3-tier ARBITER validation gate; <2% equity auto-promote; ≥2% requires Hyperion",
            "Safety: 3-tier ARBITER validation gate; shadow-only until human YES (all equity tiers)",
        ),
        (
            r"Auto-approve: routine rebalances <2% equity, weekly profit sweeps, CB triggers, §RDSCOUT strategy promotions that pass all 3-tier validation with <2% equity requirement",
            "Require approval: strategy promotion, evolution-touched agents (DGM-H/GEPA/HyEvo/SIA LoRA/EurekAgent), leverage changes, flash-loan live deploy, positions >1% equity\n"
            "- Auto-execute: routine rebalances <1% equity, weekly profit sweeps (post-$15K), CB auto-responses per tier",
        ),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    return text


def reconcile_bft_honesty(text: str) -> str:
    """Document same-model BFT limitation; recommend heterogeneous voters."""
    text = re.sub(
        r"- \*\*BFT Voting Consensus:\*\* Automated 2-out-of-3 threshold\. No human voters\.",
        "- **BFT Voting Consensus:** 2-out-of-3 agent vote (ARCHON/CORTEX/GUARDIAN) — "
        "**same-model limitation:** all voters share GLM-5.2 weights; this is correlated consensus, "
        "not independent BFT. Recommend heterogeneous voter models for true fault tolerance. "
        "Independent risk kernel stub validates deterministically out-of-process.",
        text,
    )
    bft_note = (
        "\n\n> **BFT HONESTY (reconciled):** Orchestrator-tier voters (ARCHON, CORTEX, GUARDIAN) "
        "share the same base model — correlated failures possible. Treat as advisory consensus, "
        "not cryptographic BFT. Heterogeneous voters + out-of-process risk kernel recommended.\n"
    )
    if "BFT HONESTY (reconciled)" not in text:
        text = text.replace(
            "- **Trade authorization:** Automated via BFT consensus. <5s end-to-end.",
            "- **Trade authorization:** Automated via BFT consensus. <5s end-to-end."
            + bft_note,
            1,
        )
    return text


def reconcile_drawdown_tiers(text: str) -> str:
    """Align drawdown tiers to risk_kernel authority: 2/5/8/10/12%."""
    canonical = "2% alert / 5% soft pause / 8% reduce / 10% CRITICAL / 12% full halt"
    replacements = [
        (
            r"\| Drawdown threshold \| 3-tier circuit breakers \(3%/7%/12% 24h\) \|",
            f"| Drawdown threshold | 5-tier circuit breakers ({canonical}) |",
        ),
        (
            r"\| Drawdown threshold \| 4-tier circuit breakers \(3% / 7% / 12% CRITICAL / 15% halt\) \|",
            f"| Drawdown threshold | 5-tier circuit breakers ({canonical}) |",
        ),
        (r"3-tier: 3% / 7% / 12% / 15%", f"5-tier: {canonical}"),
        (
            r"4-tier: 3% soft pause / 7% reduce / 12% CRITICAL human alert / 15% full halt",
            f"5-tier: {canonical}",
        ),
        (
            r"drawdown breaches ≥2%",
            "drawdown breaches ≥2% (tiered: 2/5/8/10/12%)",
        ),
        (
            r"drawdown breaches ≥3% \(tiered: 3/7/12/15%\)",
            "drawdown breaches ≥2% (tiered: 2/5/8/10/12%)",
        ),
        (
            r"15-50% drawdown \(dynamic per strategy\)",
            "10% CRITICAL / 12% full halt (per risk_kernel)",
        ),
        (
            r"Portfolio drawdown 15-50% \(dynamic per strategy\) in 24h",
            "Portfolio drawdown ≥10% CRITICAL or ≥12% full halt in 24h",
        ),
        (
            r"12% drawdown in 24h",
            "12% drawdown halt tier in 24h (10% = CRITICAL alert)",
        ),
        (
            r"Max 15% portfolio drawdown before full halt \(4-tier: 3% soft pause / 7% reduce / 12% CRITICAL human alert / 15% full halt\)",
            f"Max 12% portfolio drawdown before full halt ({canonical})",
        ),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    return text


def reconcile_implicit_approval(text: str) -> str:
    """Remove operator-absence = implicit approval; silence never promotes."""
    replacements = [
        (
            r"- Operator absence = implicit approval \(system never waits\)",
            "- Operator absence ≠ approval — dead-man's switch de-risks at 48h, flattens at 72h",
        ),
        (
            r"Operator absence = implicit approval",
            "Operator absence ≠ approval — promotion requires explicit YES",
        ),
        (
            r'rationale: "Continuous autonomous operation — operator absence \\?= implicit approval"',
            'rationale: "Bounded autonomy — routine trades autonomous; promotion/evolution require explicit YES"',
        ),
        (
            r'rationale: "Continuous autonomous operation — operator absence = implicit approval"',
            'rationale: "Bounded autonomy — routine trades autonomous; promotion/evolution require explicit YES"',
        ),
        (
            r"Operator absence \\?= implicit approval \(system never waits\)",
            "Operator absence ≠ approval — dead-man's switch at 48h/72h",
        ),
        (
            r"All standard operations execute without human intervention\. Pre-authorized by default\.",
            "Routine trades execute autonomously within GUARDIAN + risk_kernel limits. "
            "Human YES required for promotion, evolution deploys, leverage changes, flash-loan live, "
            "and positions >1% equity. Silence on promotion = HOLD/de-risk.",
        ),
        (
            r"human_required: true  # Only for 6 CRITICAL conditions listed above",
            "human_required: true  # CRITICAL alerts + promotion gates; routine CB auto-responds",
        ),
        (
            r"timeout_policy: \"No timeout — system never waits for operator\. Auto-promote is default\.",
            'timeout_policy: "Silence defaults to HOLD/de-risk. Never auto-promote on timeout.',
        ),
        (
            # GUI/Telegram mirror comment: routine trades don't queue; promotions do.
            r"# All system actions and trade proposals halt in a `PENDING_HUMAN_APPROVAL`\s*\n+"
            r"# state\. Approving a trade via the GUI instantly clears the Telegram\s*\n+"
            r"# prompt, and vice-versa, utilizing the shared NATS event bus\.",
            "# Routine trades execute autonomously (no per-trade approval queue).\n"
            "#\n"
            "# Promotions / high-risk actions enter PENDING_PROMOTION_APPROVAL; approving\n"
            "#\n"
            "# via GUI or Telegram clears the other over the shared NATS event bus.",
        ),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    return text


def reconcile_model_tiers(text: str) -> str:
    """3-tier inference: Qwen3-30B critical, Qwen3-Coder-80B reasoning, GLM-5.2 offline."""
    replacements = [
        (
            r"GLM-5\.2 \(744B MoE, ~400GB Q4_K_M\) exceeds 192GB VRAM",
            "GLM-5.2 (744B MoE, ~400GB Q4_K_M) exceeds 192GB VRAM (2× RTX PRO 6000 96GB)",
        ),
        (
            r"GPU TP=2 \(`zai-org/GLM-5\.2` GGUF Q4_K_M via llama-server `:30000`",
            "GPU 0 (`Qwen3-30B-A3B` FP8 via llama-server `:30000`",
        ),
        (
            r"all signal/coding/orchestrator/quantum-coord agents share this single deployment",
            "critical-path signal/execution agents on Tier 1; orchestrator/reasoning on Tier 2",
        ),
        (
            r"\| ARCHON \| Orchestrator \+ A2A protocol coordinator \| GPU TP=2 \(`zai-org/GLM-5\.2`",
            "| ARCHON | Orchestrator + A2A protocol coordinator | GPU 1 (`Qwen3-Coder-Next-80B` :30001",
        ),
        (
            r"\| ORACLE \| Signal generation \(108 signals \+ narrative, classical-only\) \| `zai-org/GLM-5\.2`",
            "| ORACLE | Signal generation (108 signals + narrative, classical-only) | `Qwen3-30B-A3B` FP8 :30000",
        ),
        (
            r"\| TRENCH-OPS \| Trade execution \+ signing \+ calldata composition \| `zai-org/GLM-5\.2`",
            "| TRENCH-OPS | Trade execution + signing + calldata composition | `Qwen3-30B-A3B` FP8 :30000",
        ),
        (
            r"GPU inference pre-warming.*SGLang RadixAttention",
            "GPU inference pre-warming: llama-server keeps system prompt cached in KV cache",
        ),
        (
            r"Orchestrator-tier voters \(ARCHON, CORTEX, GUARDIAN\) share \*\*GLM-5\.2\*\* weights",
            "Trade voters (AUGUR, PREDATOR, ATLAS) use Tier 1/utility models — partially heterogeneous; "
            "orchestrator voters (ARCHON, CORTEX, GUARDIAN) share Tier 2 weights",
        ),
        (
            r"\*\*BFT Voting Consensus:\*\* 2-out-of-3 threshold consensus \(AUGUR \+ PREDATOR \+ ATLAS\)",
            "**Trade Voting Consensus:** 2-of-3 threshold (AUGUR + PREDATOR + ATLAS) — advisory; "
            "risk_kernel has final DENY",
        ),
        (
            # TRENCH-OPS is Tier 1 Qwen3-30B critical-path — never GLM-5.2 (offline R&D only)
            r"Runs on the shared GLM-5\.2 model with a coder-specialized system prompt; "
            r"FrontierSWE frontier-class coding quality — trades with GPT-5\.5/Claude Opus 4\.8 "
            r"on agentic coding benchmarks\. hot-swap to Qwen3-Coder-Next-80B-A3B FP8 "
            r"\(single-GPU TP=1 on cuda:1\) is available for high-throughput batch coding "
            r"sessions when ARCHON pre-empts the TP=2 deployment\.",
            "Runs on Tier 1 `:30000` Qwen3-30B-A3B FP8 (critical path — never GLM-5.2 or any "
            "cloud model). For high-throughput batch coding, ARCHON may route to Tier 2 "
            "`:30001` Qwen3-Coder-Next-80B FP8; live signing stays on Tier 1/2 local weights only.",
        ),
        (
            r'"frontier_swe": "frontier-class \(trades with GPT-5\.5 / Claude Opus 4\.8\)",',
            '"frontier_swe": "frontier-class local coding (Qwen3-Coder-Next-80B FP8)",',
        ),
        (
            r"- \*\*BFT Voting Consensus:\*\* 2-out-of-3 threshold consensus \(AUGUR \+ PREDATOR \+ ATLAS\) for trade authorization",
            "- **Trade Voting Consensus:** 2-of-3 (AUGUR + PREDATOR + ATLAS) for trade authorization — "
            "advisory; deterministic risk_kernel veto is authoritative",
        ),
        (
            r"Automated 2-out-of-3 threshold\. No human voters\.",
            "2-of-3 agent vote (AUGUR/PREDATOR/ATLAS) — advisory; risk_kernel DENY is authoritative.",
        ),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)

    if "MODEL TIER ARCHITECTURE (reconciled)" not in text:
        model_block = """
> **MODEL TIER ARCHITECTURE (reconciled):** Critical-path trading uses **Tier 1 / Tier 2** only (Qwen3 stack). Tier 3 is offline R&D/evolution.
> - **Tier 1 (:30000, GPU 0):** Qwen3-30B-A3B FP8 — signals, risk, execution (50-70 tok/s) — **UNCHANGED**
> - **Tier 2 (:30001, GPU 1):** Qwen3-Coder-Next-80B — orchestration, strategy, code (50-70 tok/s) — **UNCHANGED**
> - **Tier 3a (:30005, offline):** DeepSeek V4 Pro Q4_K_M / FP8 MoE expert-offload — **PRIMARY** long-horizon evolution (DARWIN_GODEL, HyEvo, DGM-H, SIA, SkillOpt, GEPA, etc.)
> - **Tier 3b (:30003, offline):** GLM-5.2 Q4_K_M expert-offload — **SECONDARY** R&D/evolution option (10-20 tok/s)
>
> **Constraints:**
> - **DO NOT** route TRENCH-OPS, GUARDIAN, or EXECUTOR through GLM-5.2 or DeepSeek V4 Pro on the live critical path.
> - **No closed / cloud models** (Claude Fable 5, Opus 4.8, GPT-*, Gemini, etc.) on the live trading path — 100% local open weights only.
> - Routine operations stay autonomous within GUARDIAN risk limits (bounded-autonomy matrix); Tier 3 mutations stay shadow/air-gapped until promotion gates pass with human YES.
>
> **Rationale:** DeepSeek V4 Pro improves long-horizon agentic efficiency for evolution loops while GLM-5.2 remains a strong secondary. Heterogeneous Tier-3 models also enable true multi-family BFT voting (see below). Live critical path stays on the proven Qwen3 Tier 1/2 stack.

"""
        anchor = "## AUTONOMY PRINCIPLE"
        if anchor in text:
            text = text.replace(anchor, model_block + anchor, 1)
    else:
        # Upgrade existing Tier-3-only block to DeepSeek-primary + GLM secondary (idempotent)
        text = re.sub(
            r"> \*\*MODEL TIER ARCHITECTURE \(reconciled\):\*\*.*?(?=\n\n> \*\*POWER HARDENING|\n\n## AUTONOMY PRINCIPLE)",
            """> **MODEL TIER ARCHITECTURE (reconciled):** Critical-path trading uses **Tier 1 / Tier 2** only (Qwen3 stack). Tier 3 is offline R&D/evolution.
> - **Tier 1 (:30000, GPU 0):** Qwen3-30B-A3B FP8 — signals, risk, execution (50-70 tok/s) — **UNCHANGED**
> - **Tier 2 (:30001, GPU 1):** Qwen3-Coder-Next-80B — orchestration, strategy, code (50-70 tok/s) — **UNCHANGED**
> - **Tier 3a (:30005, offline):** DeepSeek V4 Pro Q4_K_M / FP8 MoE expert-offload — **PRIMARY** long-horizon evolution (DARWIN_GODEL, HyEvo, DGM-H, SIA, SkillOpt, GEPA, etc.)
> - **Tier 3b (:30003, offline):** GLM-5.2 Q4_K_M expert-offload — **SECONDARY** R&D/evolution option (10-20 tok/s)
>
> **Constraints:**
> - **DO NOT** route TRENCH-OPS, GUARDIAN, or EXECUTOR through GLM-5.2 or DeepSeek V4 Pro on the live critical path.
> - **No closed / cloud models** (Claude Fable 5, Opus 4.8, GPT-*, Gemini, etc.) on the live trading path — 100% local open weights only.
> - Routine operations stay autonomous within GUARDIAN risk limits (bounded-autonomy matrix); Tier 3 mutations stay shadow/air-gapped until promotion gates pass with human YES.
>
> **Rationale:** DeepSeek V4 Pro improves long-horizon agentic efficiency for evolution loops while GLM-5.2 remains a strong secondary. Heterogeneous Tier-3 models also enable true multi-family BFT voting (see below). Live critical path stays on the proven Qwen3 Tier 1/2 stack.
""",
            text,
            count=1,
            flags=re.DOTALL,
        )
    # Heterogeneous BFT honesty (replace correlated-consensus wording)
    text = re.sub(
        r"- \*\*BFT Voting Consensus:\*\* 2-out-of-3 agent vote \(ARCHON/CORTEX/GUARDIAN\) — \*\*same-model limitation:\*\*[^\n]+",
        "- **BFT Voting Consensus:** 2-out-of-3 agent vote (ARCHON/CORTEX/GUARDIAN) — **heterogeneous models required** "
        "for true fault tolerance (see BFT HONESTY). Independent risk kernel validates deterministically "
        "out-of-process and remains the authoritative DENY gate.",
        text,
    )
    if "heterogeneous assignment" not in text and "BFT HONESTY (reconciled)" in text:
        text = re.sub(
            r"> \*\*BFT HONESTY \(reconciled\):\*\*.*?(?=\n  \n- \*\*Escalation:|\n- \*\*Escalation:)",
            """> **BFT HONESTY (reconciled):** Same-family / same-weight voters produce *correlated* consensus, not independent BFT — a shared failure mode can pass a 2-of-3 vote. **Required heterogeneous assignment:**
> - **GUARDIAN** → Tier 1 Qwen3-30B-A3B FP8 (`:30000`) — live risk path (unchanged)
> - **ARCHON** → Tier 2 Qwen3-Coder-Next-80B (`:30001`) — live orchestration (unchanged)
> - **CORTEX** → DeepSeek V4 Pro (`:30005`, Tier 3) for deep reflection / GEPA / PRM votes when available; fallback Tier 2 Qwen3-Coder (`:30001`) if `:30005` is offline
>
> **Why this improves fault tolerance:** distinct model families (Qwen3-30B ≠ Qwen3-Coder ≠ DeepSeek V4 Pro) fail differently under prompt injection, distribution shift, and reasoning bugs. A 2-of-3 vote across families is meaningful; a 2-of-3 vote across three copies of one weight file is not. Treat agent votes as **advisory**; the out-of-process risk kernel (`:19001`) remains the authoritative gate. No closed/cloud models on any voter.
""",
            text,
            count=1,
            flags=re.DOTALL,
        )
    return text


def reconcile_hardware_bom(text: str) -> str:
    """Align hardware references to operator-locked BOM (WRX90 + 2× RTX PRO 6000)."""
    replacements = [
        (
            r"ASUS ROG RSS \(GX10 firmware updates\)",
            "ASUS GX10 / WRX90 firmware updates",
        ),
        (
            r"ASUS Ascent DGX Spark GX10 \"TITANSPARK\"",
            'ASUS GX10 "TITANSPARK" (utility inference + operator gateway)',
        ),
        (
            r"Threadripper PRO 9995WX \(96C/192T\) \+ 2× RTX PRO 6000 Blackwell 96GB \+ TITANSPARK GB10",
            "Threadripper PRO 9995WX (96C/192T) + WRX90E-SAGE + 512GB DDR5-6000 ECC + "
            "2× RTX PRO 6000 Blackwell Max-Q (192GB VRAM) + TITANSPARK GX10",
        ),
        (
            r"Workstation \"TITANHOME\" \(home, UPS-protected 240V mains — REQUIRED for live capital\):",
            'Workstation "TITANHOME" (WRX90E-SAGE SE, Eaton 9SX UPS, Super Flower 2200W Ti):',
        ),
        (
            r"Micron 7500 PRO boot or any WD Black SN8100",
            "Micron 7500 Pro 3.8TB (boot) or WD Black SN8100 4TB (data)",
        ),
        (
            r"wall power, no UPS",
            "UPS-protected 208–240V mains (Eaton 9SX 3000VA + Super Flower 2200W — REQUIRED for live capital)",
        ),
        # PiKVM removed from operator BOM — strip / rewrite references
        (
            r"PiKVM V4 Plus \(out-of-band management\)",
            "ASUS AST2600 BMC (onboard OOB; PiKVM removed)",
        ),
        (
            r"PiKVM V4 Plus",
            "ASUS AST2600 BMC (PiKVM removed)",
        ),
        (
            r"PiKVM heartbeat",
            "AST2600 BMC heartbeat",
        ),
        (
            r"PiKVM",
            "AST2600 BMC",
        ),
        (
            r"LBE-1420 GPSDO \(PPS-locked chrony source\)",
            "LBE-1425 GPSDO (PPS + 10 MHz → E810; PPS-locked chrony source)",
        ),
        (
            r"LBE-1420",
            "LBE-1425",
        ),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)

    # Refresh stale HARDWARE BOM block if present
    text = re.sub(
        r"> \*\*HARDWARE BOM \(reconciled\):\*\*.*?(?=\n\n## Platform Architecture|\n\n> \*\*)",
        """> **HARDWARE BOM (reconciled):** Operator-locked stack — see `~/.openclaw/infra/hardware_bom.yaml`.
> TITANHOME: Threadripper PRO 9995WX, ASUS WRX90E-SAGE SE, 512GB DDR5-6000 ECC R-DIMM (V-Color),
> 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96GB each), Micron 7500 Pro 3.8TB boot,
> 2× WD Black SN8100 4TB, Super Flower Leadex Titanium 2200W, Eaton 9SX 3000VA UPS,
> Leo Bodnar LBE-1425 GPSDO → Intel E810-XXVDA4T, ASUS TPM-SPI. **PiKVM removed** (AST2600 BMC only).
> TITANSPARK: ASUS GX10. Vault: Mac Mini 2018 (64GB). UPS mandatory for live capital.
""",
        text,
        count=1,
        flags=re.DOTALL,
    )

    if "HARDWARE BOM (reconciled)" not in text:
        hw_block = """
> **HARDWARE BOM (reconciled):** Operator-locked stack — see `~/.openclaw/infra/hardware_bom.yaml`.
> TITANHOME: Threadripper PRO 9995WX, ASUS WRX90E-SAGE SE, 512GB DDR5-6000 ECC R-DIMM (V-Color),
> 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96GB each), Micron 7500 Pro 3.8TB boot,
> 2× WD Black SN8100 4TB, Super Flower Leadex Titanium 2200W, Eaton 9SX 3000VA UPS,
> Leo Bodnar LBE-1425 GPSDO → Intel E810-XXVDA4T, ASUS TPM-SPI. **PiKVM removed** (AST2600 BMC only).
> TITANSPARK: ASUS GX10. Vault: Mac Mini 2018 (64GB). UPS mandatory for live capital.

"""
        anchor = "## Platform Architecture"
        if anchor in text:
            text = text.replace(anchor, hw_block + anchor, 1)
    return text


def reconcile_endgame_phasing(text: str) -> str:
    """ENDGAME strategies are phase-gated; not active at $2.5K."""
    if "ENDGAME PHASING (reconciled)" in text:
        return text
    endgame_block = """
> **ENDGAME PHASING (reconciled):** §ENDGAME strategies (funding harvest, restaking, pred markets,
> Deribit vol, new-chain MEV, airdrops, rate arb, CLMM) are **Phase 3+** unlocks.
> Phase 1 ($2.5K): P30 bounty + paper-validated micro-live only. Gas and margin requirements
> prohibit simultaneous ENDGAME activation at starting capital.

"""
    anchor = "# §ENDGAME"
    if anchor in text:
        text = text.replace(anchor, endgame_block + anchor, 1)
    return text


def reconcile_power_ups(text: str) -> str:
    """UPS required for live capital; patch contradictory decommission language."""
    replacements = [
        (
            r"wall power, no UPS",
            "UPS-protected mains (UPS REQUIRED for live capital)",
        ),
        (
            r"Wall power connection, no UPS \(UPS completely decommissioned and[^\)]*\)",
            "UPS-protected 240V mains (UPS REQUIRED for live capital — power-loss = HALT)",
        ),
        (
            r"no UPS \(UPS completely decommissioned and removed per operator directive\)",
            "UPS REQUIRED for live capital (power-loss triggers HALT per risk_kernel)",
        ),
        (
            r"The UPS system has been completely decommissioned and removed per operator directive\.",
            "**UPS REQUIRED for live capital.** Prior decommission reversed per survivability advisory — "
            "install UPS with ≥15 min runtime before deploying real capital. Power-loss = HALT.",
        ),
        (
            r"UPS decommissioned",
            "UPS REQUIRED (mandatory for live capital)",
        ),
        (
            r"240V power upgrade, UPS decommissioned",
            "240V power upgrade + UPS REQUIRED for live capital",
        ),
        (
            r'Workstation "TITANHOME" \(home, wall power, no UPS\):',
            'Workstation "TITANHOME" (home, UPS-protected 240V mains — REQUIRED for live capital):',
        ),
        (
            r"\*\*Physical location of workstation:\*\* Hyperion's home \(wall power, behind firewall\)",
            "**Physical location of workstation:** Hyperion's home (UPS-protected 240V mains, behind firewall)",
        ),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)

    text = re.sub(
        r"The UPS system has been completely decommissioned and removed per operator directive\.",
        "**UPS REQUIRED for live capital.** Install ≥3000VA UPS with ≥15 min runtime. Power-loss = HALT.",
        text,
    )

    if "POWER HARDENING (reconciled)" not in text:
        power_block = """
> **POWER HARDENING (reconciled):** UPS is **mandatory** before live capital deployment.
> Power-loss triggers HALT: flatten exposure, revoke session keys, CRITICAL alert.
> Spec: `~/.openclaw/infra/power_requirements.yaml`. Prior "no UPS" language superseded.

"""
        anchor = "## AUTONOMY PRINCIPLE"
        if anchor in text:
            text = text.replace(anchor, power_block + anchor, 1)

    text = re.sub(
        r"\*\*Edge\*\*: 5-PoP global mesh",
        "**Edge**: Phase 1 single-PoP (EDGE-FRA default); full 5-PoP mesh Phase 3+",
        text,
        count=1,
    )
    text = re.sub(
        r"5-PoP global mesh — TKY, SIN, FRA, USE, AMS",
        "Phase 1: EDGE-FRA only (single PoP); TKY/SIN/USE/AMS deferred Phase 3+",
        text,
    )
    return text


def reconcile_dead_mans_switch(text: str) -> str:
    """No operator heartbeat → de-risk/flatten, never enable promotion."""
    dms_block = """
### Dead-Man's Switch (Operator Heartbeat)

- **Policy:** If operator heartbeat missing for >48h, system de-risks and flattens exposure.
- **Never:** Auto-promote strategies or evolution candidates on operator absence.
- **On miss:** Reduce positions 50%, pause new entries, alert CRITICAL via HERALD.
- **On 72h miss:** Flatten to stable collateral; halt non-routine pipelines.
- **Recovery:** Operator `RESUME` command required after heartbeat restored.

"""
    if "Dead-Man's Switch (Operator Heartbeat)" not in text:
        text = text.replace(
            "### Autonomous Response Handling",
            dms_block + "### Autonomous Response Handling",
            1,
        )
    return text


def reconcile_openclaw_hermes_contract(text: str) -> str:
    """Inject current OpenClaw + Hermes workspace/config contract (docs Jul 2026)."""
    if "OPENCLAW / HERMES DEPLOY CONTRACT (reconciled)" in text:
        return text
    block = """
> **OPENCLAW / HERMES DEPLOY CONTRACT (reconciled):**
>
> **OpenClaw** ([agent workspace](https://docs.openclaw.ai/concepts/agent-workspace)):
> - Workspace home: `~/.openclaw/workspace` (NOT the same as `~/.openclaw/` config root).
> - Bootstrap files in workspace: `AGENTS.md`, `SOUL.md`, `USER.md`, `IDENTITY.md`,
>   `TOOLS.md`, `HEARTBEAT.md`, `BOOT.md`, `BOOTSTRAP.md`, `MEMORY.md`, `memory/`, `skills/`.
> - Config/credentials stay under `~/.openclaw/` (`openclaw.json`, sessions, auth) — never in workspace git.
> - Defaults: `bootstrapMaxChars: 20000`, `bootstrapTotalMaxChars: 60000` (override in
>   `agents.defaults` if needed; TITAN sets 150000 explicitly for large AGENTS.md).
> - Missing bootstrap files → injected "missing file" marker; large files truncated.
>
> **Hermes** ([context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files),
> [personality](https://hermes-agent.nousresearch.com/docs/user-guide/features/personality)):
> - `SOUL.md` = global identity from `~/.hermes/SOUL.md` only (slot #1) — persona/tone, not project paths.
> - Project context: `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules` (first match wins).
> - Config: `~/.hermes/config.yaml` ← `templates/config.yaml`.
> - Context files scanned for prompt injection; default max ~20k chars/file.
>
> **TITAN mapping:** `scripts/extract_bootstrap.py` → `output/bootstrap/` →
> `workspace/` + `./deploy.sh` installs to `~/.openclaw/workspace/` and `~/.hermes/SOUL.md`.
> Companion §REF bodies: `refs/*.md` (reconstructed; originals never shipped).
> Do **not** paste `TITAN.reconciled.md` as a chat prompt — it exceeds bootstrap limits.

"""
    # Prefer after System Overview / before AUTONOMY
    anchor = "## AUTONOMY PRINCIPLE"
    if anchor in text:
        return text.replace(anchor, block + anchor, 1)
    return block + text


def reconcile_ref_pointers(text: str) -> str:
    """Point §REF stubs at reconstructed refs/ companions + configs_detail.md."""
    # CONFIGS stubs → live configs_detail / refs
    text = re.sub(
        r"# → see §CONFIGS_detail\.md[^\n]*",
        "# → see configs_detail.md / refs/CONFIGS_detail.md (live templates)",
        text,
    )
    text = re.sub(
        r"# \.\.\. \d+ more lines → §CONFIGS_detail\.md\s*",
        "# … truncated in source dump → see configs_detail.md / refs/CONFIGS_detail.md\n",
        text,
    )
    # Generic §REF see lines
    replacements = {
        "§KEYS_detail.md": "`refs/KEYS_detail.md`",
        "§MEMORY_detail.md": "`refs/MEMORY_detail.md`",
        "§SKILLS_full.md": "`refs/SKILLS_full.md`",
        "§DEPLOY_scripts.md": "`refs/DEPLOY_scripts.md`",
        "§AU_audit.md": "`refs/AU_audit.md`",
        "§PERF_detail.md": "`refs/PERF_detail.md`",
        "§COMM_detail.md": "`refs/COMM_detail.md`",
        "§COCKPIT_detail.md": "`refs/COCKPIT_detail.md`",
        "§MODELS_detail.md": "`refs/MODELS_detail.md`",
        "§GHOST_detail.md": "`refs/GHOST_detail.md`",
        "§RESEARCH_detail.md": "`refs/RESEARCH_detail.md`",
        "§MAINT_detail.md": "`refs/MAINT_detail.md`",
        "§MEV_detail.md": "`refs/MEV_detail.md`",
        "§REAPER_detail.md": "`refs/REAPER_detail.md`",
        "§AEGIS_detail.md": "`refs/AEGIS_detail.md`",
        "§FORTRESS_detail.md": "`refs/FORTRESS_detail.md`",
        "§EVERGREEN_detail.md": "`refs/EVERGREEN_detail.md`",
        "§CONDUIT_detail.md": "`refs/CONDUIT_detail.md`",
        "§XB_detail.md": "`refs/XB_detail.md`",
        "§CONFIGS_detail.md": "`configs_detail.md` / `refs/CONFIGS_detail.md`",
    }
    for old, new in replacements.items():
        text = text.replace(f"See `{old}`", f"See {new}")
        text = text.replace(f"see `{old}`", f"see {new}")
        text = text.replace(f"See {old}", f"See {new}")
        text = text.replace(f"see {old}", f"see {new}")

    # System Overview §REF list
    text = re.sub(
        r"\*\*§REF files\*\*:[^\n]+",
        "**§REF files (reconstructed under `refs/`):** CONFIGS, SKILLS_full, DEPLOY_scripts, "
        "KEYS, MEMORY, AU_audit, PERF, COMM, COCKPIT, MODELS + narrative stubs "
        "(GHOST/RESEARCH/MAINT/…). Originals were never on disk.",
        text,
        count=1,
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile TITAN policy for survivability")
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=NORMALIZED_PATH,
        help="Normalized TITAN path",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=RECONCILED_PATH,
        help="Output path",
    )
    args = parser.parse_args()

    text = read_source(args.input)
    text = reconcile_counts(text)
    text = reconcile_quantum(text)
    text = reconcile_autonomy_scope(text)
    text = reconcile_phase5_and_timeout(text)
    text = reconcile_paper_minimum(text)
    text = reconcile_shadow_evolution(text)
    text = reconcile_bft_honesty(text)
    text = reconcile_drawdown_tiers(text)
    text = reconcile_implicit_approval(text)
    text = reconcile_model_tiers(text)
    text = reconcile_hardware_bom(text)
    text = reconcile_endgame_phasing(text)
    text = reconcile_power_ups(text)
    text = reconcile_dead_mans_switch(text)
    text = reconcile_openclaw_hermes_contract(text)
    text = reconcile_ref_pointers(text)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_text(args.output, text)
    print(f"Reconciled (survivability) -> {args.output} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
