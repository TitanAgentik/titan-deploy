import { useState } from "react";
import { PageHeader, Card, Btn, Tag } from "@/components/ui";

export function Settings() {
  const [bind, setBind] = useState("0.0.0.0");
  const [token, setToken] = useState("");

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Remote access, auth, and cockpit connectivity. Prefer Tailscale / SSH tunnel — never expose unsigned admin UI publicly."
      />

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Remote access">
          <div className="form-row">
            <div className="field" style={{ flex: 1 }}>
              <label>Bind</label>
              <select value={bind} onChange={(e) => setBind(e.target.value)}>
                <option value="127.0.0.1">127.0.0.1 (local only)</option>
                <option value="0.0.0.0">0.0.0.0 (LAN / reverse proxy)</option>
              </select>
            </div>
            <div className="field">
              <label>Port</label>
              <input defaultValue="5173" />
            </div>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>
            Anywhere access: Tailscale Serve, Cloudflare Tunnel, or{" "}
            <span className="kbd">ssh -L 5173:127.0.0.1:5173</span>. OpenClaw Control UI pattern —
            token in sessionStorage, strip from URL.
          </p>
          <div style={{ marginTop: 10 }}>
            <Tag kind="watch">DEMO · no gateway auth yet</Tag>
          </div>
        </Card>

        <Card title="Control-plane HMAC">
          <div className="field">
            <label>Operator token (session)</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="X-Titan-Auth secret — not persisted to disk"
            />
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            <Btn variant="primary">Save session</Btn>
            <Btn
              variant="ghost"
              onClick={() => {
                setToken("");
              }}
            >
              Clear
            </Btn>
          </div>
        </Card>
      </div>

      <Card title="API proxy map (Vite)">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>UI path</th>
                <th>Upstream</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["/api/risk", ":19001"],
                ["/api/recon", ":19002"],
                ["/api/status", ":19003"],
                ["/api/portfolio", ":19004"],
                ["/api/dms", ":19005"],
                ["/api/allocator", ":19006"],
                ["/api/tca", ":19007"],
                ["/api/sign", ":19010"],
              ].map(([a, b]) => (
                <tr key={a}>
                  <td>{a}</td>
                  <td>http://127.0.0.1{b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
