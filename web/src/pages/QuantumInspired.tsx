import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { ToastStack, useToasts } from "@/components/interactive";
import { quantumInspired, strategyDisplay } from "@/lib/data";

type LaneView = "sa" | "kelly" | "compare";

export function QuantumInspired() {
  const { toasts, push, dismiss } = useToasts();
  const [laneView, setLaneView] = useState<LaneView>("compare");
  const [scenarioIdx, setScenarioIdx] = useState(0);

  const qi = quantumInspired;
  const scenario = qi.altScenarios[scenarioIdx];
  const selectedSet = useMemo(
    () => new Set(qi.result.selected_pipeline_ids),
    [qi.result.selected_pipeline_ids],
  );
  const kellySet = useMemo(
    () => new Set(qi.kelly.allocations.map((a) => a.pipeline_id)),
    [qi.kelly.allocations],
  );

  const views: { id: LaneView; label: string }[] = [
    { id: "sa", label: "SA selection" },
    { id: "kelly", label: "Kelly allocator" },
    { id: "compare", label: "SA vs Kelly" },
  ];

  return (
    <>
      <PageHeader
        title="Quantum-Inspired Optimizer"
        subtitle="Classical QUBO + simulated annealing lane subset selection — research / advisory only. Compares against fractional-Kelly CapitalAllocator."
        actions={
          <>
            <Link className="btn" to="/pipelines">
              Pipelines
            </Link>
            <Link className="btn" to="/risk">
              Risk & CBs
            </Link>
            <Btn
              variant="primary"
              onClick={() =>
                push("Demo replay queued — titan-safety qi demo --seed 42 --k 4 --compare-kelly", "ok")
              }
            >
              Replay demo CLI
            </Btn>
          </>
        }
      />

      <div className="alert-banner">
        <strong>Advisory only</strong> — live_path=false · backend=classical_sa · quantum.enabled unchanged ·
        QCC/QSA/QRP dormant. SA output does not gate execution; risk kernel DENY remains authoritative.
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Backend" value={qi.backend} delta="no QPU" />
        <Metric label="QUBO energy" value={qi.result.energy.toFixed(2)} delta={`k=${qi.config.k}`} />
        <Metric
          label="Kelly overlap"
          value={`${qi.comparison.overlap_count}/${qi.comparison.target_k}`}
          delta={qi.comparison.qi_only.length || qi.comparison.kelly_only.length ? "divergence" : "full match"}
        />
        <Metric label="Cardinality" value={String(qi.result.cardinality)} delta={`bitstring ${qi.result.bitstring}`} />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {views.map((v) => (
          <button
            key={v.id}
            type="button"
            className={`btn${laneView === v.id ? " primary" : ""}`}
            onClick={() => setLaneView(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div className="grid grid-2">
        <Card title="Demo lane universe">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>net bps</th>
                  <th>σ</th>
                  <th>Trades</th>
                  <th>Cluster</th>
                  {(laneView === "sa" || laneView === "compare") && <th>SA</th>}
                  {(laneView === "kelly" || laneView === "compare") && <th>Kelly</th>}
                </tr>
              </thead>
              <tbody>
                {qi.lanes.map((lane) => {
                  const saOn = selectedSet.has(lane.pipeline_id);
                  const kellyOn = kellySet.has(lane.pipeline_id);
                  const diverge = laneView === "compare" && saOn !== kellyOn;
                  return (
                    <tr key={lane.pipeline_id}>
                      <td>{strategyDisplay(lane.pipeline_id)}</td>
                      <td>{lane.net_bps.toFixed(1)}</td>
                      <td>{lane.return_std.toFixed(3)}</td>
                      <td>{lane.trade_count}</td>
                      <td>
                        <Tag kind="info">{lane.cluster}</Tag>
                      </td>
                      {(laneView === "sa" || laneView === "compare") && (
                        <td>
                          <Tag kind={saOn ? "healthy" : "neutral"}>{saOn ? "selected" : "—"}</Tag>
                        </td>
                      )}
                      {(laneView === "kelly" || laneView === "compare") && (
                        <td>
                          <Tag kind={kellyOn ? "healthy" : diverge ? "watch" : "neutral"}>
                            {kellyOn
                              ? "funded"
                              : (qi.kelly.excluded as Record<string, string>)[lane.pipeline_id] ??
                                "—"}
                          </Tag>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 10 }}>
            Reward vector (Kelly-like): {qi.result.rewards.map((r) => r.toFixed(2)).join(" · ")}
          </p>
        </Card>

        <Card title="SA vs Kelly comparison">
          <DetailRow k="QI selected" v={qi.result.selected_pipeline_ids.join(", ")} />
          <DetailRow k="Kelly funded" v={qi.kelly.allocations.map((a) => a.pipeline_id).join(", ")} />
          <DetailRow k="Overlap" v={qi.comparison.overlap.join(", ") || "—"} />
          <DetailRow
            k="QI only"
            v={qi.comparison.qi_only.length ? qi.comparison.qi_only.join(", ") : "—"}
          />
          <DetailRow
            k="Kelly only"
            v={qi.comparison.kelly_only.length ? qi.comparison.kelly_only.join(", ") : "—"}
          />
          <DetailRow k="Deployed (Kelly)" v={`$${qi.kelly.deployed_usd.toLocaleString()} (${(qi.kelly.utilization * 100).toFixed(1)}%)`} />
          <p className="muted small" style={{ marginTop: 12, marginBottom: 0 }}>
            {qi.kelly.notes.map((n) => (
              <span key={n} style={{ display: "block" }}>
                {n}
              </span>
            ))}
          </p>
        </Card>
      </div>

      {laneView === "kelly" && (
        <Card title="Kelly allocations" style={{ marginTop: 14 }}>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>Target $</th>
                  <th>Weight</th>
                  <th>Signal</th>
                  <th>Cluster</th>
                </tr>
              </thead>
              <tbody>
                {qi.kelly.allocations.map((a) => (
                  <tr key={a.pipeline_id}>
                    <td>{strategyDisplay(a.pipeline_id)}</td>
                    <td>${a.target_notional_usd.toLocaleString()}</td>
                    <td>{(a.weight * 100).toFixed(1)}%</td>
                    <td>{a.kelly_signal.toFixed(2)}</td>
                    <td>{a.cluster}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <Card title="QUBO config">
          <DetailRow k="k (target lanes)" v={String(qi.config.k)} />
          <DetailRow k="seed" v={String(qi.config.seed)} />
          <DetailRow k="sweeps" v={String(qi.config.sweeps)} />
          <DetailRow k="risk_lambda" v={String(qi.config.risk_lambda)} />
          <DetailRow k="cluster_penalty" v={String(qi.config.cluster_penalty)} />
          <DetailRow k="cardinality_lambda" v={String(qi.config.cardinality_lambda)} />
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            CLI: <span className="mono">{qi.cli}</span>
          </p>
        </Card>

        <Card
          title="Alt scenarios"
          action={
            <div style={{ display: "flex", gap: 6 }}>
              {qi.altScenarios.map((s, i) => (
                <button
                  key={s.label}
                  type="button"
                  className={`btn small${scenarioIdx === i ? " primary" : ""}`}
                  onClick={() => setScenarioIdx(i)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          }
        >
          <DetailRow k="Selected" v={scenario.selected.join(", ")} />
          <DetailRow k="Energy" v={scenario.energy.toFixed(2)} />
          <DetailRow k="Overlap" v={`${scenario.overlap_count}/${scenario.k}`} />
          <DetailRow k="QI only" v={scenario.qi_only.join(", ") || "—"} />
          <DetailRow k="Kelly only" v={scenario.kelly_only.join(", ") || "—"} />
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            Seed / k sweeps for allocator research — not promoted to live path.
          </p>
        </Card>
      </div>

      <Card title="Constraints & posture" style={{ marginTop: 14 }}>
        <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>
            <Tag kind="info">advisory_only</Tag> — no ExecutionGate or allocator service wiring
          </li>
          <li>
            Dormant quantum agents: {qi.dormantAgents.join(", ")} — classical-only mode unchanged
          </li>
          <li>
            <span className="mono">quantum.enabled</span> remains <Tag kind="neutral">false</Tag>
          </li>
          <li>Stdlib-only module: <span className="mono">titan_safety/quantum_inspired.py</span></li>
          <li>Memory sidecar: <span className="mono">workspace/memory/research/quantum-inspired.md</span></li>
        </ul>
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}

function DetailRow({ k, v }: { k: string; v: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        padding: "6px 0",
        borderBottom: "1px solid var(--border)",
        fontSize: 13,
      }}
    >
      <span className="muted">{k}</span>
      <span className="mono" style={{ textAlign: "right" }}>
        {v}
      </span>
    </div>
  );
}
