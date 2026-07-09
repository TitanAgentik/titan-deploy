import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { autonomyMatrix } from "@/lib/data";

const IDENTITY_DEFAULTS = { showMatrix: true };

export function Identity() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("identity", IDENTITY_DEFAULTS);

  return (
    <>
      <PageHeader
        title="Identity"
        subtitle="Operator + system identity — SOUL / IDENTITY bootstrap, bounded autonomy matrix, signing isolation."
        actions={
          <Btn
            variant={draft.showMatrix ? "primary" : "ghost"}
            onClick={() => update({ showMatrix: !draft.showMatrix })}
          >
            {draft.showMatrix ? "Hide" : "Show"} autonomy matrix
          </Btn>
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

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Operator">
          <div className="mono" style={{ fontSize: 20 }}>
            Hyperion
          </div>
          <p className="muted small">Primary operator · Telegram primary on EDGE-FRA · Trezor Safe 7 sweeps</p>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Tag kind="info">ROLE · OWNER</Tag>
            <Tag kind="healthy">MFA · TPM</Tag>
            <Tag kind="watch">DMS · ARMED</Tag>
          </div>
        </Card>
        <Card title="System persona">
          <div className="mono" style={{ fontSize: 20 }}>
            Titan Agentik · OpenClaw + Hermes
          </div>
          <p className="muted small">
            Capital-preservation-first. No closed/cloud models on live path. Quantum agents DORMANT.
          </p>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Tag kind="healthy">23 AGENTS</Tag>
            <Tag kind="info">47 PIPELINES</Tag>
            <Tag kind="neutral">CLASSICAL ONLY</Tag>
          </div>
        </Card>
      </div>

      {draft.showMatrix ? (
        <Card title="Bounded autonomy matrix (enforced)">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Auto-execute</th>
                  <th>Human YES</th>
                </tr>
              </thead>
              <tbody>
                {autonomyMatrix.map((row) => (
                  <tr key={row.action}>
                    <td>{row.action}</td>
                    <td>
                      <Tag kind={row.auto ? "healthy" : "neutral"}>{row.auto ? "YES" : "—"}</Tag>
                    </td>
                    <td>
                      <Tag kind={!row.auto ? "watch" : "neutral"}>
                        {row.note ?? (!row.auto ? "YES" : "—")}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
