import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Atom,
  Bell,
  Cpu,
  GitBranch,
  KeyRound,
  Lock,
  Radio,
  Save,
  Shield,
  ShieldAlert,
  Skull,
  Snowflake,
  Wallet,
} from "lucide-react";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import {
  ActionMenu,
  DetailGrid,
  Modal,
  SelectField,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import {
  circuitBreakers,
  drawdownPolicy,
  edgePops,
  manualControl,
  portfolio,
  type HeraldAlertLevel,
  type ManualPipelineControl,
  type WindDownMode,
} from "@/lib/data";
import { getHmacToken } from "@/lib/auth";
import {
  postAllocatorRefresh,
  postEdgeSelect,
  postEvolutionFreeze,
  postHeraldAlertLevel,
  postHoneypotArm,
  postKillActivate,
  postKillResume,
  postLockdown,
  postPipelineAdvisory,
  postPipelineHalt,
  postPromotionHold,
  postSigningHalt,
  postTradingHalt,
  postWindDown,
  type ControlResult,
} from "@/lib/manualControlApi";
import {
  clearManualControlPrefs,
  defaultsFromSeed,
  formToPrefs,
  hydrateFormState,
  loadManualControlPrefs,
  prefsFingerprint,
  saveManualControlPrefs,
  type ManualControlFormState,
} from "@/lib/manualControlPrefs";

type ConfirmKind =
  | "kill"
  | "resume"
  | "flatten"
  | "lockdown_exec"
  | "signing_halt"
  | null;

function Badge({
  kind,
  children,
}: {
  kind: "healthy" | "bleeding" | "watch" | "info" | "neutral";
  children: ReactNode;
}) {
  return <Tag kind={kind}>{children}</Tag>;
}

function AuthNote({ hmac, humanYes }: { hmac?: boolean; humanYes?: boolean }) {
  return (
    <p className="muted small" style={{ margin: "8px 0 0" }}>
      {hmac ? (
        <span className="chip warn" style={{ marginRight: 6 }}>
          HMAC
        </span>
      ) : null}
      {humanYes ? (
        <span className="chip danger" style={{ marginRight: 6 }}>
          Human YES
        </span>
      ) : null}
      {!hmac && !humanYes ? (
        <span className="chip">advisory / demo</span>
      ) : (
        <span>required for live mutate</span>
      )}
    </p>
  );
}

function SectionHead({
  icon: Icon,
  title,
  hint,
}: {
  icon: typeof Shield;
  title: string;
  hint: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        marginBottom: 10,
      }}
    >
      <Icon size={16} style={{ color: "var(--text-dim)" }} />
      <div>
        <div style={{ fontWeight: 600, fontSize: 14 }}>{title}</div>
        <div className="muted small">{hint}</div>
      </div>
    </div>
  );
}

function applyForm(
  form: ManualControlFormState,
  setters: {
    setTradingHalted: (v: boolean) => void;
    setKillActive: (v: boolean) => void;
    setSigningHalted: (v: boolean) => void;
    setWindDown: (v: WindDownMode) => void;
    setEvolutionFrozen: (v: boolean) => void;
    setHoneypotArmed: (v: boolean) => void;
    setPromotionHold: (v: boolean) => void;
    setEdgePop: (v: string) => void;
    setHeraldLevel: (v: HeraldAlertLevel) => void;
    setMaxActivePipelines: (v: number) => void;
    setPipelines: (v: ManualPipelineControl[]) => void;
  },
) {
  setters.setTradingHalted(form.tradingHalted);
  setters.setKillActive(form.killActive);
  setters.setSigningHalted(form.signingHalted);
  setters.setWindDown(form.windDown);
  setters.setEvolutionFrozen(form.evolutionFrozen);
  setters.setHoneypotArmed(form.honeypotArmed);
  setters.setPromotionHold(form.promotionHold);
  setters.setEdgePop(form.edgePop);
  setters.setHeraldLevel(form.heraldLevel);
  setters.setMaxActivePipelines(form.maxActivePipelines);
  setters.setPipelines(form.pipelines.map((p) => ({ ...p })));
}

