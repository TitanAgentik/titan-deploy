# §SKILLS_full.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `SKILLS_full.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Index of extracted skill directories (full bodies live under output/workspace/skills/*/SKILL.md).
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---


## Active skills

- `alchemy_defi/` — Alchemy Defi — stub skill (full definition pending §SKILLS_full.md)
- `arbiter_backtest/` — Arbiter Backtest — stub skill (full definition pending §SKILLS_full.md)
- `archon_orchestration/` — Archon Orchestration — stub skill (full definition pending §SKILLS_full.md)
- `atlas_portfolio/` — Atlas Portfolio — stub skill (full definition pending §SKILLS_full.md)
- `augur_macro/` — Augur Macro — stub skill (full definition pending §SKILLS_full.md)
- `auto_research/` — Auto Research
- `backtest_validation/` — Backtest Validation
- `bridge_security/` — Bridge Security
- `capability_surprise/` — Capability Surprise
- `causal_inference/` — CORTEX/ORACLE signal validation — DoWhy/EconML causal inference engine between signal detection and strategy execution; filters spurious correlations from genuine causal predictors
- `compositional_synthesis/` — Compositional Synthesis
- `cortex_reflection/` — Cortex Reflection — stub skill (full definition pending §SKILLS_full.md)
- `darwin_godel_research/` — Darwin Godel Research — stub skill (full definition pending §SKILLS_full.md)
- `defi_operations/` — Defi Operations
- `dissent_log/` — Dissent Log
- `flash_loan_router/` — Multi-source flash-loan routing — Balancer/Morpho/Uni V4/Aave atomic compose
- `forge_infra/` — Forge Infra — TITANHOME health, UPS telemetry, GPU schedule enforcement
- `guardian_risk/` — Guardian Risk — stub skill (full definition pending §SKILLS_full.md)
- `herald_notify/` — HERALD institutional Telegram trade notifications — JSON-first payloads + Markdown alerts (§TGCMD.2 / §TGCMD.3)
- `honcho_operator/` — Honcho dialectic user modeling for Hyperion operator context — peer cards, session summary, dual-layer injection
- `horizon_rd/` — Horizon Rd — stub skill (full definition pending §SKILLS_full.md)
- `infra_health/` — Infra Health
- `lamarck_learning/` — Lamarck Learning — stub skill (full definition pending §SKILLS_full.md)
- `liquidation_hunter/` — Liquidation Hunter
- `maintenance_scanner/` — Maintenance Scanner
- `market_regime/` — Market Regime
- `memecoin_trench/` — P22 Solana memecoin trench — Pump.fun lifecycle, 6-gate filter, Jito execution
- `memory_management/` — Memory Management
- `narrative_catalyst/` — Narrative Catalyst
- `nexus_feeds/` — Nexus Feeds — stub skill (full definition pending §SKILLS_full.md)
- `on_chain_intel/` — On Chain Intel
- `online_learning/` — Online Learning
- `oracle_signals/` — Oracle Signals — stub skill (full definition pending §SKILLS_full.md)
- `portfolio_management/` — Portfolio Management
- `predator_scanner/` — PREDATOR stalking + predatory modules — mempool hunt, copy-trade detect, honeypot feed, poison fills
- `quant_analysis/` — Quant Analysis — stub skill (full definition pending §SKILLS_full.md)
- `rd_metrology/` — Rd Metrology
- `research_scout/` — see SKILL.md
- `risk_validation/` — Risk Validation
- `security_audit/` — Security Audit
- `sentinel_security/` — SENTINEL four-pillar security — Impenetrable layers, PCR/CodeQL, honeypot arm, lockdown sequencing
- `signal_analysis/` — Signal Analysis
- `skill_evolution/` — see SKILL.md
- `stat_pairs_trading/` — Stat Pairs Trading
- `trade_execution/` — Trade Execution
- `trench_ops_execution/` — Trench Ops Execution — DEX/bridge execution with in-process signing
- `voice_mode/` — ---
- `wraith_onchain/` — Wraith Onchain — stub skill (full definition pending §SKILLS_full.md)

## Archived (not loaded at runtime)

- `_archived/quantum/quantum_counterparty_score/`
- `_archived/quantum/quantum_derivative_pricing/`
- `_archived/quantum/quantum_fraud_detection/`
- `_archived/quantum/quantum_gas_prediction/`
- `_archived/quantum/quantum_portfolio_rebalance/`
- `_archived/quantum/quantum_var_cvar/`
- `_archived/quantum/quantum_yield_optimizer/`

## OpenClaw / Hermes load order

- OpenClaw workspace skills: `~/.openclaw/workspace/skills/` (highest precedence)
- Hermes: symlink or copy to `~/.hermes/skills`
- Quantum skills stay under `_archived/quantum/` — dormant for live capital
