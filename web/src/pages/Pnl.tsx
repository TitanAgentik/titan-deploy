import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { Drawer, ToastStack, useToasts } from "@/components/interactive";
import {
  formatPnl,
  pnl,
  pnlByStrategy,
  pnlBySubStrategy,
  pnlDeltaDir,
  pnlSeries,
  pnlShareOfWtd,
  portfolio,
  recentTradesPnl,
  strategyCategoryLabels,
} from "@/lib/data";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";

type Trade = (typeof recentTradesPnl)[number];
type Strategy = (typeof pnlByStrategy)[number];

const CHART_COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#06b6d4", "#ec4899", "#ef4444"];

export function Pnl() {
  const { toasts, push, dismiss } = useToasts();
  const [selected, setSelected] = useState<Trade | null>(null);
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const {
    draft: pnlPrefs,
    update: updatePnl,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("pnl", { chartMode: "cumulative" as "cumulative" | "daily" });
  const chartMode = pnlPrefs.chartMode;
  const setChartMode = (v: "cumulative" | "daily") => updatePnl({ chartMode: v });

  const chartData =
    chartMode === "cumulative"
      ? pnlSeries.map((d) => ({ t: d.t, value: d.cumulative }))
      : pnlSeries.map((d) => ({ t: d.t, value: d.daily }));

  const strategyChart = useMemo(
    () =>
      [...pnlByStrategy]
        .sort((a, b) => Math.abs(b.wtdUsd) - Math.abs(a.wtdUsd))
        .map((s) => ({
          id: s.id,
          label: `${s.id}`,
          wtd: s.wtdUsd,
          share: pnlShareOfWtd(s.wtdUsd),
        })),
    [],
  );

  const deployedTotal = useMemo(
    () => pnlByStrategy.reduce((n, s) => n + s.allocationUsd, 0),
    [],
  );

  const topContributors = useMemo(
    () => [...pnlByStrategy].sort((a, b) => b.wtdUsd - a.wtdUsd).slice(0, 3),
    [],
  );

  return (
    <>
      <PageHeader
        eyebrow="Trading attribution"
        title="PnL"
        subtitle="DEX-only PnL attribution — TCA (:19007) when live. Deposits excluded."
        actions={
          <>
            <Btn variant="ghost" onClick={() => push("PnL CSV export queued (demo)")}>
              Export
            </Btn>
            <Link className="btn primary" to="/reports">
              Reports pack
            </Link>
          </>
        }
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        onSave={() => {
          save();
          push("Saved locally (cockpit)", "ok");
        }}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric
          label="Trading PnL (all-time)"
          value={formatPnl(pnl.tradingPnlUsd, false)}
          delta={`equity − deposits ($${portfolio.depositedUsd.toLocaleString()})`}
          deltaDir={pnlDeltaDir(pnl.tradingPnlUsd)}
        />
        <Metric
          label="Today"
          value={formatPnl(pnl.dailyUsd)}
          delta={`${pnl.tradesClosed24h} closes · ${topContributors[0]?.id} leads`}
          deltaDir={pnlDeltaDir(pnl.dailyUsd)}
        />
        <Metric
          label="WTD"
          value={formatPnl(pnl.weeklyUsd)}
          delta={`${pnl.netBpsWtd.toFixed(1)} net bps · ${pnlByStrategy.length} strategies`}
          deltaDir={pnlDeltaDir(pnl.weeklyUsd)}
        />
        <Metric
          label="MTD"
          value={formatPnl(pnl.mtdUsd)}
          deltaDir={pnlDeltaDir(pnl.mtdUsd)}
        />
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Realized" value={formatPnl(pnl.realizedUsd, false)} delta="closed" />
        <Metric
          label="Unrealized"
          value={formatPnl(pnl.unrealizedUsd, false)}
          delta="open positions"
          deltaDir={pnlDeltaDir(pnl.unrealizedUsd)}
        />
        <Metric label="Win rate" value={`${pnl.winRatePct}%`} delta="24h closes" />
        <Metric
          label="Fees (24h)"
          value={`$${pnl.feesUsd24h.toFixed(2)}`}
          delta={`avg W ${formatPnl(pnl.avgWinUsd, false)} · L ${formatPnl(pnl.avgLossUsd)}`}
        />
      </div>

      <div className="split" style={{ marginBottom: 14 }}>
        <Card title="Where WTD PnL comes from · by strategy">
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={strategyChart} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                <XAxis type="number" stroke="#7b8798" fontSize={11} tickFormatter={(v) => `$${v}`} />
                <YAxis type="category" dataKey="label" stroke="#7b8798" fontSize={11} width={36} />
                <Tooltip
                  formatter={(v: number, _n, p) => {
                    const row = p?.payload as (typeof strategyChart)[number] | undefined;
                    return [
                      `${formatPnl(v, false)} (${row?.share.toFixed(1)}% of WTD)`,
                      "WTD PnL",
                    ];
                  }}
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid rgba(11,21,40,0.12)",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="wtd" radius={[0, 4, 4, 0]}>
                  {strategyChart.map((d, i) => (
                    <Cell key={d.id} fill={d.wtd >= 0 ? CHART_COLORS[i % CHART_COLORS.length] : "#ef4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
            Top contributor:{" "}
            <strong>
              {topContributors[0]?.id} · {topContributors[0]?.name}
            </strong>{" "}
            ({formatPnl(topContributors[0]?.wtdUsd ?? 0)} ·{" "}
            {pnlShareOfWtd(topContributors[0]?.wtdUsd ?? 0).toFixed(1)}% of WTD) —{" "}
            {topContributors[0]?.revenueSource}
          </p>
        </Card>

        <Card title="Capital deployed · where money sits">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Allocated</th>
                  <th>% deployed</th>
                  <th>Phase</th>
                </tr>
              </thead>
              <tbody>
                {[...pnlByStrategy]
                  .filter((s) => s.allocationUsd > 0)
                  .sort((a, b) => b.allocationUsd - a.allocationUsd)
                  .map((s) => (
                    <tr
                      key={s.id}
                      className="row-click"
                      onClick={() => setStrategy(s)}
                    >
                      <td>
                        {s.id} · {s.name}
                      </td>
                      <td>${s.allocationUsd.toLocaleString()}</td>
                      <td>{((s.allocationUsd / deployedTotal) * 100).toFixed(1)}%</td>
                      <td>
                        <Tag kind={s.phase === "funded" ? "healthy" : s.phase === "paper" ? "watch" : "info"}>
                          {s.phase}
                        </Tag>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
            ${deployedTotal.toLocaleString()} deployed across strategies · $
            {portfolio.availableUsd.toLocaleString()} available · equity $
            {portfolio.equityUsd.toLocaleString()}
          </p>
        </Card>
      </div>

      <div className="split" style={{ marginBottom: 14 }}>
        <Card
          title={chartMode === "cumulative" ? "Cumulative PnL (7d)" : "Daily PnL (7d)"}
          action={
            <div style={{ display: "flex", gap: 6 }}>
              <Btn
                variant={chartMode === "cumulative" ? "primary" : "ghost"}
                onClick={() => setChartMode("cumulative")}
              >
                Cumulative
              </Btn>
              <Btn
                variant={chartMode === "daily" ? "primary" : "ghost"}
                onClick={() => setChartMode("daily")}
              >
                Daily
              </Btn>
            </div>
          }
        >
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              {chartMode === "daily" ? (
                <BarChart data={chartData}>
                  <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                  <XAxis dataKey="t" stroke="#7b8798" fontSize={11} />
                  <YAxis stroke="#7b8798" fontSize={11} />
                  <Tooltip
                    formatter={(v: number) => [formatPnl(v, false), "PnL"]}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid rgba(11,21,40,0.12)",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((d) => (
                      <Cell key={d.t} fill={d.value >= 0 ? "#10b981" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              ) : (
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                  <XAxis dataKey="t" stroke="#7b8798" fontSize={11} />
                  <YAxis stroke="#7b8798" fontSize={11} />
                  <Tooltip
                    formatter={(v: number) => [formatPnl(v, false), "Cumulative"]}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid rgba(11,21,40,0.12)",
                      borderRadius: 8,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#10b981"
                    fill="url(#pnlFill)"
                    strokeWidth={2}
                  />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
            Deposits are not PnL — see{" "}
            <Link to="/capital">Capital &amp; Wallets</Link> for ledger events.
          </p>
        </Card>

        <Card title="P22 Memecoin · sub-strategy split (WTD)">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Sub-strategy</th>
                  <th>WTD PnL</th>
                  <th>24h trades</th>
                  <th>% of P22</th>
                </tr>
              </thead>
              <tbody>
                {pnlBySubStrategy.map((sub) => {
                  const parent = pnlByStrategy.find((s) => s.id === sub.parent)!;
                  return (
                    <tr key={sub.id}>
                      <td className="mono">{sub.name}</td>
                      <td>
                        <Tag kind={sub.wtdUsd >= 0 ? "healthy" : "bleeding"}>
                          {formatPnl(sub.wtdUsd)}
                        </Tag>
                      </td>
                      <td>{sub.trades24h}</td>
                      <td>{((sub.wtdUsd / parent.wtdUsd) * 100).toFixed(0)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
            <Link to="/memecoin">Memecoin Trench</Link> · paper mode · EDGE-FRA
          </p>
        </Card>
      </div>

      <Card title="Strategy attribution · click row for detail" style={{ marginBottom: 14 }}>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Category</th>
                <th>Revenue source</th>
                <th>Today</th>
                <th>WTD PnL</th>
                <th>% WTD</th>
                <th>MTD PnL</th>
                <th>Health</th>
              </tr>
            </thead>
            <tbody>
              {[...pnlByStrategy]
                .sort((a, b) => b.wtdUsd - a.wtdUsd)
                .map((s) => (
                  <tr key={s.id} className="row-click" onClick={() => setStrategy(s)}>
                    <td>
                      {s.id} · {s.name}
                    </td>
                    <td>{strategyCategoryLabels[s.category]}</td>
                    <td className="small muted">{s.revenueSource}</td>
                    <td>
                      <Tag kind={s.dailyUsd >= 0 ? "healthy" : "bleeding"}>
                        {formatPnl(s.dailyUsd)}
                      </Tag>
                    </td>
                    <td>
                      <Tag kind={s.wtdUsd >= 0 ? "healthy" : "bleeding"}>
                        {formatPnl(s.wtdUsd)}
                      </Tag>
                    </td>
                    <td>{pnlShareOfWtd(s.wtdUsd).toFixed(1)}%</td>
                    <td className="mono">{formatPnl(s.mtdUsd)}</td>
                    <td>
                      <Tag
                        kind={
                          s.health === "HEALTHY"
                            ? "healthy"
                            : s.health === "WATCH"
                              ? "watch"
                              : "bleeding"
                        }
                      >
                        {s.health}
                      </Tag>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Recent fills · click row">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Time</th>
                <th>Strategy</th>
                <th>Sub-strategy</th>
                <th>Asset</th>
                <th>Side</th>
                <th>Notional</th>
                <th>PnL</th>
                <th>Net bps</th>
              </tr>
            </thead>
            <tbody>
              {recentTradesPnl.map((t) => (
                <tr key={t.ts + t.asset} className="row-click" onClick={() => setSelected(t)}>
                  <td className="mono small">{t.ts.replace("T", " ").slice(11, 19)}</td>
                  <td>
                    {t.lane} · {t.strategyName}
                  </td>
                  <td className="mono small">{t.subStrategy ?? "—"}</td>
                  <td className="mono">{t.asset}</td>
                  <td>{t.side}</td>
                  <td>${t.notionalUsd.toLocaleString()}</td>
                  <td>
                    <Tag kind={t.pnlUsd >= 0 ? "healthy" : "bleeding"}>{formatPnl(t.pnlUsd)}</Tag>
                  </td>
                  <td>{t.netBps.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Drawer
        open={!!strategy}
        onClose={() => setStrategy(null)}
        title={strategy ? `${strategy.id} · ${strategy.name}` : ""}
        subtitle={strategy ? strategyCategoryLabels[strategy.category] : ""}
        footer={
          <>
            {strategy?.id === "P22" ? (
              <Link className="btn" to="/memecoin" onClick={() => setStrategy(null)}>
                Memecoin page
              </Link>
            ) : strategy?.category === "flash" ? (
              <Link className="btn" to="/flash-loans" onClick={() => setStrategy(null)}>
                Flash loans
              </Link>
            ) : (
              <Link className="btn" to="/pipelines" onClick={() => setStrategy(null)}>
                Pipelines
              </Link>
            )}
            <Btn variant="ghost" onClick={() => setStrategy(null)}>
              Close
            </Btn>
          </>
        }
      >
        {strategy ? (
          <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
            {[
              { k: "Revenue source", v: strategy.revenueSource },
              { k: "Edge PoP", v: strategy.edge },
              { k: "Phase", v: strategy.phase },
              { k: "Allocated", v: `$${strategy.allocationUsd.toLocaleString()}` },
              { k: "Today PnL", v: formatPnl(strategy.dailyUsd) },
              { k: "WTD PnL", v: `${formatPnl(strategy.wtdUsd)} (${pnlShareOfWtd(strategy.wtdUsd).toFixed(1)}%)` },
              { k: "MTD PnL", v: formatPnl(strategy.mtdUsd) },
              { k: "Net bps", v: strategy.netBps.toFixed(1) },
              { k: "24h trades", v: String(strategy.trades24h) },
            ].map((r) => (
              <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <dt>{r.k}</dt>
                <dd className="mono" style={{ margin: 0, textAlign: "right" }}>
                  {r.v}
                </dd>
              </div>
            ))}
          </dl>
        ) : null}
      </Drawer>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.asset ?? ""}
        subtitle={
          selected
            ? `${selected.lane} · ${selected.strategyName}${selected.subStrategy ? ` · ${selected.subStrategy}` : ""}`
            : ""
        }
        footer={
          <Btn variant="ghost" onClick={() => setSelected(null)}>
            Close
          </Btn>
        }
      >
        {selected ? (
          <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
            {[
              { k: "Strategy", v: `${selected.lane} · ${selected.strategyName}` },
              { k: "Category", v: strategyCategoryLabels[selected.category] },
              { k: "Sub-strategy", v: selected.subStrategy ?? "—" },
              { k: "Revenue source", v: selected.revenueSource },
              { k: "Timestamp", v: selected.ts },
              { k: "Notional", v: `$${selected.notionalUsd.toLocaleString()}` },
              { k: "Gross PnL", v: formatPnl(selected.pnlUsd) },
              { k: "Fees", v: `$${selected.feesUsd.toFixed(2)}` },
              { k: "Net bps", v: String(selected.netBps) },
            ].map((r) => (
              <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <dt>{r.k}</dt>
                <dd className="mono" style={{ margin: 0, textAlign: "right" }}>
                  {r.v}
                </dd>
              </div>
            ))}
          </dl>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
