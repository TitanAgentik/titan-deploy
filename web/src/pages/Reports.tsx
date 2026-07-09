import { Link } from "react-router-dom";
import { PageHeader, Card, Btn, Metric, Tag } from "@/components/ui";
import { formatPnl, lanes, pnl, portfolio, capitalLedger } from "@/lib/data";

export function Reports() {
  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Crypto reporting — PnL attribution, TCA, drawdown, and weekly sweep readiness."
        actions={
          <>
            <Link className="btn" to="/pnl">
              PnL detail
            </Link>
            <Btn variant="ghost">PDF</Btn>
            <Btn variant="primary">Generate pack</Btn>
          </>
        }
      />
      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="WTD PnL" value={formatPnl(pnl.weeklyUsd)} deltaDir="up" delta="trading" />
        <Metric label="MTD PnL" value={formatPnl(pnl.mtdUsd)} deltaDir="up" delta="trading" />
        <Metric label="Deposits YTD" value={`$${portfolio.depositedUsd.toLocaleString()}`} delta="ledger ≠ PnL" />
        <Metric
          label="Sweep threshold"
          value={`$${capitalLedger.sweepThresholdUsd.toLocaleString()}`}
          delta={
            capitalLedger.growthPhase
              ? `${Math.round((portfolio.equityUsd / capitalLedger.sweepThresholdUsd) * 100)}% to unlock`
              : "HARVEST · sweep armed"
          }
        />
      </div>
      <Card title="PnL by lane (WTD)" style={{ marginBottom: 14 }}>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Lane</th>
                <th>WTD PnL</th>
                <th>MTD PnL</th>
                <th>Net bps</th>
                <th>Health</th>
              </tr>
            </thead>
            <tbody>
              {lanes.map((l) => (
                <tr key={l.id}>
                  <td>
                    {l.id} · {l.name}
                  </td>
                  <td>
                    <Tag kind={l.pnlWtdUsd >= 0 ? "healthy" : "bleeding"}>
                      {formatPnl(l.pnlWtdUsd)}
                    </Tag>
                  </td>
                  <td className="mono">{formatPnl(l.pnlMtdUsd)}</td>
                  <td>{l.netBps.toFixed(1)}</td>
                  <td>{l.health}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <div className="grid grid-2">
        <Card title="Weekly profit sweep policy">
          <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>Below $15K equity → 100% reinvest (no sweep)</li>
            <li>At/above $15K → 20% of weekly profit → Trezor Safe 7 every 7 days</li>
            <li>Injections continue regardless of sweep</li>
            <li>Do not confuse deposits with profit attribution</li>
          </ul>
        </Card>
        <Card title="Compliance pack contents">
          <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>decision_log.jsonl excerpt (last 100)</li>
            <li>Kill / flatten / promotion audit</li>
            <li>TCA by lane + allocator exclusions</li>
            <li>Gate receipt + signing audit hashes</li>
          </ul>
        </Card>
      </div>
    </>
  );
}
