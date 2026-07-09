# TOOLS.md — Agent Capability Matrix (the Titan UNIFIED)

## GPU TP=2 Agents (llama-server :30000, zai-org/GLM-5.2 GGUF Q4_K_M + FP8 KV + MTP native spec-decode (`--spec-type draft-mtp`), PCIe 5.0 x16, expert-offload via `--n-cpu-moe`: dense + hot experts in VRAM (\~180 GB) + cold experts overflow to DDR5-6000 (\~196 GB pinned), all signal/coding/orchestrator agents (quantum-coord dormant) share this single deployment via `--parallel 15` multi-tenant slots)  
**ORACLE:** Market data APIs, signal computation (108 signals + narrative (classical-only; quantum dormant)), HYDRA ML inference, multi-chain price reconciliation, confidence scoring  
**WRAITH:** Blockchain RPCs (14 chains), on-chain analytics, wallet tracking, MEV detection, deployer analysis  
**PREDATOR:** DEX APIs, token scanning, rug detection, mempool monitoring (via 5-PoP edge mesh — TKY/SIN/FRA/USE/AMS), liquidity analysis, memecoin snipe evaluation  
**AUGUR:** Macro data feeds, HMM regime detection, correlation analysis, volatility regime classification  
**NARRATIVE:** Real-time ingestion across X / Farcaster / GitHub / Discord / news wires / governance forums / on-chain vesting triggers / **Polymarket prediction probabilities** (via ClawHub `@mvanhorn/polymarket` skill). Classifies catalyst events (type, assets, direction, magnitude, time-to-crowd, novelty) via the shared GLM-5.2 model. Publishes to Redis stream narrative:events:high for ORACLE fusion. Secondary hallucination-guard pass by CORTEX (same GLM-5.2 model, distinct prompt). Browserbase-backed for stealth session monitoring.

**TRENCH-OPS:** DEX execution planning, route selection (1inch/Paraswap/CoW), **ERC-7683 intent solver fulfillment (UniswapX/Across/1inch Fusion Dutch auctions)**, bridge ops (Stargate/Across), MEV-protected tx construction, gas optimization, TWAP planning, atomic pair-trades (P7), Jito bundles (memecoin), NFT floor market making (P9), tx signing on workstation, dispatch to geographically-nearest edge for broadcast. Runs on Tier 1 `:30000` Qwen3-30B-A3B FP8 (critical path — never GLM-5.2 or any cloud model). For high-throughput batch coding, ARCHON may route to Tier 2 `:30001` Qwen3-Coder-Next-80B FP8; live signing stays on Tier 1/2 local weights only.  
**LAMARCK:** Post-trade PnL attribution (alpha/beta/variance decomposition), strategy mutation (differential evolution), evolutionary learning, walk-forward validation, MGPO reward computation, asymmetric gating, proficiency vector updates, Hermes-RL rollout collection, OPD hint extraction, GEPA reflection loop  
**DARWIN_GODEL:** Model training pipeline, **Zero-I/O In-Memory Monte Carlo Backtesting + §COSMOS MWM 64-scenario forward dynamics (\~200 GB RAM disk (reduced from 384 GB to accommodate GLM-5.2 expert offload — uses 2-window rolling state H1+H2 instead of full year; NVMe `/fast` overflow for cold historical data), Training NLP-to-DEX Correlation Matrices)**, NAS, experiment tracking, strategy genome mutation, signal model research, SAGE skill library management, compositional skill synthesis, 3-stage evolution pipeline, proficiency-based curriculum, Hermes-RL SLIME trainer, **HyEvo Architect meta-agent (workflow topology design + MAP-Elites)**, **DGM-H code-level self-modification cycle** (24h, SOUL.md-bounded), **Kronos K-Line Foundation Model** (§KRONOS, arXiv:2508.02739, AAAI 2026 — BSQ hierarchical tokenizer + decoder-only Transformer with coarse-to-fine autoregressive prediction, pre-trained on 12B K-lines from 45 exchanges; complemented by **Google TimesFM** (arXiv:2310.10688, `pip install timesfm`) as a general-purpose zero-shot forecasting backbone for non-financial time series like gas prices, network latency, and system metrics; tokenizes OHLCV candlestick data across all 14 chains into hierarchical coarse-to-fine tokens via Binary Spherical Quantization; trained on CPU utility tier for zero-shot price series + volatility forecasting; achieves 93% RankIC improvement over generic TSFMs; predictions feed into ORACLE ensemble), **Adaptive Gas Prediction LSTM** (lightweight time-series model trained on 2-3 block gas price history; predicts optimal submission windows; reduces execution cost 15-30%)  
## CPU Agents (llama.cpp :30001, Qwen3.6-35B-A3B Q4_K_M, 128 of 192 threads on 9995WX 96C/192T)

