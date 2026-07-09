import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { powerStatus } from "@/lib/data";

const POWER_DEFAULTS = { showTiming: true };

export function PowerStatus() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("power", POWER_DEFAULTS);

  const loadPct = Math.round((powerStatus.loadWatts / powerStatus.capacityWatts) * 100);
  const runtimeOk = powerStatus.runtimeMinutes >= powerStatus.minimumRuntimeMinutes;

  return (
    <>
      <PageHeader
        title="Power & UPS"
        subtitle="Live capital requires UPS. Power-loss = HALT — flatten, revoke session keys, no discretionary signing. Spec: power_requirements.yaml."
        actions={
          <>
            <Link className="btn" to="/health">
              Health & Verify
            </Link>
            <Link className="btn" to="/signing">
              Signing Node
            </Link>
            <Btn
              variant="primary"
              onClick={() => push("UPS status refresh queued (demo)", "ok")}
            >
              Refresh status
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
          label="Mains"
          value={powerStatus.onMains ? "ON" : "OFF"}
          delta={powerStatus.onBattery ? "ON BATTERY" : "utility"}
        />
        <Metric
          label="Runtime"
          value={`${powerStatus.runtimeMinutes}m`}
          delta={`min ${powerStatus.minimumRuntimeMinutes}m`}
        />
        <Metric label="Load" value={`${loadPct}%`} delta={`${powerStatus.loadWatts}W / ${powerStatus.capacityWatts}W`} />
        <Metric
          label="UPS ack"
          value={powerStatus.upsAcknowledged ? "YES" : "NO"}
          delta={powerStatus.liveCapitalRequiresUps ? "required for live" : "optional"}
        />
      </div>

      {!powerStatus.onMains || powerStatus.onBattery ? (
        <div className="alert-banner" style={{ marginBottom: 14 }}>
          <strong>Power event</strong> — policy mandates halt_trading · flatten · revoke keys ·{" "}
          {powerStatus.onPowerLoss.cb}
        </div>
      ) : null}

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card
          title="UPS"
          action={
            <Tag kind={runtimeOk && powerStatus.onMains ? "healthy" : "bleeding"}>
              {powerStatus.onMains ? "MAINS" : "BATTERY"}
            </Tag>
          }
        >
          <p className="muted small" style={{ marginTop: 0 }}>
            {powerStatus.model}
          </p>
          <div className="table-wrap">
            <table className="data">
              <tbody>
                <tr>
                  <td className="muted">Service</td>
                  <td className="mono">{powerStatus.service}</td>
                </tr>
                <tr>
                  <td className="muted">Alert below</td>
                  <td>{powerStatus.alertOnRuntimeBelowMinutes}m runtime</td>
                </tr>
                <tr>
                  <td className="muted">Policy</td>
                  <td className="mono">{powerStatus.policyRef}</td>
                </tr>
                <tr>
                  <td className="muted">On loss</td>
                  <td>
                    {powerStatus.onPowerLoss.action} · flatten=
                    {String(powerStatus.onPowerLoss.flatten)} · revoke=
                    {String(powerStatus.onPowerLoss.revokeKeys)}
                  </td>
                </tr>
                <tr>
                  <td className="muted">CB</td>
                  <td className="mono">{powerStatus.onPowerLoss.cb}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Protected outlets">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Outlet</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {powerStatus.protectedOutlets.map((o) => (
                  <tr key={o.id}>
                    <td className="mono">{o.id}</td>
                    <td>
                      <Tag kind="healthy">{o.status.toUpperCase()}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card
        title="Timing chain (GPSDO / NIC)"
        action={
          <Btn
            variant={draft.showTiming ? "primary" : "ghost"}
            onClick={() => update({ showTiming: !draft.showTiming })}
          >
            {draft.showTiming ? "Hide" : "Show"}
          </Btn>
        }
      >
        {!draft.showTiming ? (
          <p className="muted small" style={{ margin: 0 }}>
            Timing details hidden.
          </p>
        ) : (
          <>
            <div className="grid grid-4">
              <Metric label="GPSDO" value={powerStatus.timing.gpsdo} />
              <Metric label="NIC" value={powerStatus.timing.nic.split(" ")[0]} delta={powerStatus.timing.nic} />
              <Metric label="PPS" value={powerStatus.timing.ppsState.toUpperCase()} />
              <Metric
                label="PPS lost → degrade"
                value={`${powerStatus.timing.onPpsLostMinutes}m`}
                delta={powerStatus.timing.fallback}
              />
            </div>
            <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
              Signing node and TITANHOME share UPS protection — live capital gate fails in verify.sh
              without ups_acknowledged.
            </p>
          </>
        )}
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
