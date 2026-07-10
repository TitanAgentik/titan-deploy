import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts, Drawer, DetailGrid } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { decisionLog } from "@/lib/data";

type StatusFilter = "all" | "pending" | "resolved";
type DecisionFilter = "all" | "ALLOW" | "DENY" | "HOLD";

const LOG_DEFAULTS = {
  status: "all" as StatusFilter,
  decision: "all" as DecisionFilter,
};

export function DecisionLog() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("decisionLog", LOG_DEFAULTS);
  const [selected, setSelected] = useState<(typeof decisionLog)[number] | null>(null);

  const entries = useMemo(() => {
    return decisionLog.filter((e) => {
      if (draft.status !== "all" && e.status !== draft.status) return false;
      if (draft.decision !== "all" && e.decision !== draft.decision) return false;
      return true;
    });
  }, [draft.status, draft.decision]);

  const pending = decisionLog.filter((e) => e.status === "pending").length;

  return (
    <>
      <PageHeader
        title="Decision Log"
        subtitle="Structured trade / promotion decisions — mirrors decision_log.jsonl with confidence, BFT outcome, and reflection hooks. CLI: titan-safety audit verify."
        actions={
          <>
            <Link className="btn" to="/ai-log">
              AI Log stream
            </Link>
            <Link className="btn" to="/promotions">
              Promotions
            </Link>
            <Btn
              variant="primary"
              onClick={() => push("audit verify queued — chain OK (demo)", "ok")}
            >
              Verify chain
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
        <Metric label="Entries" value={String(decisionLog.length)} delta="demo window" />
        <Metric label="Pending" value={String(pending)} />
        <Metric label="Shown" value={String(entries.length)} />
        <Metric label="Path" value="decision_log.jsonl" delta="memory/" />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {(
          [
            ["all", "All status"],
            ["pending", "Pending"],
            ["resolved", "Resolved"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn${draft.status === id ? " primary" : ""}`}
            onClick={() => update({ status: id })}
          >
            {label}
          </button>
        ))}
        <span style={{ width: 8 }} />
        {(
          [
            ["all", "All decisions"],
            ["ALLOW", "ALLOW"],
            ["DENY", "DENY"],
            ["HOLD", "HOLD"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn${draft.decision === id ? " primary" : ""}`}
            onClick={() => update({ decision: id })}
          >
            {label}
          </button>
        ))}
      </div>

      <Card title="Log · click row for detail">
        {entries.length === 0 ? (
          <div className="empty">No entries match filters.</div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>ID</th>
                  <th>Agent</th>
                  <th>Pipeline</th>
                  <th>Decision</th>
                  <th>Conf</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr
                    key={e.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelected(e)}
                  >
                    <td className="mono">{e.ts.slice(11, 19)}</td>
                    <td className="mono">{e.id}</td>
                    <td>{e.agent}</td>
                    <td className="mono">{e.pipeline}</td>
                    <td>
                      <Tag
                        kind={
                          e.decision === "ALLOW"
                            ? "healthy"
                            : e.decision === "DENY"
                              ? "bleeding"
                              : "watch"
                        }
                      >
                        {e.decision}
                      </Tag>
                    </td>
                    <td className="mono">{e.confidence.toFixed(2)}</td>
                    <td>
                      <Tag kind={e.status === "pending" ? "watch" : "neutral"}>{e.status}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Drawer
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected?.id ?? ""}
        subtitle={selected ? `${selected.agent} · ${selected.pipeline}` : ""}
      >
        {selected ? (
          <>
            <DetailGrid
              rows={[
                { label: "Asset", value: selected.asset },
                { label: "Action", value: selected.action },
                { label: "Decision", value: selected.decision },
                { label: "Confidence", value: selected.confidence.toFixed(2) },
                {
                  label: "Alpha",
                  value: selected.alphaPct == null ? "—" : `${selected.alphaPct}%`,
                },
                { label: "Status", value: selected.status },
                { label: "Timestamp", value: selected.ts },
              ]}
            />
            <p className="muted small" style={{ marginTop: 14 }}>
              {selected.rationale}
            </p>
            <p className="mono small muted" style={{ marginBottom: 0 }}>
              titan-safety audit append / verify · memory rotation @ 500 resolved
            </p>
          </>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