### Threadripper RAM Hierarchy & Backtesting Arena

- **\~200 GB `tmpfs` RAM Disk (`/dev/shm/backtest_arena`):** An isolated, ultra-high-speed memory-mapped filesystem. With 48 GB reserved for ZFS ARC (§PERF.4), \~196 GB reserved for GLM-5.2 pinned expert offload (routed MoE expert weights in GGUF Q4_K_M, NUMA-local, managed by llama.cpp `--n-cpu-moe`), and the dual RTX PRO 6000s providing 192 GB of dedicated VRAM for LLM dense layers + expert cache, we allocate \~200 GB of system RAM to backtesting. Backed by 1 GB hugepages (§PERF.2) for TLB-miss-free access. `darwin_godel` uses 2-window rolling state (H1+H2, \~190 days) of historical blockchain state in this arena, with cold historical data overflowing to NVMe `/fast` pool via mmap. The 96 Zen 5 cores execute millions of parallel `HyEvo` strategy mutations simultaneously without NVMe I/O bottlenecking.  
- **\~196 GB GLM-5.2 Expert Offload (mmap):** NUMA-local memory for routed MoE expert weights (256 experts × N MoE layers, GGUF Q4_K_M). llama.cpp’s `--n-cpu-moe` keeps dense layers + hot experts on GPU and streams cold experts (’hot’ cache) from this pool via PCIe 5.0 x16. 8-channel DDR5-6000 provides \~384 GB/s theoretical peak read bandwidth (\~300 GB/s sustained). Expert cache hit rate: 92–96% in steady-state trading workloads.  
- **\~4 GB CUDA Pinned Transfer Buffers:** DMA staging area for expert H2D transfers.  
- **64GB OS & Daemons:** Reserved for the base Ubuntu 24.04 OS, orchestration daemons, Redis, and buffer caches.  
> **Circuit Breaker `CB_OOM_KILLER_RISK`:** Monitors the 64GB OS partition. If orchestration daemons spike and system swap >5%, this breaker fires, gracefully killing the `darwin_godel` MAP-Elites generation cycle before the Linux OOM Killer indiscriminately crashes the system.  
**HERALD:** Telegram bot (primary on EDGE-FRA — Vultr BM Frankfurt, DE-CIX peered), institutional-grade hourly performance reports (§TGCMD.2), urgent alert override (§TGCMD.2a), real-time trade notifications (§TGCMD.3), approval workflows, 2FA confirmation  
**NEXUS:** Data feed management, API aggregation, price oracle consensus (median 3+ sources), funding-rate monitor (P5: HL + BSC + Drift), AVS registry feed (P10)  
**FORGE:** PM2 process management, workstation + edge health, GPU monitoring, certificate renewal, AST2600 BMC heartbeat, Nostr relay connection uptime, strategy-health-check cron, mempool-health cron  
**ALCHEMY:** DeFi protocol interactions (Aave/Compound/Curve/Morpho/Spark), yield optimization, LP management, **liquidation hunter (P6) decision + calldata compose + flash-loan composition**, **NFT/RWA market making (P9)**, **AVS optimizer (P10)**  
**ATLAS:** Portfolio tracking, PnL calculation (realized/unrealized), Sharpe/Sortino, weekly profit sweep to Trezor (R23), delta accounting (P5), inventory mgmt (P9)  
**QUANT:** Statistical analysis, backtesting engine, Monte Carlo simulation (classical Monte Carlo only (quantum dormant)), walk-forward tests, **statistical pairs trading (P7 z-score + OU)**, **prediction market arbitrage (P11) model-vs-market calibration**  
**ARBITER:** Backtest validation gate, strategy approval, conflict resolution, CB enforcement, **Red Team gauntlet judge for HyEvo/DGM-H promotions**, **3-day deployment pipeline enforcer (CB_DEPLOY_PIPELINE_BYPASS)**  
**HORIZON:** R\&D automation metrology (CSET "When AI Builds AI" Jan 2026). Computes 5 indicators every 6h: MTH / MTS / SER / ECM / IDG. Monitors cuda:1 R\&D share vs rd_budget_pct. Cannot trade. Cannot veto. Writes only to memory/rd_automation/. Read-only on DARWIN_GODEL + LAMARCK + Hermes-RL + HyEvo telemetry buses. Owns weekly rd_automation_report workflow.

