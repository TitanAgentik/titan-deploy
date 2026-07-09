# IDENTITY — the Titan UNIFIED FRAMEWORK

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

- 23 agents | 14 chains | 108+ signals | 775+ CBs | 65 skills | 26 workflows | 47 pipelines
- Quantum agents: DORMANT (100% classical execution)

## Bootstrap Limits

- bootstrapMaxChars: 20,000 per file
- bootstrapTotalMaxChars: 150,000 total
- Sub-agents: AGENTS.md + TOOLS.md only (minimal prompt mode)

## System Overview

- **Framework**: OpenClaw (nervous system) + Hermes Agent (cognitive brain) \= "the Titan"  
- **Compute**: Threadripper PRO 9995WX (96C/192T) + WRX90E-SAGE + 512GB DDR5-6000 ECC + 2× RTX PRO 6000 Blackwell Max-Q (192GB VRAM) + TITANSPARK GX10  
- **Models**: ALL LOCAL — GLM-5.2-753B-A40B (GPU TP=2, llama.cpp `--n-cpu-moe` expert-offload) + Qwen3.6-35B-A3B (CPU, llama.cpp) + MTP native speculative  
- **Quantum**: 100% Classical Execution — quantum agents DORMANT (Quantum simulators removed to dedicate all VRAM to REVM parallelization)  
- **Scale**: 23 agents | 14 chains | 108+ signals | 775+ CBs | 65 skills | 26 workflows | 47 pipelines (P1-P34, P37-P48 incl. §GRIS)  
- **Edge**: Phase 1 single-PoP (EDGE-FRA default); full 5-PoP mesh Phase 3+ — EDGE-TKY (AWS `ap-northeast-1` c7i.metal-24xl) + EDGE-SIN (AWS `ap-southeast-1` c7i.4xlarge) + EDGE-FRA (Vultr BM Frankfurt, DE-CIX peered) + EDGE-USE (AWS `us-east-1` c7i.2xlarge) + EDGE-AMS (Vultr BM Amsterdam) — same-AZ as exchange matching engines, sub-1ms RTT  
- **OS**: Ubuntu 24.04 LTS HWE (kernel 7.0) + AF_XDP Kernel-Bypass Networking (sub-10µs packet processing) | Python 3.12 | systemd 255  
- **Learning**: SAGE + MGPO + Hermes-RL/DRPO + HyEvo + GEPA + DGM-H + SIA + SkillOpt + InterleaveThinker + ALE + Robust  
- **§REF files**: §AU_audit.md, §GHOST_detail.md, §PERF_detail.md, §SKILLS_full.md, §DEPLOY_scripts.md, §RESEARCH_detail.md  
- **Autonomy**: FULLY AUTONOMOUS — zero human gates for standard operations; operator receives informational notifications only; CRITICAL alerts for 6 emergency conditions only  
- **Global Intelligence**: §GRIS — 35+ sources (10 academic, 6 international, 7 code, 8 intelligence, 4 model), 4-stage NLP triage (800+/day → 5-15 candidates), P48 safe implementation pipeline (sandbox → benchmark → hot-swap), top-20 AI model watchlist with auto-evaluate-swap, Global Research Digest in daily Telegram briefing

> **QUANTUM STATUS (reconciled):** QCC, QSA, QRP are **DORMANT**. No cuQuantum, Wukong,
> or Tier 3 cloud QPU dispatch. 100% classical GPU execution (REVM, CuEVM, ML inference).
> OS CSPRNG for all cryptographic entropy. Quantum skills archived — not loaded at runtime.

> **MODEL TIER ARCHITECTURE (reconciled):** Critical-path trading uses **Tier 1 / Tier 2** only (Qwen3 stack). Tier 3 is offline R&D/evolution.
> - **Tier 1 (:30000, GPU 0):** Qwen3-30B-A3B FP8 — signals, risk, execution (50-70 tok/s) — **UNCHANGED**
> - **Tier 2 (:30001, GPU 1):** Qwen3-Coder-Next-80B — orchestration, strategy, code (50-70 tok/s) — **UNCHANGED**
> - **Tier 3a (:30005, offline):** DeepSeek V4 Pro Q4_K_M / FP8 MoE expert-offload — **PRIMARY** long-horizon evolution (DARWIN_GODEL, HyEvo, DGM-H, SIA, SkillOpt, GEPA, etc.)
> - **Tier 3b (:30003, offline):** GLM-5.2 Q4_K_M expert-offload — **SECONDARY** R&D/evolution option (10-20 tok/s)
>
> **Constraints:**
> - **DO NOT** route TRENCH-OPS, GUARDIAN, or EXECUTOR through GLM-5.2 or DeepSeek V4 Pro on the live critical path.
> - **No closed / cloud models** (Claude Fable 5, Opus 4.8, GPT-*, Gemini, etc.) on the live trading path — 100% local open weights only.
> - Standard operations remain fully autonomous (zero human gates); Tier 3 mutations stay shadow/air-gapped until promotion gates pass.
>
> **Rationale:** DeepSeek V4 Pro improves long-horizon agentic efficiency for evolution loops while GLM-5.2 remains a strong secondary. Heterogeneous Tier-3 models also enable true multi-family BFT voting (see below). Live critical path stays on the proven Qwen3 Tier 1/2 stack.

> **POWER HARDENING (reconciled):** UPS is **mandatory** before live capital deployment.
> Power-loss triggers HALT: flatten exposure, revoke session keys, CRITICAL alert.
> Spec: `~/.openclaw/infra/power_requirements.yaml`. Prior "no UPS" language superseded.
