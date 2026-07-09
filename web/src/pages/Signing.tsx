import { PageHeader, Card, Tag, Metric, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { signingAudit } from "@/lib/data";

const SIGNING_DEFAULTS = { showKeys: true };

export function Signing() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("signing", SIGNING_DEFAULTS);

  return (
    <>
      <PageHeader
        title="Signing Node"
        subtitle="Isolated signing at :19010 — refuses POST /v1/sign without fresh X-Titan-Gate-Receipt (max 30s)."
        actions={
          <Btn
            variant={draft.showKeys ? "primary" : "ghost"}
            onClick={() => update({ showKeys: !draft.showKeys })}
          >
            {draft.showKeys ? "Hide" : "Show"} audit log
          </Btn>
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
        <Metric label="Endpoint" value=":19010" />
        <Metric label="Receipt TTL" value="30s" />
        <Metric label="Blind sign" value="REJECTED" />
        <Metric label="Live signer" value="REQUIRED" delta="capital_profile=live" />
      </div>
      <div className="grid grid-2">
        <Card title="Pre-sign gates">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>guardian_risk_validation</li>
            <li>execution_gate_allow_receipt</li>
            <li>risk_kernel_pre_trade</li>
            <li>tenderly_simulation (bridges)</li>
            <li>eip712_typed_data_only</li>
          </ol>
          <p className="muted small" style={{ marginTop: 12 }}>
            On compromise: halt_all_signing · CB_KEYS_SIGNING_ENV_COMPROMISED · file flag
            SIGNING_HALTED
          </p>
        </Card>
        {draft.showKeys ? (
          <Card title="Audit (recent)">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Code</th>
                    <th>Trade</th>
                  </tr>
                </thead>
                <tbody>
                  {signingAudit.map((r) => (
                    <tr key={r.ts + r.code}>
                      <td>{r.ts.slice(11, 19)}</td>
                      <td>
                        <Tag
                          kind={
                            r.action === "allow"
                              ? "healthy"
                              : r.action === "halt"
                                ? "bleeding"
                                : "watch"
                          }
                        >
                          {r.action}
                        </Tag>
                      </td>
                      <td>{r.code}</td>
                      <td>{r.trade}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ) : (
          <Card title="Audit (recent)">
            <p className="muted small" style={{ margin: 0 }}>
              Audit log hidden — toggle &quot;Show audit log&quot; to view recent signing events.
            </p>
          </Card>
        )}
      </div>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