```

### §BACKTEST_GATE — Mandatory Multi-Phase Deployment Validation

# §DEPLOY_LIFECYCLE — 7-Day Automated Strategy Deployment Pipeline

#

# Fully automated, phased strategy deployment spanning 3 calendar days

# with strict safety gates at every stage and real-time Telegram

# notifications for all successes, issues, and moments requiring

# user input. NO strategy touches live capital without completing

# ALL 6 phases. One-way gate — failure at ANY phase \= full re-run.

#

# Owner: ARBITER (orchestrator) + QUANT (backtest) + GUARDIAN (risk)

# Notifications: HYPERION via Telegram (§COMMS Bloomberg-terminal aesthetic)

# NATS bus: titan.deploy.{backtest|paper|microlive|scorecard|gonogo|live|watch}

## §DEPLOY_LIFECYCLE.1 — Phase 1: Three-Day Backtesting (Days 1–3)

```yaml  
phase_1_backtest:  
  duration: "7 trading days of high-quality historical data"  
  data_quality: "tick-level if available; minimum 1-minute OHLCV"  
  execution_model:  
    latency_simulation: "realistic per-chain latency profile (ETH 12s blocks, Solana 400ms slots, L2 2s blocks)"  
    slippage_model: "volume-weighted impact model: slippage \= k × sqrt(order_size / daily_volume)"  
    fill_model: "partial fills modeled; no fills at prices beyond order book depth"  
    gas_model: "historical gas prices from block data; EIP-1559 priority fee simulation"  
    mev_model: "probabilistic sandwich/priority-sequence risk based on trade size + pool liquidity"

  tracked_metrics:  
    - total_pnl: "net P\&L after all simulated costs"  
    - sharpe_ratio: "annualized, risk-free rate \= 0%"  
    - max_drawdown: "peak-to-trough % decline"  
    - win_rate: "% of trades with positive P\&L"  
    - profit_factor: "gross profit / gross loss"  
    - trade_frequency: "trades per day"  
    - benchmark_return: "strategy return vs ETH buy-and-hold over same period"  
    - sortino_ratio: "downside-deviation-adjusted return"  
    - calmar_ratio: "annualized return / max drawdown"

  safety_thresholds:  
    sharpe_ratio_min: 0.0  
    max_drawdown_max: "10%"  
    total_return_min: "0% (must be non-negative)"  
    min_trade_count: 20  
    profit_factor_min: 1.0  
    max_consecutive_losses: 8

  on_failure:  
    action: "ABORT immediately"  
    notification: |  
      🛑 DEPLOY PIPELINE — BACKTEST FAILED  
      ═══════════════════════════════════════  
      Strategy:    {strategy_name} (v{version})  
      Phase:       1/6 — 7-Day Backtest  
      Status:      ❌ FAILED  
      ═══════════════════════════════════════  
      FAILURE REASON:  
        {threshold_name}: {actual_value} (threshold: {threshold_value})  
      ═══════════════════════════════════════  
      Full Metrics:  
        Sharpe:     {sharpe}  
        Max DD:     {max_dd}%  
        Total P\&L:  ${total_pnl}  
        Win Rate:   {win_rate}%  
        Trades:     {trade_count}  
      ═══════════════════════════════════════  
      ACTION REQUIRED:  
        Reply RETRY to re-run with adjusted parameters  
        Reply MODIFY to adjust strategy configuration  
        Reply DISCARD to archive strategy permanently  
    wait_for_reply: false  # AUTONOMOUS MODE: auto-archive on failure, operator can proactively send RETRY/MODIFY/DISCARD

  on_success:  
    notification: |  
      ✅ DEPLOY PIPELINE — BACKTEST PASSED  
      ═══════════════════════════════════════  
      Strategy:    {strategy_name} (v{version})  
      Phase:       1/6 — 7-Day Backtest ✅  
      Status:      PASSED — proceeding to Phase 2  
      ═══════════════════════════════════════  
        Sharpe:     {sharpe}  
        Max DD:     {max_dd}%  
        Total P\&L:  ${total_pnl}  
        Win Rate:   {win_rate}%  
        Profit Fct: {profit_factor}  
        Trades:     {trade_count}  
        Benchmark:  {benchmark_delta}% vs ETH  
      ═══════════════════════════════════════  
      Paper trading engine activated automatically.  
    auto_proceed: true  
