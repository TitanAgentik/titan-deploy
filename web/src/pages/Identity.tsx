import { PageHeader, Card, Tag } from "@/components/ui";
import { autonomyMatrix } from "@/lib/data";

export function Identity() {
  return (
    <>
      <PageHeader
        title="Identity"
        subtitle="Operator + system identity — SOUL / IDENTITY bootstrap, bounded autonomy matrix, signing isolation."
      />

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Operator">
          <div className="mono" style={{ fontSize: 20 }}>
            Hyperion
          </div>
          <p className="muted small">Primary operator · Telegram primary on EDGE-FRA · Trezor Safe 7 sweeps</p>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Tag kind="info">ROLE · OWNER</Tag>
            <Tag kind="healthy">MFA · TPM</Tag>
            <Tag kind="watch">DMS · ARMED</Tag>
          </div>
        </Card>
        <Card title="System persona">
          <div className="mono" style={{ fontSize: 20 }}>
            TITAN / OpenClaw + Hermes
          </div>
          <p className="muted small">
            Capital-preservation-first. No closed/cloud models on live path. Quantum agents DORMANT.
          </p>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Tag kind="healthy">23 AGENTS</Tag>
            <Tag kind="info">47 PIPELINES</Tag>
            <Tag kind="neutral">CLASSICAL ONLY</Tag>
          </div>
        </Card>
      </div>

      <Card title="Bounded autonomy matrix (enforced)">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Action</th>
                <th>Auto-execute</th>
                <th>Human YES</th>
              </tr>
            </thead>
            <tbody>
              {autonomyMatrix.map((row) => (
                <tr key={row.action}>
                  <td>{row.action}</td>
                  <td>
                    <Tag kind={row.auto ? "healthy" : "neutral"}>{row.auto ? "YES" : "—"}</Tag>
                  </td>
                  <td>
                    <Tag kind={!row.auto ? "watch" : "neutral"}>
                      {row.note ?? (!row.auto ? "YES" : "—")}
                    </Tag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
