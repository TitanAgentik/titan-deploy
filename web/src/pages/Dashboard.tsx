import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle } from "lucide-react";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { equitySeries, lanes, portfolio, promotions, services } from "@/lib/data";

export function Dashboard() {
  return (
    <>
      <PageHeader
        title="Portfolio Dashboard"
        subtitle="Institutional overview of equity, lane health, circuit breakers, and promotion gates. Demo data until safety services are live."
        actions={
          <>
            <Btn variant="ghost">Export CSV</Btn>
            <Btn variant="primary">Refresh</Btn>
          </>
        }
      />

      {portfolio.evolutionFrozen ? (
        <div className="alert-banner">
          <AlertTriangle size={16} />
          Evolution freeze active — DGM-H / GEPA / skill promotions to live are denied until unfrozen.
        </div>
      ) : null}

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric
          label="Equity"
          value={`$${portfolio.equityUsd.toLocaleString()}`}
          delta={`+$${portfolio.weeklyPnlUsd} WTD`}
          deltaDir="up"
        />
        <Metric label="Available" value={`$${portfolio.availableUsd.toLocaleString()}`} />
        <Metric
          label="Deposits (ledger)"
          value={`$${portfolio.depositedUsd.toLocaleString()}`}
          delta="≠ trading PnL"
        />
        <Metric
          label="Drawdown"
          value={`${portfolio.drawdownPct}%`}
          delta="CB tiers 2/5/8/10/12%"
          deltaDir={portfolio.drawdownPct > 2 ? "down" : "up"}
        />
      </div>

      <div className="split" style={{ marginBottom: 14 }}>
        <Card title="Equity curve (7d)">
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <AreaChart data={equitySeries}>
                <defs>
                  <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2dd4a8" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#2dd4a8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#243044" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#5c6b80" fontSize={11} />
                <YAxis stroke="#5c6b80" fontSize={11} domain={["dataMin - 200", "dataMax + 200"]} />
                <Tooltip
                  contentStyle={{ background: "#121923", border: "1px solid #243044", borderRadius: 8 }}
                />
                <Area type="monotone" dataKey="equity" stroke="#2dd4a8" fill="url(#eq)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Safety services">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Port</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {services.map((s) => (
                  <tr key={s.name}>
                    <td>{s.name}</td>
                    <td>:{s.port}</td>
                    <td>
                      <Tag kind={s.ok ? "healthy" : "bleeding"}>{s.ok ? "UP" : "DOWN"}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="Funded lanes (≤4 concentration)">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Lane</th>
                  <th>Alloc</th>
                  <th>Net bps</th>
                  <th>Trades</th>
                  <th>Health</th>
                </tr>
              </thead>
              <tbody>
                {lanes.map((l) => (
                  <tr key={l.id}>
                    <td>
                      {l.id} · {l.name}
                    </td>
                    <td>${l.allocation.toLocaleString()}</td>
                    <td>{l.netBps.toFixed(1)}</td>
                    <td>{l.trades}</td>
                    <td>
                      <Tag
                        kind={
                          l.health === "HEALTHY" ? "healthy" : l.health === "WATCH" ? "watch" : "bleeding"
                        }
                      >
                        {l.health}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Promotion queue">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Strategy</th>
                  <th>Phase</th>
                  <th>Status</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {promotions.map((p) => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td>{p.strategy}</td>
                    <td>{p.phase}/6</td>
                    <td>
                      <Tag kind={p.status.includes("PENDING") ? "watch" : "info"}>{p.status}</Tag>
                    </td>
                    <td>{p.score.toFixed(2)}</td>
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
