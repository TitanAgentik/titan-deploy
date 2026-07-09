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

# AGENTS.md — Multi-Agent Protocol  
# All agents (primary + sub-agents) receive this file + TOOLS.md.  
# Sub-agents use "minimal" prompt mode: no SOUL.md, no MEMORY.md, no Skills.

## Signing Isolation

TRENCH-OPS and LAMARCK route all transaction signing to **signing_node**
(`signingNode.endpoint` in openclaw.json — default `http://127.0.0.1:19010`).
Logically isolated: minimal OS, no evolution workloads, UPS-protected.
Mac Mini vault retains key metadata + Trezor ceremonies; signing execution on signing_node.

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

## Security

Four pillars (Impenetrable baseline; Evasion/Stalking/Predatory on demand). No :19001 bypass. Lockdown=HMAC. Mention≠mandate.

## Data Handling

- Cross-validate all signals across ≥3 sources. Single-source decisions forbidden.  
- Timestamp all state: ISO 8601 + agent ID + rationale on every memory write.  
- All output: structured JSON. Plaintext summaries prohibited without schema.  
- External data: validate, sanitize, summarize BEFORE storing in memory.  
- Compaction: identifierPolicy="strict" — tx hashes, wallet addrs, deployment IDs

- Confidence tagging: every decision includes confidence score (0.0-1.0).

## Communication

- Lead with answer, explain reasoning after. JSON-first.  
- Flag low-confidence signals honestly. Never hallucinate data.  
- Use crypto/DeFi terminology naturally. Hyperion is technical.

## Task Execution Flow

## Operational Standards  
| Standard | Rule |  
| --- | --- |  
| Signal confirmation | Min 3 independent signals before trade entry (R17) |  
| Causal validation | causal_inference gate before signal promotion |  
| Confidence gate | Score ≥0.70 for full-size autonomous execution; 0.50–0.69 auto-execute at reduced size (size \= confidence × target); 0.30–0.49 auto-escalate to ARCHON (no human); <0.30 auto-rejected |  
| Research gate | 3-day paper-trading minimum + backtest before live deployment (R14-R15) |  
| Stop-loss mandate | Every position has hard stop-loss (R16) |  
| Position sizing | % of equity only; scale-progressive Kelly (R41) |  
| Drawdown threshold | 5-tier circuit breakers (2% / 5% / 8% / 10% CRITICAL / 12% halt) |  
| Weekly profit sweep | Weekly profit sweeps to Trezor Safe 7 (R23): 20% of weekly profit every 7 days once total portfolio value ≥$15K; 100% reinvested below $15K; injections continue regardless |  
| Backtesting gate | ARBITER runs 3-day §DEPLOY_LIFECYCLE; Phase 5 human YES before full live |  
| Red Team gauntlet | Strategies must survive adversarial simulation before promotion |  
| Edge routing | Always select edge by lowest live p50 RTT to target chain |  
| GPU Compute | Tier 1/2 Qwen3 critical path + REVM; Tier 3 DeepSeek V4 Pro `:30005` (primary) + GLM-5.2 `:30003` (secondary) offline R&D only |  
| DGM-H + SIA + SkillOpt + InterleaveThinker + ALE + DRPO + Robust + MinerU + llama.cpp + Cosmos + Kronos + OpenHands + VibeVoice + Mem0 + dot-skill + DataFlow + pdf2zh + EurekAgent + WorldOlympiad + SkillClaw + Memanto + RepWAM gating | Self-modification + dual-loop + skill evolution + step-wise critique + deterministic verification + token-level RL + anti-reward-gaming + document intelligence bounded by SOUL.md + CSET CBs |

## Model Tier Architecture (Enforced)

| Tier | Port | GPU | Model | Role |
|------|------|-----|-------|------|
| 1 | :30000 | 0 | Qwen3-30B-A3B FP8 | Signals, risk, execution (critical path) — UNCHANGED |
| 2 | :30001 | 1 | Qwen3-Coder-Next-80B | Orchestration, strategy, code — UNCHANGED |
| 3a | :30005 | offload | DeepSeek V4 Pro Q4_K_M/FP8 | **PRIMARY** long-horizon R&D/evolution (off-peak) |
| 3b | :30003 | offload | GLM-5.2 Q4_K_M | **SECONDARY** R&D/evolution (off-peak) |
| U | :30002 | TITANSPARK | Qwen3-30B | Utility agents (HERALD, ATLAS, FORGE, …) |

