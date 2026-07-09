#!/usr/bin/env bash
# Kill Tier 3 / off-peak GPU jobs during market hours (FORGE heartbeat)
set -euo pipefail

SCHEDULE="${1:-$HOME/.openclaw/infra/gpu_schedule.yaml}"
if [[ ! -f "$SCHEDULE" ]]; then
  echo "missing gpu_schedule.yaml" >&2
  exit 1
fi

FORBIDDEN_PATTERNS=(
  "llama-server.*30003"
  "llama-server.*30005"
  "cuevm"
  "monte_carlo"
  "skill_evolution"
)

hour_utc=$(date -u +%H)
# Market hours 00-23 UTC per gpu_schedule — Tier 3 forbidden always during trading_window
in_market=1

if [[ "$in_market" -eq 1 ]]; then
  for pat in "${FORBIDDEN_PATTERNS[@]}"; do
    pids=$(pgrep -af "$pat" 2>/dev/null | awk '{print $1}' || true)
    if [[ -n "$pids" ]]; then
      echo "[forge] killing off-peak job matching $pat: $pids"
      kill -TERM $pids 2>/dev/null || true
    fi
  done
fi
