import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { verifyChecklist, type VerifyCheckStatus } from "@/lib/data";
import { advisoryLabel, useHealth } from "@/lib/providers";

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
  const { result: health, loading, refresh } = useHealth();
  const [probing, setProbing] = useState(false);

  const groups =
    draft.group === "all"
      ? verifyChecklist.groups
      : verifyChecklist.groups.filter((g) => g.id === draft.group);

  const passCount = verifyChecklist.groups
    .flatMap((g) => g.checks)
    .filter((c) => c.status === "pass").length;
  const totalChecks = verifyChecklist.groups.flatMap((g) => g.checks).length;

  const inventory = health?.data
    ? [
        ...health.data.services,
        health.data.inProcessSigning,
        health.data.optionalLegacySigning,
      ]
    : [];

  const runProbe = useCallback(async () => {
    setProbing(true);
    try {
      const r = await refresh();
      push(
        r.data.reachable
          ? `Health probe · overall=${r.data.overall}`
          : "Status agg unreachable — showing checklist / fixture inventory",
        r.data.reachable ? "ok" : "warn",
      );
    } finally {
      setProbing(false);
    }
  }, [push, refresh]);

  return (
    <>
      <PageHeader
        title="Health & Verify"
        subtitle="Operator checklist mirroring verify.sh + safety ports :19001–:19008. Signing is in-process (not a required :19010 health fail)."
        actions={
          <>
            <span className="chip">{advisoryLabel(health)}</span>
            <Link className="btn" to="/forge">
              Forge
            </Link>
            <Link className="btn" to="/power">
              Power / UPS
            </Link>
            <Btn variant="primary" disabled={probing || loading} onClick={() => void runProbe()}>
              {probing || loading ? "Probing…" : "Probe :19003"}
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
          value={health?.data.overall ? health.data.overall.toUpperCase() : "—"}
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

      <Card title="Service inventory">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Service</th>
                <th>Port</th>
                <th>Kind</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((s) => (
                <tr key={s.name}>
                  <td className="mono">
                    {s.kind === "in_process" || s.kind === "optional_legacy"
                      ? s.name
                      : `titan-${s.name}`}
                  </td>
                  <td className="mono">{s.port != null ? `:${s.port}` : "in-process"}</td>
                  <td className="muted small">
                    {s.kind === "optional_legacy"
                      ? "optional"
                      : s.kind === "in_process"
                        ? "in-process"
                        : "safety"}
                  </td>
                  <td>
                    <Tag
                      kind={
                        s.kind === "optional_legacy"
                          ? "neutral"
                          : s.ok
                            ? "healthy"
                            : "bleeding"
                      }
                    >
                      {s.kind === "optional_legacy"
                        ? "OPTIONAL"
                        : s.ok
                          ? "UP"
                          : "DOWN"}
                    </Tag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
          CLI · <span className="mono">{verifyChecklist.script}</span> · fails live capital without
          UPS ack. Required safety ports are :19001–:19008. Signing is in-process in titan-safety —
          :19010 is optional legacy HTTP only (never a mandatory health fail).
        </p>
        {health?.error ? (
          <p className="muted small" style={{ marginTop: 8 }}>
            Provider note: {health.error}
          </p>
        ) : null}
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