export function ManualControl() {
  const { toasts, push, dismiss } = useToasts();
  const seed = manualControl;
  const initial = useMemo(() => hydrateFormState(), []);

  const [tradingHalted, setTradingHalted] = useState(initial.tradingHalted);
  const [killActive, setKillActive] = useState(initial.killActive);
  const [signingHalted, setSigningHalted] = useState(initial.signingHalted);
  const [windDown, setWindDown] = useState<WindDownMode>(initial.windDown);
  const [evolutionFrozen, setEvolutionFrozen] = useState(initial.evolutionFrozen);
  const [honeypotArmed, setHoneypotArmed] = useState(initial.honeypotArmed);
  const [promotionHold, setPromotionHold] = useState(initial.promotionHold);
  const [edgePop, setEdgePop] = useState(initial.edgePop);
  const [heraldLevel, setHeraldLevel] = useState<HeraldAlertLevel>(initial.heraldLevel);
  const [maxActivePipelines, setMaxActivePipelines] = useState(initial.maxActivePipelines);
  const [pipelines, setPipelines] = useState<ManualPipelineControl[]>(initial.pipelines);
  const [savedFingerprint, setSavedFingerprint] = useState(() => {
    const existing = loadManualControlPrefs();
    return existing
      ? prefsFingerprint(existing)
      : prefsFingerprint(formToPrefs(defaultsFromSeed()));
  });
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(
    () => loadManualControlPrefs()?.savedAt ?? null,
  );
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<ConfirmKind>(null);
  const [reason, setReason] = useState("operator manual control");
  const [killScope, setKillScope] = useState<"global" | "portfolio" | "pipeline">("global");
  const [killPipeline, setKillPipeline] = useState("P12");
  const [revokeKeys, setRevokeKeys] = useState(true);
  const [lockdownDryRun, setLockdownDryRun] = useState(true);

  const formState: ManualControlFormState = useMemo(
    () => ({
      tradingHalted,
      killActive,
      signingHalted,
      windDown,
      evolutionFrozen,
      honeypotArmed,
      promotionHold,
      edgePop,
      heraldLevel,
      maxActivePipelines,
      pipelines,
    }),
    [
      tradingHalted,
      killActive,
      signingHalted,
      windDown,
      evolutionFrozen,
      honeypotArmed,
      promotionHold,
      edgePop,
      heraldLevel,
      maxActivePipelines,
      pipelines,
    ],
  );

  const dirty = useMemo(
    () => prefsFingerprint(formToPrefs(formState)) !== savedFingerprint,
    [formState, savedFingerprint],
  );

  const hasHmac = Boolean(getHmacToken());
  const overall = killActive
    ? "LOCKDOWN"
    : seed.overallPosture === "HARDENED"
      ? "HARDENED"
      : seed.overallPosture;

  const activeCount = useMemo(
    () => pipelines.filter((p) => p.runState === "running" && p.advisoryEnabled).length,
    [pipelines],
  );

  const formSetters = {
    setTradingHalted,
    setKillActive,
    setSigningHalted,
    setWindDown,
    setEvolutionFrozen,
    setHoneypotArmed,
    setPromotionHold,
    setEdgePop,
    setHeraldLevel,
    setMaxActivePipelines,
    setPipelines,
  };

  const audit = (msg: string, tone: "ok" | "warn" | "danger" = "ok") => {
    const line = `${new Date().toISOString()}  ${msg}`;
    setLog((l) => [line, ...l].slice(0, 24));
    push(msg, tone);
  };

  const applyResult = (r: ControlResult, tone?: "ok" | "warn" | "danger") => {
    const t =
      tone ??
      (r.ok ? (r.demo ? "warn" : "ok") : r.requiresHmac ? "warn" : "danger");
    audit(r.detail, t);
  };

  const run = async (fn: () => Promise<ControlResult>, onOk?: () => void) => {
    setBusy(true);
    try {
      const r = await fn();
      if (r.ok) onOk?.();
      applyResult(r);
      return r;
    } finally {
      setBusy(false);
    }
  };

  const saveLocal = () => {
    const prefs = formToPrefs(formState);
    saveManualControlPrefs(prefs);
    setSavedFingerprint(prefsFingerprint(prefs));
    setLastSavedAt(prefs.savedAt);
    push("Saved locally", "ok");
    setLog((l) =>
      [`${prefs.savedAt}  Saved locally`, ...l].slice(0, 24),
    );
  };

  const discardUnsaved = () => {
    const restored = hydrateFormState(loadManualControlPrefs());
    applyForm(restored, formSetters);
    push("Discarded unsaved changes", "warn");
  };

  const resetToDefaults = () => {
    clearManualControlPrefs();
    const defaults = defaultsFromSeed();
    applyForm(defaults, formSetters);
    const prefs = formToPrefs(defaults);
    setSavedFingerprint(prefsFingerprint(prefs));
    setLastSavedAt(null);
    push("Reset to defaults (local prefs cleared)", "warn");
  };

  return (
    <>
      <PageHeader
        eyebrow="OPERATOR · GUARDIAN · SENTINEL"
        title="Manual Control"
        subtitle="Single command center for trading, risk, security, inference, pipelines, allocator, evolution, and HERALD — demo state until wired to titan-safety HTTP. Risk kernel DENY remains authoritative."
        actions={
          <>
            <Link className="btn" to="/command">
              Command Center
            </Link>
            <Link className="btn" to="/security">
              Security Ops
            </Link>
            <ActionMenu
              label="Emergency"
              variant="danger"
              items={[
                { label: "Activate kill…", danger: true, onClick: () => setConfirm("kill") },
                { label: "Flatten all…", danger: true, onClick: () => setConfirm("flatten") },
                {
                  label: "Lockdown execute…",
                  danger: true,
                  onClick: () => {
                    setLockdownDryRun(false);
                    setConfirm("lockdown_exec");
                  },
                },
              ]}
            />
          </>
        }
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        disabled={busy}
        onSave={saveLocal}
        onDiscard={discardUnsaved}
        onResetDefaults={resetToDefaults}
      />

      {/* System posture strip */}
      <div
        className="card"
        style={{
          marginBottom: 14,
          padding: "12px 16px",
          borderColor:
            overall === "LOCKDOWN" || killActive
              ? "rgba(255, 122, 122, 0.45)"
              : "var(--border-strong)",
          background:
            overall === "LOCKDOWN" || killActive
              ? "linear-gradient(90deg, var(--danger-dim), transparent 65%)"
              : undefined,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            alignItems: "center",
          }}
        >
          <span className="muted small" style={{ marginRight: 4 }}>
            System posture
          </span>
          <span className={`chip ${overall === "HARDENED" ? "ok" : "danger"}`}>
            {overall}
          </span>
          <span className={`chip ${killActive ? "danger" : "ok"}`}>
            kill · {killActive ? "ACTIVE" : "CLEAR"}
          </span>
          <span className={`chip ${signingHalted ? "danger" : "ok"}`}>
            signing · {signingHalted ? "HALTED" : "ARMED"}
          </span>
          <span className={`chip ${tradingHalted ? "warn" : "ok"}`}>
            trading · {tradingHalted ? "HALTED" : "LIVE-READY"}
          </span>
          <span className="chip">
            capital · {seed.capitalProfile.toUpperCase()}
          </span>
          <span className="chip ok">quantum · OFF</span>
          <span className={`chip ${evolutionFrozen ? "warn" : "ok"}`}>
            evolution · {evolutionFrozen ? "FROZEN" : "OPEN"}
          </span>
          <span className={`chip ${hasHmac ? "ok" : "warn"}`}>
            HMAC · {hasHmac ? "SET" : "NOT SET"}
          </span>
          <span className="chip">
            equity · ${seed.equityUsd.toLocaleString()}
          </span>
          <span className="chip">
            active lanes · {activeCount}/{maxActivePipelines}
          </span>
        </div>
      </div>

      <div className="alert-banner">
        <AlertTriangle size={14} />
        <span>
          <strong>Fail-closed</strong> — mutating controls are advisory/demo until backends respond.
          Live path never flips <span className="mono">quantum.enabled</span>. Actions needing Human
          YES stay labeled. Kernel <span className="mono">:19001</span> DENY is authoritative.
        </span>
      </div>

      {/* 1. Trading / capital */}
      <Card
        title="1 · Trading / capital"
        style={{ marginBottom: 14 }}
        action={<Badge kind={tradingHalted || killActive ? "bleeding" : "healthy"}>
          {killActive ? "KILL" : tradingHalted ? "HALTED" : "CLEAR"}
        </Badge>}
      >
        <SectionHead
          icon={Wallet}
          title="Halt, kill, wind-down, capital overview"
          hint="Global trading posture · FlattenExecutor · capital profile"
        />
        <div className="grid grid-4" style={{ marginBottom: 12 }}>
          <Metric label="Capital profile" value={seed.capitalProfile.toUpperCase()} />
          <Metric
            label="Equity"
            value={`$${seed.equityUsd.toLocaleString()}`}
            delta={`avail $${seed.availableUsd.toLocaleString()}`}
          />
          <Metric
            label="Drawdown"
            value={`${seed.drawdownPct}%`}
            delta="notify-only"
          />
          <Metric
            label="Wind-down"
            value={windDown === "none" ? "NONE" : windDown.toUpperCase()}
            delta={windDown === "flatten" ? "danger zone" : "mode"}
          />
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <Btn
            variant="danger"
            disabled={busy || tradingHalted}
            onClick={() =>
              void run(
                () => postTradingHalt(true, "cockpit", reason),
                () => setTradingHalted(true),
              )
            }
          >
            Halt trading
          </Btn>
          <Btn
            disabled={busy || !tradingHalted || killActive}
            onClick={() =>
              void run(
                () => postTradingHalt(false, "cockpit", reason),
                () => setTradingHalted(false),
              )
            }
          >
            Resume trading
          </Btn>
          <Btn variant="danger" disabled={busy} onClick={() => setConfirm("kill")}>
            Kill switch…
          </Btn>
          <Btn disabled={busy || !killActive} onClick={() => setConfirm("resume")}>
            Signed resume…
          </Btn>
          <Btn
            disabled={busy}
            onClick={() =>
              void run(
                () => postWindDown("safe", "cockpit", reason),
                () => setWindDown("safe"),
              )
            }
          >
            Safe mode
          </Btn>
          <Btn
            disabled={busy}
            onClick={() =>
              void run(
                () => postWindDown("derisk", "cockpit", reason),
                () => setWindDown("derisk"),
              )
            }
          >
            Derisk
          </Btn>
          <Btn variant="danger" disabled={busy} onClick={() => setConfirm("flatten")}>
            Flatten…
          </Btn>
          <Link className="btn" to="/capital">
            Capital &amp; Wallets
          </Link>
        </div>
        <AuthNote hmac humanYes={false} />
        <p className="muted small" style={{ marginBottom: 0 }}>
          Kill deactivate and flatten require confirm · RESUME needs signed token · DMS{" "}
          {portfolio.dmsHoursSinceHeartbeat}h since heartbeat
        </p>
      </Card>

      {/* 2. Risk / gates */}
      <Card
        title="2 · Risk / gates"
        style={{ marginBottom: 14 }}
        action={
          <Badge kind={promotionHold ? "watch" : "healthy"}>
            {promotionHold ? "PROMO HOLD" : "PROMO OPEN"}
          </Badge>
        }
      >
        <SectionHead
          icon={ShieldAlert}
          title="Circuit breakers, BFT, confidence, gate receipts"
          hint="GUARDIAN + :19001 · drawdown notify-only · velocity fail-closed"
        />
        <div className="grid grid-3" style={{ marginBottom: 12 }}>
          <div>
            <DetailGrid
              rows={[
                { label: "BFT posture", value: seed.bftPosture.replace("_", " ") },
                { label: "Confidence floor", value: String(seed.confidenceFloor) },
                {
                  label: "Gate receipt",
                  value: `${seed.gateReceipt.state} · TTL ${seed.gateReceipt.ttlSec}s`,
                },
                { label: "Last receipt", value: seed.gateReceipt.lastIssuedAt },
              ]}
            />
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>DD tier</th>
                  <th>Action</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {circuitBreakers.map((cb) => (
                  <tr key={cb.pct}>
                    <td>{cb.pct}%</td>
                    <td className="small">{cb.action}</td>
                    <td>
                      <Badge
                        kind={seed.drawdownPct >= cb.pct ? "watch" : "healthy"}
                      >
                        {seed.drawdownPct >= cb.pct ? "NOTIFIED" : "CLEAR"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <p className="muted small" style={{ marginTop: 0 }}>
              {drawdownPolicy.note}
            </p>
            <p className="muted small">
              Velocity halt: ${drawdownPolicy.velocityHalt60s}/60s · $
              {drawdownPolicy.velocityHalt15m}/15m
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              <Btn
                disabled={busy || promotionHold}
                onClick={() =>
                  void run(
                    () => postPromotionHold(true, "cockpit"),
                    () => setPromotionHold(true),
                  )
                }
              >
                Engage promo HOLD
              </Btn>
              <Btn
                disabled={busy || !promotionHold}
                onClick={() =>
                  void run(
                    () => postPromotionHold(false, "cockpit"),
                    () => setPromotionHold(false),
                  )
                }
              >
                Clear HOLD
              </Btn>
              <Link className="btn" to="/risk">
                Risk detail
              </Link>
              <Link className="btn" to="/dms">
                Dead Man&apos;s Switch
              </Link>
              <Link className="btn" to="/promotions">
                Promotions
              </Link>
            </div>
            <AuthNote humanYes />
          </div>
        </div>
      </Card>

      {/* 3. Security */}
      <Card
        title="3 · Security"
        style={{ marginBottom: 14 }}
        action={
          <Badge kind={honeypotArmed ? "healthy" : "watch"}>
            {honeypotArmed ? "HONEYPOT ARMED" : "DISARMED"}
          </Badge>
        }
      >
        <SectionHead
          icon={Shield}
          title="Four pillars · honeypot · lockdown · edge fail-closed · signing"
          hint="Impenetrable + Evasion + Stalking + Predatory — :19008"
        />
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            marginBottom: 12,
          }}
        >
          {Object.entries(seed.pillars).map(([k, v]) => (
            <span key={k} className="chip ok">
              {k} · {v}
            </span>
          ))}
          <span className={`chip ${seed.edgeFailClosed ? "ok" : "danger"}`}>
            edge · {seed.edgeFailClosed ? "FAIL-CLOSED" : "OPEN"}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn
            disabled={busy || honeypotArmed}
            onClick={() =>
              void run(
                () => postHoneypotArm(true, "cockpit"),
                () => setHoneypotArmed(true),
              )
            }
          >
            Arm honeypot
          </Btn>
          <Btn
            disabled={busy || !honeypotArmed}
            onClick={() =>
              void run(
                () => postHoneypotArm(false, "cockpit"),
                () => setHoneypotArmed(false),
              )
            }
          >
            Disarm honeypot
          </Btn>
          <Btn
            disabled={busy}
            onClick={() =>
              void run(() => postLockdown("cockpit", reason, true))
            }
          >
            Lockdown dry-run
          </Btn>
          <Btn
            variant="danger"
            disabled={busy}
            onClick={() => {
              setLockdownDryRun(false);
              setConfirm("lockdown_exec");
            }}
          >
            Lockdown execute…
          </Btn>
          <Btn
            variant="danger"
            disabled={busy || signingHalted}
            onClick={() => setConfirm("signing_halt")}
          >
            Halt signing…
          </Btn>
          <Btn
            disabled={busy || !signingHalted}
            onClick={() =>
              void run(
                () => postSigningHalt(false, "cockpit", reason),
                () => setSigningHalted(false),
              )
            }
          >
            Resume signing
          </Btn>
          <Link className="btn" to="/security">
            Security Ops
          </Link>
          <Link className="btn" to="/signing">
            Signing Node
          </Link>
        </div>
        <AuthNote hmac humanYes />
        <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
          Lockdown execute defaults to dry-run in policy · HMAC on mutate · edge fail-closed stays
          armed
        </p>
      </Card>

      {/* 4. Inference / infra */}
      <Card
        title="4 · Inference / infra"
        style={{ marginBottom: 14 }}
        action={<Badge kind="healthy">MESH OK</Badge>}
      >
        <SectionHead
          icon={Cpu}
          title="Model tiers · edge PoP · in-process signing · control plane"
          hint="Tier 1/2 critical path · Tier 3 offline R&D · 5-PoP mesh"
        />
        <div className="grid grid-2" style={{ marginBottom: 12 }}>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Tier</th>
                  <th>Port</th>
                  <th>Model</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {seed.inferenceTiers.map((t) => (
                  <tr key={t.tier + t.port}>
                    <td>{t.tier}</td>
                    <td className="mono">{t.port}</td>
                    <td className="small">{t.model}</td>
                    <td>
                      <Badge kind={t.status === "online" ? "healthy" : "info"}>
                        {t.status === "online" ? "ONLINE" : "OFFLINE R&D"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <div className="table-wrap" style={{ marginBottom: 10 }}>
              <table className="data">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Port</th>
                    <th>OK</th>
                  </tr>
                </thead>
                <tbody>
                  {seed.controlPlaneServices.map((s) => (
                    <tr key={s.name}>
                      <td>{s.name}</td>
                      <td className="mono">:{s.port}</td>
                      <td>
                        <Badge kind={s.ok ? "healthy" : "bleeding"}>
                          {s.ok ? "UP" : "DOWN"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <SelectField
              label="Preferred edge PoP"
              value={edgePop}
              onChange={setEdgePop}
              options={edgePops.map((e) => ({
                value: e.id,
                label: `${e.id} · ${e.region} · ${e.rtt}`,
              }))}
            />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
              <Btn
                variant="primary"
                disabled={busy || !dirty}
                onClick={saveLocal}
              >
                <Save size={14} /> Save cockpit prefs
              </Btn>
              <Btn
                disabled={busy}
                onClick={() =>
                  void run(
                    () => postEdgeSelect(edgePop, "cockpit"),
                    () => audit(`Edge preference stored: ${edgePop}`, "ok"),
                  )
                }
              >
                Apply edge (API/demo)
              </Btn>
              <Link className="btn" to="/forge">
                Forge
              </Link>
              <Link className="btn" to="/health">
                Health & Verify
              </Link>
              <Link className="btn" to="/power">
                Power / UPS
              </Link>
              <Link className="btn" to="/edge">
                Edge Mesh
              </Link>
              <Link className="btn" to="/latency">
                Latency
              </Link>
            </div>
            <p className="muted small" style={{ marginBottom: 0, marginTop: 8 }}>
              <Radio size={12} style={{ verticalAlign: "-1px" }} /> signing ·{" "}
              <span className="mono">titan-safety in-process</span> ·{" "}
              <KeyRound size={12} style={{ verticalAlign: "-1px" }} /> gate receipt required
            </p>
          </div>
        </div>
      </Card>

      {/* 5. Pipelines */}
      <Card
        title="5 · Pipelines"
        style={{ marginBottom: 14 }}
        action={
          <Badge kind="info">
            {activeCount}/{maxActivePipelines} active
          </Badge>
        }
      >
        <SectionHead
          icon={GitBranch}
          title="Advisory enable/disable · per-lane halt · selective activation"
          hint="P22 memecoin gated · new activation = Human YES · allocator cap ≤4"
        />
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            alignItems: "flex-end",
            marginBottom: 12,
          }}
        >
          <div className="field" style={{ marginBottom: 0, minWidth: 160 }}>
            <label htmlFor="max-active-pipelines">Max active pipelines</label>
            <input
              id="max-active-pipelines"
              type="number"
              min={1}
              max={12}
              value={maxActivePipelines}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isFinite(n)) return;
                setMaxActivePipelines(Math.max(1, Math.min(12, Math.round(n))));
              }}
            />
          </div>
          <span className="muted small" style={{ paddingBottom: 8 }}>
            Preference only · Save to keep across navigation
          </span>
        </div>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Phase</th>
                <th>Run</th>
                <th>Advisory</th>
                <th>Edge</th>
                <th>Controls</th>
              </tr>
            </thead>
            <tbody>
              {pipelines.map((p) => (
                <tr key={p.id}>
                  <td>
                    {p.id}
                    {p.memecoin ? (
                      <span className="chip warn" style={{ marginLeft: 6 }}>
                        P22
                      </span>
                    ) : null}
                    {p.flash ? (
                      <span className="chip" style={{ marginLeft: 4 }}>
                        FL
                      </span>
                    ) : null}
                  </td>
                  <td>{p.name}</td>
                  <td>
                    <Badge
                      kind={
                        p.phase === "funded"
                          ? "healthy"
                          : p.phase === "defunded"
                            ? "bleeding"
                            : p.phase === "pending_yes"
                              ? "watch"
                              : "info"
                      }
                    >
                      {p.phase}
                    </Badge>
                  </td>
                  <td>
                    <Badge
                      kind={
                        p.runState === "running"
                          ? "healthy"
                          : p.runState === "halted"
                            ? "bleeding"
                            : p.runState === "gated"
                              ? "watch"
                              : "neutral"
                      }
                    >
                      {p.runState}
                    </Badge>
                  </td>
                  <td>
                    <button
                      type="button"
                      className={`btn${p.advisoryEnabled ? " primary" : ""}`}
                      style={{ padding: "4px 10px", fontSize: 12 }}
                      disabled={busy || Boolean(p.humanYesRequired && !p.advisoryEnabled)}
                      onClick={() => {
                        const next = !p.advisoryEnabled;
                        if (p.humanYesRequired && next) {
                          audit(
                            `${p.id} live activation requires Human YES (Phase 5) — advisory toggle blocked`,
                            "warn",
                          );
                          return;
                        }
                        void run(
                          () => postPipelineAdvisory(p.id, next),
                          () =>
                            setPipelines((rows) =>
                              rows.map((r) =>
                                r.id === p.id ? { ...r, advisoryEnabled: next } : r,
                              ),
                            ),
                        );
                      }}
                    >
                      {p.advisoryEnabled ? "ON" : "OFF"}
                    </button>
                  </td>
                  <td className="small">{p.edge}</td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <Btn
                        disabled={busy || p.runState === "halted" || p.runState === "gated"}
                        onClick={() =>
                          void run(
                            () => postPipelineHalt(p.id, true, "cockpit"),
                            () =>
                              setPipelines((rows) =>
                                rows.map((r) =>
                                  r.id === p.id ? { ...r, runState: "halted" } : r,
                                ),
                              ),
                          )
                        }
                      >
                        Halt
                      </Btn>
                      <Btn
                        disabled={busy || p.runState === "running" || p.runState === "gated"}
                        onClick={() =>
                          void run(
                            () => postPipelineHalt(p.id, false, "cockpit"),
                            () =>
                              setPipelines((rows) =>
                                rows.map((r) =>
                                  r.id === p.id
                                    ? {
                                        ...r,
                                        runState:
                                          r.phase === "funded" || r.phase === "micro_live"
                                            ? "running"
                                            : "paper",
                                      }
                                    : r,
                                ),
                              ),
                          )
                        }
                      >
                        Resume
                      </Btn>
                    </div>
                    {p.humanYesRequired ? (
                      <div className="muted small" style={{ marginTop: 4 }}>
                        Human YES
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small" style={{ marginBottom: 0, marginTop: 10 }}>
          P22 Memecoin Trench stays catalog/paper until Phase 5 YES + live profile — see{" "}
          <Link to="/memecoin">Memecoin Trench</Link>.
        </p>
      </Card>

      {/* 6. Allocator / QI */}
      <Card
        title="6 · Allocator / QI"
        style={{ marginBottom: 14 }}
        action={<Badge kind="info">ADVISORY</Badge>}
      >
        <SectionHead
          icon={Atom}
          title="CapitalAllocator plan · QI optimizer · max active"
          hint="SA/Kelly advisory only · does not gate execution"
        />
        <div className="grid grid-4" style={{ marginBottom: 12 }}>
          <Metric label="Max active" value={String(maxActivePipelines)} />
          <Metric
            label="QI selected"
            value={seed.allocator.selectedIds.join(", ") || "—"}
          />
          <Metric label="Last plan" value={seed.allocator.lastPlanAt.slice(11, 19) + "Z"} />
          <Metric label="Backend" value="classical_sa" delta="agents removed" />
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn
            variant="primary"
            disabled={busy}
            onClick={() => void run(() => postAllocatorRefresh("cockpit"))}
          >
            Refresh allocator plan
          </Btn>
          <Link className="btn" to="/qi-optimizer">
            Open QI Optimizer
          </Link>
          <Link className="btn" to="/tca">
            TCA & Allocator
          </Link>
          <Link className="btn" to="/pipelines">
            Pipelines catalog
          </Link>
        </div>
        <p className="mono small muted" style={{ marginTop: 10, marginBottom: 0 }}>
          {seed.allocator.cliRefresh}
        </p>
      </Card>

      {/* 7. Evolution */}
      <Card
        title="7 · Evolution"
        style={{ marginBottom: 14 }}
        action={
          <Badge kind={evolutionFrozen ? "watch" : "healthy"}>
            {evolutionFrozen ? "FROZEN" : "OPEN"}
          </Badge>
        }
      >
        <SectionHead
          icon={Snowflake}
          title="DGM-H / GEPA / SkillOpt freeze (shadow)"
          hint="Unfreeze does not authorize live evolution — Human YES still required"
        />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn
            disabled={busy || evolutionFrozen}
            onClick={() =>
              void run(
                () => postEvolutionFreeze(true, "cockpit"),
                () => setEvolutionFrozen(true),
              )
            }
          >
            Freeze evolution
          </Btn>
          <Btn
            variant="primary"
            disabled={busy || !evolutionFrozen}
            onClick={() =>
              void run(
                () => postEvolutionFreeze(false, "cockpit"),
                () => setEvolutionFrozen(false),
              )
            }
          >
            Unfreeze (shadow)
          </Btn>
          <Link className="btn" to="/promotions">
            Promotions
          </Link>
        </div>
        <AuthNote humanYes />
      </Card>

      {/* 8. Notifications / HERALD */}
      <Card
        title="8 · Notifications / HERALD"
        style={{ marginBottom: 14 }}
        action={
          <Badge kind={heraldLevel === "muted" ? "watch" : "healthy"}>
            {heraldLevel.toUpperCase()}
          </Badge>
        }
      >
        <SectionHead
          icon={Bell}
          title="Alert level / mute (advisory)"
          hint="Telegram primary on EDGE-FRA · drawdown tiers notify-only"
        />
        <div className="option-grid" style={{ marginBottom: 12 }}>
          {(
            [
              ["all", "All alerts"],
              ["high", "High+"],
              ["critical", "Critical only"],
              ["muted", "Muted"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`option-tile${heraldLevel === id ? " active" : ""}`}
              onClick={() => setHeraldLevel(id)}
            >
              <strong>{label}</strong>
              <span>{id}</span>
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Btn variant="primary" disabled={busy || !dirty} onClick={saveLocal}>
            <Save size={14} /> Save cockpit prefs
          </Btn>
          <Btn
            disabled={busy}
            onClick={() =>
              void run(
                () => postHeraldAlertLevel(heraldLevel, "cockpit"),
                () => audit(`HERALD level applied: ${heraldLevel}`, "ok"),
              )
            }
          >
            Apply HERALD (API/demo)
          </Btn>
        </div>
      </Card>

      {/* Autonomy matrix + audit */}
      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Autonomy gates (Human YES)">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Gate</th>
                </tr>
              </thead>
              <tbody>
                {seed.autonomyNotes.map((a) => (
                  <tr key={a.action}>
                    <td>{a.action}</td>
                    <td>
                      <Badge kind="watch">{a.gate}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card
          title="Operator audit"
          action={
            <Btn
              variant="ghost"
              onClick={() => {
                setLog([]);
                push("Audit cleared", "ok");
              }}
            >
              Clear
            </Btn>
          }
        >
          {log.length === 0 ? (
            <div className="empty">No manual actions yet this session.</div>
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
      </div>

      {/* Confirm modals */}
      <Modal
        open={confirm === "kill"}
        onClose={() => setConfirm(null)}
        title="Activate kill switch"
        subtitle="Destructive — confirms global or scoped halt"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Btn>
            <Btn
              variant="danger"
              disabled={busy}
              onClick={() => {
                void run(
                  () =>
                    postKillActivate(
                      "cockpit",
                      reason,
                      killScope,
                      killScope === "pipeline" ? killPipeline : undefined,
                    ),
                  () => {
                    setKillActive(true);
                    setTradingHalted(true);
                    setConfirm(null);
                  },
                );
              }}
            >
              <Skull size={14} /> Activate kill
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
              className={`option-tile${killScope === id ? " active" : ""}`}
              onClick={() => setKillScope(id)}
            >
              <strong>{label}</strong>
              <span>{id}</span>
            </button>
          ))}
        </div>
        {killScope === "pipeline" && (
          <div className="field" style={{ marginBottom: 12 }}>
            <label>Pipeline ID</label>
            <input
              value={killPipeline}
              onChange={(e) => setKillPipeline(e.target.value)}
            />
          </div>
        )}
        <div className="field">
          <label>Reason</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <AuthNote hmac />
      </Modal>

      <Modal
        open={confirm === "resume"}
        onClose={() => setConfirm(null)}
        title="Signed RESUME"
        subtitle="kill sign --command RESUME then deactivate --signed"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Btn>
            <Btn
              variant="primary"
              disabled={busy}
              onClick={() => {
                void run(
                  () => postKillResume("cockpit", reason),
                  () => {
                    setKillActive(false);
                    setTradingHalted(false);
                    setConfirm(null);
                  },
                );
              }}
            >
              Apply signed resume
            </Btn>
          </>
        }
      >
        <DetailGrid
          rows={[
            {
              label: "Step 1",
              value: "titan-safety kill sign --command RESUME --operator YOU",
            },
            { label: "Step 2", value: "kill deactivate --signed $TOKEN" },
            { label: "Auth", value: "HMAC control_plane.secret" },
          ]}
        />
        <AuthNote hmac />
      </Modal>

      <Modal
        open={confirm === "flatten"}
        onClose={() => setConfirm(null)}
        title="Flatten all positions"
        subtitle="Wind-down flatten · optional key revoke / SIGNING_HALTED"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Btn>
            <Btn
              variant="danger"
              disabled={busy}
              onClick={() => {
                void run(
                  () => postWindDown("flatten", "cockpit", reason, revokeKeys),
                  () => {
                    setWindDown("flatten");
                    if (revokeKeys) setSigningHalted(true);
                    setTradingHalted(true);
                    setConfirm(null);
                  },
                );
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
        <AuthNote hmac humanYes />
      </Modal>

      <Modal
        open={confirm === "lockdown_exec"}
        onClose={() => setConfirm(null)}
        title="Security lockdown"
        subtitle={
          lockdownDryRun
            ? "Dry-run (safe)"
            : "EXECUTE — HMAC + Human YES · fail-closed"
        }
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Btn>
            <Btn
              variant={lockdownDryRun ? "primary" : "danger"}
              disabled={busy}
              onClick={() => {
                void run(
                  () => postLockdown("cockpit", reason, lockdownDryRun),
                  () => setConfirm(null),
                );
              }}
            >
              <Lock size={14} /> {lockdownDryRun ? "Run dry-run" : "Execute lockdown"}
            </Btn>
          </>
        }
      >
        <div className="option-grid" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className={`option-tile${lockdownDryRun ? " active" : ""}`}
            onClick={() => setLockdownDryRun(true)}
          >
            <strong>Dry-run</strong>
            <span>no mutate</span>
          </button>
          <button
            type="button"
            className={`option-tile${!lockdownDryRun ? " active" : ""}`}
            onClick={() => setLockdownDryRun(false)}
          >
            <strong>Execute</strong>
            <span>HMAC + YES</span>
          </button>
        </div>
        <div className="field">
          <label>Reason</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <AuthNote hmac humanYes={!lockdownDryRun} />
      </Modal>

      <Modal
        open={confirm === "signing_halt"}
        onClose={() => setConfirm(null)}
        title="Halt signing node"
        subtitle="SIGNING_HALTED — no new signatures until resume"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Btn>
            <Btn
              variant="danger"
              disabled={busy}
              onClick={() => {
                void run(
                  () => postSigningHalt(true, "cockpit", reason),
                  () => {
                    setSigningHalted(true);
                    setConfirm(null);
                  },
                );
              }}
            >
              Halt signing
            </Btn>
          </>
        }
      >
        <div className="field">
          <label>Reason</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <AuthNote hmac />
      </Modal>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
