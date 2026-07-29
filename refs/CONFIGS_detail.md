# §CONFIGS_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `CONFIGS_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Full Hermes config.yaml + OpenClaw openclaw.json + risk policy bodies that TITAN stubs as `# → see §CONFIGS_detail.md`.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Hermes `~/.hermes/config.yaml`

```yaml
# TITAN Hermes Agent Configuration
# Deploy target: ~/.hermes/config.yaml

system:
  name: titan
  version: "49.7"
  framework: openclaw-hermes-unified
  autonomy: bounded_supervised  # human gates for promotion/evolution/>1% equity

autonomy_matrix:
  auto_execute:
    - routine_trades_under_1pct_equity
    - agent_bft_verified_trades_up_to_max_equity_pct
    - autonomous_sign_and_verify
    - rebalances_under_1pct_equity
    - cb_tier_responses_within_policy
    - shadow_evolution_outputs
    - paper_trading
  human_required:
    - strategy_promotion_phase5
    - evolution_deploy_to_live
    - leverage_changes
    - flash_loan_live
    - new_pipeline_activation
    - model_promotion
  timeout_policy: hold_derisk_never_auto_promote

model:
  default: qwen3-critical
  tier1_critical:
    provider: openai-compatible
    base_url: http://localhost:30000/v1
    model: Qwen/Qwen3-30B-A3B-Instruct-2507-FP8
    gpu: 0
    role: signals_risk_execution
  tier2_reasoning:
    provider: openai-compatible
    base_url: http://localhost:30001/v1
    model: Qwen/Qwen3-Coder-Next-80B-A3B-Instruct
    gpu: 1
    role: orchestration_strategy_code
  tier3_offline:
    provider: openai-compatible
    base_url: http://localhost:30003/v1
    model: zai-org/GLM-5.2
    role: rd_evolution_batch_only
    critical_path: false
  tier3a_deepseek:
    provider: openai-compatible
    base_url: http://localhost:30005/v1
    model: deepseek-ai/DeepSeek-V4-Pro
    role: rd_evolution_primary
    critical_path: false
  utility:
    provider: openai-compatible
    base_url: http://192.168.10.20:30002/v1
    fallback_url: http://10.0.10.3:30002/v1
    model: Qwen3-30B-A3B-Instruct-2507
    host: titanspark
  embedder:
    base_url: http://localhost:30004/v1
    model: Qwen3-Embedding-0.6B

gateway:
  openclaw:
    host: localhost
    port: 18789

channels:
  telegram:
    enabled: true
    token_env: TELEGRAM_BOT_TOKEN
    user_id_env: TELEGRAM_USER_ID
    mode: informational  # no per-trade approval; promotion gates via PENDING_PROMOTION_APPROVAL
    parse_mode: Markdown
    json_first: true

notifications:
  herald:
    skill: herald_notify
    templates_dir: ~/.openclaw/workspace/telegram
    schema: trade_notification.v1.json
    material_threshold_pct_equity: 0.5
    immediate_severities: [CRITICAL, HIGH]
    nats:
      trade: tgcmd.herald.trade
      pnl: tgcmd.herald.pnl
      hourly: tgcmd.herald.report.hourly
      urgent: tgcmd.herald.alert.urgent
    delivery:
      per_trade_telegram: true
      hourly_digest: true
      material_immediate: true

promotion:
  paper_minimum_days: 3
  phase5_requires_human_yes: true
  timeout_policy: hold_derisk
  air_gapped_staging: true
  staging_path: ~/.openclaw/staging/
  playbook_path: ~/.openclaw/playbooks/promotion.yaml
  red_team_checklist: ~/.openclaw/playbooks/red_team_checklist.yaml  # silence never auto-promotes
  shadow_only_evolution:
    - dgm-h
    - gepa
    - hyevo
    - sia-lora
    - eurekagent
    - gris-model-swap

rollout:
  phase_duration_days: 3
  operator_directive: true
  note: "3 days per phase per operator directive — gates and human YES unchanged"
  phases:
    - id: 0
      name: infrastructure_paper
      duration_days: 3
    - id: 1
      name: micro_live
      duration_days: 3
    - id: 2
      name: validated_scale
      duration_days: 3
    - id: 3
      name: mature_production
      duration_days: 3

dead_mans_switch:
  operator_heartbeat_hours: 48
  flatten_after_hours: 72
  on_miss: derisk_flatten
  never_auto_promote: true

drawdown_notify_only: true

drawdown_volatile_exempt:
  pipelines: [P22, P29, P30, P12]
  correlation_groups: [memecoin_trench, mev_arb]
  venues: [solana_pumpfun, solana_pumpswap, jito, paper]
  note: "No portfolio drawdown tiers — lane-local CBs only"

drawdown_tiers:
  alert: 2.0
  soft_pause: 5.0
  reduce: 8.0
  critical: 10.0
  halt: 12.0

drawdown_velocity:
  max_loss_usd_per_60s: 150
  max_loss_usd_per_15m: 400

terminal:
  json_first: true
  confidence_tagging: true

memory:
  provider: honcho
  honcho_config: ~/.hermes/honcho.json
  engine: sqlite
  path: ~/.hermes/memory/titan.db
  fts5: true
  openclaw_sync: ~/.openclaw/memory/
  note: "Honcho dialectic user modeling — see HONCHO_SETUP.md; SQLite FTS5 remains fallback when provider != honcho"

skills:
  directory: ~/.openclaw/workspace/skills
  symlink_from_hermes: true
  trust_tiers:
    - T1  # metadata only
    - T2  # full instructions
    - T3  # execution code

mcp_servers:
  - name: nats
    command: nats-mcp-bridge
    env:
      NATS_URL: nats://localhost:4222
  - name: filesystem
    command: mcp-server-filesystem
    args: ["~/.openclaw/workspace"]

cron:
  - name: daily_brief
    schedule: "0 8 * * *"
    agent: HERALD
    task: daily_brief
  - name: hourly_report
    schedule: "0 * * * *"
    agent: HERALD
    task: hourly_performance_report
  - name: weekly_rd_brief
    schedule: "0 9 * * 1"
    agent: HORIZON
    task: weekly_rd_brief
  - name: operator_heartbeat_check
    schedule: "0 */6 * * *"
    agent: FORGE
    task: dead_mans_switch_check

activeHours:
  timezone: UTC
  trading: "00:00-23:59"
  maintenance_window: "06:00-10:00"

quantum:
  status: dormant
  cloud_qpu_enabled: false
  cuquantum_enabled: false
  wukong_budget_active: false
  note: "Classical-only — quantum agents removed from catalog; no QPU dispatch for live capital"

risk_kernel:
  enabled: true
  policy_path: ~/.openclaw/risk_kernel/policy.yaml
  out_of_process: true
  pre_trade_validation_url: http://127.0.0.1:19001/v1/validate
  portfolio_risk_url: http://127.0.0.1:19004/v1/simulate
  reconciliation_gate_url: http://127.0.0.1:19002/v1/pre_trade
  fail_closed: true

kill_switch:
  safety_dir: ~/.openclaw/safety
  cli_path: ~/.openclaw/safety/bin/titan-safety

safety_services:
  risk_kernel: http://127.0.0.1:19001/health
  reconciliation: http://127.0.0.1:19002/health
  status_aggregator: http://127.0.0.1:19003/health
  portfolio_risk: http://127.0.0.1:19004/health
  dead_mans_switch: http://127.0.0.1:19005/health

observability:
  prometheus_scrape:
    - http://127.0.0.1:19001/metrics
    - http://127.0.0.1:19003/metrics
    - http://127.0.0.1:19004/metrics
  grafana_stub: ~/.openclaw/playbooks/observability_grafana_stub.yaml

infrastructure:
  hardware_bom: ~/.openclaw/infra/hardware_bom.yaml
  titanhome:
    role: primary_compute_inference_safety
    cpu: "AMD Ryzen Threadripper PRO 9995WX (96C/192T)"
    motherboard: "ASUS Pro WS WRX90E-SAGE SE"
    memory: "512GB DDR5-6000 ECC R-DIMM"
    gpu: "2× NVIDIA RTX PRO 6000 Blackwell Max-Q (192GB VRAM)"
    storage: "Micron 7500 Pro 3.8TB + 2× WD Black SN8100 4TB"
    psu: "Super Flower Leadex Titanium 2200W"
    timing: "Leo Bodnar LBE-1425 GPSDO → Intel E810-XXVDA4T"
    nic: "Intel E810-XXVDA4T"
    ups: "Eaton 9SX 3000VA / 2700W 208V"
    oob: "ASUS AST2600 BMC (PiKVM removed)"
    hosts:
      - tier1_inference_qwen3_30b  # :30000 GPU 0
      - tier2_inference_qwen3_coder_80b  # :30001 GPU 1
      - tier3_offline_glm52  # :30003 off-peak only
      - risk_kernel_services  # :19001-19005
      - revm_simulation  # :30020
      - safety_systemd_units
  titanspark:
    role: utility_inference_operator_gateway
    hardware: ASUS GX10
    hosts:
      - qwen3_utility  # :30002
      - telegram_gateway_failover
  macmini_vault:
    role: encrypted_key_metadata_trezor_ceremonies
    hardware: "Mac Mini 2018 — i7 6-core, 64GB DDR4"
    note: "Key custody + profit workloads; signing via in-process titan-safety on TITANHOME"
  power_requirements: ~/.openclaw/infra/power_requirements.yaml
  gpu_schedule: ~/.openclaw/infra/gpu_schedule.yaml
  signing_node: ~/.openclaw/infra/signing_node.yaml

signing_node:
  enabled: true
  mode: in_process
  endpoint: ""
  host: localhost
  port: 19010
  isolated: true
  route_agents:
    - TRENCH-OPS
    - LAMARCK
  note: "In-process SigningNode; :19010 optional legacy only"

edge_mesh:
  mode: full_mesh
  phase1: full_five_pop
  default_pop: EDGE-FRA
  paper_latency_faithful: true
  mesh_config: ~/.openclaw/infra/edge_mesh.yaml
  latency_budget_ms:
    hot_path_gate_p95: 15
    hot_path_submit_p95: 50
    home_to_edge_p95: 25
    edge_to_jito_p95: 5
    edge_to_exchange_p95: 1
    nostr_dispatch: 3
    warm_path_gate_p95: 150
  phase1_apac_deferred: false
  routing_policy: lowest_live_p50_rtt
  active_pops:
    - id: EDGE-FRA
      wireguard_ip: 10.0.10.100
      provider: vultr
      region: eu-central
      roles: [erigon_archive, jito_fra, eu_rpc, telegram_relay]
    - id: EDGE-TKY
      wireguard_ip: 10.0.10.101
      provider: aws
      region: ap-northeast-1
      roles: [binance, okx, hyperliquid]
    - id: EDGE-SIN
      wireguard_ip: 10.0.10.102
      provider: aws
      region: ap-southeast-1
      roles: [bybit, bsc, sui]
    - id: EDGE-USE
      wireguard_ip: 10.0.10.103
      provider: aws
      region: us-east-1
      roles: [coinbase, l2_sequencers, flashbots_us]
    - id: EDGE-AMS
      wireguard_ip: 10.0.10.104
      provider: vultr
      region: amsterdam
      roles: [solana_grpc_redundancy, nostr_relay]
  note: "Full 5-PoP from paper — scale instance size with capital; routing identical to live"

capital:
  capital_profile: paper
  state_path: ~/.openclaw/capital/portfolio_state.json
  audit_path: ~/.openclaw/capital/capital_audit.jsonl
  min_operating_capital_usd: 500
  max_single_withdrawal_pct: 20
  withdrawal_adapter: trezor_signing
  trezor_sweep:
    harvest_threshold_usd: 15000
    sweep_pct_of_weekly_profit: 20
    sweep_day_utc: Sunday
    pause_below_threshold: true
    note: "Growth phase below $15K — 100% reinvest; no sweep until harvest threshold"
  telegram_commands:
    deposit: "/deposit <amount> <asset> [chain] [tx_hash] [source]"
    withdraw: "/withdraw <amount> <asset> [address]"
    withdraw_confirm: "/withdraw confirm <request_id>"
    balance: "/balance"
    sweep: "/sweep"
    alt_prefix: "/capital deposit|withdraw|balance|sweep"
```

