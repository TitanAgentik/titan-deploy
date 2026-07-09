import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import {
  probeHealth,
  services,
  verifyChecklist,
  type VerifyCheckStatus,
} from "@/lib/data";

type GroupFilter = "all" | "bootstrap" | "config" | "safety" | "live_gates";

const HEALTH_DEFAULTS = { group: "all" as GroupFilter };

function statusKind(s: VerifyCheckStatus): "healthy" | "bleeding" | "watch" | "neutral" {
  if (s === "pass") return "healthy";
  if (s === "fail") return "bleeding";
  if (s === "warn") return "watch";
  return "neutral";
}

export function HealthVerify() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("healthVerify", HEALTH_DEFAULTS);
  const [probing, setProbing] = useState(false);
  const [liveOverall, setLiveOverall] = useState<string | null>(null);

  const groups =
    draft.group === "all"
      ? verifyChecklist.groups
      : verifyChecklist.groups.filter((g) => g.id === draft.group);

  const passCount = verifyChecklist.groups
    .flatMap((g) => g.checks)
    .filter((c) => c.status === "pass").length;
  const totalChecks = verifyChecklist.groups.flatMap((g) => g.checks).length;

  const runProbe = useCallback(async () => {
    setProbing(true);
    try {
      const r = await probeHealth();
      if (!r.reachable) {
        setLiveOverall("unreachable");
        push("Status agg unreachable — showing checklist demo data", "warn");
      } else {
        setLiveOverall(r.overall);
        push(`Health probe · overall=${r.overall} · ${r.services.length} services`, "ok");
      }
    } finally {
      setProbing(false);
    }
  }, [push]);

  return (
    <>
      <PageHeader
        title="Health & Verify"
        subtitle="Operator checklist mirroring verify.sh + safety service ports. Live probe hits status-agg :19003 when available."
        actions={
          <>
            <Link className="btn" to="/forge">
              Forge
            </Link>
            <Link className="btn" to="/power">
              Power / UPS
            </Link>
            <Btn variant="primary" disabled={probing} onClick={() => void runProbe()}>
              {probing ? "Probing…" : "Probe :19003"}
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
          label="Checklist"
          value={`${passCount}/${totalChecks}`}
          delta={verifyChecklist.overall.toUpperCase()}
        />
        <Metric label="Last verify" value={verifyChecklist.lastRunAt.slice(11, 19) + "Z"} />
        <Metric
          label="Live probe"
          value={liveOverall ? liveOverall.toUpperCase() : "—"}
          delta="status-agg"
        />
        <Metric label="Script" value="verify.sh" delta="repo root" />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {(
          [
            ["all", "All"],
            ["bootstrap", "Bootstrap"],
            ["config", "Config"],
            ["safety", "Safety"],
            ["live_gates", "Live gates"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn${draft.group === id ? " primary" : ""}`}
            onClick={() => update({ group: id })}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        {groups.map((g) => (
          <Card key={g.id} title={g.label}>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Check</th>
                    <th>Port</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {g.checks.map((c) => (
                    <tr key={c.id}>
                      <td>{c.label}</td>
                      <td className="mono">{"port" in c && c.port ? `:${c.port}` : "—"}</td>
                      <td>
                        <Tag kind={statusKind(c.status)}>{c.status.toUpperCase()}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </div>

      <Card title="Safety service inventory (demo)">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Service</th>
                <th>Port</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {services.map((s) => (
                <tr key={s.name}>
                  <td className="mono">titan-{s.name}</td>
                  <td className="mono">:{s.port}</td>
                  <td>
                    <Tag kind={s.ok ? "healthy" : "bleeding"}>{s.ok ? "UP" : "DOWN"}</Tag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
          CLI · <span className="mono">{verifyChecklist.script}</span> · fails live capital without
          UPS ack
        </p>
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
