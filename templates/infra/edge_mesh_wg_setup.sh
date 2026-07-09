#!/usr/bin/env bash
# Provision WireGuard peers for full 5-PoP mesh from TITANHOME
# Operator: fill public keys + endpoints in ~/.openclaw/infra/wg_peers.env first
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
PEERS="${OPENCLAW_HOME}/infra/wg_peers.env"
MESH="${OPENCLAW_HOME}/infra/edge_mesh.yaml"

echo "=== TITAN 5-PoP WireGuard mesh helper ==="
echo "Hub: titanhome 10.0.10.1"
echo "Config: $MESH"

if [[ ! -f "$MESH" ]]; then
  echo "Run ./deploy.sh first" >&2
  exit 1
fi

python3 - <<'PY'
import yaml, os
from pathlib import Path
mesh = yaml.safe_load(Path(os.environ["MESH"]).read_text())
for pop_id, cfg in sorted((mesh.get("pops") or {}).items()):
    ip = cfg.get("wireguard_ip", "?")
    region = cfg.get("region", "?")
    print(f"  {pop_id:10} {ip:16} {region}")
PY

cat <<'EOF'

Next steps (operator):
1. Copy templates/infra/wg_peers.env.example → ~/.openclaw/infra/wg_peers.env
2. On each PoP: install wireguard, set wg0 to assigned 10.0.10.10x/24
3. On each PoP: POP=EDGE-XXX bash ~/.openclaw/infra/edge_pop_bootstrap.sh
4. From home: ping 10.0.10.100-104; curl http://10.0.10.101:19100/health
5. titan-safety edge route --venue hyperliquid --strategy P29
6. FORGE records RTT → memory/infra/rtt.jsonl

EOF