## OpenClaw `~/.openclaw/openclaw.json`

```json
{
  "version": "49.7",
  "framework": "titan-unified",
  "capitalProfile": "live",
  "bootstrapMaxChars": 20000,
  "bootstrapTotalMaxChars": 150000,
  "_bootstrapNote": "OpenClaw default total is 60000; TITAN raises to 150000 for AGENTS.md. Workspace is ~/.openclaw/workspace (not config root).",
  "gateway": {
    "host": "0.0.0.0",
    "port": 18789,
    "telegram": {
      "enabled": true,
      "tokenEnv": "TELEGRAM_BOT_TOKEN",
      "allowedUsers": [
        "${TELEGRAM_USER_ID}"
      ],
      "parseMode": "Markdown",
      "jsonFirst": true
    }
  },
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace",
      "bootstrapMaxChars": 20000,
      "bootstrapTotalMaxChars": 150000,
      "skipBootstrap": false
    },
    "defaultModel": "qwen3-critical",
    "subAgentPromptMode": "minimal",
    "confidenceGate": {
      "fullSize": 0.7,
      "reducedSize": 0.5,
      "reject": 0.3
    },
    "autonomousSigning": {
      "enabled": true,
      "requireGateReceipt": true,
      "requireTypedDataLive": true,
      "bftVoters": [
        "AUGUR",
        "PREDATOR",
        "ATLAS"
      ],
      "bftThreshold": 2,
      "bftAboveEquityPct": 1.0,
      "note": "Agents verify + sign via in-process titan-safety SigningNode \u2014 no human on trade path; kernel DENY is authoritative"
    },
    "definitions": [
      {
        "id": "ARCHON",
        "tier": "orchestrator",
        "endpoint": "http://localhost:30001",
        "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct"
      },
      {
        "id": "CORTEX",
        "tier": "orchestrator",
        "endpoint": "http://localhost:30005",
        "fallbackEndpoint": "http://localhost:30001",
        "model": "deepseek-ai/DeepSeek-V4-Pro"
      },
      {
        "id": "GUARDIAN",
        "tier": "orchestrator",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "SENTINEL",
        "tier": "orchestrator",
        "endpoint": "http://localhost:30001",
        "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct"
      },
      {
        "id": "ORACLE",
        "tier": "signal",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "WRAITH",
        "tier": "signal",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "PREDATOR",
        "tier": "signal",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "AUGUR",
        "tier": "signal",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "NARRATIVE",
        "tier": "signal",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "TRENCH-OPS",
        "tier": "execution",
        "endpoint": "http://localhost:30000",
        "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
      },
      {
        "id": "LAMARCK",
        "tier": "execution",
        "endpoint": "http://localhost:30001",
        "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct"
      },
      {
        "id": "DARWIN_GODEL",
        "tier": "execution",
        "endpoint": "http://localhost:30001",
        "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct"
      },
      {
        "id": "HERALD",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "NEXUS",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "FORGE",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "ALCHEMY",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "ATLAS",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "QUANT",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "ARBITER",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      },
      {
        "id": "HORIZON",
        "tier": "utility",
        "endpoint": "http://localhost:30002",
        "model": "Qwen3-30B-A3B-Instruct-2507"
      }
    ]
  },
  "autonomy": {
    "mode": "bounded_supervised",
    "selectiveActivation": true,
    "note": "Specs are a catalog \u2014 enable only pipelines/skills/security modules required for current phase and capital. maxActivePipelines caps concentration.",
    "matrix": {
      "auto_execute": [
        "routine_trades_under_1pct_equity",
        "agent_bft_verified_trades_up_to_max_equity_pct",
        "autonomous_sign_and_verify",
        "rebalances_under_1pct_equity",
        "cb_tier_responses_within_policy",
        "shadow_evolution_outputs",
        "paper_trading",
        "heartbeat_and_health_checks",
        "honeypot_arm_disarm_sentinel",
        "predatory_poison_fills_under_1pct_equity"
      ],
      "human_required": [
        "strategy_promotion_phase5",
        "evolution_deploy_to_live",
        "leverage_changes",
        "flash_loan_live",
        "new_pipeline_activation",
        "model_promotion",
        "withdrawal_over_20pct_equity",
        "security_lockdown"
      ],
      "timeout_policy": "hold_derisk_never_auto_promote"
    },
    "humanGates": {
      "strategyPromotion": true,
      "evolutionDeploy": true,
      "leverageChanges": true,
      "flashLoanLive": true,
      "positionOver1PctEquity": false,
      "phase5GoNoGo": true,
      "securityLockdown": true
    },
    "criticalAlertsOnly": false,
    "criticalConditions": [
      "drawdown_10pct_24h",
      "drawdown_12pct_notify",
      "drawdown_velocity_15m",
      "hardware_failure",
      "security_breach",
      "pcr_drift",
      "honeypot_tripwire",
      "stalk_severity_high",
      "security_lockdown_activated",
      "soul_modification_attempt",
      "exchange_api_failure_5min",
      "unknown_contract_interaction"
    ],
    "operatorAbsencePolicy": "dead_mans_switch_derisk_never_implicit_approval"
  },
  "promotion": {
    "paperMinimumDays": 3,
    "phase5RequiresHumanYes": true,
    "timeoutPolicy": "hold_derisk",
    "airGappedStaging": true,
    "stagingPath": "~/.openclaw/staging/",
    "playbookPath": "~/.openclaw/playbooks/promotion.yaml",
    "redTeamChecklist": "~/.openclaw/playbooks/red_team_checklist.yaml",
    "shadowOnlyEvolution": [
      "dgm-h",
      "gepa",
      "hyevo",
      "sia-lora",
      "eurekagent",
      "gris-model-swap"
    ],
    "pendingState": "PENDING_PROMOTION_APPROVAL"
  },
  "evolution": {
    "freezeDuringLive": true,
    "flagFile": "~/.openclaw/safety/EVOLUTION_FROZEN",
    "note": "While frozen, promotion of evolution_deploy/strategy_promotion/phase5 is denied"
  },
  "rollout": {
    "phaseDurationDays": 3,
    "operatorDirective": true,
    "calendarIsNotAGate": true,
    "note": "Phase clock is advisory only \u2014 stretch until regime diversity + \u2265200 fills/lane; gates and human YES unchanged",
    "phases": [
      {
        "id": 0,
        "name": "infrastructure_paper",
        "durationDays": 3
      },
      {
        "id": 1,
        "name": "micro_live",
        "durationDays": 3
      },
      {
        "id": 2,
        "name": "validated_scale",
        "durationDays": 3
      },
      {
        "id": 3,
        "name": "mature_production",
        "durationDays": 3
      }
    ]
  },
  "deadMansSwitch": {
    "enabled": true,
    "operatorHeartbeatHours": 48,
    "flattenAfterHours": 72,
    "onMiss": "derisk_flatten",
    "neverAutoPromote": true
  },
  "riskKernel": {
    "enabled": true,
    "outOfProcess": true,
    "policyPath": "~/.openclaw/risk_kernel/policy.yaml",
    "preTradeValidationUrl": "http://127.0.0.1:19001/v1/validate",
    "portfolioRiskUrl": "http://127.0.0.1:19004/v1/simulate",
    "reconciliationGateUrl": "http://127.0.0.1:19002/v1/pre_trade",
    "failClosed": true,
    "servicePort": 19001
  },
  "killSwitch": {
    "safetyDir": "~/.openclaw/safety",
    "cliPath": "~/.openclaw/safety/bin/titan-safety",
    "fileFlag": "~/.openclaw/safety/KILL_SWITCH.active"
  },
  "securityOps": {
    "enabled": true,
    "pillars": [
      "impenetrable",
      "evasion",
      "stalking",
      "predatory"
    ],
    "doctrine": "invisible_to_them_visible_to_us",
    "cli": "titan-safety security",
    "playbook": "~/.openclaw/playbooks/security_lockdown.yaml",
    "honeypotDir": "~/.openclaw/safety/honeypots",
    "postureLog": "~/.openclaw/memory/security/posture.jsonl",
    "skills": [
      "sentinel_security",
      "predator_scanner"
    ],
    "refs": [
      "AEGIS",
      "FORTRESS",
      "GHOST",
      "MEV",
      "REAPER"
    ],
    "cockpitPath": "/security",
    "requireHmacForLockdown": true,
    "huntModeDefault": true,
    "honeypotArmedDefault": true,
    "servicePort": 19008,
    "healthUrl": "http://127.0.0.1:19008/health"
  },
  "ghostEvasion": {
    "enabled": true,
    "infraSpec": "~/.openclaw/infra/ghost_evasion.yaml",
    "requireShieldedPathLive": true,
    "structuralInvisibilityMaxDetectionPct": 1.0,
    "fingerprintRotateHours": 168,
    "trafficJitterEnabled": true,
    "stealthPipelines": [
      "P22",
      "P29",
      "P12",
      "P30"
    ],
    "denyPublicRpc": true,
    "controls": [
      "mev_shield_intents",
      "edge_rtt",
      "nostr_nip44",
      "fingerprint_rotate",
      "traffic_jitter",
      "structural_invisibility_gate"
    ]
  },
  "safetyServices": {
    "riskKernel": "http://127.0.0.1:19001/health",
    "reconciliation": "http://127.0.0.1:19002/health",
    "statusAggregator": "http://127.0.0.1:19003/health",
    "portfolioRisk": "http://127.0.0.1:19004/health",
    "deadMansSwitch": "http://127.0.0.1:19005/health",
    "allocator": "http://127.0.0.1:19006/health",
    "tca": "http://127.0.0.1:19007/health",
    "securityOps": "http://127.0.0.1:19008/health",
    "signing": "in_process",
    "allocatorPlanUrl": "http://127.0.0.1:19006/v1/plan",
    "tcaIngestUrl": "http://127.0.0.1:19007/v1/ingest",
    "tcaScorecardUrl": "http://127.0.0.1:19007/v1/scorecard",
    "securityOpsUrl": "http://127.0.0.1:19008/v1/status"
  },
  "memecoinTrench": {
    "pipelineId": "P22",
    "enabled": false,
    "requiresLiveProfile": true,
    "requiresPromotionYes": true,
    "infraSpec": "~/.openclaw/infra/solana_memecoin.yaml",
    "playbook": "~/.openclaw/playbooks/memecoin_trench.yaml",
    "skill": "memecoin_trench",
    "agents": {
      "scan": "PREDATOR",
      "execute": "TRENCH-OPS",
      "feeds": "NEXUS"
    },
    "geyserUrlEnv": "GEYSER_GRPC_URL",
    "jitoBlockEngine": "https://frankfurt.mainnet.block-engine.jito.wtf",
    "edgePop": "EDGE-FRA",
    "pumpFunProgram": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "note": "Real SOL: set enabled true after promotion YES; live profile already active"
  },
  "flashLoanRouter": {
    "enabled": false,
    "requiresLiveProfile": true,
    "requiresPromotionYes": false,
    "skill": "flash_loan_router",
    "infraSpec": "~/.openclaw/infra/flash_loan.yaml",
    "playbook": "~/.openclaw/playbooks/flash_loan_live.yaml",
    "agents": {
      "compose": "ALCHEMY",
      "execute": "TRENCH-OPS"
    },
    "chains": [
      "ethereum",
      "arbitrum",
      "base"
    ],
    "defaultSourcePriority": [
      "balancer",
      "morpho",
      "uniswap_v4",
      "aave_v3"
    ],
    "note": "Set enabled true after paper sim evidence; no flash_loan_live promotion YES required"
  },
  "drawdownTiers": {
    "alert": 2.0,
    "softPause": 5.0,
    "reduce": 8.0,
    "critical": 10.0,
    "halt": 12.0,
    "notifyOnly": true,
    "note": "Tiers notify via HERALD \u2014 trading continues autonomously; no operator ack"
  },
  "drawdownVolatileExempt": {
    "pipelines": [
      "P22",
      "P29",
      "P30",
      "P12"
    ],
    "correlationGroups": [
      "memecoin_trench",
      "mev_arb"
    ],
    "venues": [
      "solana_pumpfun",
      "solana_pumpswap",
      "jito",
      "paper"
    ],
    "note": "Portfolio drawdown tiers 2\u201312% do not apply \u2014 lane-local CBs only"
  },
  "quantum": {
    "status": "dormant",
    "enabled": false,
    "cloudQpuEnabled": false,
    "cuQuantumEnabled": false,
    "wukongBudgetActive": false,
    "note": "Classical-only \u2014 quantum agents removed from catalog; no QPU dispatch for live capital"
  },
  "inference": {
    "latencyBudgetPath": "~/.openclaw/infra/latency_budget.yaml",
    "latencyFastPath": "~/.openclaw/infra/latency_fast_path.yaml",
    "edgeHotPath": "~/.openclaw/infra/edge_hot_path.yaml",
    "tier1_critical": {
      "port": 30000,
      "gpu": 0,
      "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8",
      "role": "signals_risk_execution",
      "target_tps": "50-70",
      "parallel_slots": 12,
      "prewarm": true,
      "agents_critical": [
        "GUARDIAN",
        "TRENCH-OPS"
      ],
      "agents_shared": [
        "ORACLE",
        "PREDATOR",
        "AUGUR",
        "WRAITH",
        "NARRATIVE"
      ]
    },
    "tier2_reasoning": {
      "port": 30001,
      "gpu": 1,
      "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct",
      "role": "orchestration_strategy_code",
      "target_tps": "50-70",
      "parallel_slots": 6,
      "must_not_block_tier1": true
    },
    "tier3a_deepseek": {
      "port": 30005,
      "gpu": "0+1_expert_offload",
      "model": "deepseek-ai/DeepSeek-V4-Pro",
      "role": "rd_evolution_primary",
      "target_tps": "10-20",
      "critical_path": false,
      "market_hours": "forbidden"
    },
    "tier3_offline": {
      "port": 30003,
      "gpu": "0+1_expert_offload",
      "model": "zai-org/GLM-5.2",
      "role": "rd_evolution_batch_only",
      "target_tps": "10-20",
      "critical_path": false,
      "market_hours": "forbidden"
    },
    "embedder": {
      "port": 30004,
      "gpu": 0,
      "model": "Qwen/Qwen3-Embedding-0.6B",
      "role": "memory_rerank_ride_along",
      "mps_sm_pct": 10
    },
    "utility": {
      "port": 30002,
      "host": "titanspark",
      "lanUrl": "http://192.168.10.20:30002/v1",
      "wireguardUrl": "http://10.0.10.3:30002/v1",
      "localhostUrl": "http://127.0.0.1:30002/v1",
      "model": "Qwen3-30B-A3B-Instruct-2507"
    }
  },
  "providers": {
    "qwen3-critical": {
      "type": "openai-compatible",
      "baseUrl": "http://localhost:30000/v1",
      "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
    },
    "qwen3-coder": {
      "type": "openai-compatible",
      "baseUrl": "http://localhost:30001/v1",
      "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct"
    },
    "glm-5.2-offline": {
      "type": "openai-compatible",
      "baseUrl": "http://localhost:30003/v1",
      "model": "zai-org/GLM-5.2"
    },
    "qwen3-utility": {
      "type": "openai-compatible",
      "baseUrl": "http://192.168.10.20:30002/v1",
      "fallbackUrl": "http://10.0.10.3:30002/v1",
      "model": "Qwen3-30B-A3B-Instruct-2507"
    },
    "qwen3-embedder": {
      "type": "openai-compatible",
      "baseUrl": "http://localhost:30004/v1",
      "model": "Qwen/Qwen3-Embedding-0.6B"
    },
    "deepseek-offline": {
      "type": "openai-compatible",
      "baseUrl": "http://localhost:30005/v1",
      "model": "deepseek-ai/DeepSeek-V4-Pro"
    }
  },
  "skills": {
    "directory": "~/.openclaw/workspace/skills"
  },
  "memory": {
    "directory": "~/.openclaw/memory",
    "persistentData": "/data/openclaw/memory"
  },
  "notifications": {
    "herald": {
      "agent": "HERALD",
      "skill": "herald_notify",
      "templatesDir": "~/.openclaw/workspace/telegram",
      "materialThresholdPctEquity": 0.5,
      "immediateSeverities": [
        "CRITICAL",
        "HIGH"
      ],
      "natsSubjects": {
        "trade": "tgcmd.herald.trade",
        "pnl": "tgcmd.herald.pnl",
        "hourly": "tgcmd.herald.report.hourly",
        "urgent": "tgcmd.herald.alert.urgent"
      }
    }
  },
  "infrastructure": {
    "hardwareBomPath": "~/.openclaw/infra/hardware_bom.yaml",
    "titanhome": {
      "role": "primary_compute_inference_safety",
      "cpu": "AMD Ryzen Threadripper PRO 9995WX (96C/192T)",
      "motherboard": "ASUS Pro WS WRX90E-SAGE SE",
      "memory": "512GB DDR5-6000 ECC R-DIMM (8\u00d764GB)",
      "gpu": "2\u00d7 NVIDIA RTX PRO 6000 Blackwell Max-Q (96GB each, 192GB total)",
      "storage": "Micron 7500 Pro 3.8TB boot + 2\u00d7 WD Black SN8100 4TB",
      "psu": "Super Flower Leadex Titanium 2200W",
      "cooling": "Silverstone XE360-TR5 360mm AIO + Noctua iPPC fans",
      "timing": "Leo Bodnar LBE-1425 GPSDO \u2192 Intel E810-XXVDA4T",
      "nic": "Intel E810-XXVDA4T",
      "ups": "Eaton 9SX 3000VA / 2700W 208V",
      "oob": "ASUS AST2600 BMC (PiKVM removed)",
      "tpm": "ASUS TPM-SPI",
      "note": "Tier 1/2 inference + REVM + risk kernel + safety services"
    },
    "titanspark": {
      "role": "utility_inference_operator_gateway",
      "hardware": "ASUS GX10",
      "note": "Qwen3-30B utility tier + operator gateway failover"
    },
    "macminiVault": {
      "role": "encrypted_key_metadata_trezor_ceremonies",
      "hardware": "Mac Mini 2018 \u2014 i7 6-core, 64GB DDR4",
      "note": "Key custody + profit workloads; signing execution via in-process titan-safety on TITANHOME"
    },
    "powerRequirementsPath": "~/.openclaw/infra/power_requirements.yaml",
    "gpuSchedulePath": "~/.openclaw/infra/gpu_schedule.yaml",
    "latencyBudgetPath": "~/.openclaw/infra/latency_budget.yaml",
    "latencyFastPath": "~/.openclaw/infra/latency_fast_path.yaml",
    "edgeHotPath": "~/.openclaw/infra/edge_hot_path.yaml",
    "edgeRttProbePath": "~/.openclaw/infra/edge_rtt_probe.yaml",
    "signingNodeConfigPath": "~/.openclaw/infra/signing_node.yaml"
  },
  "signingNode": {
    "enabled": true,
    "mode": "in_process",
    "endpoint": "",
    "host": "localhost",
    "port": 19010,
    "isolated": true,
    "requireGateReceipt": true,
    "maxReceiptAgeSeconds": 10,
    "routeAgents": [
      "TRENCH-OPS",
      "LAMARCK"
    ],
    "cli": "titan-safety gate sign",
    "note": "In-process SigningNode in titan-safety \u2014 refuses sign without fresh X-Titan-Gate-Receipt; :19010 HTTP is optional legacy only"
  },
  "augur": {
    "regimeFeed": "stub",
    "regimeFile": "~/.openclaw/safety/augur_regime.json",
    "note": "Set regimeFeed=file and have AUGUR write regimeFile for live portfolio scaling"
  },
  "allocator": {
    "maxActivePipelines": 2,
    "selectiveActivation": true,
    "v1SurfaceEnforced": true,
    "note": "v1: \u22642 TCA-HEALTHY lanes; catalog \u2260 checklist (iron law 14)"
  },
  "v1SurfaceLockdown": {
    "enabled": true,
    "configPath": "~/.openclaw/risk_kernel/v1_surface_lockdown.yaml",
    "chain": "hyperliquid",
    "venueClass": "perp_dex",
    "maxActiveStrategies": 2,
    "disabledForV1": {
      "memecoinP22": true,
      "flashLoans": true,
      "predatoryHoneypots": true,
      "quantumInspiredLive": true,
      "multiCexAllowlists": true,
      "fullEdgeMesh5Pop": true
    },
    "note": "Does NOT auto-enable live capital \u2014 Phase 5 YES still required"
  },
  "edgeMesh": {
    "mode": "single_pop",
    "phase1": "single_pop",
    "defaultPop": "EDGE-FRA",
    "activePops": [
      "EDGE-FRA"
    ],
    "paperLatencyFaithful": true,
    "meshConfigPath": "~/.openclaw/infra/edge_mesh.yaml",
    "latencyBudgetMs": {
      "hotPathGateP95": 15,
      "hotPathSubmitP95": 50,
      "homeToEdgeFraP95": 25,
      "edgeToJitoP95": 5,
      "nostrDispatch": 3,
      "warmPathGateP95": 150
    },
    "phase1ApacDeferred": true,
    "routingPolicy": "lowest_live_p50_rtt",
    "note": "v1 single PoP (EDGE-FRA) \u2014 expand to full_mesh only after operator unlock"
  },
  "capital": {
    "capital_profile": "paper",
    "state_path": "~/.openclaw/capital/portfolio_state.json",
    "audit_path": "~/.openclaw/capital/capital_audit.jsonl",
    "min_operating_capital_usd": 500,
    "max_single_withdrawal_pct": 20,
    "withdrawal_adapter": "trezor_signing",
    "trezor_sweep": {
      "harvest_threshold_usd": 15000,
      "sweep_pct_of_weekly_profit": 20,
      "sweep_day_utc": "Sunday",
      "pause_below_threshold": true,
      "note": "Growth phase below $15K \u2014 100% reinvest; no sweep until harvest threshold"
    },
    "endgame_phase_unlock": 3
  },
  "honcho": {
    "enabled": true,
    "provider": "honcho",
    "configPath": "~/.hermes/honcho.json",
    "operatorPeer": "hyperion",
    "recallMode": "hybrid",
    "observationMode": "directional",
    "sessionStrategy": "per-repo",
    "gatewayIdentity": {
      "pinUserPeer": true,
      "peerName": "hyperion",
      "userPeerAliases": {},
      "runtimePeerPrefix": "telegram_",
      "note": "Single operator (Hyperion) via Telegram \u2014 all gateway users collapse to hyperion peer"
    },
    "agentPeers": {
      "HYPERION": {
        "profile": "hyperion",
        "aiPeer": "hyperion-assistant",
        "observationMode": "directional"
      },
      "HERALD": {
        "profile": "herald",
        "aiPeer": "herald-telegram",
        "observationMode": "directional"
      }
    },
    "tools": [
      "honcho_profile",
      "honcho_search",
      "honcho_context",
      "honcho_reasoning",
      "honcho_conclude"
    ],
    "note": "Dialectic operator modeling \u2014 local Hermes Honcho only; not on trade critical path"
  }
}
```

