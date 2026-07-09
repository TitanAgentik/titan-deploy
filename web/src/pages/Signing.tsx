import { PageHeader, Card, Tag, Metric } from "@/components/ui";
import { signingAudit } from "@/lib/data";

export function Signing() {
  return (
    <>
      <PageHeader
        title="Signing Node"
        subtitle="Isolated signing at :19010 — refuses POST /v1/sign without fresh X-Titan-Gate-Receipt (max 30s)."
      />
      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Endpoint" value=":19010" />
        <Metric label="Receipt TTL" value="30s" />
        <Metric label="Blind sign" value="REJECTED" />
        <Metric label="Live signer" value="REQUIRED" delta="capital_profile=live" />
      </div>
      <div className="grid grid-2">
        <Card title="Pre-sign gates">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>guardian_risk_validation</li>
            <li>execution_gate_allow_receipt</li>
            <li>risk_kernel_pre_trade</li>
            <li>tenderly_simulation (bridges)</li>
            <li>eip712_typed_data_only</li>
          </ol>
          <p className="muted small" style={{ marginTop: 12 }}>
            On compromise: halt_all_signing · CB_KEYS_SIGNING_ENV_COMPROMISED · file flag
            SIGNING_HALTED
          </p>
        </Card>
        <Card title="Audit (recent)">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Code</th>
                  <th>Trade</th>
                </tr>
              </thead>
              <tbody>
                {signingAudit.map((r) => (
                  <tr key={r.ts + r.code}>
                    <td>{r.ts.slice(11, 19)}</td>
                    <td>
                      <Tag
                        kind={
                          r.action === "allow"
                            ? "healthy"
                            : r.action === "halt"
                              ? "bleeding"
                              : "watch"
                        }
                      >
                        {r.action}
                      </Tag>
                    </td>
                    <td>{r.code}</td>
                    <td>{r.trade}</td>
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
