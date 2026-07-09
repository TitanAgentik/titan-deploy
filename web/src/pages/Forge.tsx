import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { services } from "@/lib/data";

const INFRA = [
  { host: "TITANHOME", role: "Primary inference + safety", gpu: "2× RTX PRO 6000", status: "healthy" },
  { host: "TITANSPARK", role: "Utility SGLang :30002", gpu: "GB10 128GB", status: "healthy" },
  { host: "EDGE-FRA", role: "Solana-EU / Erigon", gpu: "—", status: "healthy" },
  { host: "EDGE-TKY", role: "Binance / OKX / HL", gpu: "—", status: "watch" },
  { host: "signing_node", role: "Isolated signing :19010", gpu: "—", status: "healthy" },
];

export function Forge() {
  return (
    <>
      <PageHeader
        title="Forge"
        subtitle="Infrastructure health, inference tiers, and edge PoP latency — FORGE agent surface."
        actions={<Btn variant="primary">Run health sweep</Btn>}
      />

      <div className="grid grid-3" style={{ marginBottom: 14 }}>
        <Card title="Tier 1 · :30000">
          <div className="mono" style={{ fontSize: 18 }}>Qwen3-30B FP8</div>
          <p className="muted small">Critical path — signals, risk, TRENCH-OPS</p>
          <div className="progress" style={{ marginTop: 12 }}>
            <span style={{ width: "61%" }} />
          </div>
          <div className="muted small" style={{ marginTop: 6 }}>
            SM util 61%
          </div>
        </Card>
        <Card title="Tier 2 · :30001">
          <div className="mono" style={{ fontSize: 18 }}>Qwen3-Coder-80B</div>
          <p className="muted small">Orchestration · ARCHON / SENTINEL</p>
          <div className="progress" style={{ marginTop: 12 }}>
            <span style={{ width: "42%" }} />
          </div>
          <div className="muted small" style={{ marginTop: 6 }}>
            SM util 42%
          </div>
        </Card>
        <Card title="Tier 3 · off-peak">
          <div className="mono" style={{ fontSize: 18 }}>DeepSeek V4 / GLM-5.2</div>
          <p className="muted small">R&amp;D only — never live critical path</p>
          <div className="progress" style={{ marginTop: 12 }}>
            <span style={{ width: "8%" }} />
          </div>
          <div className="muted small" style={{ marginTop: 6 }}>
            offline / standby
          </div>
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="Hosts">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Host</th>
                  <th>Role</th>
                  <th>GPU</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {INFRA.map((h) => (
                  <tr key={h.host}>
                    <td>{h.host}</td>
                    <td>{h.role}</td>
                    <td>{h.gpu}</td>
                    <td>
                      <Tag kind={h.status === "healthy" ? "healthy" : "watch"}>{h.status}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Safety systemd units">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Unit</th>
                  <th>Port</th>
                  <th>Health</th>
                </tr>
              </thead>
              <tbody>
                {services.map((s) => (
                  <tr key={s.name}>
                    <td>titan-{s.name}.service</td>
                    <td>:{s.port}</td>
                    <td>
                      <Tag kind={s.ok ? "healthy" : "bleeding"}>{s.ok ? "active" : "failed"}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  );
}