## Risk kernel `~/.openclaw/risk_kernel/policy.yaml`

```yaml
# TITAN Independent Risk Kernel — deterministic out-of-process guard
# Deploy target: ~/.openclaw/risk_kernel/policy.yaml
# Agents propose; kernel vetoes. Cannot be modified by agent runtime.

version: "2.2"
mode: enforce
# Default deploy profile — paper until Phase 5 YES + operator checklist.
capital_profile: paper

trading_limits:
  max_notional_usd_per_trade: 500.0
  max_aggregate_exposure_usd: 2500.0
  max_leverage: 3.0
  max_loss_velocity_usd_per_60s: 150.0
  max_open_positions: 8
  max_slippage_bps: 50
  equity_usd: 2500.0

allowed_venues:
  - paper  # paper-only default — live profile adds DEX venues via tier1 merge

allowed_contracts:
  - "0x0000000000000000000000000000000000000000"  # paper sentinel
  - "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH — add venue-specific allowlist as you deploy

position_limits:
  max_equity_pct_per_trade: 2.0
  human_approval_above_pct: 1.0  # above this → BFT agent votes (not human) when autonomous_signing enabled
  flash_loan_live_requires_approval: false  # autonomous when flash_loan_live.enabled + flashLoanRouter.enabled
  leverage_change_requires_approval: true
  new_pipeline_requires_approval: true

# Agent-autonomous sign/verify — replaces human approval on the trade path.
# Safety retained: reconciliation → risk kernel → confidence → BFT → gate receipt → in-process sign.
autonomous_signing:
  enabled: false  # paper default — enable only in live profile after evidence
  min_confidence_reduced: 0.50
  min_confidence_full: 0.70
  paper_min_confidence: 0.30
  bft_required_above_equity_pct: 1.0
  bft_voters: [AUGUR, PREDATOR, ATLAS]
  bft_threshold: 2
  require_typed_data_live: true
  note: "Human gates remain for promotion, evolution, leverage, large withdrawals; flash-loan live autonomous per policy"

# Portfolio drawdown — paper default notify-only; live profile enforces tiers (tier1_capital_risk).
drawdown_notify_only: true

drawdown_volatile_exempt:
  pipelines: [P22, P29, P30, P12]
  correlation_groups: [memecoin_trench, mev_arb]
  venues: [solana_pumpfun, solana_pumpswap, jito, paper]
  note: "Memecoin/trench/MEV hot lanes — memecoin_circuit_breakers + velocity only"

drawdown_tiers:
  - pct: 2.0
    action: notify_operator
    severity: MEDIUM
  - pct: 5.0
    action: notify_operator
    severity: HIGH
  - pct: 8.0
    action: notify_operator
    severity: HIGH
  - pct: 10.0
    action: notify_critical_continue
    severity: CRITICAL
  - pct: 12.0
    action: notify_critical_continue
    severity: CRITICAL
    note: "Immediate HERALD alert — trading continues; no operator ack required"

drawdown_velocity:
  max_loss_usd_per_60s: 150.0
  max_loss_usd_per_15m: 400.0
  note: "Velocity breakers — faster than tier drawdown; independent of 24h PnL"

portfolio_risk:
  var_confidence: 0.95
  max_var_pct_equity: 8.0
  max_cvar_pct_equity: 12.0
  max_correlated_cluster_pct: 25.0
  min_return_samples: 20
  augur_regime_stub: neutral  # paper only — live profile uses augur_feed: file
  augur_feed: stub
  augur_regime_file: ~/.openclaw/safety/augur_regime.json
  regime_limits:
    risk_off: 50.0
    neutral: 100.0
    risk_on: 120.0
  correlation_groups:
    defi_yield: ["P1", "P3", "P7", "P8"]
    mev_arb: ["P29", "P30", "P41"]
    liquidations: ["P6", "P11", "P18"]
    memecoin_trench: ["P22"]

reconciliation:
  divergence_threshold_usd: 25.0
  divergence_threshold_pct: 1.0
  adapter: mock  # paper default; live profile overrides to live adapter
  recon_halt_on_divergence: true

# Tier 0 money path — one venue depth-first (Hyperliquid). Does NOT auto-enable live capital.
tier0_money_path:
  enabled: false  # operator sets true after Phase 5 YES + checklist in docs/TIER0_MONEY_PATH.md
  venue: hyperliquid
  venue_adapter: "titan_safety.adapters.hyperliquid_live:HyperliquidLiveAdapter"
  broadcast_authority_enforced: true
  require_payload_hash_binding: true
  recon_halt_on_divergence: true
  builtin_aggregator: true
  dual_control_withdrawals: true
  agent_submit_denied: true
  allowed_callers: [trench-ops, execution_daemon, flatten_executor]
  session_envelope:
    enabled: false  # set true when session keys armed
    max_notional_usd: 500.0
    allowed_venues: [hyperliquid]
    require_typed_data: true
  deferred_venues: [solana_jupiter, jito, solana_pumpfun, solana_pumpswap, flashbots_protect]
  note: "Hyperliquid first — Solana/Jito/P22/Flashbots deferred explicitly"

# Control-plane HMAC auth (X-Titan-Auth) required on mutating POSTs:
# FLATTEN, REGIME, HEARTBEAT, TCA_INGEST, PROFIT_LOOP, REFUND, ALLOCATE
control_plane:
  auth_required: true
  max_age_seconds: 100
  # Prefer dedicated control_plane.secret (0600). Falls back to kill_switch.secret.
  # Isolate from agent-writable paths; do not sync to staging/ or skills/.
  secret_file: control_plane.secret
  secret_mode: "0600"
  note: "Host compromise = auth compromise — keep secret off agent FS where possible"

# Daily compound engine — day-over-day equity tracking + winner feed / loser cut.
# Does NOT guarantee profit every calendar day; enforces measured-edge compounding.
daily_compound:
  enabled: true
  growth_threshold_usd: 15000.0
  min_green_streak_for_boost: 2
  green_day_kelly_boost: 0.05
  max_kelly_fraction: 0.35
  min_kelly_fraction: 0.15
  base_kelly_fraction: 0.25
  red_day_degross_mult: 0.70
  red_day_kelly_cut: 0.05
  max_active_on_red: 1
  max_active_on_green: 2
  min_trades_for_deploy: 30
  min_net_bps_for_deploy: 1.0
  starve_marginal: true
  marginal_weight_scale: 0.35
  apply_tca_pnl_to_equity: false  # set true only when TCA is the sole equity source
  note: "Green days reinvest within Kelly envelope; red days de-gross; BLEEDING auto-defund"

# Capital allocator — attribution -> forward fractional-Kelly allocation.
# Humans own the gross envelope (base_gross_pct); the machine allocates within it.
allocator:
  kelly_fraction: 0.25            # 1/4-Kelly — geometric-growth sweet spot, not full Kelly
  base_gross_pct: 100.0           # gross exposure cap as % equity (risk envelope)
  max_lane_pct: 25.0              # per-lane cap as % equity
  max_cluster_pct: 40.0           # per-correlation-cluster cap as % equity
  min_net_bps: 1.0               # lanes below this net-of-cost edge get zero capital
  min_trades: 100                # lanes below this sample size get zero capital
  max_active_pipelines: 2        # hard concentration — fund few HEALTHY lanes; catalog ≠ all-on
  # v1 surface lockdown caps this to 2 when enabled (v1_surface_lockdown.yaml)
  selective_activation: true
  advisory_mode: true   # paper default; live profile sets false (enforced de-gross)
  note: "Do not enable every strategy or feature mentioned in specs — use only what is necessary"
  regime_multipliers:
    risk_off: 0.5
    neutral: 1.0
    risk_on: 1.2
  degross_ladder:                 # [drawdown_pct, gross_multiplier] — enforced when advisory_mode false
    - [2.0, 0.75]
    - [5.0, 0.5]
    - [8.0, 0.25]
    - [10.0, 0.0]

# Tier 1 capital risk — profile overrides (items 6–10). load_policy merges active profile.
tier1_capital_risk:
  version: "1.0"
  slo:
    gate_p99_ms: 250
    gate_fast_p99_ms: 150
    kill_resume_dual_control: true
  profiles:
    paper:
      allowed_venues:
        - paper
      drawdown_notify_only: true
      autonomous_signing:
        enabled: false
      reconciliation:
        adapter: mock
      allocator:
        advisory_mode: true
        max_active_pipelines: 2
      portfolio_risk:
        augur_feed: stub
        allow_augur_stub: true
      kill_switch:
        dual_control_resume: false
      drawdown_tiers:
        - pct: 2.0
          action: notify_operator
          severity: MEDIUM
        - pct: 5.0
          action: notify_operator
          severity: HIGH
        - pct: 8.0
          action: notify_operator
          severity: HIGH
        - pct: 10.0
          action: notify_critical_continue
          severity: CRITICAL
        - pct: 12.0
          action: notify_critical_continue
          severity: CRITICAL
    live:
      allowed_venues:
        - paper
        - hyperliquid
        - uniswap_v3
        - curve
        - aave_v3
        - solana_jupiter
        - solana_pumpfun
        - solana_pumpswap
        - jito
        - flashbots_protect
      drawdown_notify_only: false
      autonomous_signing:
        enabled: true
      reconciliation:
        adapter: live
        recon_module: "titan_safety.adapters.live_bundle:build_position_fetcher"
        recon_halt_on_divergence: true
      allocator:
        advisory_mode: false
        max_active_pipelines: 2
      portfolio_risk:
        augur_feed: file
        augur_feed_live: file
        allow_augur_stub: false
      kill_switch:
        dual_control_resume: true
      drawdown_tiers:
        - pct: 2.0
          action: soft_de_gross
          severity: MEDIUM
        - pct: 5.0
          action: hard_de_gross
          severity: HIGH
        - pct: 8.0
          action: halt_new_risk
          severity: HIGH
        - pct: 10.0
          action: halt_new_risk
          severity: CRITICAL
        - pct: 12.0
          action: full_halt_flatten
          severity: CRITICAL
          note: "Immediate flatten — operator dual-control RESUME required to clear kill"

kill_switch:
  dual_control_resume: false  # overridden to true in live profile

# Execution-quality / transaction-cost analysis thresholds.
tca:
  window: 500
  min_fills_for_verdict: 30
  healthy_net_bps: 5.0
  marginal_net_bps: 0.0
  max_tip_efficiency: 0.40        # tips > 40% of gross MEV => lane is bleeding
  max_slippage_bps: 20.0
  min_fill_rate: 0.80

# Statistical evidence required before a strategy touches live capital.
# Replaces the old "Sharpe>=0, 20 trades, auto-promote" criteria.
promotion_stats:
  min_trades: 200
  min_deflated_sharpe: 0.90       # DSR probability, corrects for multiple-testing/overfit
  min_psr: 0.90                   # probabilistic Sharpe vs zero
  max_shadow_divergence_pct: 15.0 # live/shadow Sharpe must track backtest

# P22 Solana memecoin trench — Pump.fun lifecycle (catalog until promotion YES)
memecoin_trench:
  pipeline_id: P22
  enabled: false  # operator + openclaw memecoinTrench.enabled after YES
  max_top10_holder_pct: 30.0
  max_insider_pct: 15.0
  min_curve_progress_pct: 2.0
  max_fast_fill_minutes: 30.0
  min_curve_progress_for_climb: 15.0
  graduation_target_usd: 69000.0
  max_snipe_pct_equity: 0.5
  daily_sol_cap: 2.0
  require_sell_sim: true
  recon_module: ""  # operator: custom Solana recon module path when P22 enabled
  jito_block_engine: "https://frankfurt.mainnet.block-engine.jito.wtf"
  strategies_enabled:
    - curve_climb
    - graduation
    - post_grad_pullback
    - smart_money_mirror
    - first_block_snipe
  # LIVE venues (P22 still requires promotion YES + memecoinTrench.enabled)
  allowed_venues_add: [solana_pumpfun, solana_pumpswap, jito]

  min_net_bps: 1.0
  require_cost_model: true         # backtests with zero modeled cost are rejected
  require_walk_forward: true
  min_walk_forward_folds: 5
  require_purged_cv: true
  min_fat_slippage_bps: 5.0
  require_capacity_curve: true
  min_shadow_days: 3
  require_shadow_gas_tip_sim: true

# Tier 2 promotion quality — items 11–14 (research / promotion gates)
tier2_promotion_quality:
  version: "1.0"
  micro_live_caps:
    calendar_is_gate: false
    default_phase: micro_live_conservative
    max_jump_notional_usd: 500.0
    phases:
      micro_live_conservative:
        max_equity_pct_per_trade: 0.05
        max_aggregate_equity_pct: 0.25
        min_fills_before_scale: 50
      micro_live:
        max_equity_pct_per_trade: 0.10
        max_aggregate_equity_pct: 0.50
        min_fills_before_scale: 50
      validated_scale:
        max_equity_pct_per_trade: 0.50
        max_aggregate_equity_pct: 2.0
        min_fills_before_scale: 200
  promotion_registry:
    enabled: true
    registry_file: ~/.openclaw/safety/promotion_registry.jsonl
    note: "Global trial count feeds deflated Sharpe multiple-testing correction"
  tca_daily_scorecard:
    enabled: true
    herald_agent: HERALD
    schedule_utc: "08:00"
  v1_surface_lockdown:
    enabled: true
    config_ref: ~/.openclaw/risk_kernel/v1_surface_lockdown.yaml

flash_loan_live:
  enabled: false  # default off — enable explicitly after boring profit; autonomous when enabled
  max_amount_usd: 500000.0
  max_fee_bps: 9.0
  paper_sim_required_days: 3
  pipeline_ids: [P1, P2, P3, P5, P6, P7, P8, P12, P15, P16, P17]
  sources:
    ethereum: [balancer, morpho, uniswap_v4, aave_v3]
    arbitrum: [balancer, morpho, aave_v3]
    base: [morpho, balancer, aave_v3]
  infra_spec: ~/.openclaw/infra/flash_loan.yaml
  playbook: ~/.openclaw/playbooks/flash_loan_live.yaml
  note: "Live flash loans: enable policy + router; kernel enforces amount/source/pipeline caps; paper venue always allowed"

promotion_gates:
  phase5_requires_human_yes: true
  paper_minimum_days: 3
  timeout_policy: hold_derisk
  air_gapped_staging_required: true
  shadow_only_evolution:
    - dgm-h
    - gepa
    - hyevo
    - sia-lora
    - eurekagent
    - gris-model-swap
  pending_state: PENDING_PROMOTION_APPROVAL
  constitutional_blocks:
    - SOUL.md
    - iron-laws.md
    - risk_kernel/
    - safety/titan_safety/

dead_mans_switch:
  operator_heartbeat_hours: 48
  flatten_after_hours: 72
  on_miss: derisk_flatten
  never_auto_promote: true

bft:
  note: "Orchestrator voters share GLM-5.2 — correlated, not independent BFT"
  require_kernel_veto: true

quantum:
  enabled: false
  note: "Classical-only — quantum agents removed; no cuQuantum/Wukong/Tier 3 dispatch for live capital"

power_loss:
  on_ups_battery: halt_trading
  on_mains_loss: halt_trading
  flatten_open_positions: true
  revoke_session_keys: true
  require_operator_ack_to_resume: true
  ups_required_for_live_capital: true
  policy_ref: ~/.openclaw/infra/power_requirements.yaml
  note: "Power-loss = HALT — no discretionary signing during outage"

signing:
  mode: in_process  # default — SigningNode library in titan-safety (no :19010 hop)
  isolated_module_required: true  # logical isolation in titan_safety; not a separate daemon
  endpoint: ""  # legacy HTTP only when mode=http
  config_ref: ~/.openclaw/infra/signing_node.yaml
  blind_sign_rejected: true
  require_gate_receipt: true
  max_receipt_age_seconds: 10
  on_env_compromised: halt_all_signing
  signer_module: "titan_safety.adapters.live_bundle:live_signer"

# Flatten adapters — live profile (mock banned at startup)
flatten:
  closer: broadcast_authority  # Tier 0: single submit path; aliases: signing_node, in_process, mock
  revoker: "titan_safety.adapters.live_bundle:LiveKeyRevoker"
  signing_endpoint: ""  # unused when signing.mode=in_process

# Evolution freeze — set freeze_during_live true; CLI: titan-safety evolution freeze
evolution:
  freeze_during_live: true
  flag_file: ~/.openclaw/safety/EVOLUTION_FROZEN

# Four-pillar security ops — Impenetrable / Evasion / Stalking / Predatory
# CLI: titan-safety security status|lockdown|honeypot
# Refs: AEGIS / FORTRESS / GHOST / MEV / REAPER
security_ops:
  enabled: true
  hunt_mode_default: true
  honeypot_armed_default: true
  honeypot_dir: ~/.openclaw/safety/honeypots
  posture_log: ~/.openclaw/memory/security/posture.jsonl
  require_hmac_for_lockdown: true
  pillars:
    impenetrable:
      owner: SENTINEL
      layers: [L1_risk_kernel, L2_signing_in_process, L3_netns, L4_pcr_codeql, L5_dms, L6_closed_model_ban]
    evasion:
      owner: TRENCH-OPS
      controls: [mev_shield_intents, edge_rtt, nostr_nip44, fingerprint_rotate, traffic_jitter, airgap_vault]
    stalking:
      owner: PREDATOR
      cadence_seconds: 60
      escalate_severity: high
    predatory:
      owner: PREDATOR
      modules: [honeypot_lattice, red_team, graph_r1, poison_fills, kill_chain]
      poison_max_equity_pct_auto: 1.0
  circuit_breakers:
    - id: CB_TPM_PCR_DRIFT
      action: halt_new_risk_critical_alert
    - id: CB_KEYS_SIGNING_ENV_COMPROMISED
      action: signing_halted
    - id: CB_NETNS_POLICY_BYPASS
      action: kill_pipeline
    - id: CB_RISK_KERNEL_UNREACHABLE
      action: fail_closed_deny
    - id: CB_DARKINT_HONEYPOT
      action: critical_alert_optional_pipeline_halt
    - id: CB_HYDRA_HONEYPOT
      action: critical_alert_optional_pipeline_halt
    - id: CB_STALK_SEVERITY_HIGH
      action: escalate_archon_herald
    - id: CB_STEALTH_PUBLIC_PATH
      action: fail_closed_deny
    - id: CB_STEALTH_UNSHIELDED_VENUE
      action: fail_closed_deny
    - id: CB_SECURITY_LOCKDOWN
      action: kill_freeze_signing_halt_honeypot_arm
  # ENDGAME CBs — unlock Phase 3+ per openclaw capital.endgame_phase_unlock (documented for memory extract; not all wired yet).
  endgame_circuit_breakers:
    - id: CB_FUNDING_FLIP
      action: halt_funding_lanes
    - id: CB_RESTAKING_SLASH
      action: halt_restaking_exposure
    - id: CB_RESTAKING_DEPEG
      action: halt_restaking_exposure
    - id: CB_PRED_MARKET_RESOLVE_RISK
      action: halt_pred_market_lanes
    - id: CB_VOL_HARVEST_GAP
      action: halt_vol_harvest
    - id: CB_NEW_CHAIN_MEV_HALT
      action: halt_new_chain_mev
    - id: CB_AIRDROP_SYBIL
      action: halt_airdrop_farming
    - id: CB_RATE_ARB_LIQUIDITY
      action: halt_rate_arb
    - id: CB_CLMM_IL_SPIKE
      action: halt_clmm_lp
    - id: CB_ENDGAME_PHASE_GATE
      action: deny_until_phase_unlock
  memecoin_circuit_breakers:
    - id: CB_MEMECOIN_DAILY_SOL_CAP
      action: halt_p22_until_reset
    - id: CB_MEMECOIN_FILTER_BYPASS
      action: deny_trade_fail_closed
    - id: CB_MEMECOIN_HONEYPOT
      action: deny_and_alert
    - id: CB_MEMECOIN_GRAD_FAIL
      action: halt_lane_p22
    - id: CB_MEMECOIN_TIP_BLEED
      action: reduce_size_p22
  lockdown_sequence:
    - kill_switch_activate
    - evolution_freeze
    - signing_halt
    - honeypot_arm
    - edge_fail_closed
    - herald_critical

ghost_evasion:
  enabled: true
  require_shielded_path_live: true
  hunt_mode_default: true
  honeypot_armed_default: true
  structural_invisibility_max_detection_pct: 1.0
  fingerprint_rotate_hours: 168
  traffic_jitter_enabled: true
  infra_spec: ~/.openclaw/infra/ghost_evasion.yaml
  forbidden_venues:
    - public_rpc
    - public_mempool
    - eth_public_rpc
    - solana_public_rpc
    - alchemy_public
    - infura_public
    - quicknode_public
    - helius_public_unshielded
    - jupiter_public_api
    - binance_public
    - cex_api_direct
  shielded_venues:
    - uniswap_v3
    - curve
    - aave_v3
    - hyperliquid
    - solana_jupiter
    - solana_pumpfun
    - solana_pumpswap
    - jito
    - flashbots_protect
    - intent_solver
    - cowswap
    - uniswapx
    - mev_share
    - across_intent
  stealth_pipelines: [P22, P29, P12, P30]
  pipeline_required_venues:
    P22: [jito, solana_pumpfun, solana_pumpswap]
    P29: [flashbots_protect, jito, intent_solver, mev_share]
    P12: [intent_solver, uniswapx, cowswap, across_intent]
    P30: [flashbots_protect, intent_solver]
  doctrine: invisible_to_them_visible_to_us

# Tier 4 ultimate — gated scaffold; requires tiers 0–3 complete. Does NOT enable live capital.
tier4_ultimate:
  enabled: false  # operator sets true ONLY after Tier 0–3 checklists + explicit tier*_complete flags
  requires_tiers: [0, 1, 2, 3]
  tier_checklist:
    tier0_complete: false
    tier1_complete: false
    tier2_complete: false
    tier3_complete: false
  shadow_twin:
    enabled: false
    max_divergence_pct: 15.0
    block_live_on_divergence: true
  multi_pop:
    rtt_probe_interval_s: 30
    unhealthy_rtt_p95_ms: 50.0
    failover_enabled: true
    rtt_routing: true
    note: "STUB RTT probes until wireguard/HTTP probe wired on edge workers"
  intent_solver:
    enabled: false
    stub_submit: true
    networks: [cowswap, uniswapx, across_intent, mev_share]
    note: "Honest STUB — no live solver RPC until operator wires endpoints"
  mev_tip_optimizer:
    enabled: false
    advisory_only: true
    max_tip_bps: 40.0
  red_team_continuous:
    enabled: false
    interval_minutes: 60
    note: "Runs tests/adversarial/adversarial_harness.py on schedule — not checklist YAML only"
  portfolio_construction:
    borrow_rate_cap_annual_pct: 25.0
    funding_rate_cap_8h_pct: 0.15
    capacity_curve_enabled: false
  note: "Evolution shadow-only unchanged; kernel DENY absolute; Phase 5 YES still required for live"

# Millisecond hot path — combined gate validate for latency-critical pipelines
latency:
  target: millisecond
  fast_path_ref: ~/.openclaw/infra/latency_fast_path.yaml
  hot_path:
    enabled: true
    combined_validate: true
    gate_timeout_s: 0.25
    fast_gate_timeout_s: 0.15
    pipelines: [P22, P29, P12, P30]
    skip_trading_agents_debate: true
  edge:
    colocate_trench_ops: true
    default_pop: EDGE-FRA
    max_broadcast_ms: 3
    max_jito_ms: 5

service:
  risk_kernel_port: 19001
  reconciliation_port: 19002
  status_aggregator_port: 19003
  portfolio_risk_port: 19004
  dead_mans_switch_port: 19005
  allocator_port: 19006
  tca_port: 19007
  security_ops_port: 19008
  # signing_node_port retained for optional legacy HTTP mode only (not required)
  signing_node_port: 19010
```

