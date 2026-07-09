#!/usr/bin/env bash
# TITANHOME one-shot latency tuning — run after deploy as root once
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
INFRA="$OPENCLAW_HOME/infra"

echo "=== TITAN latency tune ==="

if [[ -f "$INFRA/sysctl/99-openclaw-performance.conf" ]]; then
  sudo cp "$INFRA/sysctl/99-openclaw-performance.conf" /etc/sysctl.d/
  sudo sysctl --system >/dev/null 2>&1 || sudo sysctl -p /etc/sysctl.d/99-openclaw-performance.conf
  echo "OK: sysctl applied"
fi

if [[ -f "$INFRA/chrony-gpsdo.conf" ]] && [[ -d /etc/chrony/chrony.conf.d ]]; then
  sudo cp "$INFRA/chrony-gpsdo.conf" /etc/chrony/chrony.conf.d/titan-gpsdo.conf
  sudo systemctl restart chrony 2>/dev/null || true
  echo "OK: chrony GPSDO fragment installed"
fi

# tmpfs backtest arena + hugepages hint (off-peak DARWIN_GODEL)
if ! mountpoint -q /dev/shm/backtest_arena 2>/dev/null; then
  sudo mkdir -p /dev/shm/backtest_arena
  sudo mount -t tmpfs -o size=200G,huge=always tmpfs /dev/shm/backtest_arena 2>/dev/null \
    || sudo mount -t tmpfs -o size=200G tmpfs /dev/shm/backtest_arena 2>/dev/null \
    || echo "WARN: could not mount backtest_arena tmpfs"
fi

# IRQ balance off for dedicated trading host (optional — reduces jitter)
if [[ -f /etc/default/irqbalance ]]; then
  sudo sed -i 's/^ENABLED=.*/ENABLED="0"/' /etc/default/irqbalance 2>/dev/null || true
  sudo systemctl stop irqbalance 2>/dev/null || true
fi

chmod +x "$INFRA/forge_gpu_schedule_enforce.sh" 2>/dev/null || true
echo "Done — verify: chronyc tracking, sysctl net.ipv4.tcp_low_latency"
