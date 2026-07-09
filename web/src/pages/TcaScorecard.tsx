import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { allocatorPlan, tcaScorecard } from "@/lib/data";

type Focus = "scorecard" | "allocator" | "loop";

const TCA_DEFAULTS = { focus: "scorecard" as Focus };

function verdictKind(v: string): "healthy" | "watch" | "bleeding" | "neutral" {
  if (v === "HEALTHY") return "healthy";
  if (v === "MARGINAL" || v === "INSUFFICIENT_DATA") return "watch";
  if (v === "BLEEDING") return "bleeding";
  return "neutral";
}

export function TcaScorecard() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("tcaScorecard", TCA_DEFAULTS);

  const healthy = tcaScorecard.lanes.filter((l) => l.verdict === "HEALTHY").length;
  const bleeding = tcaScorecard.lanes.filter((l) => l.verdict === "BLEEDING").length;

  return (
    <>
      <PageHeader
        title="TCA & Allocator"
        subtitle="Transaction-cost scorecards (:19007) and CapitalAllocator plan (:19006). Profit loop auto-defunds BLEEDING — re-fund needs human YES."
        actions={
          <>
            <Link className="btn" to="/ops">
              Ops Center
            </Link>
            <Link className="btn" to="/qi-optimizer">
              QI Optimizer
            </Link>
            <Btn
              variant="primary"
              onClick={() =>
                push("Dry-run profit loop queued — no defund writes (demo)", "ok")
              }
            >
              Dry-run profit loop
            </Btn>
          </>
        }
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        onSave={() => {
          save();
          push("Saved locally", "ok");
        }}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Lanes tracked" value={String(tcaScorecard.lanes.length)} />
        <Metric label="HEALTHY" value={String(healthy)} deltaDir="up" />
        <Metric label="BLEEDING" value={String(bleeding)} deltaDir="down" delta="auto-defund" />
        <Metric
          label="Defunded"
          value={tcaScorecard.defundedLanes.join(", ") || "—"}
          delta="human YES to re-fund"
        />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {(
          [
            ["scorecard", "Scorecard"],
            ["allocator", "Allocator plan"],
            ["loop", "Profit loop"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn${draft.focus === id ? " primary" : ""}`}
            onClick={() => update({ focus: id })}
          >
            {label}
          </button>
        ))}
      </div>

      {(draft.focus === "scorecard" || draft.focus === "loop") && (
        <Card
          title="Lane scorecards"
          style={{ marginBottom: 14 }}
          action={<Tag kind="info">:19007</Tag>}
        >
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Lane</th>
                  <th>Net bps</th>
                  <th>Fills</th>
                  <th>Fill rate</th>
                  <th>Tip eff.</th>
                  <th>Slip bps</th>
                  <th>Decay</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {tcaScorecard.lanes.map((l) => (
                  <tr key={l.pipelineId}>
                    <td>
                      {l.pipelineId} · {l.name}
                    </td>
                    <td className="mono">{l.netBps.toFixed(1)}</td>
                    <td>{l.fills}</td>
                    <td>{(l.fillRate * 100).toFixed(0)}%</td>
                    <td>{(l.tipEfficiency * 100).toFixed(0)}%</td>
                    <td>{l.slippageBps.toFixed(1)}</td>
                    <td className="mono">{l.decaySlopeBps.toFixed(1)}</td>
                    <td>
                      <Tag kind={verdictKind(l.verdict)}>{l.verdict}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            Thresholds · healthy ≥{tcaScorecard.healthyNetBps} bps · tip ≤
            {(tcaScorecard.maxTipEfficiency * 100).toFixed(0)}% · min fills{" "}
            {tcaScorecard.minFillsForVerdict} · last ingest {tcaScorecard.lastIngestAt}
          </p>
        </Card>
      )}

      {(draft.focus === "allocator" || draft.focus === "loop") && (
        <Card
          title="Allocator plan"
          style={{ marginBottom: 14 }}
          action={<Tag kind="info">:19006</Tag>}
        >
          <div className="grid grid-4" style={{ marginBottom: 12 }}>
            <Metric label="Equity" value={`$${Math.round(allocatorPlan.equityUsd).toLocaleString()}`} />
            <Metric label="Max active" value={String(allocatorPlan.maxActive)} />
            <Metric label="Regime" value={allocatorPlan.regime} />
            <Metric label="Last plan" value={allocatorPlan.lastPlanAt.slice(11, 19) + "Z"} />
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>Weight</th>
                  <th>Notional</th>
                  <th>Capped by</th>
                </tr>
              </thead>
              <tbody>
                {allocatorPlan.allocations.map((a) => (
                  <tr key={a.pipelineId}>
                    <td className="mono">{a.pipelineId}</td>
                    <td>{(a.weight * 100).toFixed(0)}%</td>
                    <td>${a.notionalUsd.toLocaleString()}</td>
                    <td>
                      {a.cappedBy ? (
                        <Tag kind={a.cappedBy === "defunded" ? "bleeding" : "watch"}>
                          {a.cappedBy}
                        </Tag>
                      ) : (
                        <Tag kind="healthy">—</Tag>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="muted small" style={{ marginBottom: 0, marginTop: 12, paddingLeft: 18 }}>
            {allocatorPlan.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </Card>
      )}

      {draft.focus === "loop" && (
        <Card title="Profit loop">
          <p className="muted small" style={{ marginTop: 0 }}>
            After TCA ingest: read scorecards → zero BLEEDING → write defund ledger → halt pipeline.
            Re-funding requires human YES (never auto).
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn
              variant="primary"
              onClick={() =>
                push("Dry-run · would_defund=" + tcaScorecard.defundedLanes.join(","), "ok")
              }
            >
              Run dry-run
            </Btn>
            <Btn
              variant="ghost"
              onClick={() => push(`CLI · ${tcaScorecard.cliScorecard}`, "ok")}
            >
              Copy scorecard CLI
            </Btn>
            <Link className="btn" to="/promotions">
              Promotions / re-fund
            </Link>
          </div>
          <p className="mono small muted" style={{ marginTop: 12, marginBottom: 0 }}>
            {tcaScorecard.cliProfitLoop}
          </p>
        </Card>
      )}

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