## Signing node `~/.openclaw/infra/signing_node.yaml`

```yaml
# TITAN Signing — in-process module (titan_safety.SigningNode)
# Deploy target: ~/.openclaw/infra/signing_node.yaml
#
# Default: signing runs in-process inside titan-safety (gate sign / flatten /
# capital) after a fresh ExecutionGate ALLOW receipt — no separate :19010 daemon.
# Mac Mini vault retains key metadata + Trezor ceremonies; signing execution is
# colocated on TITANHOME in the deterministic safety process (not agent/LLM).

version: "1.1"
enabled: true
mode: in_process  # in_process (default) | http (legacy optional)

# Legacy HTTP listener — optional; not required for deploy or verify.sh
endpoint:
  optional_legacy: true
  host: localhost
  port: 19010
  url: http://127.0.0.1:19010
  health: http://127.0.0.1:19010/health
  note: "Only when signing.mode=http / TITAN_SIGNING_MODE=http"

isolation:
  in_process_module: titan_safety.signing_service.SigningNode
  no_evolution_workloads: true
  no_llm_inference: true
  no_agent_runtime: true  # never sign inside agent/LLM process
  power_protected: true  # UPS-backed TITANHOME per power_requirements.yaml
  cgroup: openclaw-safety
  allowed_processes:
    - titan-safety
    - openclaw-trezor-bridge
    - tpm-pcr-watch
  forbidden_in_signer_process:
    - dgm-h
    - gepa
    - hyevo
    - skill_evolution
    - cuquantum
    - cudev_fuzzing
    - llama-server
    - agent runtime

routing:
  agents:
    - TRENCH-OPS
    - LAMARCK
  cli: titan-safety gate sign
  pre_sign_gates:
    - guardian_risk_validation
    - execution_gate_allow_receipt  # X-Titan-Gate-Receipt required
    - risk_kernel_pre_trade
    - tenderly_simulation  # bridge txs
    - eip712_typed_data_only
  receipt:
    header: X-Titan-Gate-Receipt
    max_age_seconds: 10
    issued_by: titan_safety.execution_gate
  on_compromise:
    action: halt_all_signing
    circuit_breaker: CB_KEYS_SIGNING_ENV_COMPROMISED
    file_flag: ~/.openclaw/safety/SIGNING_HALTED

hardware_options:
  colocated_in_process:
    description: "SigningNode library inside titan-safety on TITANHOME; same machine as gate — zero extra network hop"
    default: true
  legacy_http_daemon:
    description: "Optional python -m titan_safety.signing_service on :19010 — compatibility only"
    required: false

macmini_vault:
  role: "Trezor ceremony + cold key metadata"
  not_a_substitute_for: "in-process SigningNode on TITANHOME — vault holds metadata, safety stack executes"

# Four-pillar Impenetrable layer L2 — security lockdown sets SIGNING_HALTED
security_ops:
  pillar: impenetrable
  layer: L2
  pcr_watch: tpm-pcr-watch
  lockdown_flag: ~/.openclaw/safety/SIGNING_HALTED
  cli: titan-safety security lockdown
  ref: refs/AEGIS_detail.md
```
