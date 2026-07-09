import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, Download, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import {
  ActionMenu,
  DetailGrid,
  Drawer,
  Modal,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import {
  equitySeries,
  formatPnl,
  lanes,
  pnl,
  pnlByStrategy,
  pnlSeries,
  pnlShareOfWtd,
  portfolio,
  probeHealth,
  promotions,
  services,
  strategyCategoryLabels,
  type HealthOverall,
  type HealthProbeResult,
} from "@/lib/data";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";

type Lane = (typeof lanes)[number];
type Promo = (typeof promotions)[number];
type Svc = (typeof services)[number];

function overallChip(overall: HealthOverall): "ok" | "warn" | "danger" {
  if (overall === "ok") return "ok";
  if (overall === "degraded") return "warn";
  return "danger";
}

function overallLabel(overall: HealthOverall): string {
  if (overall === "ok") return "ok";
  if (overall === "degraded") return "degraded";
  if (overall === "halted") return "halted";
  return "unreachable";
}

export function Dashboard() {
  const { toasts, push, dismiss } = useToasts();
  const [lane, setLane] = useState<Lane | null>(null);
  const [promo, setPromo] = useState<Promo | null>(null);
  const [svc, setSvc] = useState<Svc | null>(null);
  const [metric, setMetric] = useState<"equity" | "pnl" | "available" | "deposits" | "dd" | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const {
    draft: dashPrefs,
    update: updateDash,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("dashboard", { range: "7d" as string, chartMode: "equity" as "equity" | "pnl" });
  const range = dashPrefs.range;
  const chartMode = dashPrefs.chartMode;
  const setRange = (v: string) => updateDash({ range: v });
  const setChartMode = (v: "equity" | "pnl") => updateDash({ chartMode: v });
  const [health, setHealth] = useState<HealthProbeResult | null>(null);

  const refreshHealth = useCallback(async () => {
    const result = await probeHealth("/api/status/health");
    setHealth(result);
    return result;
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  const displayServices: Svc[] =
    health?.reachable && health.services.length > 0
      ? health.services.map((s) => ({
          name: s.name,
          port: s.port || services.find((d) => d.name === s.name)?.port || 0,
          ok: s.ok,
        }))
      : services;

  return (
    <>
      <PageHeader
        eyebrow="Portfolio overview"
        title="Crypto Dashboard"
        subtitle="Click any metric for detail · DEX-only strategies, promotions, and services below."
        actions={
          <>
            <ActionMenu
              label={
                <>
                  <Download size={14} /> Export
                </>
              }
              items={[
                { label: "Equity CSV", hint: "7d series", onClick: () => { setExportOpen(true); push("Queued equity CSV export"); } },
                { label: "Lane TCA pack", hint: "JSON", onClick: () => push("Queued TCA pack") },
                { label: "Compliance PDF", hint: "Reports", onClick: () => push("Queued compliance PDF", "warn") },
              ]}
            />

            <ActionMenu
              label={<>Range · {range}</>}
              items={[
                { label: "24 hours", onClick: () => { setRange("24h"); push("Chart range → 24h"); } },
                { label: "7 days", onClick: () => { setRange("7d"); push("Chart range → 7d"); } },
                { label: "30 days", onClick: () => { setRange("30d"); push("Chart range → 30d"); } },
                { label: "MTD", onClick: () => { setRange("MTD"); push("Chart range → MTD"); } },
              ]}
            />
            <Btn
              variant="primary"
              onClick={() => {
                void refreshHealth().then((r) =>
                  push(
                    r.reachable
                      ? `Health · ${overallLabel(r.overall)} (:19003)`
                      : "Health probe unreachable — demo labels",
                    r.reachable && r.overall === "ok" ? "ok" : "warn",
                  ),
                );
              }}
            >
              <RefreshCw size={14} /> Refresh
            </Btn>
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

      {portfolio.evolutionFrozen ? (
        <div className="alert-banner">
          <AlertTriangle size={16} />
          Evolution freeze active — click for options.
          <Btn
            variant="ghost"
            onClick={() =>
              push("Open Command Center → Evolution freeze to unfreeze", "warn")
            }
          >
            Manage freeze
          </Btn>
          <Link className="btn" to="/command">
            Command Center
          </Link>
        </div>
      ) : null}

      <section className="status-strip" aria-label="Key portfolio metrics">
        <button type="button" className="status-stat" onClick={() => setMetric("equity")}>
          <span className="label">Equity</span>
          <span className="value">${portfolio.equityUsd.toLocaleString()}</span>
          <span className="delta up">+${portfolio.weeklyPnlUsd} WTD</span>
        </button>
        <button type="button" className="status-stat" onClick={() => setMetric("pnl")}>
          <span className="label">WTD PnL</span>
          <span className="value">{formatPnl(pnl.weeklyUsd)}</span>
          <span className={`delta ${pnl.dailyUsd >= 0 ? "up" : "down"}`}>
            {formatPnl(pnl.dailyUsd)} today
          </span>
        </button>
        <button type="button" className="status-stat" onClick={() => setMetric("pnl")}>
          <span className="label">Trading PnL</span>
          <span className="value">{formatPnl(pnl.tradingPnlUsd, false)}</span>
          <span className="delta">all-time · ex deposits</span>
        </button>
        <button type="button" className="status-stat" onClick={() => setMetric("available")}>
          <span className="label">Available</span>
          <span className="value">${portfolio.availableUsd.toLocaleString()}</span>
          <span className="delta">deployable</span>
        </button>
        <button type="button" className="status-stat" onClick={() => setMetric("dd")}>
          <span className="label">Drawdown</span>
          <span className="value">{portfolio.drawdownPct}%</span>
          <span className={`delta ${portfolio.drawdownPct > 2 ? "down" : "up"}`}>
            CB tiers 2–12%
          </span>
        </button>
      </section>

      <div className="split" style={{ marginBottom: 14 }}>
        <Card
          title={chartMode === "equity" ? `Equity curve (${range})` : `PnL curve (${range})`}
          action={
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <Btn
                variant={chartMode === "equity" ? "primary" : "ghost"}
                onClick={() => setChartMode("equity")}
              >
                Equity
              </Btn>
              <Btn
                variant={chartMode === "pnl" ? "primary" : "ghost"}
                onClick={() => setChartMode("pnl")}
              >
                PnL
              </Btn>
              <ActionMenu
                label="Chart"
                variant="ghost"
                items={[
                  { label: "Toggle annotations", onClick: () => push("Annotations toggled") },
                  { label: "Compare to deposits", onClick: () => push("Deposit overlay on") },
                  { label: "Open PnL", onClick: () => push("Navigate via PnL sidebar") },
                ]}
              />
            </div>
          }
        >
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <AreaChart data={chartMode === "equity" ? equitySeries : pnlSeries}>
                <defs>
                  <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="pnlDash" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#7b8798" fontSize={11} />
                <YAxis stroke="#7b8798" fontSize={11} domain={chartMode === "equity" ? ["dataMin - 200", "dataMax + 200"] : ["dataMin - 50", "dataMax + 50"]} />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-2)",
                    border: "1px solid var(--border-strong)",
                    borderRadius: 8,
                    color: "var(--text)",
                  }}
                  formatter={(v: number) => [
                    chartMode === "equity" ? `$${Number(v).toLocaleString()}` : formatPnl(Number(v), false),
                    chartMode === "equity" ? "Equity" : "Cumulative PnL",
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey={chartMode === "equity" ? "equity" : "cumulative"}
                  stroke={chartMode === "equity" ? "#06b6d4" : "#10b981"}
                  fill={chartMode === "equity" ? "url(#eq)" : "url(#pnlDash)"}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card
          title="Safety services · click row"
          action={
            <Tag kind={health?.reachable ? (health.overall === "ok" ? "healthy" : "watch") : "neutral"}>
              {health?.reachable ? `:19003 ${overallLabel(health.overall)}` : "demo"}
            </Tag>
          }
        >
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
                {displayServices.map((s) => (
                  <tr key={s.name} className="row-click" onClick={() => setSvc(s)}>
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
        <Card title="Strategy PnL (WTD) · click for actions">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Source</th>
                  <th>Alloc</th>
                  <th>WTD PnL</th>
                  <th>% WTD</th>
                  <th>Health</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {[...pnlByStrategy]
                  .sort((a, b) => b.wtdUsd - a.wtdUsd)
                  .map((s) => {
                    const laneRow = lanes.find((l) => l.id === s.id)!;
                    return (
                      <tr key={s.id} className="row-click" onClick={() => setLane(laneRow)}>
                        <td>
                          {s.id} · {s.name}
                        </td>
                        <td className="small muted">{s.revenueSource}</td>
                        <td>${s.allocationUsd.toLocaleString()}</td>
                        <td>
                          <Tag kind={s.wtdUsd >= 0 ? "healthy" : "bleeding"}>
                            {formatPnl(s.wtdUsd)}
                          </Tag>
                        </td>
                        <td>{pnlShareOfWtd(s.wtdUsd).toFixed(1)}%</td>
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
                        <td onClick={(e) => e.stopPropagation()}>
                          <ActionMenu
                            label="⋯"
                            variant="ghost"
                            items={[
                              { label: "Open details", onClick: () => setLane(laneRow) },
                              { label: "View PnL attribution", onClick: () => push(`PnL · ${s.id}`) },
                              {
                                label: "Defund lane",
                                danger: true,
                                disabled: s.allocationUsd === 0,
                                onClick: () => push(`Defund queued · ${s.id}`, "warn"),
                              },
                            ]}
                          />
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
            <Link to="/pnl">Full PnL attribution</Link> · P1 + P5 ={" "}
            {pnlShareOfWtd(
              (pnlByStrategy.find((s) => s.id === "P1")?.wtdUsd ?? 0) +
                (pnlByStrategy.find((s) => s.id === "P5")?.wtdUsd ?? 0),
            ).toFixed(0)}
            % of WTD
          </p>
        </Card>

        <Card title="Promotion queue · click row">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Phase</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {promotions.map((p) => (
                  <tr key={p.id} className="row-click" onClick={() => setPromo(p)}>
                    <td>{p.strategy}</td>
                    <td>{p.phase}/6</td>
                    <td>
                      <Tag kind={p.status.includes("PENDING") ? "watch" : "info"}>{p.status}</Tag>
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <ActionMenu
                        label="Decide"
                        variant="ghost"
                        items={[
                          { label: "YES · promote", onClick: () => push(`YES · ${p.id}`, "ok") },
                          { label: "HOLD / de-risk", onClick: () => push(`HOLD · ${p.id}`, "warn") },
                          { label: "NO · archive", danger: true, onClick: () => push(`NO · ${p.id}`, "danger") },
                          { label: "Open Promotions page", onClick: () => setPromo(p) },
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Drawer
        open={!!lane}
        onClose={() => setLane(null)}
        title={lane ? `${lane.id} · ${lane.name}` : ""}
        subtitle="Lane detail · allocator / TCA actions"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setLane(null)}>
              Close
            </Btn>
            <Btn onClick={() => { push(`TCA opened · ${lane?.id}`); }}>View TCA</Btn>
            <Btn
              variant="danger"
              disabled={!lane || lane.allocation === 0}
              onClick={() => { push(`Defund · ${lane?.id}`, "warn"); setLane(null); }}
            >
              Defund
            </Btn>
            <Btn
              variant="primary"
              disabled={!lane || lane.health === "BLEEDING"}
              onClick={() => { push(`Increase allocation · ${lane?.id}`); setLane(null); }}
            >
              Scale up
            </Btn>
          </>
        }
      >
        {lane ? (
          <>
            <DetailGrid
              rows={[
                { label: "Category", value: strategyCategoryLabels[lane.category] },
                { label: "Revenue source", value: lane.revenueSource },
                { label: "Phase", value: lane.phase },
                { label: "Allocation", value: `$${lane.allocation.toLocaleString()}` },
                {
                  label: "WTD PnL",
                  value: `${formatPnl(lane.pnlWtdUsd)} (${pnlShareOfWtd(lane.pnlWtdUsd).toFixed(1)}%)`,
                },
                { label: "Net bps", value: lane.netBps.toFixed(2) },
                { label: "Trades (est.)", value: String(lane.trades) },
                { label: "Health", value: lane.health },
              ]}
            />
            <div className="option-grid" style={{ marginTop: 14 }}>
              <button type="button" className="option-tile" onClick={() => push("Hold size")}>
                <strong>Hold size</strong>
                <span>no rebalance</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push("Paper only")}>
                <strong>Paper only</strong>
                <span>strip live capital</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push("Pin to EDGE")}>
                <strong>Pin edge</strong>
                <span>force PoP</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push("Red Team re-run")}>
                <strong>Red Team</strong>
                <span>re-run gauntlet</span>
              </button>
            </div>
          </>
        ) : null}
      </Drawer>

      <Drawer
        open={!!promo}
        onClose={() => setPromo(null)}
        title={promo?.strategy ?? ""}
        subtitle={promo ? `${promo.id} · phase ${promo.phase}/6` : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setPromo(null)}>
              Close
            </Btn>
            <Btn variant="danger" onClick={() => { push(`NO · ${promo?.id}`, "danger"); setPromo(null); }}>
              NO
            </Btn>
            <Btn onClick={() => { push(`HOLD · ${promo?.id}`, "warn"); setPromo(null); }}>
              HOLD
            </Btn>
            <Btn variant="primary" onClick={() => { push(`YES · ${promo?.id}`); setPromo(null); }}>
              YES · promote
            </Btn>
          </>
        }
      >
        {promo ? (
          <DetailGrid
            rows={[
              { label: "Status", value: promo.status },
              { label: "Score", value: promo.score.toFixed(2) },
              { label: "Timeout policy", value: "HOLD / de-risk (never auto-promote)" },
              { label: "Evolution freeze", value: portfolio.evolutionFrozen ? "blocks live" : "open" },
            ]}
          />
        ) : null}
      </Drawer>

      <Modal
        open={!!svc}
        onClose={() => setSvc(null)}
        title={svc ? `titan-${svc.name}` : ""}
        subtitle={svc ? `127.0.0.1:${svc.port}` : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSvc(null)}>
              Close
            </Btn>
            <Btn onClick={() => push(`Restart ${svc?.name}`, "warn")}>Restart unit</Btn>
            <Btn variant="primary" onClick={() => push(`Health probe ${svc?.name}`)}>
              Probe /health
            </Btn>
          </>
        }
      >
        {svc ? (
          <DetailGrid
            rows={[
              { label: "Status", value: svc.ok ? "UP" : "DOWN" },
              { label: "Proxy path", value: `/api/${svc.name.split("-")[0]}` },
              { label: "Auth", value: "X-Titan-Auth on mutating POSTs" },
            ]}
          />
        ) : null}
      </Modal>

      <Modal
        open={!!metric}
        onClose={() => setMetric(null)}
        title={
          metric === "equity"
            ? "Equity detail"
            : metric === "pnl"
              ? "PnL detail"
              : metric === "available"
                ? "Available capital"
                : metric === "deposits"
                  ? "Deposit ledger"
                  : "Drawdown"
        }
        footer={
          <>
            <Btn variant="ghost" onClick={() => setMetric(null)}>
              Close
            </Btn>
            {metric === "pnl" ? (
              <Link className="btn primary" to="/pnl" onClick={() => setMetric(null)}>
                Open PnL
              </Link>
            ) : metric === "deposits" || metric === "available" || metric === "equity" ? (
              <Link className="btn primary" to="/capital" onClick={() => setMetric(null)}>
                Open Capital &amp; Wallets
              </Link>
            ) : (
              <Link className="btn primary" to="/risk" onClick={() => setMetric(null)}>
                Open Risk &amp; CBs
              </Link>
            )}
          </>
        }
      >
        {metric === "pnl" && (
          <>
            <DetailGrid
              rows={[
                { label: "WTD PnL", value: formatPnl(pnl.weeklyUsd) },
                { label: "Today", value: formatPnl(pnl.dailyUsd) },
                { label: "MTD", value: formatPnl(pnl.mtdUsd) },
                { label: "Realized", value: formatPnl(pnl.realizedUsd, false) },
                { label: "Unrealized", value: formatPnl(pnl.unrealizedUsd, false) },
                { label: "Trading PnL (all-time)", value: formatPnl(pnl.tradingPnlUsd, false) },
              ]}
            />
            <p className="muted small" style={{ marginTop: 12, marginBottom: 6 }}>
              Top WTD contributors
            </p>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>WTD</th>
                    <th>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {[...pnlByStrategy]
                    .sort((a, b) => b.wtdUsd - a.wtdUsd)
                    .slice(0, 5)
                    .map((s) => (
                      <tr key={s.id}>
                        <td>
                          {s.id} · {s.name}
                        </td>
                        <td>{formatPnl(s.wtdUsd)}</td>
                        <td>{pnlShareOfWtd(s.wtdUsd).toFixed(1)}%</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {metric === "equity" && (
          <DetailGrid
            rows={[
              { label: "Mark equity", value: `$${portfolio.equityUsd.toLocaleString()}` },
              { label: "WTD PnL", value: `$${portfolio.weeklyPnlUsd}` },
              { label: "Profile", value: portfolio.capitalProfile },
            ]}
          />
        )}
        {metric === "available" && (
          <DetailGrid
            rows={[
              { label: "Available", value: `$${portfolio.availableUsd.toLocaleString()}` },
              { label: "Reserved in lanes", value: `$${(portfolio.equityUsd - portfolio.availableUsd).toFixed(2)}` },
            ]}
          />
        )}
        {metric === "deposits" && (
          <>
            <p className="muted small">Deposits ≠ trading profit. Ledger only.</p>
            <DetailGrid
              rows={[
                { label: "Lifetimeposited", value: `$${portfolio.depositedUsd.toLocaleString()}` },
                { label: "Next injection", value: "Biweekly schedule" },
              ]}
            />
          </>
        )}
        {metric === "dd" && (
          <DetailGrid
            rows={[
              { label: "Current DD", value: `${portfolio.drawdownPct}%` },
              { label: "Next tier", value: "2% alert + size reduce" },
              { label: "Halt tier", value: "12% HERALD CRITICAL (no halt)" },
            ]}
          />
        )}
      </Modal>

      <Modal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        title="Export equity CSV"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setExportOpen(false)}>
              Cancel
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                push("Download started (demo)");
                setExportOpen(false);
              }}
            >
              Download
            </Btn>
          </>
        }
      >
        <div className="option-grid">
          {["UTF-8 CSV", "Excel-friendly", "JSONL"].map((fmt) => (
            <button key={fmt} type="button" className="option-tile active">
              <strong>{fmt}</strong>
              <span>{range}</span>
            </button>
          ))}
        </div>
      </Modal>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
