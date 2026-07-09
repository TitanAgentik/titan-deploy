import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { Drawer, ToastStack, useToasts } from "@/components/interactive";
import {
  edgeMesh,
  latencyBudget,
  latencyCenter,
  latencySegmentStatus,
  type LatencySegmentStatus,
} from "@/lib/data";

type HotSegment = (typeof latencyCenter.hotPath.segments)[number];
type VenueRtt = (typeof latencyCenter.venueRtt)[number];
type PipelineClass = (typeof latencyCenter.pipelineClasses)[number];
type LatencyEvent = (typeof latencyCenter.recentEvents)[number];
type Tab = "overview" | "hot" | "edge" | "pipelines";

function statusTag(status: LatencySegmentStatus | "healthy" | "info") {
  if (status === "ok" || status === "healthy") return "healthy" as const;
  if (status === "warn") return "watch" as const;
  if (status === "info") return "info" as const;
  return "bleeding" as const;
}

function pathClassTag(pathClass: PipelineClass["pathClass"]) {
  if (pathClass === "hot") return "bleeding" as const;
  if (pathClass === "warm") return "watch" as const;
  return "info" as const;
}

export function Latency() {
  const { toasts, push, dismiss } = useToasts();
  const [tab, setTab] = useState<Tab>("overview");
  const [segment, setSegment] = useState<HotSegment | null>(null);
  const [venue, setVenue] = useState<VenueRtt | null>(null);
  const [event, setEvent] = useState<LatencyEvent | null>(null);

  const lc = latencyCenter;
  const gate = lc.hotPath.segments.find((s) => s.id === "gate_combined")!;
  const submit = lc.hotPath.segments.find((s) => s.id === "total_submit")!;
  const homeEdge = lc.hotPath.segments.find((s) => s.id === "home_to_edge")!;

  const hotWaterfall = useMemo(
    () =>
      lc.hotPath.segments
        .filter((s) => s.id !== "total_submit")
        .map((s) => ({
          label: s.id.replace(/_/g, " "),
          budget: s.budgetP95Ms,
          live: s.liveP95Ms,
          status: s.status,
        })),
    [lc.hotPath.segments],
  );

  const openWarns = lc.recentEvents.filter((e) => !e.resolved && e.severity === "warn").length;

  return (
    <>
      <PageHeader
        eyebrow="FORGE · millisecond SLOs"
        title="Latency"
        subtitle="Hot path, warm path, DEX / sequencer RTT, and pipeline latency classes — paper + live use identical routing."
        actions={
          <>
            <Btn variant="ghost" onClick={() => push("RTT probe sweep queued (demo)")}>
              Run probe
            </Btn>
            <Link className="btn" to="/edge">
              Edge Mesh
            </Link>
            <Link className="btn primary" to="/forge">
              Forge
            </Link>
          </>
        }
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric
          label="Hot gate p95"
          value={`${gate.liveP95Ms} ms`}
          delta={`budget ${gate.budgetP95Ms} ms`}
          deltaDir={gate.status === "ok" ? "up" : "down"}
        />
        <Metric
          label="Total submit p95"
          value={`${submit.liveP95Ms} ms`}
          delta={`budget ${submit.budgetP95Ms} ms · E2E`}
          deltaDir={submit.status === "ok" ? "up" : "down"}
        />
        <Metric
          label="Home → edge p95"
          value={`${homeEdge.liveP95Ms} ms`}
          delta={`WG · budget ${homeEdge.budgetP95Ms} ms`}
          deltaDir={homeEdge.status === "ok" ? "up" : "down"}
        />
        <Metric
          label="Overall SLO"
          value={lc.overallStatus === "ok" ? "IN BUDGET" : lc.overallStatus.toUpperCase()}
          delta={`${openWarns} open warn${openWarns === 1 ? "" : "s"} · ${lc.probeAgent}`}
        />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {(
          [
            ["overview", "Overview"],
            ["hot", "Hot path"],
            ["edge", "Edge RTT"],
            ["pipelines", "Pipelines"],
          ] as const
        ).map(([id, label]) => (
          <Btn key={id} variant={tab === id ? "primary" : "ghost"} onClick={() => setTab(id)}>
            {label}
          </Btn>
        ))}
        <Tag kind={edgeMesh.paperLatencyFaithful ? "healthy" : "watch"}>
          paper routing {edgeMesh.paperLatencyFaithful ? "FAITHFUL" : "OFF"}
        </Tag>
        <Tag kind="info">{edgeMesh.mode.replace("_", " ")} · {edgeMesh.activePops} PoPs</Tag>
      </div>

      {tab === "overview" && (
        <>
          <div className="split" style={{ marginBottom: 14 }}>
            <Card title="Gate p95 · 8h (hot path)">
              <div style={{ width: "100%", height: 220 }}>
                <ResponsiveContainer>
                  <AreaChart data={lc.gateP95Series}>
                    <defs>
                      <linearGradient id="gateFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                    <XAxis dataKey="t" stroke="#7b8798" fontSize={11} />
                    <YAxis stroke="#7b8798" fontSize={11} domain={[0, 20]} unit="ms" />
                    <ReferenceLine
                      y={latencyBudget.hotPathGateP95Ms}
                      stroke="#ef4444"
                      strokeDasharray="4 4"
                      label={{ value: "15ms budget", position: "insideTopRight", fontSize: 10 }}
                    />
                    <Tooltip
                      formatter={(v: number) => [`${v} ms`, "Gate p95"]}
                      contentStyle={{
                        background: "#fff",
                        border: "1px solid rgba(11,21,40,0.12)",
                        borderRadius: 8,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="p95"
                      stroke="#3b82f6"
                      fill="url(#gateFill)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Submit p95 · 8h (E2E)">
              <div style={{ width: "100%", height: 220 }}>
                <ResponsiveContainer>
                  <LineChart data={lc.submitP95Series}>
                    <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                    <XAxis dataKey="t" stroke="#7b8798" fontSize={11} />
                    <YAxis stroke="#7b8798" fontSize={11} domain={[30, 55]} unit="ms" />
                    <ReferenceLine
                      y={latencyBudget.hotPathSubmitP95Ms}
                      stroke="#ef4444"
                      strokeDasharray="4 4"
                    />
                    <Tooltip
                      formatter={(v: number) => [`${v} ms`, "Submit p95"]}
                      contentStyle={{
                        background: "#fff",
                        border: "1px solid rgba(11,21,40,0.12)",
                        borderRadius: 8,
                      }}
                    />
                    <Line type="monotone" dataKey="p95" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <div className="split" style={{ marginBottom: 14 }}>
            <Card title="Hot path segments · budget vs live p95">
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={hotWaterfall} layout="vertical" margin={{ left: 4, right: 16 }}>
                    <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" />
                    <XAxis type="number" stroke="#7b8798" fontSize={11} unit="ms" />
                    <YAxis type="category" dataKey="label" stroke="#7b8798" fontSize={10} width={88} />
                    <Tooltip
                      contentStyle={{
                        background: "#fff",
                        border: "1px solid rgba(11,21,40,0.12)",
                        borderRadius: 8,
                      }}
                    />
                    <Legend />
                    <Bar dataKey="budget" name="Budget p95" fill="rgba(11,21,40,0.15)" radius={[0, 3, 3, 0]} />
                    <Bar dataKey="live" name="Live p95" radius={[0, 3, 3, 0]}>
                      {hotWaterfall.map((d) => (
                        <Cell
                          key={d.label}
                          fill={
                            d.status === "breach"
                              ? "#ef4444"
                              : d.status === "warn"
                                ? "#f59e0b"
                                : "#10b981"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
                Click a segment in the Hot path tab for endpoint detail. Last probe:{" "}
                <span className="mono">{lc.lastProbeAt.replace("T", " ").slice(0, 19)} UTC</span>
              </p>
            </Card>

            <Card title="Dispatch path · signal → ack">
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Hop</th>
                      <th>Target</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lc.dispatchSteps.map((d) => (
                      <tr key={d.step}>
                        <td>{d.step}</td>
                        <td className="mono small">{d.hop}</td>
                        <td>{d.latency}</td>
                        <td className="muted small">{d.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
                Hot pipelines skip TradingAgents debate —{" "}
                {latencyBudget.hotPipelines.join(", ")}. CLI:{" "}
                <span className="mono">titan-safety edge route --strategy P22</span>
              </p>
            </Card>
          </div>

          <div className="grid grid-2" style={{ marginBottom: 14 }}>
            <Card title="Warm path · LLM-assisted lanes">
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Segment</th>
                      <th>Budget p95</th>
                      <th>Live p95</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lc.warmPath.segments.map((s) => (
                      <tr key={s.id}>
                        <td>
                          {s.label}
                          {"endpoint" in s && s.endpoint ? (
                            <span className="muted small"> · {s.endpoint}</span>
                          ) : null}
                        </td>
                        <td>{s.budgetP95Ms} ms</td>
                        <td>{s.liveP95Ms} ms</td>
                        <td>
                          <Tag kind={statusTag(s.status)}>{s.status.toUpperCase()}</Tag>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card title="Inference · feeds · off hot path">
              <dl className="muted small" style={{ margin: 0, display: "grid", gap: 8 }}>
                {[
                  {
                    k: "Tier 1 TTFT warm p95",
                    v: `${lc.inference.liveTier1WarmP95Ms} / ${lc.inference.tier1FirstTokenWarmP95Ms} ms`,
                  },
                  {
                    k: "Tier 1 TTFT cold p95",
                    v: `${lc.inference.liveTier1ColdP95Ms} / ${lc.inference.tier1FirstTokenColdP95Ms} ms`,
                  },
                  {
                    k: "Tier 2 blocks Tier 1",
                    v: lc.inference.tier2MustNotBlockTier1 ? "must NOT" : "allowed",
                  },
                  {
                    k: "NEXUS staleness",
                    v: `${lc.feeds.liveNexusStalenessSec}s / max ${lc.feeds.nexusStalenessMaxSec}s`,
                  },
                  { k: "RPC timeout", v: `${lc.feeds.rpcTimeoutSec}s` },
                  { k: "WS reconnect", v: `${lc.feeds.websocketReconnectMs} ms` },
                  { k: "Feed status", v: lc.feeds.status },
                ].map((r) => (
                  <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <dt>{r.k}</dt>
                    <dd className="mono" style={{ margin: 0 }}>
                      {r.v}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="muted small" style={{ marginTop: 12, marginBottom: 0 }}>
                {lc.inference.note}
              </p>
            </Card>
          </div>

          <Card title="Recent latency events · click row">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Severity</th>
                    <th>Segment</th>
                    <th>Detail</th>
                    <th>Resolved</th>
                  </tr>
                </thead>
                <tbody>
                  {lc.recentEvents.map((e) => (
                    <tr key={e.ts + e.segment} className="row-click" onClick={() => setEvent(e)}>
                      <td className="mono small">{e.ts.replace("T", " ").slice(5, 16)}</td>
                      <td>
                        <Tag kind={e.severity === "warn" ? "watch" : "info"}>{e.severity}</Tag>
                      </td>
                      <td>{e.segment}</td>
                      <td className="small">{e.detail}</td>
                      <td>{e.resolved ? "yes" : "open"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {tab === "hot" && (
        <>
          <Card title="Hot path budget · all segments" style={{ marginBottom: 14 }}>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Segment</th>
                    <th>Endpoint</th>
                    <th>p50</th>
                    <th>p95 live</th>
                    <th>p95 budget</th>
                    <th>Utilization</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lc.hotPath.segments.map((s) => {
                    const util = Math.round((s.liveP95Ms / s.budgetP95Ms) * 100);
                    return (
                      <tr key={s.id} className="row-click" onClick={() => setSegment(s)}>
                        <td>{s.label}</td>
                        <td className="mono small">{s.endpoint}</td>
                        <td>{s.liveP50Ms} ms</td>
                        <td>{s.liveP95Ms} ms</td>
                        <td>{s.budgetP95Ms} ms</td>
                        <td>
                          <div className="progress" style={{ minWidth: 80 }}>
                            <span
                              style={{
                                width: `${Math.min(100, util)}%`,
                                background:
                                  s.status === "breach"
                                    ? "#ef4444"
                                    : s.status === "warn"
                                      ? "#f59e0b"
                                      : undefined,
                              }}
                            />
                          </div>
                          <span className="muted small">{util}%</span>
                        </td>
                        <td>
                          <Tag kind={statusTag(s.status)}>{s.status.toUpperCase()}</Tag>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
              Gate timeout {lc.hotPath.gateTimeoutSec}s · signing receipt max age{" "}
              {lc.hotPath.signingReceiptMaxAgeSec}s · combined validate{" "}
              {lc.hotPath.combinedValidate ? "ON" : "OFF"}
            </p>
          </Card>

          <Card title="Hard halt rules · FORGE enforced">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {lc.enforcement.hardHalts.map((h) => (
                    <tr key={h.rule}>
                      <td className="mono small">{h.rule}</td>
                      <td>
                        <Tag kind="bleeding">{h.action}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginTop: 8, marginBottom: 0 }}>
              Specs: {lc.enforcement.specs.join(" · ")} · on breach:{" "}
              {lc.enforcement.onBreach.join(", ")}
            </p>
          </Card>
        </>
      )}

      {tab === "edge" && (
        <>
          <Card title="Venue RTT · lowest live p50 PoP" style={{ marginBottom: 14 }}>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Venue</th>
                    <th>DEX / venue</th>
                    <th>PoP</th>
                    <th>Region</th>
                    <th>p50</th>
                    <th>p95</th>
                    <th>Target</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lc.venueRtt.map((v) => (
                    <tr key={v.venue} className="row-click" onClick={() => setVenue(v)}>
                      <td>{v.venue}</td>
                      <td>{v.protocol}</td>
                      <td className="mono">{v.pop}</td>
                      <td className="small muted">{v.region}</td>
                      <td>{v.p50Ms} ms</td>
                      <td>{v.p95Ms} ms</td>
                      <td>&lt;{v.targetMs} ms</td>
                      <td>
                        <Tag kind={statusTag(v.status)}>{v.status.toUpperCase()}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="PoP health · DEX RTT + WireGuard">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>PoP</th>
                    <th>Region</th>
                    <th>DEX p50/p95</th>
                    <th>WG p95</th>
                    <th>Targets</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lc.popHealth.map((p) => (
                    <tr key={p.id}>
                      <td className="mono">{p.id}</td>
                      <td>{p.region}</td>
                      <td>
                        {p.liveP50Ms} / {p.liveP95Ms} ms
                      </td>
                      <td>{p.wgLatencyP95Ms} ms</td>
                      <td className="small">{p.targets}</td>
                      <td>
                        <Tag kind={p.status === "healthy" ? "healthy" : "watch"}>{p.status}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginTop: 8, marginBottom: 0 }}>
              Routing policy: <span className="mono">{edgeMesh.routingPolicy}</span> · default{" "}
              {edgeMesh.defaultPop} · bootstrap{" "}
              <span className="mono">POP=EDGE-* bash edge_pop_bootstrap.sh</span>
            </p>
          </Card>
        </>
      )}

      {tab === "pipelines" && (
        <>
          <div className="grid grid-3" style={{ marginBottom: 14 }}>
            <Metric
              label="Hot pipelines"
              value={String(lc.pipelineClasses.filter((p) => p.pathClass === "hot").length)}
              delta={latencyBudget.hotPipelines.join(", ")}
            />
            <Metric
              label="Warm pipelines"
              value={String(lc.pipelineClasses.filter((p) => p.pathClass === "warm").length)}
              delta="LLM debate allowed"
            />
            <Metric
              label="Cold pipelines"
              value={String(lc.pipelineClasses.filter((p) => p.pathClass === "cold").length)}
              delta="research / promotion"
            />
          </div>

          <Card title="Pipeline latency class · skip debate · live gate p95">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Pipeline</th>
                    <th>Class</th>
                    <th>Edge PoP</th>
                    <th>Skip debate</th>
                    <th>Live gate p95</th>
                    <th>Budget</th>
                  </tr>
                </thead>
                <tbody>
                  {lc.pipelineClasses.map((p) => {
                    const budget =
                      p.pathClass === "hot"
                        ? latencyBudget.hotPathGateP95Ms
                        : p.pathClass === "warm"
                          ? latencyBudget.warmPathGateP95Ms
                          : null;
                    const st =
                      p.liveGateP95Ms != null && budget != null
                        ? latencySegmentStatus(p.liveGateP95Ms, budget)
                        : null;
                    return (
                      <tr key={p.id}>
                        <td>
                          {p.id} · {p.name}
                        </td>
                        <td>
                          <Tag kind={pathClassTag(p.pathClass)}>{p.pathClass.toUpperCase()}</Tag>
                        </td>
                        <td className="mono">{p.edgePop}</td>
                        <td>{p.skipDebate ? "yes" : "no"}</td>
                        <td>{p.liveGateP95Ms != null ? `${p.liveGateP95Ms} ms` : "—"}</td>
                        <td>
                          {budget != null ? (
                            <Tag kind={st ? statusTag(st) : "info"}>{budget} ms</Tag>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginTop: 8, marginBottom: 0 }}>
              Hot = millisecond path (fast_validate, no TradingAgents). Warm = up to{" "}
              {latencyBudget.warmPathGateP95Ms}ms gate. Cold = seconds OK (backtest / GEPA).
            </p>
          </Card>
        </>
      )}

      <Drawer
        open={!!segment}
        onClose={() => setSegment(null)}
        title={segment?.label ?? ""}
        subtitle={segment?.endpoint}
        footer={
          <Btn variant="ghost" onClick={() => setSegment(null)}>
            Close
          </Btn>
        }
      >
        {segment ? (
          <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
            {[
              { k: "Live p50", v: `${segment.liveP50Ms} ms` },
              { k: "Live p95", v: `${segment.liveP95Ms} ms` },
              { k: "Budget p95", v: `${segment.budgetP95Ms} ms` },
              {
                k: "Utilization",
                v: `${Math.round((segment.liveP95Ms / segment.budgetP95Ms) * 100)}%`,
              },
              { k: "Status", v: segment.status.toUpperCase() },
            ].map((r) => (
              <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <dt>{r.k}</dt>
                <dd className="mono" style={{ margin: 0 }}>
                  {r.v}
                </dd>
              </div>
            ))}
          </dl>
        ) : null}
      </Drawer>

      <Drawer
        open={!!venue}
        onClose={() => setVenue(null)}
        title={venue?.venue ?? ""}
        subtitle={venue ? `${venue.protocol} · ${venue.pop}` : ""}
        footer={
          <>
            <Link className="btn" to="/edge" onClick={() => setVenue(null)}>
              Edge Mesh
            </Link>
            <Btn variant="ghost" onClick={() => setVenue(null)}>
              Close
            </Btn>
          </>
        }
      >
        {venue ? (
          <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
            {[
              { k: "Region", v: venue.region },
              { k: "p50 RTT", v: `${venue.p50Ms} ms` },
              { k: "p95 RTT", v: `${venue.p95Ms} ms` },
              { k: "Target", v: `<${venue.targetMs} ms` },
              { k: "Status", v: venue.status.toUpperCase() },
            ].map((r) => (
              <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <dt>{r.k}</dt>
                <dd className="mono" style={{ margin: 0 }}>
                  {r.v}
                </dd>
              </div>
            ))}
          </dl>
        ) : null}
      </Drawer>

      <Drawer
        open={!!event}
        onClose={() => setEvent(null)}
        title={event?.segment ?? ""}
        subtitle={event?.ts.replace("T", " ").slice(0, 19)}
        footer={
          <Btn variant="ghost" onClick={() => setEvent(null)}>
            Close
          </Btn>
        }
      >
        {event ? (
          <>
            <Tag kind={event.severity === "warn" ? "watch" : "info"}>{event.severity}</Tag>
            <p className="small" style={{ marginTop: 12 }}>
              {event.detail}
            </p>
            <p className="muted small">Resolved: {event.resolved ? "yes" : "no — monitoring"}</p>
          </>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