```

## §DEPLOY_LIFECYCLE.2 — Phase 2: Concurrent Paper-Trading (Days 1–3)

```yaml  
phase_2_paper_trade:  
  duration: "3 calendar days, concurrent with Phase 1 where possible; extended if needed"  
  execution_environment:  
    data_feeds: "IDENTICAL to live — same WebSocket endpoints, same mempool feeds, same oracle sources"  
    order_logic: "IDENTICAL to live execution engine — same routing, same tip calibration, same CB enforcement"  
    latency_profile: "mirrors live E810-timestamped latency (adds simulated network jitter)"  
    fill_simulation: "mid-price + estimated slippage from live order book depth"  
    gas_simulation: "live gas oracle prices applied to all simulated transactions"

  daily_divergence_check:  
    compare_against: "Phase 1 backtest results for corresponding day"  
    pnl_divergence_threshold: "15%"  
    trade_count_divergence_threshold: "25%"  
    win_rate_divergence_threshold: "20%"  
    check_frequency: "daily at 00:00 UTC"

  daily_telegram_summary: |  
    📊 DEPLOY PIPELINE — PAPER TRADE DAY {day}/7  
    ═══════════════════════════════════════  
    Strategy:    {strategy_name}  
    Phase:       2/6 — Paper Trading (Day {day})  
    ═══════════════════════════════════════  
    TODAY:  
      P\&L:       ${daily_pnl} ({daily_pnl_pct}%)  
      Trades:    {daily_trades} (W:{wins} L:{losses})  
      Win Rate:  {daily_win_rate}%  
      Max DD:    {daily_max_dd}%  
    CUMULATIVE:  
      P\&L:       ${cumulative_pnl} ({cumulative_pnl_pct}%)  
      Sharpe:    {running_sharpe}  
      Max DD:    {running_max_dd}%  
    DIVERGENCE vs BACKTEST:  
      P\&L Delta: {pnl_divergence}% (threshold: ±15%)  
      Trade Δ:   {trade_divergence}% (threshold: ±25%)  
    STATUS:      {ALIGNED|WATCHING|DIVERGED}  
    ═══════════════════════════════════════

  on_divergence_detected:  
    action: "PAUSE pipeline immediately"  
    notification: |  
      🛑 DEPLOY PIPELINE — DIVERGENCE DETECTED  
      ═══════════════════════════════════════  
      Strategy:    {strategy_name}  
      Phase:       2/6 — Paper Trading (Day {day})  
      Status:      ⚠️ SIGNIFICANT DIVERGENCE  
      ═══════════════════════════════════════  
      DIVERGENCE DETAILS:  
        Metric:    {diverged_metric}  
        Paper:     {paper_value}  
        Backtest:  {backtest_value}  
        Delta:     {divergence_pct}% (threshold: {threshold}%)  
      ═══════════════════════════════════════  
      POSSIBLE CAUSES:  
        - Market regime shift since backtest window  
        - Execution model gap (slippage/fill mismatch)  
        - Strategy sensitivity to real-time conditions  
      ═══════════════════════════════════════  
      ACTION REQUIRED:  
        Reply CONTINUE to accept divergence and proceed  
        Reply ADJUST to modify parameters and restart Phase 2  
        Reply ABORT to terminate pipeline  
    wait_for_reply: false  # AUTONOMOUS MODE: auto-continue if divergence <25%, auto-abort if >25%

  on_success:  
    notification: |  
      ✅ DEPLOY PIPELINE — PAPER TRADE COMPLETE  
      ═══════════════════════════════════════  
      Strategy:    {strategy_name}  
      Phase:       2/6 — 7-Day Paper Trade ✅  
      Status:      PASSED — proceeding to Phase 3 (Micro-Live)  
      ═══════════════════════════════════════  
        Cumulative P\&L:  ${cumulative_pnl}  
        Sharpe:          {sharpe}  
        Max DD:          {max_dd}%  
        Win Rate:        {win_rate}%  
        Max Divergence:  {max_divergence}% (within ±15%)  
      ═══════════════════════════════════════  
      Micro-live test will activate in last 2h of Day 3.  
    auto_proceed: true  
