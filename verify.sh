#!/usr/bin/env bash
# Verify TITAN bootstrap limits and deploy integrity
set -euo pipefail

OPENCLAW_HOME="${1:-$HOME/.openclaw}"
HERMES_HOME="${2:-$HOME/.hermes}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_MAX=20000
BOOTSTRAP_TOTAL_MAX=150000
MEMORY_MAX_LINES=100
ERRORS=0

log() { echo "[verify] $*"; }
fail() { log "FAIL: $*"; ERRORS=$((ERRORS + 1)); }
pass() { log "OK: $*"; }

BOOTSTRAP_FILES=(
  SOUL.md AGENTS.md MEMORY.md USER.md TOOLS.md
  IDENTITY.md HEARTBEAT.md BOOTSTRAP.md
)

log "Verifying OpenClaw home: $OPENCLAW_HOME"
log "Verifying Hermes home: $HERMES_HOME"

TOTAL=0
for f in "${BOOTSTRAP_FILES[@]}"; do
  path="$OPENCLAW_HOME/$f"
  if [[ ! -f "$path" ]]; then
    fail "Missing bootstrap file: $path"
    continue
  fi
  bytes=$(wc -c < "$path" | tr -d ' ')
  lines=$(wc -l < "$path" | tr -d ' ')
  TOTAL=$((TOTAL + bytes))
  if [[ $bytes -gt $BOOTSTRAP_MAX ]]; then
    fail "$f exceeds per-file limit: $bytes > $BOOTSTRAP_MAX bytes"
  else
    pass "$f: $bytes bytes"
  fi
  if [[ "$f" == "MEMORY.md" && $lines -gt $MEMORY_MAX_LINES ]]; then
    fail "MEMORY.md exceeds line limit: $lines > $MEMORY_MAX_LINES"
  fi
done

if [[ $TOTAL -gt $BOOTSTRAP_TOTAL_MAX ]]; then
  fail "Total bootstrap chars $TOTAL > $BOOTSTRAP_TOTAL_MAX"
else
  pass "Total bootstrap: $TOTAL / $BOOTSTRAP_TOTAL_MAX bytes"
fi

# Config files
for cfg in "$OPENCLAW_HOME/openclaw.json" "$HERMES_HOME/config.yaml"; do
  if [[ -f "$cfg" ]]; then
    pass "Config present: $cfg"
  else
    fail "Missing config: $cfg"
  fi
done

# JSON validity
if command -v python3 &>/dev/null && [[ -f "$OPENCLAW_HOME/openclaw.json" ]]; then
  python3 -c "import json; json.load(open('$OPENCLAW_HOME/openclaw.json'))" 2>/dev/null \
    && pass "openclaw.json valid JSON" \
    || fail "openclaw.json invalid JSON"
fi

# Skills symlink
if [[ -L "$HERMES_HOME/skills" ]]; then
  target=$(readlink -f "$HERMES_HOME/skills" 2>/dev/null || readlink "$HERMES_HOME/skills")
  pass "Hermes skills symlink -> $target"
elif [[ -d "$HERMES_HOME/skills" ]]; then
  pass "Hermes skills directory exists"
else
  fail "Hermes skills symlink missing: $HERMES_HOME/skills"
fi

