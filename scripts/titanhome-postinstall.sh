#!/usr/bin/env bash
# TITANHOME post-Ubuntu verification and base packages
# Run on TITANHOME as hyperion after first boot + NVIDIA drivers

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC}: $*"; }
fail() { echo -e "${RED}FAIL${NC}: $*"; FAILED=1; }
warn() { echo -e "${YELLOW}WARN${NC}: $*"; }

FAILED=0

echo "=== TITANHOME Post-Install Verification ==="
echo "Hostname: $(hostname)"
echo "Date: $(date -Iseconds)"
echo

# CPU
if lscpu | grep -qi "9995WX\|Threadripper PRO"; then
  pass "CPU: Threadripper PRO detected"
else
  warn "CPU: expected 9995WX — check lscpu"
  lscpu | grep "Model name" || true
fi

CORES=$(nproc)
if [[ "$CORES" -ge 96 ]]; then
  pass "CPU threads: $CORES (expected ~192 with SMT)"
else
  warn "CPU threads: $CORES (expected 192 with SMT enabled in BIOS)"
fi

# RAM
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [[ "$RAM_GB" -ge 480 ]]; then
  pass "RAM: ${RAM_GB} GiB total"
else
  fail "RAM: ${RAM_GB} GiB — expected ~512GB (check BIOS EXPO + DIMM seating)"
fi

# GPU
if command -v nvidia-smi &>/dev/null; then
  GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
  if [[ "$GPU_COUNT" -ge 2 ]]; then
    pass "GPU: $GPU_COUNT NVIDIA devices"
    nvidia-smi -L
  else
    fail "GPU: only $GPU_COUNT detected — expected 2× RTX PRO 6000 (check PCIe slots, power cables)"
    nvidia-smi -L 2>/dev/null || true
  fi
else
  fail "nvidia-smi not found — install drivers: sudo ubuntu-drivers install"
fi

# Storage
if lsblk -d -o NAME,SIZE,MODEL | grep -qi micron; then
  pass "Boot NVMe: Micron detected"
else
  warn "Micron 7500 not found in lsblk — verify boot drive"
fi
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL

# TPM
if [[ -e /dev/tpm0 ]] || [[ -e /dev/tpmrm0 ]]; then
  pass "TPM device present"
else
  warn "TPM not visible — enable in BIOS, check TPM-SPI module"
fi

# Network
IFACE=$(ip -br link | awk '$2=="UP" && $1!="lo"{print $1; exit}')
if [[ -n "$IFACE" ]]; then
  pass "Active interface: $IFACE"
  ip -br addr show "$IFACE"
else
  warn "No Ethernet UP — connect cable before production"
fi

# Base packages for Titan
echo
echo "=== Installing base packages (optional) ==="
PACKAGES=(
  build-essential
  git
  curl
  jq
  chrony
  htop
  nvme-cli
  smartmontools
  nut
  python3-pip
  python3-venv
  nodejs
  npm
)

if [[ "${SKIP_INSTALL:-0}" != "1" ]]; then
  sudo apt-get update -qq
  sudo apt-get install -y "${PACKAGES[@]}" 2>/dev/null || warn "Some packages failed — install manually"
  pass "Base packages installed (or attempted)"
else
  warn "SKIP_INSTALL=1 — skipping apt install"
fi

# Data mount points
echo
echo "=== Preparing mount points ==="
sudo mkdir -p /data/openclaw/{memory,logs,ledger,audit}
sudo mkdir -p /data/models
sudo chown -R "$USER:$USER" /data 2>/dev/null || warn "Set /data ownership manually if needed"

if ! grep -q "/data" /etc/fstab 2>/dev/null; then
  warn "Mount WD SN8100 drives to /data and /fast — see titanhome_ubuntu_install.md"
fi

# Infra spec reminder
echo
echo "=== Next steps ==="
echo "1. Set static IP: /etc/netplan/01-titanhome.yaml → 192.168.10.10"
echo "2. See: ~/.openclaw/infra/titanhome_bios_checklist.md (after deploy)"
echo "3. cd titan-deploy && ./deploy.sh && ./verify.sh"
echo "4. Enable systemd user services (risk kernel, llama-server tiers)"

echo
if [[ "$FAILED" -eq 0 ]]; then
  echo -e "${GREEN}=== TITANHOME hardware check PASSED ===${NC}"
  exit 0
else
  echo -e "${RED}=== TITANHOME hardware check FAILED — fix items above ===${NC}"
  exit 1
fi