import { PageHeader, Card, Tag, Metric, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { advisoryLabel, useSigning } from "@/lib/providers";

const SIGNING_DEFAULTS = { showKeys: true };

export function Signing() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("signing", SIGNING_DEFAULTS);
  const { result: signing, loading, refresh } = useSigning();
  const snap = signing?.data;

  return (
    <>
      <PageHeader
        title="Signing"
        subtitle="In-process titan-safety SigningNode — refuses to sign without fresh X-Titan-Gate-Receipt (max 30s). No :19010 daemon required."
        actions={
          <>
            <span className="chip">{advisoryLabel(signing)}</span>
            <Btn
              variant="ghost"
              disabled={loading}
              onClick={() => {
                void refresh().then(() => push("Signing status refreshed", "ok"));
              }}
            >
              Refresh
            </Btn>
            <Btn
              variant={draft.showKeys ? "primary" : "ghost"}
              onClick={() => update({ showKeys: !draft.showKeys })}
            >
              {draft.showKeys ? "Hide" : "Show"} audit log
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
        <Metric label="Mode" value="in-process" delta="titan-safety" />
        <Metric label="Receipt TTL" value={`${snap?.receiptTtlSec ?? 30}s`} />
        <Metric label="Blind sign" value={snap?.blindSign ?? "REJECTED"} />
        <Metric
          label="Daemon :19010"
          value="NOT REQUIRED"
          delta={snap?.halted ? "SIGNING_HALTED" : "optional legacy only"}
        />
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
            SIGNING_HALTED. Live capital still requires an in-process signer — never a mandatory
            :19010 hop.
          </p>
          {signing?.error ? (
            <p className="muted small" style={{ marginTop: 8 }}>
              Provider note: {signing.error}
            </p>
          ) : null}
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
                  {(snap?.audit ?? []).map((r) => (
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
