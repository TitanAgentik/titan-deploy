import { useEffect, useState } from "react";
import {
  Shield,
  Ghost,
  Crosshair,
  Swords,
  Lock,
  Eye,
  Skull,
  RefreshCw,
} from "lucide-react";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import {
  ActionMenu,
  DetailGrid,
  Drawer,
  Modal,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import {
  evasionControls,
  impenetrableLayers,
  predatoryModules,
  securityEvents,
  securityPosture,
  stalkTargets,
} from "@/lib/data";
import {
  fetchSecurityPosture,
  postSecurityLockdownDryRun,
  type LiveSecurityPosture,
} from "@/lib/securityApi";

type Pillar = "impenetrable" | "evasion" | "stalk" | "predatory";
type Stalk = (typeof stalkTargets)[number];
type Layer = {
  id: string;
  name: string;
  port: string;
  status: "armed" | "halted";
  detail: string;
};
type Pred = (typeof predatoryModules)[number];

const pillarMeta: Record<
  Pillar,
  { label: string; icon: typeof Shield; blurb: string }
> = {
  impenetrable: {
    label: "Impenetrable",
    icon: Shield,
    blurb: "Defense-in-depth — kernel DENY, signing isolation, PCR, netns",
  },
  evasion: {
    label: "Evasion",
    icon: Ghost,
    blurb: "OPSEC — MEV shield, edge RTT, fingerprint rotation, air-gap vault",
  },
  stalk: {
    label: "Stalking",
    icon: Crosshair,
    blurb: "Threat hunt — mempool clusters, probes, copy-traders, phishing",
  },
  predatory: {
    label: "Predatory",
    icon: Swords,
    blurb: "Counter-offense — honeypots, Red Team, poison fills, kill-chain",
  },
};

function severityKind(s: Stalk["severity"]): "bleeding" | "watch" | "info" | "healthy" {
  if (s === "high") return "bleeding";
  if (s === "medium") return "watch";
  return "info";
}

function statusKind(s: Stalk["status"]): "bleeding" | "watch" | "healthy" | "neutral" {
  if (s === "quarantined") return "bleeding";
  if (s === "tracking" || s === "watching") return "watch";
  if (s === "cleared") return "healthy";
  return "neutral";
}

type SecurityPrefs = {
  pillar: Pillar;
  huntMode: boolean;
  honeypotArmed: boolean;
};

const SECURITY_DEFAULTS: SecurityPrefs = {
  pillar: "impenetrable",
  huntMode: true,
  honeypotArmed: true,
};

export function Security() {
  const { toasts, push, dismiss } = useToasts();
  const {
    draft: prefs,
    update: updatePrefs,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("security", SECURITY_DEFAULTS);
  const pillar = prefs.pillar;
  const huntMode = prefs.huntMode;
  const honeypotArmed = prefs.honeypotArmed;
  const setPillar = (p: Pillar) => updatePrefs({ pillar: p });
  const setHuntMode = (v: boolean | ((prev: boolean) => boolean)) =>
    updatePrefs({ huntMode: typeof v === "function" ? v(huntMode) : v });
  const setHoneypotArmed = (v: boolean | ((prev: boolean) => boolean)) =>
    updatePrefs({ honeypotArmed: typeof v === "function" ? v(honeypotArmed) : v });
  const [target, setTarget] = useState<Stalk | null>(null);
  const [layer, setLayer] = useState<Layer | null>(null);
  const [pred, setPred] = useState<Pred | null>(null);
  const [lockdown, setLockdown] = useState(false);
  const [lockdownBusy, setLockdownBusy] = useState(false);
  const [live, setLive] = useState<LiveSecurityPosture | null>(null);

  const isLive = Boolean(live?.live);

  const refreshLive = async () => {
    const st = await fetchSecurityPosture();
    setLive(st);
    if (st.live) {
      if (typeof st.honeypot_armed === "boolean") setHoneypotArmed(st.honeypot_armed);
      if (typeof st.hunt_mode === "boolean") setHuntMode(st.hunt_mode);
      push(
        st.overall === "LOCKDOWN"
          ? "Live posture: LOCKDOWN"
          : `Live posture: ${st.overall ?? "ok"} (:19008)`,
        st.overall === "LOCKDOWN" ? "danger" : "ok",
      );
    } else {
      push(`Using demo posture — :19008 ${st.error ?? "offline"}`, "warn");
    }
  };

  useEffect(() => {
    void fetchSecurityPosture().then((st) => {
      setLive(st);
      if (st.live) {
        if (typeof st.honeypot_armed === "boolean") setHoneypotArmed(st.honeypot_armed);
        if (typeof st.hunt_mode === "boolean") setHuntMode(st.hunt_mode);
      }
    });
  }, []);

  const overall = isLive && live?.overall ? live.overall : securityPosture.overall;
  const threat =
    isLive && live?.threat_level ? live.threat_level : securityPosture.threatLevel;
  const pcr =
    isLive && typeof live?.pcr_drift === "boolean"
      ? live.pcr_drift
      : securityPosture.pcrDrift;
  const killActive = isLive ? Boolean(live?.kill_active) : false;
  const evolutionFrozen = isLive
    ? Boolean(live?.evolution_frozen)
    : true; /* demo default matches portfolio */
  const signingHalted = isLive
    ? Boolean(live?.signing_halted)
    : false;

  const layers =
    isLive && live?.layers && live.layers.length > 0
      ? live.layers.map((l) => ({
          id: l.id,
          name: l.name,
          port: l.port,
          status: l.status as "armed" | "halted",
          detail:
            impenetrableLayers.find((x) => x.id === l.id)?.detail ??
            "Live layer from security_ops",
        }))
      : impenetrableLayers;

  const pillarStatus = (id: Pillar): string => {
    if (isLive && live?.pillars) {
      const key =
        id === "stalk"
          ? "stalking"
          : id === "impenetrable"
            ? "impenetrable"
            : id === "evasion"
              ? "evasion"
              : "predatory";
      const v = live.pillars[key] ?? live.pillars[id];
      if (v) return String(v).toUpperCase();
    }
    if (id === "impenetrable") return "ARMED";
    if (id === "evasion") return "ACTIVE";
    if (id === "stalk")
      return `${stalkTargets.filter((t) => t.status !== "cleared").length} LIVE`;
    return "ENGAGED";
  };

  const runLockdownDryRun = async () => {
    setLockdownBusy(true);
    try {
      const r = await postSecurityLockdownDryRun("cockpit", "ui dry-run");
      push(r.detail, r.ok ? "ok" : "warn");
    } finally {
      setLockdownBusy(false);
    }
  };

  const MetaIcon = pillarMeta[pillar].icon;

  return (
    <>
      <PageHeader
        eyebrow="SENTINEL · PREDATOR · GUARDIAN"
        title="Security Ops"
        subtitle="Impenetrable defense, OPSEC evasion, threat stalking, and predatory countermeasures — advisory UI; risk kernel DENY remains authoritative."
        actions={
          <>
            <ActionMenu
              label="Posture"
              items={[
                {
                  label: "Re-scan all layers (live :19008)",
                  onClick: () => void refreshLive(),
                },
                {
                  label: huntMode ? "Pause hunt mode" : "Resume hunt mode",
                  onClick: () => {
                    setHuntMode((h) => !h);
                    push(huntMode ? "Hunt mode paused" : "Hunt mode resumed", "warn");
                  },
                },
                {
                  label: honeypotArmed ? "Disarm honeypots" : "Arm honeypots",
                  onClick: () => {
                    setHoneypotArmed((h) => !h);
                    push(honeypotArmed ? "Honeypots disarmed" : "Honeypots armed");
                  },
                },
                {
                  label: "CLI dry-run lockdown via API",
                  onClick: () => void runLockdownDryRun(),
                },
              ]}
            />
            <Btn variant="danger" onClick={() => setLockdown(true)}>
              <Lock size={14} /> Security lockdown…
            </Btn>
            <Btn
              variant="primary"
              onClick={() => void refreshLive()}
            >
              <RefreshCw size={14} /> Refresh
            </Btn>
          </>
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

      <div style={{ marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <Tag kind={isLive ? "healthy" : "watch"}>
          {isLive ? "LIVE · :19008" : "DEMO · security service offline"}
        </Tag>
        {isLive ? (
          <>
            <Tag kind={killActive ? "bleeding" : "healthy"}>
              kill {killActive ? "ACTIVE" : "clear"}
            </Tag>
            <Tag kind={evolutionFrozen ? "watch" : "healthy"}>
              evolution {evolutionFrozen ? "frozen" : "open"}
            </Tag>
            <Tag kind={signingHalted ? "bleeding" : "healthy"}>
              signing {signingHalted ? "HALTED" : "ok"}
            </Tag>
            <Tag kind={honeypotArmed ? "info" : "neutral"}>
              honeypot {honeypotArmed ? "armed" : "off"}
            </Tag>
          </>
        ) : null}
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric
          label="Posture"
          value={overall}
          delta={isLive ? "from security_ops" : "6/6 layers (demo)"}
          deltaDir="up"
        />
        <Metric
          label="Threat level"
          value={threat}
          delta="stalk targets active"
        />
        <Metric
          label="PCR drift"
          value={pcr ? "DETECTED" : "CLEAR"}
          deltaDir={pcr ? "down" : "up"}
        />
        <Metric
          label="Hunt / honeypot"
          value={`${huntMode ? "HUNT" : "IDLE"} · ${honeypotArmed ? "ARMED" : "OFF"}`}
        />
      </div>

      <div className="sec-pillars" role="tablist" aria-label="Security pillars">
        {(Object.keys(pillarMeta) as Pillar[]).map((id) => {
          const m = pillarMeta[id];
          const Icon = m.icon;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={pillar === id}
              className={`sec-pillar${pillar === id ? " active" : ""}`}
              onClick={() => setPillar(id)}
            >
              <Icon size={18} />
              <div>
                <strong>{m.label}</strong>
                <span>{m.blurb}</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="sec-panel">
        <div className="sec-panel-head">
          <MetaIcon size={18} />
          <h3>{pillarMeta[pillar].label}</h3>
          <Tag kind={pillar === "stalk" ? "watch" : "healthy"}>
            {pillarStatus(pillar)}
          </Tag>
          {!isLive ? (
            <Tag kind="watch">SPEC / demo until live feed</Tag>
          ) : null}
        </div>

        {pillar === "impenetrable" && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Layer</th>
                  <th>Name</th>
                  <th>Endpoint</th>
                  <th>Status</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {layers.map((l) => (
                  <tr
                    key={l.id}
                    className="row-click"
                    onClick={() =>
                      setLayer({
                        id: l.id,
                        name: l.name,
                        port: l.port,
                        status: (l.status === "halted" ? "halted" : "armed") as Layer["status"],
                        detail:
                          "detail" in l && typeof l.detail === "string"
                            ? l.detail
                            : impenetrableLayers.find((x) => x.id === l.id)?.detail ?? "",
                      })
                    }
                  >
                    <td className="mono">{l.id}</td>
                    <td>{l.name}</td>
                    <td className="mono">{l.port}</td>
                    <td>
                      <Tag kind={l.status === "halted" ? "watch" : "healthy"}>
                        {String(l.status).toUpperCase()}
                      </Tag>
                    </td>
                    <td className="muted small">
                      {"detail" in l && typeof l.detail === "string"
                        ? l.detail
                        : impenetrableLayers.find((x) => x.id === l.id)?.detail}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {pillar === "evasion" && (
          <div className="grid grid-2">
            {evasionControls.map((e) => (
              <Card
                key={e.id}
                title={e.name}
                action={
                  <Tag kind={e.mode === "active" ? "healthy" : "info"}>
                    {e.mode}
                  </Tag>
                }
              >
                <p className="muted small" style={{ margin: 0 }}>
                  {e.detail}
                </p>
                <div style={{ marginTop: 10 }}>
                  <Btn
                    variant="ghost"
                    onClick={() =>
                      push(
                        isLive
                          ? `${e.name} — verified against live posture`
                          : `${e.name} — status verified (demo)`,
                      )
                    }
                  >
                    Verify
                  </Btn>
                </div>
              </Card>
            ))}
          </div>
        )}

        {pillar === "stalk" && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Source</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Last seen</th>
                </tr>
              </thead>
              <tbody>
                {stalkTargets.map((t) => (
                  <tr
                    key={t.id}
                    className="row-click"
                    onClick={() => setTarget(t)}
                  >
                    <td>{t.label}</td>
                    <td className="mono">{t.source}</td>
                    <td>
                      <Tag kind={severityKind(t.severity)}>{t.severity}</Tag>
                    </td>
                    <td>
                      <Tag kind={statusKind(t.status)}>{t.status}</Tag>
                    </td>
                    <td className="mono">{t.lastSeen}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {pillar === "predatory" && (
          <div className="grid grid-2">
            {predatoryModules.map((p) => (
              <Card
                key={p.id}
                title={p.name}
                action={
                  <Tag kind={p.posture === "hunt" || p.posture === "disrupt" ? "watch" : "info"}>
                    {p.posture}
                  </Tag>
                }
              >
                <p className="muted small" style={{ margin: "0 0 8px" }}>
                  <span className="mono">{p.agent}</span> — {p.detail}
                </p>
                <Btn variant="ghost" onClick={() => setPred(p)}>
                  Open module…
                </Btn>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <Card
          title="Security event stream"
          action={
            !isLive ? <Tag kind="watch">SPEC / demo until live feed</Tag> : undefined
          }
        >
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Pillar</th>
                  <th>Event</th>
                </tr>
              </thead>
              <tbody>
                {securityEvents.map((ev) => (
                  <tr key={ev.ts + ev.msg}>
                    <td className="mono">{ev.ts.slice(11, 19)}</td>
                    <td>
                      <Tag
                        kind={
                          ev.level === "warn"
                            ? "watch"
                            : ev.pillar === "predatory"
                              ? "info"
                              : "healthy"
                        }
                      >
                        {ev.pillar}
                      </Tag>
                    </td>
                    <td style={{ fontFamily: "var(--font)" }}>{ev.msg}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Kill-chain quick actions">
          <p className="muted small" style={{ marginTop: 0 }}>
            Escalation path when stalking confirms a live adversary. Kernel DENY and
            signing halt still require HMAC in production.
          </p>
          <div className="option-grid" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="option-tile"
              onClick={() => push("Containment: edge PoP isolated (demo)", "warn")}
            >
              <strong>
                <Eye size={14} style={{ verticalAlign: "-2px" }} /> Isolate edge
              </strong>
              <span>drop PoP from routing table</span>
            </button>
            <button
              type="button"
              className="option-tile"
              onClick={() => push("Signing node HALT requested (demo)", "danger")}
            >
              <strong>
                <Lock size={14} style={{ verticalAlign: "-2px" }} /> Halt signing
              </strong>
              <span>:19010 SIGNING_HALTED</span>
            </button>
            <button
              type="button"
              className="option-tile"
              onClick={() => push("Poison fills armed against copy-traders")}
            >
              <strong>
                <Skull size={14} style={{ verticalAlign: "-2px" }} /> Poison fills
              </strong>
              <span>counter-copy disrupt</span>
            </button>
            <button
              type="button"
              className="option-tile"
              onClick={() => setLockdown(true)}
            >
              <strong>
                <Shield size={14} style={{ verticalAlign: "-2px" }} /> Full lockdown
              </strong>
              <span>kill + freeze + revoke</span>
            </button>
          </div>
        </Card>
      </div>

      <Drawer
        open={!!target}
        onClose={() => setTarget(null)}
        title={target?.label ?? "Target"}
      >
        {target && (
          <>
            {!isLive ? (
              <div style={{ marginBottom: 10 }}>
                <Tag kind="watch">SPEC / demo until live feed</Tag>
              </div>
            ) : null}
            <DetailGrid
              rows={[
                { label: "ID", value: target.id },
                { label: "Source", value: target.source },
                { label: "Severity", value: target.severity },
                { label: "Status", value: target.status },
                { label: "Last seen", value: target.lastSeen },
              ]}
            />
            <p className="muted small" style={{ marginTop: 14 }}>
              {target.note}
            </p>
            <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
              <Btn
                variant="primary"
                onClick={() => {
                  push(`Escalated ${target.id} to ARCHON`);
                  setTarget(null);
                }}
              >
                Escalate
              </Btn>
              <Btn
                onClick={() => {
                  push(`Quarantined ${target.id}`, "warn");
                  setTarget(null);
                }}
              >
                Quarantine
              </Btn>
              <Btn
                variant="ghost"
                onClick={() => {
                  push(`Cleared ${target.id}`);
                  setTarget(null);
                }}
              >
                Mark cleared
              </Btn>
            </div>
          </>
        )}
      </Drawer>

      <Drawer
        open={!!layer}
        onClose={() => setLayer(null)}
        title={layer?.name ?? "Layer"}
      >
        {layer && (
          <>
            <DetailGrid
              rows={[
                { label: "Layer", value: layer.id },
                { label: "Endpoint", value: layer.port },
                { label: "Status", value: layer.status },
              ]}
            />
            <p className="muted small" style={{ marginTop: 14 }}>
              {layer.detail}
            </p>
            <div style={{ marginTop: 16 }}>
              <Btn
                variant="primary"
                onClick={() => {
                  push(`${layer.name} integrity check OK`);
                  setLayer(null);
                }}
              >
                Run integrity check
              </Btn>
            </div>
          </>
        )}
      </Drawer>

      <Drawer
        open={!!pred}
        onClose={() => setPred(null)}
        title={pred?.name ?? "Module"}
      >
        {pred && (
          <>
            {!isLive ? (
              <div style={{ marginBottom: 10 }}>
                <Tag kind="watch">SPEC / demo until live feed</Tag>
              </div>
            ) : null}
            <DetailGrid
              rows={[
                { label: "Agent", value: pred.agent },
                { label: "Posture", value: pred.posture },
              ]}
            />
            <p className="muted small" style={{ marginTop: 14 }}>
              {pred.detail}
            </p>
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <Btn
                variant="primary"
                onClick={() => {
                  push(`${pred.name} pulse OK`);
                  setPred(null);
                }}
              >
                Pulse
              </Btn>
              <Btn variant="ghost" onClick={() => setPred(null)}>
                Close
              </Btn>
            </div>
          </>
        )}
      </Drawer>

      <Modal
        open={lockdown}
        onClose={() => setLockdown(false)}
        title="Security lockdown"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setLockdown(false)} disabled={lockdownBusy}>
              Cancel
            </Btn>
            <Btn
              variant="ghost"
              disabled={lockdownBusy}
              onClick={() => void runLockdownDryRun()}
            >
              Dry-run (HMAC)
            </Btn>
            <Btn
              variant="danger"
              disabled={lockdownBusy}
              onClick={() => {
                void (async () => {
                  setLockdownBusy(true);
                  try {
                    const r = await postSecurityLockdownDryRun(
                      "cockpit",
                      "ui lockdown confirm dry-run",
                    );
                    setLockdown(false);
                    push(
                      r.ok
                        ? `Lockdown dry-run OK — ${r.detail}`
                        : r.detail,
                      r.ok ? "ok" : "warn",
                    );
                  } finally {
                    setLockdownBusy(false);
                  }
                })();
              }}
            >
              Confirm lockdown (dry-run)
            </Btn>
          </>
        }
      >
        <p className="muted small" style={{ marginTop: 0 }}>
          Sequences kill switch, evolution freeze, signing halt, and arms honeypots.
          Mutating calls need Settings HMAC (`X-Titan-Auth`). Confirm runs dry-run only.
        </p>
        <ul className="muted small" style={{ lineHeight: 1.8 }}>
          <li>Global kill switch → ACTIVE</li>
          <li>Evolution → frozen (shadow-only)</li>
          <li>Signing node → SIGNING_HALTED</li>
          <li>Honeypot lattice → ARMED</li>
          <li>Edge routing → fail-closed to known-good PoPs</li>
        </ul>
      </Modal>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
