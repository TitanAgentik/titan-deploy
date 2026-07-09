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

  # Bootstrap files (9)
  for f in SOUL.md AGENTS.md MEMORY.md USER.md TOOLS.md IDENTITY.md HEARTBEAT.md BOOTSTRAP.md; do
    cp "$OUTPUT/bootstrap/$f" "$OPENCLAW_HOME/$f"
    log "Installed $OPENCLAW_HOME/$f"
  done

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
