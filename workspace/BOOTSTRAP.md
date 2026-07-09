# BOOTSTRAP — First-Run Ritual

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
- [ ] Enable systemd: `systemctl --user enable --now llama-server-tier1 llama-server-tier2 titan-risk-kernel titan-reconciliation titan-dead-mans-switch titan-signing-node openclaw-gateway hermes-gateway`