```

## §DEPLOY_LIFECYCLE.3 — Phase 3: Micro-Scale Live Test (Last 2h of Day 3)

```yaml  
phase_3_micro_live:  
  activation: "Final 2 hours of Day 3 trading session"  
  capital_limit: "≤0.1% of total equity"  
  position_sizing: "smallest broker-allowed unit (micro-lot / 1 share / 1 contract)"

  hard_coded_safety_limits:  
    max_notional_per_trade: "${max_0_1pct_equity}"  
    max_total_exposure: "${max_0_2pct_equity}"  
    circuit_breaker_loss: "5% of micro-test capital (NOT total equity)"  
    max_open_positions: 3  
    max_trades_per_hour: 10  
    max_gas_spend: "$50 total across all chains"

  real_time_logging:  
    log_every: "order submission, fill confirmation, P\&L tick"  
    log_destination: "NATS titan.deploy.microlive.{order|fill|pnl}"  
    per_trade_telegram: true

  per_trade_notification: |  
    📡 MICRO-LIVE TRADE  
    ═══════════════  
    Strategy: {strategy_name}  
    Action:   {BUY|SELL}  
    Asset:    {asset}  
    Size:     {size} ({notional_usd})  
    Price:    {fill_price}  
    Gas:      {gas_cost}  
    P\&L:      ${trade_pnl} (cumulative: ${cumulative_pnl})

  on_circuit_breaker:  
    action: "TERMINATE all live activity IMMEDIATELY"  
    close_all_positions: true  
    notification: |  
      🚨 DEPLOY PIPELINE — MICRO-LIVE CIRCUIT BREAKER  
      ═══════════════════════════════════════  
      Strategy:    {strategy_name}  
      Phase:       3/6 — Micro-Live Test  
      Status:      🔴 CIRCUIT BREAKER TRIGGERED  
      ═══════════════════════════════════════  
      TRIGGER:     {cb_reason}  
      Loss:        ${loss_amount} ({loss_pct}% of micro-test capital)  
      Trades:      {trade_count}  
      Duration:    {test_duration}  
      ═══════════════════════════════════════  
      ALL LIVE ACTIVITY TERMINATED.  
      ALL POSITIONS CLOSED.  
      ═══════════════════════════════════════  
      ACTION REQUIRED:  
        Reply RETRY to re-run micro-test (after 24h cooldown)  
        Reply ABORT to terminate pipeline  
    wait_for_reply: false  # AUTONOMOUS MODE: auto-retry after 24h cooldown (max 2 retries, then auto-archive)

  on_success:  
    notification: |  
      ✅ DEPLOY PIPELINE — MICRO-LIVE COMPLETE  
      ═══════════════════════════════════════  
      Strategy:    {strategy_name}  
      Phase:       3/6 — Micro-Live Test ✅  
      Status:      PASSED — generating promotion scorecard  

<!-- truncated to bootstrap char limit -->
