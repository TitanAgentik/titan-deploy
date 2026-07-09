import { PageHeader, Card, Metric, Tag } from "@/components/ui";
import { circuitBreakers, drawdownPolicy, latencyBudget, portfolio } from "@/lib/data";

export function Risk() {
  return (
    <>
      <PageHeader
        title="Risk & Circuit Breakers"
        subtitle="GUARDIAN + out-of-process risk kernel (:19001) and portfolio risk (:19004). Drawdown tiers notify-only — trading continues; velocity breakers still halt."
      />
      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Drawdown" value={`${portfolio.drawdownPct}%`} delta="notify-only" />
        <Metric label="Regime" value={portfolio.regime} />
        <Metric label="Kill switch" value={portfolio.killActive ? "ACTIVE" : "CLEAR"} />
        <Metric label="DMS heartbeat" value={`${portfolio.dmsHoursSinceHeartbeat}h`} delta="derisk 48h / flatten 72h" />
      </div>
      <div className="grid grid-2">
        <Card title="5-tier drawdown — HERALD notify only">
          <p className="muted small" style={{ marginTop: 0 }}>
            {drawdownPolicy.note}
          </p>
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
                      <Tag kind={portfolio.drawdownPct >= cb.pct ? "watch" : "healthy"}>
                        {portfolio.drawdownPct >= cb.pct ? "NOTIFIED" : cb.state}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            Volatile exempt: {drawdownPolicy.volatileExemptPipelines.join(", ")} — lane-local CBs only
          </p>
        </Card>
        <Card title="Pre-trade gates">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>Autonomous BFT 2-of-3 above 1% equity (AUGUR/PREDATOR/ATLAS)</li>
            <li>Confidence ≥0.70 full · 0.50–0.69 reduced · &lt;0.30 reject</li>
            <li>Hot path: <span className="mono">POST /v1/fast_validate</span> ≤{latencyBudget.hotPathGateP95Ms}ms p95</li>
            <li>Flash-loan live → promotion YES + typed_data signing</li>
            <li>ExecutionGate: recon → kernel → gate receipt → signing_node</li>
            <li>Velocity: ${drawdownPolicy.velocityHalt60s}/60s · ${drawdownPolicy.velocityHalt15m}/15m → HALT</li>
          </ol>
        </Card>
      </div>
    </>
  );
}