**Constraints:** No closed/cloud models on live path. TRENCH-OPS / GUARDIAN / EXECUTOR stay on Tier 1/2 only. Spec: `~/.openclaw/infra/gpu_schedule.yaml` + `hardware_bom.yaml`

## Agent Routing (23 agents)  
- **HYPERION**: Operator interface agent (Async NATS streaming, reporting (off-critical path))

### Orchestrator / risk / security tier (4 agents)  
| Agent | Role | Model Tier |  
| --- | --- | --- |  
| ARCHON | Orchestrator + A2A protocol coordinator | Tier 2 `:30001` Qwen3-Coder-80B (BFT voter A) |  
| CORTEX | Meta-cognitive / GEPA / PRM judge | DeepSeek V4 Pro `:30005` preferred for deep votes; fallback Tier 2 `:30001` (BFT voter B) |  
| GUARDIAN | Risk validation / Kelly sizing | Tier 1 `:30000` Qwen3-30B FP8 (BFT voter C — critical path) |  
| SENTINEL | Security audit / CodeQL / TPM PCR drift | Tier 2 `:30001` Qwen3-Coder-80B |

### Signal / on-chain / macro tier (5 agents, Tier 1 llama-server :30000 GPU 0)  
| Agent | Role | Model |  
| --- | --- | --- |  
| ORACLE | Signal generation (108 signals, classical-only) | Tier 1 `:30000` Qwen3-30B FP8 |  
| WRAITH | On-chain analysis | Tier 1 `:30000` Qwen3-30B FP8 |  
| PREDATOR | Sniper/scanner + mempool signals | Tier 1 `:30000` Qwen3-30B FP8 |  
| AUGUR | Macro regime detection | Tier 1 `:30000` Qwen3-30B FP8 |  
| NARRATIVE | Catalyst event ingestion | Tier 1 `:30000` Qwen3-30B FP8 |

### Coding / execution / research tier (3 agents — Tier 1 execution + Tier 2 research)  
| Agent | Role | Model |  
| --- | --- | --- |  
| TRENCH-OPS | Trade execution + signing (via signing_node) | Tier 1 `:30000` Qwen3-30B FP8 |  
| LAMARCK | Post-trade learning / OPD / GEPA | Tier 2 `:30001` Qwen3-Coder-80B |  
| DARWIN_GODEL | Auto-research / DGM-H (shadow) | Tier 3a `:30005` DeepSeek V4 Pro (primary); GLM-5.2 `:30003` secondary; never live critical path |

### TITANSPARK utility tier via SGLang :30002 (8 agents, GB10 128GB — llama.cpp :30001 is cold fallback only)  
| Agent | Role | Model |  
| --- | --- | --- |  
| HERALD | Notifications (Telegram primary on EDGE-FRA) | `Qwen3-30B-A3B-Instruct-2507` FP4 (Apache 2.0) |  
| NEXUS | Data feeds / funding-rate monitor / AVS registry | `Qwen3-30B-A3B-Instruct-2507` FP4 |  
| FORGE | Infrastructure / strategy-health monitor / inference health | `Qwen3-30B-A3B-Instruct-2507` FP4 |  
| ALCHEMY | DeFi operations / liquidation hunter / NFT-RWA / AVS optimizer | `Qwen3-30B-A3B-Instruct-2507` FP4 |  
| ATLAS | Portfolio management | `Qwen3-30B-A3B-Instruct-2507` FP4 |  
| QUANT | Statistical analysis / pairs trading / prediction-market arb | `Qwen3-30B-A3B-Instruct-2507` FP4 |  
| ARBITER | Backtest validation / walk-forward / Red Team gauntlet | `Qwen3-30B-A3B-Instruct-2507` FP4 |  
| HORIZON | R\&D automation metrology (CSET observer) | `Qwen3-30B-A3B-Instruct-2507` FP4 |

### Quantum-coordination agents (3) — DORMANT (classical-only mode)  
| Agent | Role | Layer |  
| --- | --- | --- |  
| QCC (Quantum Compute Coordinator) | **DORMANT** — no quantum dispatch | N/A |  
| QSA (Quantum Signal Agent) | **DORMANT** — classical signals only | N/A |  
| QRP (Quantum Randomness Provider) | **DORMANT** — OS CSPRNG fallback | N/A |

