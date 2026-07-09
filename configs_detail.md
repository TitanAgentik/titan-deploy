# §CONFIGS_detail.md — TITAN Configuration Reference

> **Auto-generated** by `scripts/sync_workspace_docs.py` on every `build.py` run.
> Do not hand-edit — change `templates/*` then rebuild.
>
> Aligns stubs in `output/TITAN.reconciled.md` (`# → see §CONFIGS_detail.md`)
> with the live OpenClaw + Hermes configs.
>
> Docs: [OpenClaw agent workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Index from TITAN.reconciled.md

### Config sections
- `# §M  — openclaw.json Configuration (OpenClaw gateway + agents + providers)`
- `# §MA — config.yaml Configuration (Hermes cognitive engine + MCP + cron + Telegram)`
- `# §MA — config.yaml Configuration (Hermes)`

### Stub references (0 unique)
Source TITAN offloads full YAML/JSON bodies to this companion file. Bodies below are the **live templates** (source of truth), not the missing original §REF dump.



## File map

| Deploy path | Template | Role |
|-------------|----------|------|
| `~/.openclaw/workspace/*.md` | `workspace/` ← `output/bootstrap/` | OpenClaw bootstrap context |
| `~/.hermes/SOUL.md` | `workspace/SOUL.md` | Hermes identity (slot #1) |
| `~/.hermes/config.yaml` | `templates/config.yaml` | Hermes agent config |
| `~/.openclaw/openclaw.json` | `templates/openclaw.json` | OpenClaw gateway + agents |
| `~/.openclaw/risk_kernel/policy.yaml` | `templates/risk_kernel/policy.yaml` | Risk / safety policy |
| `~/.openclaw/infra/signing_node.yaml` | `templates/infra/signing_node.yaml` | Signing isolation |

---

## §MA — config.yaml (Hermes)

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
    - rebalances_under_1pct_equity
    - cb_tier_responses_within_policy
    - shadow_evolution_outputs
    - paper_trading
  human_required:
    - strategy_promotion_phase5
    - evolution_deploy_to_live
    - leverage_changes
    - flash_loan_live
    - trades_over_1pct_equity
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
  utility:
    provider: openai-compatible
    base_url: http://localhost:30002/v1
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
  engine: sqlite
  path: ~/.hermes/memory/titan.db
  fts5: true
  openclaw_sync: ~/.openclaw/memory/

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
  note: "100% classical execution — QCC/QSA/QRP disabled for live capital"

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
    timing: "LBE-1420 GPSDO"
    oob: "PiKVM V4 Plus"
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
    note: "Key custody + profit workloads; signing routed to signing_node"
  power_requirements: ~/.openclaw/infra/power_requirements.yaml
  gpu_schedule: ~/.openclaw/infra/gpu_schedule.yaml
  signing_node: ~/.openclaw/infra/signing_node.yaml

signing_node:
  enabled: true
  endpoint: http://127.0.0.1:19010
  host: localhost
  port: 19010
  isolated: true
  route_agents:
    - TRENCH-OPS
    - LAMARCK

edge_mesh:
  phase1: single_pop
  default_pop: EDGE-FRA
  active_pops:
    - id: EDGE-FRA
      provider: vultr
      region: eu-central
      roles:
        - telegram_relay
        - erigon_archive
        - eu_rpc
  deferred_pops_phase3_plus:
    - id: EDGE-TKY
      note: "Hyperliquid / APAC latency — Phase 3+"
    - id: EDGE-SIN
      note: "APAC secondary — Phase 3+"
    - id: EDGE-USE
      note: "US East exchange colo — Phase 3+"
    - id: EDGE-AMS
      note: "Amsterdam DE-CIX — Phase 3+"
  phase1_note: "One PoP sufficient for $2.5K Phase 1; full 5-PoP mesh deferred to Phase 3+"

capital:
  state_path: ~/.openclaw/capital/portfolio_state.json
  audit_path: ~/.openclaw/capital/capital_audit.jsonl
  min_operating_capital_usd: 500
  max_single_withdrawal_pct: 20
  withdrawal_adapter: mock
  trezor_sweep:
    harvest_threshold_usd: 35000
    sweep_pct_of_weekly_profit: 20
    sweep_day_utc: Sunday
    pause_below_threshold: true
    note: "Growth phase below $35K — 100% reinvest; no sweep until harvest threshold"
  telegram_commands:
    deposit: "/deposit <amount> <asset> [chain] [tx_hash] [source]"
    withdraw: "/withdraw <amount> <asset> [address]"
    withdraw_confirm: "/withdraw confirm <request_id>"
    balance: "/balance"
    sweep: "/sweep"
    alt_prefix: "/capital deposit|withdraw|balance|sweep"
```

---

## §M — openclaw.json (OpenClaw)

```json
{
  "version": "49.7",
  "framework": "titan-unified",
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
        "endpoint": "http://localhost:30001",
        "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct"
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
      },
      {
        "id": "QCC",
        "tier": "quantum",
        "status": "dormant"
      },
      {
        "id": "QSA",
        "tier": "quantum",
        "status": "dormant"
      },
      {
        "id": "QRP",
        "tier": "quantum",
        "status": "dormant"
      }
    ]
  },
  "autonomy": {
    "mode": "bounded_supervised",
    "matrix": {
      "auto_execute": [
        "routine_trades_under_1pct_equity",
        "rebalances_under_1pct_equity",
        "cb_tier_responses_within_policy",
        "shadow_evolution_outputs",
        "paper_trading",
        "heartbeat_and_health_checks"
      ],
      "human_required": [
        "strategy_promotion_phase5",
        "evolution_deploy_to_live",
        "leverage_changes",
        "flash_loan_live",
        "trades_over_1pct_equity",
        "new_pipeline_activation",
        "model_promotion",
        "withdrawal_over_20pct_equity"
      ],
      "timeout_policy": "hold_derisk_never_auto_promote"
    },
    "humanGates": {
      "strategyPromotion": true,
      "evolutionDeploy": true,
      "leverageChanges": true,
      "flashLoanLive": true,
      "positionOver1PctEquity": true,
      "phase5GoNoGo": true
    },
    "criticalAlertsOnly": false,
    "criticalConditions": [
      "drawdown_10pct_24h",
      "drawdown_12pct_halt",
      "drawdown_velocity_15m",
      "hardware_failure",
      "security_breach",
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
  "safetyServices": {
    "riskKernel": "http://127.0.0.1:19001/health",
    "reconciliation": "http://127.0.0.1:19002/health",
    "statusAggregator": "http://127.0.0.1:19003/health",
    "portfolioRisk": "http://127.0.0.1:19004/health",
    "deadMansSwitch": "http://127.0.0.1:19005/health",
    "allocator": "http://127.0.0.1:19006/health",
    "tca": "http://127.0.0.1:19007/health",
    "signingNode": "http://127.0.0.1:19010/health"
  },
  "drawdownTiers": {
    "alert": 2.0,
    "softPause": 5.0,
    "reduce": 8.0,
    "critical": 10.0,
    "halt": 12.0
  },
  "quantum": {
    "status": "dormant",
    "cloudQpuEnabled": false,
    "cuQuantumEnabled": false,
    "wukongBudgetActive": false,
    "note": "100% classical execution \u2014 QCC/QSA/QRP disabled for live capital"
  },
  "inference": {
    "tier1_critical": {
      "port": 30000,
      "gpu": 0,
      "model": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8",
      "role": "signals_risk_execution",
      "target_tps": "50-70"
    },
    "tier2_reasoning": {
      "port": 30001,
      "gpu": 1,
      "model": "Qwen/Qwen3-Coder-Next-80B-A3B-Instruct",
      "role": "orchestration_strategy_code",
      "target_tps": "50-70"
    },
    "tier3_offline": {
      "port": 30003,
      "gpu": "0+1_expert_offload",
      "model": "zai-org/GLM-5.2",
      "role": "rd_evolution_batch_only",
      "target_tps": "10-20",
      "critical_path": false
    },
    "utility": {
      "port": 30002,
      "host": "titanspark",
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
      "baseUrl": "http://localhost:30002/v1",
      "model": "Qwen3-30B-A3B-Instruct-2507"
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
      "timing": "LBE-1420 GPSDO",
      "oob": "PiKVM V4 Plus",
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
      "note": "Key custody + profit workloads; signing execution via signingNode"
    },
    "powerRequirementsPath": "~/.openclaw/infra/power_requirements.yaml",
    "gpuSchedulePath": "~/.openclaw/infra/gpu_schedule.yaml",
    "signingNodeConfigPath": "~/.openclaw/infra/signing_node.yaml"
  },
  "signingNode": {
    "enabled": true,
    "endpoint": "http://127.0.0.1:19010",
    "host": "localhost",
    "port": 19010,
    "isolated": true,
    "requireGateReceipt": true,
    "maxReceiptAgeSeconds": 30,
    "routeAgents": [
      "TRENCH-OPS",
      "LAMARCK"
    ],
    "note": "Logically isolated signing \u2014 refuses POST /v1/sign without fresh X-Titan-Gate-Receipt"
  },
  "augur": {
    "regimeFeed": "stub",
    "regimeFile": "~/.openclaw/safety/augur_regime.json",
    "note": "Set regimeFeed=file and have AUGUR write regimeFile for live portfolio scaling"
  },
  "allocator": {
    "maxActivePipelines": 4,
    "note": "Concentrate capital on \u22644 TCA-HEALTHY lanes"
  },
  "edgeMesh": {
    "phase1": "single_pop",
    "defaultPop": "EDGE-FRA",
    "activePops": [
      "EDGE-FRA"
    ],
    "deferredPopsPhase3Plus": [
      "EDGE-TKY",
      "EDGE-SIN",
      "EDGE-USE",
      "EDGE-AMS"
    ],
    "note": "Phase 1 ($2.5K): one PoP only; full 5-PoP mesh is Phase 3+"
  },
  "capital": {
    "state_path": "~/.openclaw/capital/portfolio_state.json",
    "audit_path": "~/.openclaw/capital/capital_audit.jsonl",
    "min_operating_capital_usd": 500,
    "max_single_withdrawal_pct": 20,
    "withdrawal_adapter": "mock",
    "trezor_sweep": {
      "harvest_threshold_usd": 35000,
      "sweep_pct_of_weekly_profit": 20,
      "sweep_day_utc": "Sunday",
      "pause_below_threshold": true,
      "note": "Growth phase below $35K \u2014 100% reinvest; no sweep until harvest threshold"
    },
    "endgame_phase_unlock": 3
  }
}
```

---

## risk_kernel/policy.yaml

```yaml
# TITAN Independent Risk Kernel — deterministic out-of-process guard
# Deploy target: ~/.openclaw/risk_kernel/policy.yaml
# Agents propose; kernel vetoes. Cannot be modified by agent runtime.

version: "2.1"
mode: enforce

trading_limits:
  max_notional_usd_per_trade: 500.0
  max_aggregate_exposure_usd: 2500.0
  max_leverage: 3.0
  max_loss_velocity_usd_per_60s: 150.0
  max_open_positions: 8
  max_slippage_bps: 50
  equity_usd: 2500.0

allowed_venues:
  - paper
  - binance_spot
  - uniswap_v3

allowed_contracts:
  - "0x0000000000000000000000000000000000000000"  # paper sentinel
  - "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH

position_limits:
  max_equity_pct_per_trade: 2.0
  human_approval_above_pct: 1.0
  flash_loan_live_requires_approval: true
  leverage_change_requires_approval: true
  new_pipeline_requires_approval: true

drawdown_tiers:
  - pct: 2.0
    action: alert_operator
  - pct: 5.0
    action: soft_pause_new_entries
  - pct: 8.0
    action: reduce_exposure_50pct
  - pct: 10.0
    action: critical_alert_human_required
  - pct: 12.0
    action: full_halt_flatten

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
  augur_regime_stub: neutral
  # Live: set augur_feed to file|http; AUGUR agent writes augur_regime.json
  augur_feed: stub
  # augur_regime_file: ~/.openclaw/safety/augur_regime.json
  regime_limits:
    risk_off: 50.0
    neutral: 100.0
    risk_on: 120.0
  correlation_groups:
    defi_yield: ["P1", "P3", "P7", "P8"]
    mev_arb: ["P29", "P30", "P41"]
    liquidations: ["P6", "P11", "P18"]

reconciliation:
  divergence_threshold_usd: 25.0
  divergence_threshold_pct: 1.0
  # PAPER DEFAULT: mock is allowed only while allowed_venues is paper-only.
  # LIVE PROFILE: set adapter to "live" (or "exchange"/"onchain") and wire a fetcher.
  # enforce mode + any non-paper venue + adapter=mock → MOCK_ADAPTER_FORBIDDEN (startup + execution gate).
  adapter: mock
  live_profile_note: "Before real capital: adapter=live, withdrawal_adapter≠mock, 48h zero-divergence"

# Control-plane HMAC auth (X-Titan-Auth) required on mutating POSTs:
# FLATTEN, REGIME, HEARTBEAT, TCA_INGEST, PROFIT_LOOP, REFUND, ALLOCATE
control_plane:
  auth_required: true
  max_age_seconds: 300
  # Prefer dedicated control_plane.secret (0600). Falls back to kill_switch.secret.
  # Isolate from agent-writable paths; do not sync to staging/ or skills/.
  secret_file: control_plane.secret
  secret_mode: "0600"
  note: "Host compromise = auth compromise — keep secret off agent FS where possible"

# Capital allocator — attribution -> forward fractional-Kelly allocation.
# Humans own the gross envelope (base_gross_pct); the machine allocates within it.
allocator:
  kelly_fraction: 0.25            # 1/4-Kelly — geometric-growth sweet spot, not full Kelly
  base_gross_pct: 100.0           # gross exposure cap as % equity (risk envelope)
  max_lane_pct: 25.0              # per-lane cap as % equity
  max_cluster_pct: 40.0           # per-correlation-cluster cap as % equity
  min_net_bps: 1.0               # lanes below this net-of-cost edge get zero capital
  min_trades: 100                # lanes below this sample size get zero capital
  max_active_pipelines: 4        # hard concentration cap — fund few HEALTHY lanes
  regime_multipliers:
    risk_off: 0.5
    neutral: 1.0
    risk_on: 1.2
  degross_ladder:                 # [drawdown_pct, gross_multiplier] — progressive de-grossing
    - [3.0, 0.75]
    - [5.0, 0.5]
    - [7.0, 0.25]
    - [10.0, 0.0]

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
  min_net_bps: 1.0
  require_cost_model: true         # backtests with zero modeled cost are rejected

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
  note: "Permanently disabled for live capital — classical-only execution; no cuQuantum/Wukong/Tier 3 dispatch"

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
  isolated_node_required: true
  endpoint: http://127.0.0.1:19010
  config_ref: ~/.openclaw/infra/signing_node.yaml
  blind_sign_rejected: true
  require_gate_receipt: true
  max_receipt_age_seconds: 30
  on_env_compromised: halt_all_signing
  # Live signer wiring (REQUIRED when capital_profile=live — mock signer banned):
  # signer_module: "titan_signers.trezor:sign_request"   # module.path:callable

# Flatten adapters — mock is banned when capital_profile=live (startup refuses)
flatten:
  closer: mock          # mock | signing_node | "module.path:ClassOrFactory"
  revoker: mock         # mock | "module.path:ClassOrFactory"
  signing_endpoint: http://127.0.0.1:19010

# Evolution freeze — set freeze_during_live true; CLI: titan-safety evolution freeze
evolution:
  freeze_during_live: true
  flag_file: ~/.openclaw/safety/EVOLUTION_FROZEN

service:
  risk_kernel_port: 19001
  reconciliation_port: 19002
  status_aggregator_port: 19003
  portfolio_risk_port: 19004
  dead_mans_switch_port: 19005
  allocator_port: 19006
  tca_port: 19007
  signing_node_port: 19010
```

---

## infra/signing_node.yaml

```yaml
# TITAN Signing Node — logically isolated transaction signing
# Deploy target: ~/.openclaw/infra/signing_node.yaml
# May be co-located on TITANHOME hardware but MUST be logically isolated from evolution workloads.

version: "1.0"
enabled: true

endpoint:
  host: localhost  # override to dedicated host FQDN when physically separated
  port: 19010
  url: http://127.0.0.1:19010
  health: http://127.0.0.1:19010/health

isolation:
  minimal_os: true
  no_evolution_workloads: true
  no_llm_inference: true
  no_agent_runtime: true
  power_protected: true  # UPS-backed per power_requirements.yaml
  cgroup: openclaw-signing
  allowed_processes:
    - openclaw-trezor-bridge
    - openclaw-signing-daemon
    - tpm-pcr-watch
  forbidden_on_node:
    - dgm-h
    - gepa
    - hyevo
    - skill_evolution
    - cuquantum
    - cudev_fuzzing

routing:
  agents:
    - TRENCH-OPS
    - LAMARCK
  pre_sign_gates:
    - guardian_risk_validation
    - execution_gate_allow_receipt  # X-Titan-Gate-Receipt required on POST /v1/sign
    - risk_kernel_pre_trade
    - tenderly_simulation  # bridge txs
    - eip712_typed_data_only
  receipt:
    header: X-Titan-Gate-Receipt
    max_age_seconds: 30
    issued_by: titan_safety.execution_gate
  on_compromise:
    action: halt_all_signing
    circuit_breaker: CB_KEYS_SIGNING_ENV_COMPROMISED
    file_flag: ~/.openclaw/safety/SIGNING_HALTED

hardware_options:
  co_located:
    description: "Dedicated VM or cgroup on TITANHOME; separate from GPU MPS partitions"
    acceptable_for_phase1: true
  dedicated_host:
    description: "Minimal Ubuntu on separate NUC/RPi with USB to Trezor"
    recommended_for_phase3_plus: true

macmini_vault:
  role: "Trezor ceremony + cold key metadata; signing requests proxied via NATS"
  not_a_substitute_for: "isolated signing daemon — vault holds metadata, signing_node executes"
```

---

## Notes

- Paper default: `reconciliation.adapter: mock`, `capital.withdrawal_adapter: mock`.
- Live: `adapter: live` + fetcher; `withdrawal_adapter: trezor_signing`; gate receipts on `:19010`.
- Mutating safety POSTs need `X-Titan-Auth` (`titan-safety auth sign`).
- Edit `templates/*` or regenerate bootstrap via `python3 scripts/build.py` — this file refreshes automatically.
