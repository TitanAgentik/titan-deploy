import { PageHeader, Card, Metric, Tag } from "@/components/ui";
import { circuitBreakers, portfolio } from "@/lib/data";

export function Risk() {
  return (
    <>
      <PageHeader
        title="Risk & Circuit Breakers"
        subtitle="GUARDIAN + out-of-process risk kernel (:19001) and portfolio risk (:19004). Agent votes are advisory; DENY is authoritative."
      />
      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Drawdown" value={`${portfolio.drawdownPct}%`} />
        <Metric label="Regime" value={portfolio.regime} />
        <Metric label="Kill switch" value={portfolio.killActive ? "ACTIVE" : "CLEAR"} />
        <Metric label="DMS heartbeat" value={`${portfolio.dmsHoursSinceHeartbeat}h`} delta="derisk 48h / flatten 72h" />
      </div>
      <div className="grid grid-2">
        <Card title="5-tier drawdown circuit breakers">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Tier</th>
                  <th>Action</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {circuitBreakers.map((cb) => (
                  <tr key={cb.pct}>
                    <td>{cb.pct}%</td>
                    <td style={{ fontFamily: "var(--font)" }}>{cb.action}</td>
                    <td>
                      <Tag kind={portfolio.drawdownPct >= cb.pct ? "bleeding" : "healthy"}>
                        {portfolio.drawdownPct >= cb.pct ? "TRIGGERED" : cb.state}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Pre-trade gates">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>Confidence ≥0.70 full size; 0.50–0.69 sized; &lt;0.30 reject</li>
            <li>Min 3 independent signals (R17)</li>
            <li>Hard stop-loss on every position (R16)</li>
            <li>% equity sizing · progressive Kelly (R41)</li>
            <li>ExecutionGate: recon → kernel → gate receipt</li>
            <li>Trades &gt;1% equity → human YES</li>
          </ol>
        </Card>
      </div>
    </>
  );
}