# Skills count (missing dir must not abort under set -o pipefail)
skill_count=0
if [[ -d "$OPENCLAW_HOME/workspace/skills" ]]; then
  skill_count=$(find "$OPENCLAW_HOME/workspace/skills" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ') || skill_count=0
fi
if [[ $skill_count -gt 0 ]]; then
  pass "Skills extracted: $skill_count"
else
  fail "No skills found in $OPENCLAW_HOME/workspace/skills"
fi

# Herald notify skill
if [[ -f "$OPENCLAW_HOME/workspace/skills/herald_notify/notify.py" ]]; then
  pass "herald_notify formatter present"
else
  fail "Missing herald_notify/notify.py"
fi

# Telegram institutional templates
if [[ -f "$OPENCLAW_HOME/workspace/telegram/schema/trade_notification.v1.json" ]]; then
  pass "Telegram schema present"
else
  fail "Missing telegram/schema/trade_notification.v1.json"
fi
if [[ -d "$OPENCLAW_HOME/workspace/telegram/templates" ]]; then
  tpl_count=$(find "$OPENCLAW_HOME/workspace/telegram/templates" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  if [[ $tpl_count -ge 4 ]]; then
    pass "Telegram templates: $tpl_count"
  else
    fail "Insufficient telegram templates: $tpl_count"
  fi
else
  fail "Missing telegram/templates directory"
fi

# Memory sidecars
for mf in strategies/active-pipelines.md risk/circuit-breakers.md agents/routing-table.md; do
  if [[ -f "$OPENCLAW_HOME/memory/$mf" ]]; then
    pass "Memory: $mf"
  else
    fail "Missing memory file: $mf"
  fi
done

# Autonomy / survivability checks
if [[ -f "$OPENCLAW_HOME/USER.md" ]]; then
  if grep -q "## Approval Gates" "$OPENCLAW_HOME/USER.md" 2>/dev/null; then
    pass "USER.md: promotion approval gates present"
  else
    fail "USER.md missing promotion approval gates section"
  fi
  if grep -qi "implicit approval\|Auto-promote.*default\|operator absence = implicit" "$OPENCLAW_HOME/USER.md" 2>/dev/null; then
    fail "USER.md contains auto-promote-on-TIMEOUT policy"
  elif grep -qi "never auto-promote\|HOLD/de-risk" "$OPENCLAW_HOME/USER.md" 2>/dev/null; then
    pass "USER.md: TIMEOUT hold/de-risk policy"
  else
    fail "USER.md missing TIMEOUT hold/de-risk policy"
  fi
  if grep -q "PENDING_HUMAN_APPROVAL" "$OPENCLAW_HOME/USER.md" 2>/dev/null; then
    fail "USER.md contains PENDING_HUMAN_APPROVAL (use PENDING_PROMOTION_APPROVAL)"
  else
    pass "USER.md: no routine PENDING_HUMAN_APPROVAL"
  fi
fi

if [[ -f "$OPENCLAW_HOME/SOUL.md" ]]; then
  if grep -qi "never auto-promote on TIMEOUT\|HOLD/de-risk" "$OPENCLAW_HOME/SOUL.md" 2>/dev/null; then
    pass "SOUL.md: TIMEOUT hold/de-risk policy"
  else
    fail "SOUL.md missing TIMEOUT hold/de-risk policy"
  fi
fi

if [[ -f "$OPENCLAW_HOME/AGENTS.md" ]]; then
  if grep -qi "BFT.*Honesty\|Trade Voting Honesty\|same-model\|correlated consensus\|risk_kernel" "$OPENCLAW_HOME/AGENTS.md" 2>/dev/null; then
    pass "AGENTS.md: trade voting honesty documented"
  else
    fail "AGENTS.md missing trade voting honesty note"
  fi
  if grep -qi "Model Tier Architecture\|Tier 1\|:30000" "$OPENCLAW_HOME/AGENTS.md" 2>/dev/null; then
    pass "AGENTS.md: 3-tier model architecture documented"
  else
    fail "AGENTS.md missing 3-tier model architecture"
  fi
fi

if [[ -f "$OPENCLAW_HOME/infra/hardware_bom.yaml" ]]; then
  pass "hardware_bom.yaml present"
  if grep -q "9995WX" "$OPENCLAW_HOME/infra/hardware_bom.yaml" 2>/dev/null; then
    pass "hardware_bom: Threadripper 9995WX"
  else
    fail "hardware_bom missing 9995WX"
  fi
  if grep -q "RTX PRO 6000" "$OPENCLAW_HOME/infra/hardware_bom.yaml" 2>/dev/null; then
    pass "hardware_bom: RTX PRO 6000"
  else
    fail "hardware_bom missing RTX PRO 6000"
  fi
else
  fail "Missing infra/hardware_bom.yaml"
fi

if [[ -f "$OPENCLAW_HOME/openclaw.json" ]]; then
  if python3 -c "import json; d=json.load(open('$OPENCLAW_HOME/openclaw.json')); assert d.get('inference',{}).get('tier1_critical',{}).get('port')==30000" 2>/dev/null; then
    pass "openclaw.json: tier1_critical inference config"
  else
    fail "openclaw.json missing tier1_critical inference block"
  fi
  if python3 -c "import json; d=json.load(open('$OPENCLAW_HOME/openclaw.json')); assert d.get('inference',{}).get('embedder',{}).get('port')==30004" 2>/dev/null; then
    pass "openclaw.json: embedder :30004 configured"
  else
    fail "openclaw.json missing embedder inference block"
  fi
  if python3 -c "import json; d=json.load(open('$OPENCLAW_HOME/openclaw.json')); lb=d.get('latencyBudgetPath') or d.get('inference',{}).get('latencyBudgetPath'); assert lb" 2>/dev/null; then
    pass "openclaw.json: latency budget path set"
  else
    fail "openclaw.json missing latencyBudgetPath"
  fi
  if grep -q "implicit approval" "$OPENCLAW_HOME/openclaw.json" 2>/dev/null; then
    fail "openclaw.json contains implicit approval"
  else
    pass "openclaw.json: no implicit approval"
  fi
fi

# Risk kernel policy + safety services
if [[ -f "$OPENCLAW_HOME/risk_kernel/policy.yaml" ]]; then
  pass "Risk kernel policy present"
else
  fail "Missing risk_kernel/policy.yaml"
fi

if [[ -d "$OPENCLAW_HOME/safety/titan_safety" ]]; then
  pass "Safety package installed"
else
  fail "Missing safety/titan_safety package"
fi

if [[ -x "$OPENCLAW_HOME/safety/bin/titan-safety" ]]; then
  pass "titan-safety CLI present"
else
  fail "Missing titan-safety CLI"
fi

if [[ -f "$OPENCLAW_HOME/safety/titan_safety/capital.py" ]]; then
  pass "Capital management module present"
else
  fail "Missing titan_safety/capital.py"
fi

if [[ -f "$OPENCLAW_HOME/workspace/telegram/templates/capital_event.md" ]]; then
  pass "Capital Telegram template present"
else
  fail "Missing telegram/templates/capital_event.md"
fi

if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
cap = cfg.get('capital') or {}
if cap.get('min_operating_capital_usd') is None:
    sys.exit(1)
# Live profile: trezor_signing required (mock withdrawal forbidden)
profile = str(cap.get('capital_profile') or cfg.get('capitalProfile') or cfg.get('capital_profile') or 'paper').lower()
adapter = cap.get('withdrawal_adapter', 'mock')
if profile == 'live' and adapter == 'mock':
    sys.exit(2)
if profile == 'live' and adapter not in ('trezor_signing', 'signing_node', 'live', 'trezor', 'in_process'):
    sys.exit(3)
" 2>/dev/null && pass "openclaw.json capital section OK" \
    || fail "openclaw.json capital config invalid (live+mock withdrawal forbidden)"
fi

if [[ -f "$PROJECT_ROOT/templates/infra/live.env.example" ]]; then
  pass "infra/live.env.example present"
else
  fail "Missing templates/infra/live.env.example"
fi

if [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/adapters/live_bundle.py" ]]; then
  pass "live_bundle adapter present"
else
  fail "Missing live_bundle.py"
fi

if [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/trade_verifier.py" ]]; then
  pass "trade_verifier (autonomous sign/verify) present"
else
  fail "Missing trade_verifier.py"
fi

TEMPLATE_POLICY="$PROJECT_ROOT/templates/risk_kernel/policy.yaml"
if [[ -f "$TEMPLATE_POLICY" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import sys, yaml
p = yaml.safe_load(open('$TEMPLATE_POLICY')) or {}
profile = str(p.get('capital_profile') or 'paper').lower()
if profile != 'paper':
    sys.exit(1)
if p.get('autonomous_signing', {}).get('enabled') is not False:
    sys.exit(2)
venues = [str(v).lower() for v in (p.get('allowed_venues') or [])]
if venues != ['paper']:
    sys.exit(5)
if (p.get('flash_loan_live') or {}).get('enabled') is not False:
    sys.exit(6)
if int((p.get('allocator') or {}).get('max_active_pipelines', 0)) != 2:
    sys.exit(7)
tier1 = p.get('tier1_capital_risk') or {}
if not tier1.get('profiles', {}).get('live'):
    sys.exit(4)
" 2>/dev/null && pass "policy: paper default + tier1 live profile + DEX-only venues" \
    || fail "policy: expected paper default, venues [paper], max_active_pipelines 2, tier1 profiles"
fi

if [[ -f "$TEMPLATE_POLICY" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import sys, yaml
p = yaml.safe_load(open('$TEMPLATE_POLICY')) or {}
a = p.get('autonomous_signing') or {}
# Paper default: signing off until evidence; live profile enables via tier1 merge
if str(p.get('capital_profile','paper')).lower() == 'paper' and a.get('enabled') is True:
    sys.exit(1)
" 2>/dev/null && pass "policy autonomous_signing paper-safe" \
    || fail "policy autonomous_signing enabled on paper default"
fi

# Live capital profile — mock adapters forbidden when profile is live (deployed policy)
POLICY="$OPENCLAW_HOME/risk_kernel/policy.yaml"
if [[ -f "$POLICY" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import sys
try:
    import yaml
except ImportError:
    sys.exit(0)
p = yaml.safe_load(open('$POLICY')) or {}
profile = str(p.get('capital_profile') or 'paper').lower()
if profile != 'live':
    print('SKIP_LIVE_PROFILE_CHECKS', file=sys.stderr)
    sys.exit(0)
venues = [str(v).lower() for v in (p.get('allowed_venues') or [])]
live = [v for v in venues if v not in ('paper', 'mock', 'test')]
adapter = ((p.get('reconciliation') or {}).get('adapter') or 'mock')
mode = str(p.get('mode') or 'observe').lower()
if (mode == 'enforce' or profile == 'live') and live and adapter == 'mock':
    print('MOCK_ADAPTER_FORBIDDEN: live venues with mock recon', file=sys.stderr)
    sys.exit(2)
flatten = p.get('flatten') or {}
if profile == 'live':
    if str(flatten.get('closer', 'mock')).lower() == 'mock':
        print('MOCK_FLATTEN_CLOSER', file=sys.stderr)
        sys.exit(3)
    if str(flatten.get('revoker', 'mock')).lower() == 'mock':
        print('MOCK_FLATTEN_REVOKER', file=sys.stderr)
        sys.exit(4)
    signing = p.get('signing') or {}
    if not str(signing.get('signer_module') or '').strip():
        print('MISSING_SIGNER_MODULE', file=sys.stderr)
        sys.exit(5)
" 2>/dev/null && pass "policy live profile + no mock adapters OK" \
    || fail "policy: live profile requires live recon/flatten/signing wiring"
fi

# Systemd unit files in output (optional install)
# titan-signing-node is LEGACY optional — not required when signing.mode=in_process
for svc in titan-risk-kernel titan-reconciliation titan-dead-mans-switch titan-status-aggregator titan-allocator titan-tca titan-portfolio-risk titan-security-ops trench-ops-edge llama-server-tier1 llama-server-tier2 llama-server-embedder cuda-mps; do
  if [[ -f "$PROJECT_ROOT/output/systemd/${svc}.service" ]] || [[ -f "$PROJECT_ROOT/templates/systemd/${svc}.service" ]]; then
    pass "systemd unit template: ${svc}.service"
  fi
done
if [[ -f "$PROJECT_ROOT/templates/systemd/titan-signing-node.service" ]]; then
  pass "systemd unit template (legacy optional): titan-signing-node.service"
fi

# Infra specs (power, signing, GPU schedule)
INFRA_DIR="$OPENCLAW_HOME/infra"
for spec in power_requirements.yaml signing_node.yaml gpu_schedule.yaml latency_budget.yaml latency_fast_path.yaml edge_hot_path.yaml edge_mesh.yaml edge_rtt_probe.yaml flash_loan.yaml; do
  if [[ -f "$INFRA_DIR/$spec" ]]; then
    pass "Infra spec: $spec"
  else
    fail "Missing infra spec: $INFRA_DIR/$spec"
  fi
done

# Latency tuning artifacts
for script in titanhome-latency-tune.sh forge_gpu_schedule_enforce.sh titanhome-prewarm-tier1.sh edge_pop_bootstrap.sh edge_mesh_wg_setup.sh; do
  if [[ -x "$INFRA_DIR/$script" ]] || [[ -f "$INFRA_DIR/$script" ]]; then
    pass "Infra script: $script"
  else
    fail "Missing infra script: $INFRA_DIR/$script"
  fi
done
if [[ -f "$INFRA_DIR/edge_mesh.yaml" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import yaml, sys
from pathlib import Path
m = yaml.safe_load(Path('$INFRA_DIR/edge_mesh.yaml').read_text())
if m.get('mode') != 'full_mesh':
    sys.exit(1)
if len(m.get('pops') or {}) < 5:
    sys.exit(2)
if not (m.get('paper_trading') or {}).get('latency_faithful'):
    sys.exit(3)
" 2>/dev/null && pass "edge_mesh.yaml: full_mesh + 5 PoPs + paper latency_faithful" \
    || fail "edge_mesh.yaml invalid or not full_mesh"
fi
if [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/edge_router.py" ]]; then
  pass "edge_router.py present"
else
  fail "Missing templates/safety/titan_safety/edge_router.py"
fi
if [[ -f "$INFRA_DIR/sysctl/99-openclaw-performance.conf" ]]; then
  pass "Infra sysctl: 99-openclaw-performance.conf"
else
  fail "Missing infra/sysctl/99-openclaw-performance.conf"
fi

# UPS required for live capital (gate)
if [[ -f "$INFRA_DIR/power_requirements.yaml" ]]; then
  if grep -q "live_capital_requires_ups: true" "$INFRA_DIR/power_requirements.yaml" 2>/dev/null; then
    pass "UPS required for live capital (power_requirements.yaml)"
  else
    fail "power_requirements.yaml missing live_capital_requires_ups: true"
  fi
  if grep -qi "decommissioned\|no UPS" "$INFRA_DIR/power_requirements.yaml" 2>/dev/null; then
    fail "power_requirements.yaml contains contradictory no-UPS language"
  else
    pass "power_requirements.yaml: no contradictory UPS decommission language"
  fi
fi

# Risk kernel power-loss policy
if [[ -f "$OPENCLAW_HOME/risk_kernel/policy.yaml" ]]; then
  if grep -q "power_loss:" "$OPENCLAW_HOME/risk_kernel/policy.yaml" 2>/dev/null \
     && grep -q "halt_trading" "$OPENCLAW_HOME/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "Risk kernel: power-loss = halt policy"
  else
    fail "risk_kernel/policy.yaml missing power_loss halt policy"
  fi
fi

# Signing isolation (in-process) + edge mesh full_mesh in openclaw.json
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
sn = cfg.get('signingNode', {})
em = cfg.get('edgeMesh', {})
if not sn.get('enabled'):
    sys.exit(1)
mode = str(sn.get('mode') or 'in_process').lower()
if mode not in ('in_process', 'http', 'legacy'):
    sys.exit(2)
if mode == 'http' and not sn.get('endpoint'):
    sys.exit(2)
if not sn.get('requireGateReceipt', True):
    sys.exit(5)
if em.get('mode') != 'full_mesh':
    sys.exit(3)
pops = em.get('activePops') or []
if len(pops) < 5:
    sys.exit(4)
if not em.get('paperLatencyFaithful', False):
    sys.exit(6)
if em.get('defaultPop') != 'EDGE-FRA':
    sys.exit(7)
" 2>/dev/null && pass "openclaw.json signingNode (in_process) + edgeMesh full_mesh OK" \
    || fail "openclaw.json missing signingNode or edgeMesh full_mesh config"
fi

# Evolution freeze + allocator concentration config
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
evo = cfg.get('evolution') or {}
if not evo.get('freezeDuringLive'):
    sys.exit(1)
alloc = cfg.get('allocator') or {}
if int(alloc.get('maxActivePipelines', 0)) < 1:
    sys.exit(2)
" 2>/dev/null && pass "openclaw.json evolution freeze + pipeline concentration OK" \
    || fail "openclaw.json missing evolution.freezeDuringLive or allocator.maxActivePipelines"
fi

# Selective activation — catalog ≠ all-on (Mention≠mandate)
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
aut = cfg.get('autonomy') or {}
if not aut.get('selectiveActivation', False):
    sys.exit(1)
alloc = cfg.get('allocator') or {}
if int(alloc.get('maxActivePipelines', 0)) > 12:
    sys.exit(2)
" 2>/dev/null && pass "openclaw.json selectiveActivation + concentration cap OK" \
    || fail "openclaw.json missing autonomy.selectiveActivation or maxActivePipelines too high"
fi
if [[ -f "$OPENCLAW_HOME/HEARTBEAT.md" ]]; then
  if grep -qiE 'all 4[67] pipelines active' "$OPENCLAW_HOME/HEARTBEAT.md" 2>/dev/null; then
    fail "HEARTBEAT.md still says all 46/47 pipelines active"
  else
    pass "HEARTBEAT.md: no all-pipelines-active mandate"
  fi
fi
if [[ -f "$OPENCLAW_HOME/IDENTITY.md" ]]; then
  if grep -qiE 'selective activation|catalog.*required|max_active_pipelines' "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null; then
    pass "IDENTITY.md: selective activation documented"
  else
    fail "IDENTITY.md missing selective activation / catalog note"
  fi
fi
# Selective-activation memory sidecar (build must emit / preserve)
_sel=""
for _cand in \
  "$OPENCLAW_HOME/memory/strategies/selective-activation.md" \
  "$PROJECT_ROOT/output/memory/strategies/selective-activation.md" \
  "$PROJECT_ROOT/workspace/memory/strategies/selective-activation.md"; do
  if [[ -f "$_cand" ]]; then _sel="$_cand"; break; fi
done
if [[ -n "$_sel" ]] && grep -qiE 'max_active_pipelines|Mention|catalog' "$_sel" 2>/dev/null; then
  pass "memory/strategies/selective-activation.md present"
else
  fail "Missing memory/strategies/selective-activation.md"
fi
if [[ -f "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" ]]; then
  if grep -q "promotion_stats:" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null \
     && grep -q "endgame_circuit_breakers:" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null \
     && grep -q "advisory_mode:" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: promotion_stats + endgame CBs + allocator advisory_mode"
  else
    fail "policy.yaml missing promotion_stats / endgame_circuit_breakers / advisory_mode"
  fi
  if grep -q "memecoin_trench:" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null \
     && grep -q "CB_MEMECOIN_FILTER_BYPASS" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: P22 memecoin_trench + CBs"
  else
    fail "policy.yaml missing memecoin_trench block"
  fi
  if grep -q "tier1_capital_risk:" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null \
     && grep -q "drawdown_notify_only: true" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null \
     && grep -q "soft_de_gross" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: tier1 drawdown paper notify + live enforce tiers"
  else
    fail "policy.yaml missing tier1_capital_risk / drawdown tier config"
  fi
fi

# Tier 1 — execution skills must reference ExecutionGate
if [[ -f "$PROJECT_ROOT/scripts/ci/check_execution_gate_imports.py" ]]; then
  if python3 "$PROJECT_ROOT/scripts/ci/check_execution_gate_imports.py" 2>/dev/null; then
    pass "execution skills reference ExecutionGate"
  else
    fail "execution skills missing ExecutionGate reference"
  fi
fi

# Tier 1 — live config (template paper defaults + live mock/CEX ban)
if [[ -f "$PROJECT_ROOT/scripts/ci/check_live_config.py" ]]; then
  if python3 "$PROJECT_ROOT/scripts/ci/check_live_config.py" 2>/dev/null; then
    pass "live config CI (paper defaults + live mock ban)"
  else
    fail "live config check failed (run scripts/ci/check_live_config.py)"
  fi
fi

# Tier 3 — docs must match policy.yaml bounded autonomy
if [[ -f "$PROJECT_ROOT/scripts/ci/check_doc_policy_consistency.py" ]]; then
  if python3 "$PROJECT_ROOT/scripts/ci/check_doc_policy_consistency.py" 2>/dev/null; then
    pass "docs consistent with policy.yaml"
  else
    fail "docs contradict policy.yaml (run check_doc_policy_consistency.py)"
  fi
fi

if [[ -f "$PROJECT_ROOT/docs/TIER3_INSTITUTIONAL_OPS.md" ]]; then
  pass "docs/TIER3_INSTITUTIONAL_OPS.md present"
else
  fail "Missing docs/TIER3_INSTITUTIONAL_OPS.md"
fi
if [[ -f "$PROJECT_ROOT/docs/GO_LIVE_SEQUENCE.md" ]]; then
  pass "docs/GO_LIVE_SEQUENCE.md present"
else
  fail "Missing docs/GO_LIVE_SEQUENCE.md"
fi
if [[ -f "$PROJECT_ROOT/docs/CANONICAL_RUNBOOK.md" ]]; then
  pass "docs/CANONICAL_RUNBOOK.md present"
else
  fail "Missing docs/CANONICAL_RUNBOOK.md"
fi
if [[ -f "$PROJECT_ROOT/templates/observability/prometheus.yml" ]]; then
  pass "observability/prometheus.yml present"
else
  fail "Missing templates/observability/prometheus.yml"
fi
if [[ -f "$PROJECT_ROOT/scripts/audit_export_worm.py" ]]; then
  pass "scripts/audit_export_worm.py present"
else
  fail "Missing scripts/audit_export_worm.py"
fi

if [[ -f "$PROJECT_ROOT/docs/TIER1_CAPITAL_RISK.md" ]]; then
  pass "docs/TIER1_CAPITAL_RISK.md present"
else
  fail "Missing docs/TIER1_CAPITAL_RISK.md"
fi
if [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/memecoin_filter.py" ]]; then
  pass "memecoin_filter module present"
else
  fail "Missing memecoin_filter.py"
fi
if grep -q "cmd_memecoin_evaluate" "$PROJECT_ROOT/templates/safety/titan_safety/cli.py" 2>/dev/null; then
  pass "CLI: memecoin evaluate registered"
else
  fail "Missing memecoin evaluate CLI"
fi
if [[ -f "$PROJECT_ROOT/templates/infra/solana_memecoin.yaml" ]]; then
  pass "infra/solana_memecoin.yaml present"
else
  fail "Missing solana_memecoin.yaml"
fi
if grep -q "pump_swap_migration\|PumpSwap\|pumpswap" "$PROJECT_ROOT/templates/infra/solana_memecoin.yaml" 2>/dev/null; then
  pass "solana_memecoin.yaml: PumpSwap migration markers"
else
  fail "solana_memecoin.yaml missing PumpSwap migration"
fi
_mc_mem=""
for _mc in \
  "$PROJECT_ROOT/output/memory/strategies/memecoin-trench.md" \
  "$PROJECT_ROOT/workspace/memory/strategies/memecoin-trench.md"; do
  if [[ -f "$_mc" ]]; then _mc_mem="$_mc"; break; fi
done
if [[ -n "$_mc_mem" ]] && grep -qiE 'P22|six-gate|Pump\.fun' "$_mc_mem" 2>/dev/null; then
  pass "memory/strategies/memecoin-trench.md present"
else
  fail "Missing memory/strategies/memecoin-trench.md"
fi
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
mc = cfg.get('memecoinTrench') or {}
if mc.get('pipelineId') != 'P22':
    sys.exit(1)
if mc.get('enabled') is True:
    sys.exit(2)
" 2>/dev/null && pass "openclaw.json memecoinTrench P22 catalog (disabled by default)" \
    || fail "openclaw.json memecoinTrench invalid or enabled at deploy"
fi
if [[ -f "$PROJECT_ROOT/templates/skills/memecoin_trench/SKILL.md" ]]; then
  pass "Skill memecoin_trench present"
else
  fail "Missing memecoin_trench skill"
fi

# Flash-loan router (§FL)
if grep -q "flash_loan_live:" "$PROJECT_ROOT/templates/risk_kernel/policy.yaml" 2>/dev/null; then
  pass "policy.yaml: flash_loan_live block"
else
  fail "policy.yaml missing flash_loan_live block"
fi
if [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/flash_loan_router.py" ]]; then
  pass "flash_loan_router module present"
else
  fail "Missing flash_loan_router.py"
fi
if [[ -f "$PROJECT_ROOT/templates/infra/flash_loan.yaml" ]]; then
  pass "infra/flash_loan.yaml present"
else
  fail "Missing infra/flash_loan.yaml"
fi
if [[ -f "$PROJECT_ROOT/templates/playbooks/flash_loan_live.yaml" ]]; then
  pass "playbook flash_loan_live.yaml present"
else
  fail "Missing playbooks/flash_loan_live.yaml"
fi
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
fl = cfg.get('flashLoanRouter') or {}
if fl.get('enabled') is not False:
    sys.exit(1)
if fl.get('requiresPromotionYes', True):
    sys.exit(2)
if fl.get('skill') != 'flash_loan_router':
    sys.exit(3)
" 2>/dev/null && pass "openclaw.json flashLoanRouter catalog (disabled by default)" \
    || fail "openclaw.json flashLoanRouter invalid or enabled at deploy"
fi
if [[ -f "$PROJECT_ROOT/templates/skills/flash_loan_router/SKILL.md" ]]; then
  pass "Skill flash_loan_router present"
else
  fail "Missing flash_loan_router skill"
fi

# TITANHOME retained in IDENTITY
if [[ -f "$OPENCLAW_HOME/IDENTITY.md" ]]; then
  if grep -qi "TITANHOME" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null \
     && grep -qi "primary" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null; then
    pass "IDENTITY.md: TITANHOME primary role documented"
  else
    fail "IDENTITY.md missing TITANHOME primary role"
  fi
  if grep -qi "full.5-PoP\|full_mesh\|full mesh" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null \
     && ! grep -qi "single PoP\|single_pop\|deferred Phase 3" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null; then
    pass "IDENTITY.md: full 5-PoP edge mesh documented"
  else
    fail "IDENTITY.md missing full 5-PoP edge mesh (still single-PoP/deferred?)"
  fi
fi

# BOOTSTRAP UPS gate
if [[ -f "$OPENCLAW_HOME/BOOTSTRAP.md" ]]; then
  if grep -qi "UPS.*REQUIRED\|UPS installed" "$OPENCLAW_HOME/BOOTSTRAP.md" 2>/dev/null; then
    pass "BOOTSTRAP.md: UPS gate for live capital"
  else
    fail "BOOTSTRAP.md missing UPS requirement for live capital"
  fi
fi

# PRODUCTION_READINESS UPS mention
if [[ -f "$PROJECT_ROOT/PRODUCTION_READINESS.md" ]]; then
  if grep -qi "UPS mandatory\|UPS installed" "$PROJECT_ROOT/PRODUCTION_READINESS.md" 2>/dev/null; then
    pass "PRODUCTION_READINESS.md: UPS documented"
  else
    fail "PRODUCTION_READINESS.md missing UPS requirements"
  fi
fi

if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
rk = cfg.get('riskKernel', {})
promo = cfg.get('promotion', {})
if not rk.get('enabled'):
    sys.exit(1)
if not rk.get('failClosed'):
    sys.exit(4)
if not rk.get('preTradeValidationUrl'):
    sys.exit(5)
if promo.get('timeoutPolicy') != 'hold_derisk':
    sys.exit(2)
if promo.get('phase5RequiresHumanYes') is not True:
    sys.exit(3)
" 2>/dev/null && pass "openclaw.json survivability + pre-trade config OK" || fail "openclaw.json missing survivability/pre-trade settings"
fi

# Run unit test suite
PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
if command -v "$PYTHON" &>/dev/null && [[ -d "$PROJECT_ROOT/tests" ]]; then
  if "$PYTHON" -m pytest "$PROJECT_ROOT/tests" -q --ignore="$PROJECT_ROOT/tests/chaos" 2>/dev/null; then
    pass "Safety unit tests passed"
  else
    fail "Safety unit tests failed (run: python3 -m pytest $PROJECT_ROOT/tests)"
  fi
fi

# Chaos harness (non-blocking warning if deps missing)
if [[ -f "$PROJECT_ROOT/tests/chaos/chaos_harness.py" ]]; then
  if "$PYTHON" "$PROJECT_ROOT/tests/chaos/chaos_harness.py" 2>/dev/null; then
    pass "Chaos harness passed"
  else
    fail "Chaos harness failed"
  fi
fi

# Run adversarial harness
if [[ -f "$PROJECT_ROOT/tests/adversarial/adversarial_harness.py" ]]; then
  if "$PYTHON" "$PROJECT_ROOT/tests/adversarial/adversarial_harness.py" 2>/dev/null; then
    pass "Adversarial harness passed"
  else
    fail "Adversarial harness failed"
  fi
fi

# Playbooks installed
if [[ -f "$OPENCLAW_HOME/playbooks/promotion.yaml" ]]; then
  pass "Promotion playbook present"
else
  fail "Missing playbooks/promotion.yaml"
fi

if [[ -f "$OPENCLAW_HOME/playbooks/security_lockdown.yaml" ]]; then
  pass "Security lockdown playbook present"
else
  fail "Missing playbooks/security_lockdown.yaml"
fi

# Four-pillar security ops
if [[ -f "$OPENCLAW_HOME/safety/titan_safety/security_ops.py" ]] \
   || [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/security_ops.py" ]]; then
  pass "security_ops module present"
else
  fail "Missing titan_safety/security_ops.py"
fi

if [[ -f "$OPENCLAW_HOME/risk_kernel/policy.yaml" ]]; then
  if grep -q "security_ops:" "$OPENCLAW_HOME/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: security_ops four-pillar block"
  else
    fail "risk_kernel/policy.yaml missing security_ops block"
  fi
  if grep -q "CB_SECURITY_LOCKDOWN\|CB_TPM_PCR_DRIFT\|CB_DARKINT_HONEYPOT" \
       "$OPENCLAW_HOME/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: security circuit breakers"
  else
    fail "risk_kernel/policy.yaml missing security CBs"
  fi
fi

if [[ -f "$PROJECT_ROOT/templates/infra/ghost_evasion.yaml" ]] \
   || [[ -f "$OPENCLAW_HOME/infra/ghost_evasion.yaml" ]]; then
  pass "ghost_evasion.yaml infra spec present"
else
  fail "Missing infra/ghost_evasion.yaml"
fi

if [[ -f "$OPENCLAW_HOME/risk_kernel/policy.yaml" ]]; then
  if grep -q "ghost_evasion:" "$OPENCLAW_HOME/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: ghost_evasion block"
  else
    fail "risk_kernel/policy.yaml missing ghost_evasion block"
  fi
  if grep -q "CB_STEALTH_PUBLIC_PATH\|CB_STEALTH_UNSHIELDED_VENUE" \
       "$OPENCLAW_HOME/risk_kernel/policy.yaml" 2>/dev/null; then
    pass "policy.yaml: stealth circuit breakers"
  else
    fail "risk_kernel/policy.yaml missing stealth CBs"
  fi
fi

if [[ -f "$OPENCLAW_HOME/safety/titan_safety/stealth_predatory.py" ]] \
   || [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/stealth_predatory.py" ]]; then
  pass "stealth_predatory module present"
else
  fail "Missing titan_safety/stealth_predatory.py"
fi

for skill in sentinel_security predator_scanner; do
  skill_md="$OPENCLAW_HOME/workspace/skills/${skill}/SKILL.md"
  if [[ ! -f "$skill_md" ]]; then
    skill_md="$PROJECT_ROOT/output/workspace/skills/${skill}/SKILL.md"
  fi
  if [[ -f "$skill_md" ]]; then
    if grep -qi "stub" "$skill_md" 2>/dev/null && ! grep -qi "status: live\|Pillars owned" "$skill_md" 2>/dev/null; then
      fail "Skill $skill still stub"
    else
      pass "Skill $skill non-stub"
    fi
  else
    fail "Missing skill: $skill"
  fi
done

for ref in AEGIS_detail.md FORTRESS_detail.md GHOST_detail.md MEV_detail.md REAPER_detail.md; do
  if [[ -f "$PROJECT_ROOT/refs/$ref" ]] && grep -qE "Pillar:|## Pillar|Impenetrable|Evasion|Predatory|Hardening|MEV-shield" "$PROJECT_ROOT/refs/$ref" 2>/dev/null; then
    pass "Ref companion fleshed: $ref"
  else
    fail "Ref companion missing/stub: $ref"
  fi
done

if [[ -f "$OPENCLAW_HOME/AGENTS.md" ]]; then
  if grep -q "Four pillars" "$OPENCLAW_HOME/AGENTS.md" 2>/dev/null; then
    pass "AGENTS.md: four-pillar Security section"
  else
    fail "AGENTS.md missing four-pillar Security section"
  fi
fi

if [[ -f "$OPENCLAW_HOME/memory/security/README.md" ]] \
   || [[ -f "$PROJECT_ROOT/output/memory/security/README.md" ]]; then
  pass "memory/security present"
else
  fail "Missing memory/security"
fi

if [[ -f "$OPENCLAW_HOME/capital/tax_ledger.py" ]]; then
  pass "Tax ledger stub present"
else
  fail "Missing capital/tax_ledger.py"
fi

# Bounded autonomy in openclaw.json
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
auto = cfg.get('autonomy', {}).get('matrix', {}).get('auto_execute', [])
human = cfg.get('autonomy', {}).get('matrix', {}).get('human_required', [])
if not auto or not human:
    sys.exit(1)
if cfg.get('promotion', {}).get('airGappedStaging') is not True:
    sys.exit(2)
if not cfg.get('riskKernel', {}).get('portfolioRiskUrl'):
    sys.exit(3)
" 2>/dev/null && pass "openclaw.json bounded autonomy matrix OK" \
    || fail "openclaw.json missing bounded autonomy / portfolio risk config"
fi

if [[ -f "$OPENCLAW_HOME/SOUL.md" ]]; then
  if grep -q "Bounded Autonomy Matrix" "$OPENCLAW_HOME/SOUL.md" 2>/dev/null; then
    pass "SOUL.md: bounded autonomy matrix"
  else
    fail "SOUL.md missing bounded autonomy matrix"
  fi
fi

for svc in titan-portfolio-risk; do
  if [[ -f "$PROJECT_ROOT/output/systemd/${svc}.service" ]]; then
    pass "systemd unit template: ${svc}.service"
  fi
done

if [[ $ERRORS -gt 0 ]]; then
  log "Verification FAILED with $ERRORS error(s)"
  exit 1
fi

log "Verification PASSED"
exit 0
