import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { deadMansSwitch, portfolio } from "@/lib/data";

const DMS_DEFAULTS = { showTimeline: true };

export function DeadMansSwitch() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("dms", DMS_DEFAULTS);

  const hours = deadMansSwitch.hoursSinceHeartbeat;
  const deriskLeft = Math.max(0, deadMansSwitch.deriskAfterHours - hours);
  const flattenLeft = Math.max(0, deadMansSwitch.flattenAfterHours - hours);
  const urgency =
    hours >= deadMansSwitch.flattenAfterHours
      ? "bleeding"
      : hours >= deadMansSwitch.deriskAfterHours
        ? "watch"
        : hours >= 24
          ? "watch"
          : "healthy";

  return (
    <>
      <PageHeader
        title="Dead Man's Switch"
        subtitle="Operator heartbeat (:19005) — derisk at 48h, flatten at 72h. Never auto-promotes. CLI: titan-safety heartbeat."
        actions={
          <>
            <Link className="btn" to="/command">
              Command Center
            </Link>
            <Link className="btn" to="/manual-control">
              Manual Control
            </Link>
            <Btn
              variant="primary"
              onClick={() =>
                push("HEARTBEAT signed — DMS timer reset (demo)", "ok")
              }
            >
              Send heartbeat
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
        <Metric
          label="Hours since heartbeat"
          value={`${hours}h`}
          delta={`last ${deadMansSwitch.lastOperator}`}
        />
        <Metric label="Derisk in" value={`${deriskLeft.toFixed(1)}h`} delta="@ 48h" />
        <Metric label="Flatten in" value={`${flattenLeft.toFixed(1)}h`} delta="@ 72h" />
        <Metric
          label="Status"
          value={deadMansSwitch.status.toUpperCase()}
          delta={portfolio.killActive ? "kill ACTIVE" : "armed"}
        />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card
          title="Policy"
          action={<Tag kind={urgency}>{urgency === "healthy" ? "OK" : "ATTENTION"}</Tag>}
        >
          <DetailRows
            rows={[
              { label: "Port", value: `:${deadMansSwitch.port}` },
              { label: "Health URL", value: deadMansSwitch.healthUrl },
              { label: "On miss", value: deadMansSwitch.onMiss },
              { label: "Auto-promote", value: deadMansSwitch.neverAutoPromote ? "NEVER" : "allowed" },
              { label: "Last heartbeat", value: deadMansSwitch.lastHeartbeatAt },
            ]}
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
            <Btn
              variant="primary"
              onClick={() => push("HEARTBEAT signed — DMS timer reset (demo)", "ok")}
            >
              Send heartbeat
            </Btn>
            <Btn
              variant="ghost"
              onClick={() => push(`CLI · ${deadMansSwitch.cliAuthSign}`, "ok")}
            >
              Copy auth sign
            </Btn>
          </div>
          <p className="mono small muted" style={{ marginTop: 12, marginBottom: 0 }}>
            {deadMansSwitch.cliHeartbeat}
          </p>
        </Card>

        <Card title="Escalation ladder">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>
              <strong>0–48h</strong> — armed · HERALD nudge near 24h
            </li>
            <li>
              <strong>48h</strong> — derisk (reduce size / wind-down safe-mode)
            </li>
            <li>
              <strong>72h</strong> — flatten + optional SIGNING_HALTED
            </li>
            <li>
              <strong>TIMEOUT on promotion</strong> — HOLD / de-risk · never auto-promote
            </li>
          </ol>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            Linked from Command Center and Manual Control. Mutating heartbeat needs HMAC in
            production.
          </p>
        </Card>
      </div>

      <Card
        title="Heartbeat timeline"
        action={
          <Btn
            variant={draft.showTimeline ? "primary" : "ghost"}
            onClick={() => update({ showTimeline: !draft.showTimeline })}
          >
            {draft.showTimeline ? "Hide" : "Show"}
          </Btn>
        }
      >
        {!draft.showTimeline ? (
          <p className="muted small" style={{ margin: 0 }}>
            Timeline hidden.
          </p>
        ) : (
          <div className="timeline">
            {deadMansSwitch.timeline.map((e) => (
              <div className="timeline-item" key={e.ts + e.event}>
                <div
                  className="rail"
                  style={{
                    background: e.event === "WARN" ? "var(--warn)" : "var(--accent)",
                  }}
                />
                <div>
                  <div className="when">
                    {e.ts} · <Tag kind={e.event === "WARN" ? "watch" : "info"}>{e.event}</Tag>{" "}
                    <span className="mono">{e.operator}</span>
                  </div>
                  <div className="what">{e.note}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}

function DetailRows({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div className="table-wrap">
      <table className="data">
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td className="muted" style={{ width: "36%" }}>
                {r.label}
              </td>
              <td className="mono">{r.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
