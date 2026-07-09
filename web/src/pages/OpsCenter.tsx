import { PageHeader, Card, Tag, Metric } from "@/components/ui";
import { lanes, portfolio } from "@/lib/data";

export function OpsCenter() {
  return (
    <>
      <PageHeader
        title="Ops Center"
        subtitle="Live execution ops: reconciliation, TCA lanes, allocator concentration, and signing gate."
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Capital profile" value={portfolio.capitalProfile.toUpperCase()} />
        <Metric label="Regime" value={portfolio.regime} />
        <Metric label="Max active pipelines" value="4" delta="allocator cap" />
        <Metric label="Gate receipt TTL" value="30s" delta="signing_node" />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Reconciliation">
          <p className="muted small" style={{ marginTop: 0 }}>
            Believed vs DEX / on-chain. Mock adapter banned when capital_profile=live. Strict DEX-only (R02 / R46).
          </p>
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Venue</th>
                  <th>Believed</th>
                  <th>Actual</th>
                  <th>Δ USD</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>uniswap / curve</td>
                  <td>$6,200</td>
                  <td>$6,198</td>
                  <td>
                    <Tag kind="healthy">−2.00</Tag>
                  </td>
                </tr>
                <tr>
                  <td>hyperliquid DEX</td>
                  <td>$3,890</td>
                  <td>$3,890</td>
                  <td>
                    <Tag kind="healthy">0.00</Tag>
                  </td>
                </tr>
                <tr>
                  <td>solana / jito</td>
                  <td>$420</td>
                  <td>$418</td>
                  <td>
                    <Tag kind="watch">−2.00</Tag>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Signing node pre-sign gates">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
            <li>Mock-adapter ban (live)</li>
            <li>Reconciliation :19002</li>
            <li>Risk kernel :19001</li>
            <li>Issue X-Titan-Gate-Receipt</li>
            <li>POST /v1/sign with receipt ≤30s</li>
          </ol>
          <p className="mono small" style={{ marginTop: 14 }}>
            endpoint · http://127.0.0.1:19010
          </p>
        </Card>
      </div>

      <Card title="TCA → allocator profit loop">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Lane</th>
                <th>Net bps</th>
                <th>Sample</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {lanes.map((l) => (
                <tr key={l.id}>
                  <td>
                    {l.id} · {l.name}
                  </td>
                  <td>{l.netBps.toFixed(1)}</td>
                  <td>{l.trades}</td>
                  <td>
                    {l.health === "BLEEDING" ? (
                      <Tag kind="bleeding">AUTO DEFUND</Tag>
                    ) : l.health === "WATCH" ? (
                      <Tag kind="watch">HOLD SIZE</Tag>
                    ) : (
                      <Tag kind="healthy">FUND</Tag>
                    )}
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