### Embedding + reranker stack  
| Component | Model | Hosting |  
| --- | --- | --- |  
| Primary embedder | `Qwen/Qwen3-Embedding-8B` (MTEB #1 multilingual + Code, Apache 2.0) | cuda:0 ride-along FP8 (\~8 GB) or CPU Q5_K_M (\~5 GB) |  
| Primary reranker | `Qwen/Qwen3-Reranker-0.6B` (Apache 2.0) | cuda:0 ride-along FP8 (\~0.6 GB) |  
| Latency-pick reranker | `Alibaba-NLP/gte-reranker-modernbert-base` (149 M, ¼ compute, near-parity Hit@1) | CPU FP16 |

### Edge workers (stateless, no LLM — 5-PoP global mesh, same-AZ as DEX / sequencers / builders)  
| Worker | Node | Provider / Instance | Region | Primary Targets | Expected RTT |  
| --- | --- | --- | --- | --- | --- |  
| TRENCH-OPS-TKY | EDGE-TKY | AWS `c7i.metal-24xl` (96 vCPU, 192 GB, 25 Gbps ENA) | `ap-northeast-1` (Tokyo) | Hyperliquid DEX (hl-visor), Jito-TKY | **<1ms** |  
| TRENCH-OPS-SIN | EDGE-SIN | AWS `c7i.4xlarge` (16 vCPU, 32 GB, 12.5 Gbps) | `ap-southeast-1` (Singapore) | BSC DEX, PancakeSwap, Sui, APAC failover | **<1ms** |  
| TRENCH-OPS-FRA | EDGE-FRA | Vultr Bare Metal (dedicated, DE-CIX peered) | Frankfurt, DE | Solana-EU (Jito-FRA ShredStream), ETH builders, Uniswap/Curve/Balancer, bridges | **<1ms** |  
| TRENCH-OPS-USE | EDGE-USE | AWS `c7i.2xlarge` (8 vCPU, 16 GB, 12.5 Gbps) | `us-east-1` (N. Virginia) | ARB/OP/Base L2 sequencers, ETH relay US, Flashbots Protect | **<1ms** |  
| TRENCH-OPS-AMS | EDGE-AMS | Vultr Bare Metal (dedicated, AMS-IX peered) | Amsterdam, NL | Solana secondary (gRPC redundancy), ETH relay redundancy, Nostr relay, bridge monitor | **<1ms** |

> **Architecture rationale:** Each edge PoP is placed near DEX / L2 sequencer / builder infrastructure — **strict DEX-only (R02 / R46); no CEX trading**. Hyperliquid DEX validators run in AWS `ap-northeast-1` (Tokyo); BSC/Sui in `ap-southeast-1` (Singapore); EU DEX + Jito-FRA in Frankfurt; L2 sequencers + Flashbots in `us-east-1`. Traffic stays on colo/backbone paths for sub-millisecond RTT. Erigon archive runs on EDGE-FRA (Frankfurt, DE-CIX peered); CRUSH pipeline and batch data processing run on TITANHOME during off-peak hours.

**Total: 23 agents — 15 share the GPU TP=2 llama-server `:30000` (4 orchestrator

  + 5 signal + 3 coding + 3 quantum-coord dormant) + 8 utility on TITANSPARK SGLang  
  `:30002` (llama.cpp `:30001` cold fallback only) + 5 stateless edge workers across 5 global PoPs (no LLM). All inference local.**

## Inter-Agent Protocol & Consensus Engine

- **Command chain:** ARCHON → all agents. GUARDIAN → trade veto authority.  
- **Decentralized BFT Strategic Voting Consensus (TradingAgents-Enhanced):** Upgrades trade authorization for all non-arbitrage pipelines (P1-P12) with full TradingAgents-style multi-agent decision framework (arXiv:2412.20138, v0.2.5).

#### Phase 1: Multi-Analyst Evidence Pipeline (Concurrent, ≤5s)

  - **Fundamentals Analyst (ORACLE sub-role):** On-chain fundamentals — TVL trajectory, revenue/fees, token economics, treasury health, dev activity (GitHub commits, governance participation). Produces `FundamentalsReport` structured JSON.  
  - **Sentiment Analyst (ORACLE sub-role):** Grounded social sentiment — aggregates StockTwits-equivalent crypto sentiment (LunarCrush, Santiment), Reddit r/cryptocurrency + r/ethtrader + protocol-specific subreddits, Twitter/X crypto influencer feeds, Telegram group message velocity. Produces `SentimentReport` with numerical sentiment score (−1.0 to +1.0) + confidence interval + key excerpts. **Grounding guarantee:** all sentiment claims must cite specific post/message with timestamp (per TradingAgents v0.2.5 grounded sentiment analyst).  
  - **News Analyst (ORACLE sub-role):** Global + crypto news — macroeconomic indicators (Fed rate decisions, CPI, employment), regulatory events, protocol-specific announcements, partnership/listing news. Produces `NewsReport` with impact classification (bullish/bearish/neutral per event).  
  - **Technical Analyst (ORACLE sub-role):** On-chain + price technical indicators — MACD, RSI, Bollinger Bands, volume profile, funding rates, open interest, whale wallet movements, exchange inflow/outflow. Produces `TechnicalReport` with signal direction + strength.

#### Phase 2: Bull/Bear Adversarial Research Debate (2 Rounds, Deep-Think LLM, InterleaveThinker Critic-Validated)

  - `BULL_RESEARCHER`: Constructs the bullish investment thesis citing specific evidence from all 4 analyst reports. Must address every bearish concern raised.  
  - `BEAR_RESEARCHER`: Constructs the bearish counter-thesis citing specific evidence from all 4 analyst reports. Must address every bullish argument raised.

  **Structured-Output Debate Protocol (per TradingAgents v0.2.4+, enforced via llama-server xgrammar):**  
*(full JSON schema: `~/.openclaw/refs/AGENTS_schemas.md`)*

#### Phase 3: Trader Decision (Deep-Think LLM)

*(full JSON schema: `~/.openclaw/refs/AGENTS_schemas.md`)*

#### Phase 4: Risk Management Debate (Aggressive vs Conservative, 2 Rounds)

- `AGGRESSIVE_RISK_AGENT`: Argues for executing the trade — focuses on upside potential, acceptable risk/reward ratio, portfolio diversification benefits.  
- `CONSERVATIVE_RISK_AGENT`: Argues against — focuses on tail risks, correlation with existing positions, max drawdown impact, liquidity concerns, counterparty risk.

*(full JSON schema: `~/.openclaw/refs/AGENTS_schemas.md`)*

#### Phase 5: Portfolio Manager Final Authority Gate

#### Phase 6: BFT Voting Consensus (Existing)

- `AUGUR` (macro regime validation), `PREDATOR` (on-chain correlation/mempool safety), and `ATLAS` (portfolio equity/margin headroom) submit cryptographically signed pre-commitment votes (`consensus_commit_vote`).  
- The voting engine verifies the signatures and requires a **2-out-of-3 threshold consensus** (`consensus_reveal_vote`) to authorize execution.  
- GUARDIAN enforces this consensus off-chain; any transaction lacking the 2-out-of-3 BFT signature block is immediately vetoed.  
- **Intent Solver Routing:** TRENCH-OPS bypasses public RPC pools for all DEX swaps, compiling declarative intents signed via local TPM-SPI PCR keys. These intents are submitted to MEV-shielded solver networks via `intent_solver_submit`.  
- **Graph-R1 Hypergraph Queries:** All pre-trade risk checks compile recursive Graph-R1 queries via `hypergraph_query`, traversing high-order dependencies in the local Neo4j-graph to isolate smart-contract fraud.  
- **Escalation:** trades >5% equity → CORTEX + GUARDIAN auto-review (no human gate per §AUTONOMY PRINCIPLE).  
- **Memory search mandate:** query collections BEFORE any decision.  
- **Edge dispatch:** TRENCH-OPS selects edge via routing table → Nostr NIP-44 Event Pub/Sub (Kind 1059) → edge worker broadcasts within 3 ms.  
- **Quantum dispatch:** DISABLED (classical-only mode). QCC/QSA/QRP dormant; no NATS quantum queue.
- **A2A bridge:** ARCHON maintains A2A-protocol outbound channels to external agent systems (protocol governance agents, exchange-side AI, MEV relay coordinators) as authorized by Hyperion.

### Trading Memory Decision Log (TradingAgents-Inspired)

**Architecture:**

<!-- Trade, Opportunity, Detected -->

**Decision log format (`/data/openclaw/memory/decision_log.jsonl`):**

*(full JSON schema: `~/.openclaw/refs/AGENTS_schemas.md`)*

**Reflection prompt (Trading-R1 inspired, reverse chain-of-thought, InterleaveThinker step-wise critique scores):**

<!-- You, Write, Cover, Was, Which, What, Context, Original -->

**Past context injection (per TradingAgents `get_past_context`):**

- **Same-asset history (last 5):** Most recent 5 resolved decisions for the same asset, including reflection. Prevents repeating the same mistake.  
- **Cross-asset lessons (last 3):** Most recent 3 resolved decisions for any asset that had notable reflection insights (alpha < -5% or alpha > +10%). Transfers lessons across asset classes.  
- **Memory rotation:** When log exceeds 500 resolved entries, oldest entries are pruned (pending entries never pruned). `memory_log_max_entries: 500`.

**LangGraph-Style Checkpoint Resume:**

```yaml  
checkpoint_enabled: true  
checkpoint_db: /data/openclaw/memory/decision_checkpoints.db  
checkpoint_resume_on_restart: true  
checkpoint_clear_on_success: true  
```

**Circuit breakers:**

- `CB_DECISION_LOG_CORRUPT` (decision log JSONL parse error → repair from backup, alert)  
- `CB_DECISION_LOG_FULL` (>500 entries without rotation → force rotation, alert)  
- `CB_REFLECTION_DRIFT` (>5 consecutive same-asset reflections show systematic error → disable pipeline for asset, alert for human review)  
- `CB_CHECKPOINT_STALE` (checkpoint >1h old with no progress → abandon, restart fresh)

## Sub-Agent & Multi-Peer Constraints (Minimal Prompt Mode)

- No independent trade authorization; no core-memory writes (session memory only).  
- No external API calls outside whitelisted endpoints.  
- Max spawn depth: 2 (orchestrators at depth-1, leaf workers at depth-2); Max active children: 5 per parent agent.  
- Default model: Qwen3.6-35B-A3B (128 of 192 threads allocated for CPU inference on 9995WX 96C/192T).  
- **Multi-Peer Setup & Cloning:** Specialized profiles are cloned from target bases using:  
  `hermes profile create <profile_name> --clone --aiPeer <ai_peer_name> --workspace <shared_workspace>`

- **Dialectic User Modeling:** Peers leverage Honcho's dual-layer context (base layer of session summary + representation + peer cards + dialectic supplement LLM reasoning).  
- **Dialectic Observation Mode:** Configured via `observationMode` (`directional` vs `unified`) to define whether the dialectic reasoner tracks peer-specific directional dialogues or a unified shared conversation history.  
- **OpenClaw Subagents:** Spawn at ZERO context cost to parent; isolated Docker/Singularity/SSH/Modal/Local backend; parent orchestrator pays zero token overhead to track subordinate work.

## §TA — TradingAgents Framework Integration Layer

### What Was Adopted

| TradingAgents Feature | Titan Integration | Enhancement Over TradingAgents |  
| --- | --- | --- |  
| 4-Analyst concurrent pipeline | Multi-analyst evidence pipeline (fundamentals, sentiment, news, technical) | DeFi-native: on-chain metrics, mempool data, funding rates replace equity-centric Yahoo Finance data |  
| Bull/Bear research debate | BULL_RESEARCHER / BEAR_RESEARCHER adversarial sub-roles | Classical-only (quantum dormant)|  
| Structured-output agents | JSON-enforced thesis schemas for all debate participants | Integrated with existing BFT voting consensus (2-of-3 threshold) |  
| Risk management debate | AGGRESSIVE_RISK_AGENT / CONSERVATIVE_RISK_AGENT | Classical-only (quantum dormant)|  
| Portfolio Manager approval | GUARDIAN as final authority gate | Augmented with 44-pipeline portfolio-level constraint checking |  
| Trading Memory Decision Log | JSONL decision audit trail with 3-phase lifecycle | Classical signal provenance tracking only (quantum dormant) |  

<!-- truncated to bootstrap char limit -->
