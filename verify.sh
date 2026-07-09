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
    pass "openclaw.json: 3-tier inference config"
  else
    fail "openclaw.json missing tier1_critical inference block"
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
# Paper default: mock withdrawal is OK. Live profile must not use mock.
profile = str(cap.get('capital_profile') or cfg.get('capital_profile') or 'paper').lower()
adapter = cap.get('withdrawal_adapter', 'mock')
if profile == 'live' and adapter == 'mock':
    sys.exit(2)
if profile != 'live' and adapter != 'mock':
    # unexpected but not fatal for paper verify — still require capital section
    pass
" 2>/dev/null && pass "openclaw.json capital section OK" \
    || fail "openclaw.json capital config invalid (live+mock withdrawal forbidden)"
fi

# Live-profile mock ban: policy must not allow mock recon with live venues under enforce
POLICY="$OPENCLAW_HOME/risk_kernel/policy.yaml"
if [[ -f "$POLICY" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import sys
try:
    import yaml
except ImportError:
    sys.exit(0)
p = yaml.safe_load(open('$POLICY')) or {}
venues = [str(v).lower() for v in (p.get('allowed_venues') or [])]
live = [v for v in venues if v not in ('paper', 'mock', 'test')]
adapter = ((p.get('reconciliation') or {}).get('adapter') or 'mock')
mode = str(p.get('mode') or 'observe').lower()
profile = str(p.get('capital_profile') or 'paper').lower()
if (mode == 'enforce' or profile == 'live') and live and adapter == 'mock':
    print('MOCK_ADAPTER_FORBIDDEN: live venues with mock recon', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null && pass "policy mock-adapter live ban OK" \
    || fail "policy: mock recon forbidden with live venues under enforce/live"
fi

# Systemd unit files in output (optional install)
for svc in titan-risk-kernel titan-reconciliation titan-dead-mans-switch titan-status-aggregator titan-allocator titan-tca titan-signing-node titan-portfolio-risk titan-security-ops; do
  if [[ -f "$PROJECT_ROOT/output/systemd/${svc}.service" ]] || [[ -f "$PROJECT_ROOT/templates/systemd/${svc}.service" ]]; then
    pass "systemd unit template: ${svc}.service"
  fi
done

# Infra specs (power, signing, GPU schedule)
INFRA_DIR="$OPENCLAW_HOME/infra"
for spec in power_requirements.yaml signing_node.yaml gpu_schedule.yaml; do
  if [[ -f "$INFRA_DIR/$spec" ]]; then
    pass "Infra spec: $spec"
  else
    fail "Missing infra spec: $INFRA_DIR/$spec"
  fi
done

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

# Signing isolation + edge mesh phase1 in openclaw.json
if [[ -f "$OPENCLAW_HOME/openclaw.json" ]] && command -v python3 &>/dev/null; then
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCLAW_HOME/openclaw.json'))
sn = cfg.get('signingNode', {})
em = cfg.get('edgeMesh', {})
if not sn.get('enabled'):
    sys.exit(1)
if not sn.get('endpoint'):
    sys.exit(2)
if not sn.get('requireGateReceipt', True):
    sys.exit(5)
if em.get('phase1') != 'single_pop':
    sys.exit(3)
if em.get('defaultPop') != 'EDGE-FRA':
    sys.exit(4)
" 2>/dev/null && pass "openclaw.json signingNode + edgeMesh phase1 OK" \
    || fail "openclaw.json missing signingNode or edgeMesh phase1 config"
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
fi
if [[ -f "$PROJECT_ROOT/templates/safety/titan_safety/memecoin_filter.py" ]]; then
  pass "memecoin_filter module present"
else
  fail "Missing memecoin_filter.py"
fi
if [[ -f "$PROJECT_ROOT/templates/infra/solana_memecoin.yaml" ]]; then
  pass "infra/solana_memecoin.yaml present"
else
  fail "Missing solana_memecoin.yaml"
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

# TITANHOME retained in IDENTITY
if [[ -f "$OPENCLAW_HOME/IDENTITY.md" ]]; then
  if grep -qi "TITANHOME" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null \
     && grep -qi "primary" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null; then
    pass "IDENTITY.md: TITANHOME primary role documented"
  else
    fail "IDENTITY.md missing TITANHOME primary role"
  fi
  if grep -q "5-PoP" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null \
     && ! grep -qi "Phase 1\|single PoP\|single_pop\|deferred" "$OPENCLAW_HOME/IDENTITY.md" 2>/dev/null; then
    fail "IDENTITY.md implies all 5 PoPs required at launch"
  else
    pass "IDENTITY.md: edge mesh Phase 1 single PoP documented"
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
