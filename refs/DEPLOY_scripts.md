# §DEPLOY_scripts.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `DEPLOY_scripts.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Deploy / verify / build entrypoints that TITAN referenced as §DEPLOY_scripts.md.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Commands

```bash
python3 scripts/build.py          # normalize → reconcile → extract → sync workspace
./deploy.sh                       # build + install to ~/.openclaw and ~/.hermes
./deploy.sh --start-services      # also enable/start titan-* systemd units
./deploy.sh --verify              # bootstrap limits + pytest + chaos harness
```

## deploy.sh

```bash
#!/usr/bin/env bash
# TITAN OpenClaw + Hermes one-command deploy
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
OUTPUT="$PROJECT_ROOT/output"
SOURCE="${SOURCE:-$PROJECT_ROOT/source/TITAN.md}"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DRY_RUN=0
INSTALL_PACKAGES=0
INSTALL_SYSTEMD=0
START_SERVICES=0
DO_VERIFY=0
DO_BUILD=0

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [OPTIONS]

Options:
  --source PATH       TITAN.md source (default: source/TITAN.md)
  --dry-run           Build and show what would be installed
  --install-packages  Run npm/pip install for openclaw and hermes-agent
  --systemd           Install systemd unit files and enable/start safety services
  --verify            Verify deployed bootstrap limits and file presence
  --build             Build only (no install)
  --start-services    Enable and start titan-* safety systemd units (implies --systemd)
  -h, --help          Show this help

Examples:
  ./deploy.sh --source ~/Downloads/TITAN.md
  ./deploy.sh --dry-run
  ./deploy.sh --verify
EOF
}

log() { echo "[titan-deploy] $*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; DO_BUILD=1; shift ;;
    --install-packages) INSTALL_PACKAGES=1; shift ;;
    --systemd) INSTALL_SYSTEMD=1; shift ;;
    --start-services) INSTALL_SYSTEMD=1; START_SERVICES=1; shift ;;
    --verify) DO_VERIFY=1; shift ;;
    --build) DO_BUILD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# Default action: build + install if no flags
if [[ $DO_VERIFY -eq 0 && $DO_BUILD -eq 0 ]]; then
  DO_BUILD=1
fi

run_build() {
  log "Building from $SOURCE"
  python3 "$PROJECT_ROOT/scripts/build.py" --source "$SOURCE"
}

install_packages() {
  if [[ $DRY_RUN -eq 1 ]]; then
    log "[dry-run] would run: npm install -g openclaw@latest"
    log "[dry-run] would run: pip install hermes-agent"
    return
  fi
  if command -v npm &>/dev/null; then
    log "Installing openclaw@latest..."
    npm install -g openclaw@latest || log "WARN: npm install openclaw failed (may need network)"
  else
    log "WARN: npm not found — skip openclaw install"
  fi
  if command -v pip &>/dev/null || command -v pip3 &>/dev/null; then
    local PIP="pip3"
    command -v pip3 &>/dev/null || PIP="pip"
    log "Installing hermes-agent..."
    $PIP install hermes-agent || log "WARN: pip install hermes-agent failed (may need network)"
  else
    log "WARN: pip not found — skip hermes-agent install"
  fi
}

install_files() {
  local dirs=(
    "$OPENCLAW_HOME"
    "$OPENCLAW_HOME/workspace/skills"
    "$OPENCLAW_HOME/workspace/telegram"
    "$OPENCLAW_HOME/memory"
    "$OPENCLAW_HOME/risk_kernel"
    "$OPENCLAW_HOME/safety"
    "$OPENCLAW_HOME/capital"
    "$OPENCLAW_HOME/playbooks"
    "$OPENCLAW_HOME/staging"
    "$HERMES_HOME"
    "$HERMES_HOME/memory"
  )

  if [[ $DRY_RUN -eq 1 ]]; then
    log "[dry-run] Would install to:"
    for d in "${dirs[@]}"; do echo "  $d"; done
    log "[dry-run] Bootstrap files:"
    ls -1 "$OUTPUT/bootstrap/" 2>/dev/null || true
    return
  fi

  for d in "${dirs[@]}"; do mkdir -p "$d"; done

  # Capital state directory (portfolio_state.json created on first deposit)
  mkdir -p "$OPENCLAW_HOME/capital"
  log "Ensured capital dir -> $OPENCLAW_HOME/capital/"

  # OpenClaw workspace bootstrap (docs.openclaw.ai/concepts/agent-workspace)
  # Prefer ~/.openclaw/workspace/; also keep copies at ~/.openclaw/ for legacy TITAN paths
  mkdir -p "$OPENCLAW_HOME/workspace" "$OPENCLAW_HOME/workspace/memory" "$OPENCLAW_HOME/workspace/skills"
  for f in SOUL.md AGENTS.md MEMORY.md USER.md TOOLS.md IDENTITY.md HEARTBEAT.md BOOTSTRAP.md BOOT.md; do
    if [[ -f "$OUTPUT/bootstrap/$f" ]]; then
      cp "$OUTPUT/bootstrap/$f" "$OPENCLAW_HOME/workspace/$f"
      cp "$OUTPUT/bootstrap/$f" "$OPENCLAW_HOME/$f"
      log "Installed workspace/$f (+ legacy $OPENCLAW_HOME/$f)"
    fi
  done
  if [[ -f "$PROJECT_ROOT/workspace/iron-laws.md" ]]; then
    cp "$PROJECT_ROOT/workspace/iron-laws.md" "$OPENCLAW_HOME/workspace/iron-laws.md"
    cp "$PROJECT_ROOT/workspace/iron-laws.md" "$OPENCLAW_HOME/iron-laws.md"
  fi
  # Hermes identity + project context
  if [[ -f "$OUTPUT/bootstrap/SOUL.md" ]]; then
    cp "$OUTPUT/bootstrap/SOUL.md" "$HERMES_HOME/SOUL.md"
    log "Installed $HERMES_HOME/SOUL.md"
  fi
  if [[ -f "$PROJECT_ROOT/.hermes.md" ]]; then
    cp "$PROJECT_ROOT/.hermes.md" "$HERMES_HOME/.hermes.md"
  fi
  # Hermes project AGENTS.md (context) — same content as OpenClaw workspace AGENTS.md
  if [[ -f "$OUTPUT/bootstrap/AGENTS.md" ]]; then
    cp "$OUTPUT/bootstrap/AGENTS.md" "$HERMES_HOME/AGENTS.md"
    # Also place in deploy project root context if Hermes is launched from titan-deploy
    cp "$OUTPUT/bootstrap/AGENTS.md" "$PROJECT_ROOT/AGENTS.md" 2>/dev/null || true
  fi

  # Reconstructed §REF companions (reference only — not bootstrap)
  if [[ -d "$PROJECT_ROOT/refs" ]]; then
    mkdir -p "$OPENCLAW_HOME/refs"
    cp -r "$PROJECT_ROOT/refs/"* "$OPENCLAW_HOME/refs/"
    log "Installed refs/ companions -> $OPENCLAW_HOME/refs/"
  fi
  if [[ -f "$PROJECT_ROOT/configs_detail.md" ]]; then
    cp "$PROJECT_ROOT/configs_detail.md" "$OPENCLAW_HOME/configs_detail.md"
  fi

  cp "$OUTPUT/openclaw.json" "$OPENCLAW_HOME/openclaw.json"
  cp "$OUTPUT/config.yaml" "$HERMES_HOME/config.yaml"

  # Risk kernel policy + safety services
  if [[ -d "$OUTPUT/risk_kernel" ]]; then
    cp -r "$OUTPUT/risk_kernel/"* "$OPENCLAW_HOME/risk_kernel/"
    log "Installed risk_kernel -> $OPENCLAW_HOME/risk_kernel/"
  fi
  if [[ -d "$OUTPUT/safety" ]]; then
    cp -r "$OUTPUT/safety/"* "$OPENCLAW_HOME/safety/"
    log "Installed safety services -> $OPENCLAW_HOME/safety/"
    # CLI wrapper
    mkdir -p "$OPENCLAW_HOME/safety/bin"
    cat > "$OPENCLAW_HOME/safety/bin/titan-safety" <<'CLIOF'
#!/usr/bin/env bash
export PYTHONPATH="${HOME}/.openclaw/safety${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m titan_safety "$@"
CLIOF
    chmod +x "$OPENCLAW_HOME/safety/bin/titan-safety"
    # Install Python deps (prefer project venv)
    if [[ -f "$PROJECT_ROOT/.venv/bin/pip" ]]; then
      "$PROJECT_ROOT/.venv/bin/pip" install -q -r "$OUTPUT/safety/requirements.txt" \
        && log "Installed safety Python deps via project venv"
    elif [[ -f "$OUTPUT/safety/requirements.txt" ]] && command -v pip3 &>/dev/null; then
      pip3 install --user -q -r "$OUTPUT/safety/requirements.txt" 2>/dev/null \
        || log "WARN: pip install safety requirements failed (use: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)"
    fi
  fi

  # Playbooks + capital stubs
  if [[ -d "$OUTPUT/playbooks" ]]; then
    cp -r "$OUTPUT/playbooks/"* "$OPENCLAW_HOME/playbooks/"
    log "Installed playbooks -> $OPENCLAW_HOME/playbooks/"
  fi
  if [[ -d "$OUTPUT/capital" ]]; then
    cp -r "$OUTPUT/capital/"* "$OPENCLAW_HOME/capital/"
    log "Installed capital stubs -> $OPENCLAW_HOME/capital/"
  fi
  mkdir -p "$OPENCLAW_HOME/staging"
  log "Ensured air-gapped staging dir -> $OPENCLAW_HOME/staging/"

  # Skills
  if [[ -d "$OUTPUT/workspace/skills" ]]; then
    # Remove stale active quantum_* dirs (archived under _archived/quantum/)
    for stale in "$OPENCLAW_HOME/workspace/skills"/quantum_*; do
      [[ -d "$stale" ]] && rm -rf "$stale"
    done
    cp -r "$OUTPUT/workspace/skills/"* "$OPENCLAW_HOME/workspace/skills/"
    log "Installed skills -> $OPENCLAW_HOME/workspace/skills/"
  fi

  # Telegram institutional templates
  if [[ -d "$OUTPUT/workspace/telegram" ]]; then
    cp -r "$OUTPUT/workspace/telegram/"* "$OPENCLAW_HOME/workspace/telegram/"
    log "Installed telegram templates -> $OPENCLAW_HOME/workspace/telegram/"
  fi

  # Memory sidecars
  if [[ -d "$OUTPUT/memory" ]]; then
    cp -r "$OUTPUT/memory/"* "$OPENCLAW_HOME/memory/"
    log "Installed memory -> $OPENCLAW_HOME/memory/"
  fi

  # Infra specs (power, signing, GPU schedule)
  if [[ -d "$OUTPUT/infra" ]]; then
    mkdir -p "$OPENCLAW_HOME/infra"
    cp -r "$OUTPUT/infra/"* "$OPENCLAW_HOME/infra/"
    log "Installed infra specs -> $OPENCLAW_HOME/infra/"
  fi

  # Hermes skills symlink
  ln -sfn "$OPENCLAW_HOME/workspace/skills" "$HERMES_HOME/skills"

  # Env template
  if [[ ! -f "$OPENCLAW_HOME/.env" ]]; then
    cat > "$OPENCLAW_HOME/.env" <<'ENVEOF'
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_USER_ID=your-user-id-here
NATS_URL=nats://localhost:4222
ENVEOF
    log "Created $OPENCLAW_HOME/.env template"
  fi

  if [[ $INSTALL_SYSTEMD -eq 1 ]]; then
  local SUDO=""
  if [[ $EUID -ne 0 ]]; then SUDO="sudo"; fi
  $SUDO cp "$OUTPUT/systemd/"*.service /etc/systemd/system/ 2>/dev/null || \
    log "WARN: systemd install requires root; copy manually from output/systemd/"
  $SUDO systemctl daemon-reload 2>/dev/null || true
  if [[ $START_SERVICES -eq 1 ]]; then
    local units=(
      titan-risk-kernel
      titan-reconciliation
      titan-status-aggregator
      titan-portfolio-risk
      titan-dead-mans-switch
      titan-allocator
      titan-tca
      titan-signing-node
    )
    for u in "${units[@]}"; do
      if [[ -f "/etc/systemd/system/${u}.service" ]] || systemctl cat "${u}.service" &>/dev/null; then
        $SUDO systemctl enable --now "${u}.service" 2>/dev/null \
          && log "Started ${u}.service" \
          || log "WARN: could not start ${u}.service"
      else
        log "WARN: missing unit ${u}.service"
      fi
    done
    log "Safety services start attempted. Check: systemctl status titan-risk-kernel"
  else
    log "Systemd units installed. Start with: ./deploy.sh --start-services"
  fi
  fi
}

if [[ $DO_BUILD -eq 1 ]]; then
  run_build
  if [[ $DRY_RUN -eq 0 && $DO_VERIFY -eq 0 ]]; then
    [[ $INSTALL_PACKAGES -eq 1 ]] && install_packages
    install_files
    log "Deploy complete."
    log "Next: edit $OPENCLAW_HOME/.env and run ./deploy.sh --verify"
    log "Then follow $OPENCLAW_HOME/BOOTSTRAP.md checklist"
  elif [[ $DRY_RUN -eq 1 ]]; then
    install_files
    log "Dry-run complete. Artifacts in $OUTPUT"
  fi
fi

if [[ $DO_VERIFY -eq 1 ]]; then
  exec "$PROJECT_ROOT/verify.sh" "$OPENCLAW_HOME" "$HERMES_HOME"
fi
```

## verify.sh (excerpt — full file in repo)

```bash
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

# Skills count
skill_count=$(find "$OPENCLAW_HOME/workspace/skills" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')
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
if [[ -f "$POLICY" ]] && co
# … truncated; see verify.sh in repo root …
```
