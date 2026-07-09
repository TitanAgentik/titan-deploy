#!/usr/bin/env bash
# Bootstrap TRENCH-OPS edge worker on a PoP VM (stateless, no LLM)
# Run on each EDGE-* node after WireGuard is up.
# Usage: POP=EDGE-TKY bash edge_pop_bootstrap.sh

set -euo pipefail

POP="${POP:-EDGE-FRA}"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
MESH="$OPENCLAW_HOME/infra/edge_mesh.yaml"
WORKER_PORT="${WORKER_PORT:-19100}"
export POP MESH

echo "=== TITAN edge bootstrap: $POP ==="

if [[ ! -f "$MESH" ]]; then
  echo "Missing $MESH — run deploy.sh on TITANHOME first" >&2
  exit 1
fi

WG_IP=$(python3 - <<PY
import yaml, os
from pathlib import Path
p = Path(os.environ["MESH"])
m = yaml.safe_load(p.read_text())
pop = m.get("pops", {}).get(os.environ["POP"], {})
print(pop.get("wireguard_ip", ""))
PY
)

if [[ -z "$WG_IP" ]]; then
  echo "Unknown POP $POP in edge_mesh.yaml" >&2
  exit 1
fi

echo "PoP: $POP  WireGuard: $WG_IP  worker: :$WORKER_PORT"

sudo apt-get update -qq
sudo apt-get install -y curl jq chrony wireguard-tools python3 python3-pip 2>/dev/null || true

sudo mkdir -p /etc/titan-edge
sudo tee /etc/titan-edge/pop.env >/dev/null <<EOF
TITAN_EDGE_POP=$POP
TITAN_EDGE_WG_IP=$WG_IP
TITAN_EDGE_WORKER_PORT=$WORKER_PORT
TITAN_HOME_WG=10.0.10.1
NATS_URL=nats://10.0.10.1:4222
EOF

# Minimal health endpoint placeholder until full trench-ops worker binary is deployed
sudo mkdir -p /opt/titan-edge
sudo tee /opt/titan-edge/health_server.py >/dev/null <<'PY'
#!/usr/bin/env python3
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("TITAN_EDGE_WORKER_PORT", "19100"))
POP = os.environ.get("TITAN_EDGE_POP", "UNKNOWN")

class H(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path.startswith("/health"):
            body = json.dumps({"status": "ok", "pop": POP, "role": "trench_ops_edge"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
PY
sudo chmod +x /opt/titan-edge/health_server.py

sudo tee /etc/systemd/system/trench-ops-edge.service >/dev/null <<EOF
[Unit]
Description=TITAN TRENCH-OPS Edge Worker ($POP)
After=network-online.target wg-quick@wg0.service
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/titan-edge/pop.env
ExecStart=/usr/bin/python3 /opt/titan-edge/health_server.py
Restart=on-failure
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now trench-ops-edge.service

echo "OK: trench-ops-edge.service on :$WORKER_PORT"
echo "From TITANHOME: curl -s http://${WG_IP}:${WORKER_PORT}/health"
echo "Route check: titan-safety edge route --venue jito --strategy P22"
