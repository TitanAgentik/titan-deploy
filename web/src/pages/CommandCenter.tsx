import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Btn, Tag } from "@/components/ui";
import {
  ActionMenu,
  DetailGrid,
  Modal,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import { portfolio } from "@/lib/data";

export function CommandCenter() {
  const { toasts, push: toast, dismiss } = useToasts();
  const [kill, setKill] = useState(portfolio.killActive);
  const [frozen, setFrozen] = useState(portfolio.evolutionFrozen);
  const [log, setLog] = useState<string[]>([]);
  const [killModal, setKillModal] = useState(false);
  const [resumeModal, setResumeModal] = useState(false);
  const [flattenModal, setFlattenModal] = useState(false);
  const [scope, setScope] = useState<"global" | "portfolio" | "pipeline">("global");
  const [pipelineId, setPipelineId] = useState("P12");
  const [revokeKeys, setRevokeKeys] = useState(true);
  const [reason, setReason] = useState("operator command");

  const push = (msg: string) => {
    setLog((l) => [`${new Date().toISOString()}  ${msg}`, ...l].slice(0, 12));
    toast(msg);
  };

  return (
    <>
      <PageHeader
        title="Command Center"
        subtitle="Every control opens a confirmation with scope / options. Mutating calls need HMAC in production. Full operator console: Manual Control."
        actions={
          <>
            <Link className="btn primary" to="/manual-control">
              Manual Control
            </Link>
            <ActionMenu
              label="Emergency"
              variant="danger"
              items={[
                { label: "Activate kill…", onClick: () => setKillModal(true) },
                { label: "Flatten all…", onClick: () => setFlattenModal(true) },
                { label: "Send DMS heartbeat", onClick: () => push("HEARTBEAT signed") },
              ]}
            />
          </>
        }
      />

      <div className="grid grid-3" style={{ marginBottom: 14 }}>
        <Card
          title="Kill switch"
          action={
            <ActionMenu
              label="⋯"
              variant="ghost"
              items={[
                { label: "Activate…", onClick: () => setKillModal(true) },
                { label: "Signed resume…", disabled: !kill, onClick: () => setResumeModal(true) },
                { label: "Copy CLI activate", onClick: () => push("titan-safety kill activate --operator YOU") },
              ]}
            />
          }
        >
          <p className="muted small" style={{ marginTop: 0 }}>
            Global halt. Deactivate requires signed RESUME.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            <Btn variant="danger" onClick={() => setKillModal(true)}>
              Activate…
            </Btn>
            <Btn disabled={!kill} onClick={() => setResumeModal(true)}>
              Signed resume…
            </Btn>
          </div>
          <div style={{ marginTop: 12 }}>
            <Tag kind={kill ? "bleeding" : "healthy"}>{kill ? "ACTIVE" : "CLEAR"}</Tag>
          </div>
        </Card>

        <Card
          title="Flatten / wind-down"
          action={
            <ActionMenu
              label="⋯"
              variant="ghost"
              items={[
                { label: "Flatten options…", onClick: () => setFlattenModal(true) },
                { label: "Derisk only", onClick: () => push("Wind-down derisk started") },
                { label: "View flatten_status", onClick: () => push("GET /v1/flatten_status") },
              ]}
            />
          }
        >
          <p className="muted small" style={{ marginTop: 0 }}>
            FlattenExecutor + optional key revoke / SIGNING_HALTED.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            <Btn variant="danger" onClick={() => setFlattenModal(true)}>
              Flatten…
            </Btn>
            <Btn onClick={() => push("Wind-down derisk started")}>Start derisk</Btn>
          </div>
        </Card>

        <Card title="Evolution freeze">
          <p className="muted small" style={{ marginTop: 0 }}>
            Blocks live promotions while capital is at risk.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            <Btn
              onClick={() => {
                setFrozen(true);
                push("evolution freeze ON");
              }}
            >
              Freeze
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                setFrozen(false);
                push("evolution unfrozen");
              }}
            >
              Unfreeze
            </Btn>
            <ActionMenu
              label="More"
              items={[
                { label: "Status JSON", onClick: () => push("evolution status → FROZEN=" + frozen) },
                { label: "Open Promotions", onClick: () => toast("Use sidebar → Promotions") },
              ]}
            />
          </div>
          <div style={{ marginTop: 12 }}>
            <Tag kind={frozen ? "watch" : "healthy"}>{frozen ? "FROZEN" : "OPEN"}</Tag>
          </div>
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="Capital ledger">
          <p className="muted small" style={{ marginTop: 0 }}>
            Deposit, withdraw, wallets, and Trezor Safe 7 sweeps.
          </p>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn primary" to="/capital">
              Open Capital &amp; Wallets
            </Link>
            <ActionMenu
              label="Jump to"
              items={[
                { label: "Deposit tab", onClick: () => toast("Open /capital → Deposit") },
                { label: "Withdraw tab", onClick: () => toast("Open /capital → Withdraw") },
                { label: "Safe 7 sweeps", onClick: () => toast("Open /capital → Sweep") },
              ]}
            />
          </div>
        </Card>

        <Card title="Operator heartbeat (DMS)">
          <p className="muted small" style={{ marginTop: 0 }}>
            Hours since last heartbeat:{" "}
            <span className="mono">{portfolio.dmsHoursSinceHeartbeat}</span> · derisk @ 48h · flatten
            @ 72h
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn variant="primary" onClick={() => push("HEARTBEAT signed — DMS timer reset")}>
              Send heartbeat
            </Btn>
            <ActionMenu
              label="Options"
              items={[
                { label: "Sign HEARTBEAT token", onClick: () => push("titan-safety auth sign --command HEARTBEAT") },
                { label: "View DMS status", onClick: () => push("GET :19005/health") },
              ]}
            />
          </div>
        </Card>
      </div>

      <Card title="Command audit" style={{ marginTop: 14 }}>
        {log.length === 0 ? (
          <div className="empty">No commands yet — use the buttons above.</div>
        ) : (
          <div className="timeline">
            {log.map((line) => (
              <div className="timeline-item" key={line}>
                <div className="rail" />
                <div>
                  <div className="when mono">{line.slice(0, 20)}</div>
                  <div className="what mono">{line.slice(21)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal
        open={killModal}
        onClose={() => setKillModal(false)}
        title="Activate kill switch"
        subtitle="Choose scope and reason"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setKillModal(false)}>
              Cancel
            </Btn>
            <Btn
              variant="danger"
              onClick={() => {
                setKill(true);
                push(`KILL activated — scope=${scope}${scope === "pipeline" ? ":" + pipelineId : ""} · ${reason}`);
                setKillModal(false);
              }}
            >
              Activate kill
            </Btn>
          </>
        }
      >
        <div className="option-grid" style={{ marginBottom: 12 }}>
          {(
            [
              ["global", "All trading"],
              ["portfolio", "Portfolio halt"],
              ["pipeline", "Single pipeline"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`option-tile${scope === id ? " active" : ""}`}
              onClick={() => setScope(id)}
            >
              <strong>{label}</strong>
              <span>{id}</span>
            </button>
          ))}
        </div>
        {scope === "pipeline" && (
          <div className="field" style={{ marginBottom: 12 }}>
            <label>Pipeline ID</label>
            <input value={pipelineId} onChange={(e) => setPipelineId(e.target.value)} />
          </div>
        )}
        <div className="field">
          <label>Reason</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <Modal
        open={resumeModal}
        onClose={() => setResumeModal(false)}
        title="Signed RESUME"
        subtitle="kill sign --command RESUME then deactivate --signed"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setResumeModal(false)}>
              Cancel
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                setKill(false);
                push("RESUME signed — kill deactivated");
                setResumeModal(false);
              }}
            >
              Apply signed resume
            </Btn>
          </>
        }
      >
        <DetailGrid
          rows={[
            { label: "Step 1", value: "titan-safety kill sign --command RESUME --operator YOU" },
            { label: "Step 2", value: "kill deactivate --signed $TOKEN" },
            { label: "Auth", value: "HMAC control_plane.secret" },
          ]}
        />
      </Modal>

      <Modal
        open={flattenModal}
        onClose={() => setFlattenModal(false)}
        title="Flatten options"
        subtitle="POST /v1/flatten via FlattenExecutor"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setFlattenModal(false)}>
              Cancel
            </Btn>
            <Btn
              variant="danger"
              onClick={() => {
                push(`FLATTEN revoke_keys=${revokeKeys} · ${reason}`);
                setFlattenModal(false);
              }}
            >
              Execute flatten
            </Btn>
          </>
        }
      >
        <div className="option-grid" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className={`option-tile${revokeKeys ? " active" : ""}`}
            onClick={() => setRevokeKeys(true)}
          >
            <strong>Revoke keys</strong>
            <span>SIGNING_HALTED</span>
          </button>
          <button
            type="button"
            className={`option-tile${!revokeKeys ? " active" : ""}`}
            onClick={() => setRevokeKeys(false)}
          >
            <strong>Keep keys</strong>
            <span>close only</span>
          </button>
        </div>
        <div className="field">
          <label>Reason</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
