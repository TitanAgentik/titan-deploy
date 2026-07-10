import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BrainCircuit,
  Cpu,
  Fingerprint,
  HeartPulse,
  KeyRound,
  Network,
  Pause,
  Play,
  RefreshCw,
  Shield,
  SlidersHorizontal,
} from "lucide-react";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import {
  ActionMenu,
  DetailGrid,
  Drawer,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import {
  agentAlerts,
  agentBftStatus,
  agentFleetSummary,
  agentInferencePorts,
  agentRoleFamilyLabels,
  agents,
  type AgentRecord,
  type AgentRoleFamily,
  type AgentRunStatus,
  type AgentTierKey,
} from "@/lib/data";

type ViewMode = "table" | "grid";
type TierFilter = "all" | AgentTierKey;
type RoleFilter = "all" | AgentRoleFamily;
type StatusFilter = "all" | AgentRunStatus;

type AgentControl = {
  enabled: boolean;
  drain: boolean;
  priority: number;
};

type AgentManagerDraft = {
  search: string;
  tier: TierFilter;
  role: RoleFilter;
  status: StatusFilter;
  view: ViewMode;
  selectedId: string | null;
  controls: Record<string, AgentControl>;
  audit: string[];
};

function defaultControls(): Record<string, AgentControl> {
  return Object.fromEntries(
    agents.map((a) => [
      a.id,
      {
        enabled: a.runStatus === "UP" || a.runStatus === "IDLE",
        drain: false,
        priority: a.priority,
      },
    ]),
  );
}

const MANAGER_DEFAULTS: AgentManagerDraft = {
  search: "",
  tier: "all",
  role: "all",
  status: "all",
  view: "table",
  selectedId: "ARCHON",
  controls: defaultControls(),
  audit: [],
};

function runStatusTag(s: AgentRunStatus): "healthy" | "bleeding" | "watch" | "neutral" {
  if (s === "UP") return "healthy";
  if (s === "DOWN") return "bleeding";
  if (s === "IDLE") return "watch";
  return "neutral";
}

function roleFamilyTag(f: AgentRoleFamily): "info" | "watch" | "healthy" | "neutral" {
  if (f === "orch") return "info";
  if (f === "risk") return "watch";
  if (f === "exec") return "healthy";
  return "neutral";
}

function controlFor(
  controls: Record<string, AgentControl>,
  a: AgentRecord,
): AgentControl {
  return (
    controls[a.id] ?? {
      enabled: a.runStatus === "UP" || a.runStatus === "IDLE",
      drain: false,
      priority: a.priority,
    }
  );
}

function hbAgeLabel(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  const m = Math.floor(ms / 60000);
  if (m < 1) return "<1m";
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h${m % 60}m`;
}

export function AgentManager() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, setDraft, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("agentManager", MANAGER_DEFAULTS);

  const [drawerOpen, setDrawerOpen] = useState(true);

  const fleet = useMemo(() => agentFleetSummary(agents), []);
  const controls = draft.controls ?? defaultControls();

  const filtered = useMemo(() => {
    const q = draft.search.trim().toLowerCase();
    return agents.filter((a) => {
      if (draft.tier !== "all" && a.tierKey !== draft.tier) return false;
      if (draft.role !== "all" && a.roleFamily !== draft.role) return false;
      if (draft.status !== "all" && a.runStatus !== draft.status) return false;
      if (!q) return true;
      const hay = `${a.id} ${a.role} ${a.model} ${a.port} ${a.pipelines.join(" ")} ${a.skills.join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
  }, [draft.search, draft.tier, draft.role, draft.status]);

  const selected =
    agents.find((a) => a.id === draft.selectedId) ??
    filtered[0] ??
    agents[0];

  const selectedCtrl = controlFor(controls, selected);

  const appendAudit = (msg: string) => {
    const line = `${new Date().toISOString()}  ${msg}`;
    update({ audit: [line, ...(draft.audit ?? [])].slice(0, 40) });
  };

  const patchControl = (id: string, patch: Partial<AgentControl>) => {
    const cur = controlFor(controls, agents.find((a) => a.id === id)!);
    update({
      controls: {
        ...controls,
        [id]: { ...cur, ...patch },
      },
    });
  };

  const selectAgent = (a: AgentRecord) => {
    update({ selectedId: a.id });
    setDrawerOpen(true);
  };

  const commitVotes = agentBftStatus.tradeVoters.filter((v) => v.vote === "COMMIT").length;

  return (
    <>
      <PageHeader
        eyebrow="Ops · Classical fleet"
        title="Agent Manager"
        subtitle="Operator console for the 20-agent classical catalog — advisory controls, fleet posture, BFT voters, tier map. Not live process control."
        actions={
          <>
            <Link className="btn" to="/agents">
              Agent Teams
            </Link>
            <Link className="btn" to="/models">
              Model Tiers
            </Link>
            <Link className="btn primary" to="/manual-control">
              Manual Control
            </Link>
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

      {/* Fleet posture */}
      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Fleet" value={`${fleet.total}`} delta="classical · no QCC/QSA/QRP" />
        <Metric
          label="UP / DOWN"
          value={`${fleet.byStatus.UP} / ${fleet.byStatus.DOWN}`}
          delta={`${fleet.byStatus.IDLE} idle · ${fleet.byStatus.DORMANT} dormant`}
          deltaDir={fleet.byStatus.DOWN > 0 ? "down" : "up"}
        />
        <Metric
          label="By tier"
          value={`T1 ${fleet.byTier.t1} · T2 ${fleet.byTier.t2}`}
          delta={`T3a ${fleet.byTier.t3a} · U ${fleet.byTier.u}`}
        />
        <Metric
          label="Inference"
          value=":30000 / :30001 / :30002"
          delta={
            agentInferencePorts.filter((p) => [":30000", ":30001", ":30002"].includes(p.port) && p.status === "UP")
              .length === 3
              ? "live path UP"
              : "degraded"
          }
          deltaDir="up"
        />
      </div>

      {/* Alerts + ports */}
      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card
          title="Fleet alerts"
          action={<Tag kind={agentAlerts.some((a) => a.severity === "warn") ? "watch" : "healthy"}>demo</Tag>}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {agentAlerts.map((al) => (
              <button
                key={al.id}
                type="button"
                className="option-tile"
                style={{ textAlign: "left" }}
                onClick={() => {
                  update({ selectedId: al.agentId, search: al.agentId });
                  setDrawerOpen(true);
                }}
              >
                <strong>
                  <Tag kind={al.severity === "warn" ? "watch" : "info"}>{al.severity}</Tag>{" "}
                  {al.title}
                </strong>
                <span>
                  {al.detail} · <span className="mono">{al.at.slice(11, 19)}Z</span>
                </span>
              </button>
            ))}
          </div>
        </Card>

        <Card
          title="Inference port health"
          action={
            <Link className="btn" to="/forge">
              Forge
            </Link>
          }
        >
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Port</th>
                  <th>Tier</th>
                  <th>Status</th>
                  <th>Agents</th>
                </tr>
              </thead>
              <tbody>
                {agentInferencePorts.map((p) => (
                  <tr key={p.port}>
                    <td className="mono">{p.port}</td>
                    <td>{p.label}</td>
                    <td>
                      <Tag kind={p.status === "UP" ? "healthy" : "watch"}>{p.status}</Tag>
                    </td>
                    <td className="mono small">{p.agents.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card style={{ marginBottom: 14 }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            alignItems: "flex-end",
          }}
        >
          <div className="field" style={{ flex: "1 1 200px", minWidth: 180 }}>
            <label>Search</label>
            <input
              value={draft.search}
              placeholder="id · role · model · pipeline · skill"
              onChange={(e) => update({ search: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Tier</label>
            <select
              value={draft.tier}
              onChange={(e) => update({ tier: e.target.value as TierFilter })}
            >
              <option value="all">All</option>
              <option value="1">Tier 1</option>
              <option value="2">Tier 2</option>
              <option value="3a">Tier 3a</option>
              <option value="U">Utility</option>
            </select>
          </div>
          <div className="field">
            <label>Role</label>
            <select
              value={draft.role}
              onChange={(e) => update({ role: e.target.value as RoleFilter })}
            >
              <option value="all">All</option>
              {(Object.keys(agentRoleFamilyLabels) as AgentRoleFamily[]).map((k) => (
                <option key={k} value={k}>
                  {agentRoleFamilyLabels[k]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Status</label>
            <select
              value={draft.status}
              onChange={(e) => update({ status: e.target.value as StatusFilter })}
            >
              <option value="all">All</option>
              <option value="UP">UP</option>
              <option value="DOWN">DOWN</option>
              <option value="IDLE">IDLE</option>
              <option value="DORMANT">DORMANT</option>
            </select>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <Btn
              variant={draft.view === "table" ? "primary" : "ghost"}
              onClick={() => update({ view: "table" })}
            >
              Table
            </Btn>
            <Btn
              variant={draft.view === "grid" ? "primary" : "ghost"}
              onClick={() => update({ view: "grid" })}
            >
              Grid
            </Btn>
          </div>
          <span className="muted small mono" style={{ alignSelf: "center" }}>
            {filtered.length}/{agents.length}
          </span>
        </div>
      </Card>

      {/* Main split: roster + detail */}
      <div className="split" style={{ marginBottom: 14, alignItems: "start" }}>
        <Card
          title={`Roster · ${filtered.length}`}
          action={
            <ActionMenu
              label="⋯"
              variant="ghost"
              items={[
                {
                  label: "Clear filters",
                  onClick: () =>
                    update({ search: "", tier: "all", role: "all", status: "all" }),
                },
                {
                  label: "Enable all (advisory)",
                  onClick: () => {
                    const next = { ...controls };
                    for (const a of agents) {
                      next[a.id] = { ...controlFor(controls, a), enabled: true };
                    }
                    update({ controls: next });
                    appendAudit("ENABLE_ALL advisory");
                    push("All agents enabled (advisory)", "ok");
                  },
                },
                {
                  label: "Pause non-critical",
                  onClick: () => {
                    const keep = new Set(["GUARDIAN", "TRENCH-OPS", "ARCHON", "AUGUR", "PREDATOR", "ATLAS"]);
                    const next = { ...controls };
                    for (const a of agents) {
                      if (!keep.has(a.id)) {
                        next[a.id] = { ...controlFor(controls, a), enabled: false };
                      }
                    }
                    update({ controls: next });
                    appendAudit("PAUSE_NON_CRITICAL advisory");
                    push("Non-critical paused (advisory)", "warn");
                  },
                },
              ]}
            />
          }
        >
          {draft.view === "table" ? (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Role</th>
                    <th>Family</th>
                    <th>Tier</th>
                    <th>Status</th>
                    <th>Load</th>
                    <th>HB</th>
                    <th>Ctrl</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((a) => {
                    const c = controlFor(controls, a);
                    const active = selected?.id === a.id;
                    return (
                      <tr
                        key={a.id}
                        style={{
                          cursor: "pointer",
                          outline: active ? "2px solid var(--accent)" : undefined,
                          outlineOffset: -2,
                        }}
                        onClick={() => selectAgent(a)}
                      >
                        <td className="mono">{a.id}</td>
                        <td style={{ fontFamily: "var(--font)" }}>{a.role}</td>
                        <td>
                          <Tag kind={roleFamilyTag(a.roleFamily)}>
                            {agentRoleFamilyLabels[a.roleFamily]}
                          </Tag>
                        </td>
                        <td className="mono small">{a.tier}</td>
                        <td>
                          <Tag kind={runStatusTag(a.runStatus)}>{a.runStatus}</Tag>
                        </td>
                        <td className="mono">{a.load}%</td>
                        <td className="mono small muted">{hbAgeLabel(a.lastHeartbeatAt)}</td>
                        <td>
                          {!c.enabled ? (
                            <Tag kind="watch">PAUSED</Tag>
                          ) : c.drain ? (
                            <Tag kind="info">DRAIN</Tag>
                          ) : (
                            <Tag kind="healthy">ON</Tag>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid grid-3">
              {filtered.map((a) => {
                const c = controlFor(controls, a);
                const active = selected?.id === a.id;
                return (
                  <button
                    key={a.id}
                    type="button"
                    className="card metric-click"
                    style={{
                      cursor: "pointer",
                      textAlign: "left",
                      outline: active ? "2px solid var(--accent)" : undefined,
                    }}
                    onClick={() => selectAgent(a)}
                  >
                    <div className="card-title">
                      <span className="mono">{a.id}</span>
                      <Tag kind={runStatusTag(a.runStatus)}>{a.runStatus}</Tag>
                    </div>
                    <div className="muted small">{a.role}</div>
                    <div className="mono" style={{ marginTop: 8, fontSize: 12 }}>
                      {a.tier} · load {a.load}%
                    </div>
                    <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <Tag kind={roleFamilyTag(a.roleFamily)}>
                        {agentRoleFamilyLabels[a.roleFamily]}
                      </Tag>
                      {!c.enabled ? <Tag kind="watch">PAUSED</Tag> : null}
                      {c.drain ? <Tag kind="info">DRAIN</Tag> : null}
                    </div>
                    <div className="progress" style={{ marginTop: 10 }}>
                      <span style={{ width: `${a.load}%` }} />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <Card
          title={selected ? selected.id : "Detail"}
          action={
            selected ? (
              <ActionMenu
                label="⋯"
                variant="ghost"
                items={[
                  {
                    label: selectedCtrl.enabled ? "Pause (advisory)" : "Enable (advisory)",
                    onClick: () => {
                      const next = !selectedCtrl.enabled;
                      patchControl(selected.id, { enabled: next });
                      appendAudit(`${next ? "ENABLE" : "PAUSE"} ${selected.id}`);
                      push(`${selected.id} ${next ? "enabled" : "paused"} (advisory)`, "ok");
                    },
                  },
                  {
                    label: selectedCtrl.drain ? "Exit drain" : "Enter drain",
                    onClick: () => {
                      const next = !selectedCtrl.drain;
                      patchControl(selected.id, { drain: next });
                      appendAudit(`${next ? "DRAIN_ON" : "DRAIN_OFF"} ${selected.id}`);
                      push(`${selected.id} drain ${next ? "ON" : "OFF"}`, "warn");
                    },
                  },
                  {
                    label: "Restart request",
                    onClick: () => {
                      appendAudit(`RESTART_REQUEST ${selected.id}`);
                      push(`Restart requested · ${selected.id} (session audit)`, "warn");
                    },
                  },
                  {
                    label: "Halt pipeline affinity",
                    onClick: () => {
                      appendAudit(`HALT_PIPELINE_AFFINITY ${selected.id} [${selected.pipelines.join(",")}]`);
                      push(`Pipeline affinity halt advisory · ${selected.id}`, "warn");
                    },
                  },
                ]}
              />
            ) : null
          }
        >
          {selected ? (
            <>
              <p className="muted small" style={{ marginTop: 0 }}>
                {selected.role} · {selected.model}
              </p>
              <DetailGrid
                rows={[
                  { label: "Tier / port", value: `${selected.tier} · ${selected.port}` },
                  { label: "Family", value: agentRoleFamilyLabels[selected.roleFamily] },
                  { label: "Run status", value: selected.runStatus },
                  { label: "Load", value: `${selected.load}%` },
                  {
                    label: "Priority / weight",
                    value: `P${selectedCtrl.priority} · w=${selected.slotWeight.toFixed(2)}`,
                  },
                  {
                    label: "Confidence",
                    value: selected.confidence.toFixed(2),
                  },
                  {
                    label: "Last heartbeat",
                    value: `${selected.lastHeartbeatAt.slice(11, 19)}Z · ${hbAgeLabel(selected.lastHeartbeatAt)} ago`,
                  },
                  { label: "Last activity", value: selected.lastActivity },
                  {
                    label: "Advisory",
                    value: !selectedCtrl.enabled
                      ? "PAUSED"
                      : selectedCtrl.drain
                        ? "DRAIN"
                        : "ENABLED",
                  },
                ]}
              />

              {selected.notes ? (
                <p className="muted small" style={{ marginTop: 12 }}>
                  {selected.notes}
                </p>
              ) : null}

              <div style={{ marginTop: 14 }}>
                <div className="muted small" style={{ marginBottom: 6 }}>
                  Capabilities
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {selected.capabilities.map((c) => (
                    <Tag key={c} kind="info">
                      {c}
                    </Tag>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="muted small" style={{ marginBottom: 6 }}>
                  Pipelines / skills
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {selected.pipelines.length === 0 ? (
                    <Tag kind="neutral">no pipeline affinity</Tag>
                  ) : (
                    selected.pipelines.map((p) => (
                      <Link key={p} className="tag info" to="/pipelines" style={{ textDecoration: "none" }}>
                        {p}
                      </Link>
                    ))
                  )}
                  {selected.skills.map((s) => (
                    <Link key={s} className="tag neutral" to="/skills" style={{ textDecoration: "none" }}>
                      {s}
                    </Link>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Btn
                  variant={selectedCtrl.enabled ? "default" : "primary"}
                  onClick={() => {
                    const next = !selectedCtrl.enabled;
                    patchControl(selected.id, { enabled: next });
                    appendAudit(`${next ? "ENABLE" : "PAUSE"} ${selected.id}`);
                    push(`${selected.id} ${next ? "enabled" : "paused"} (advisory)`);
                  }}
                >
                  {selectedCtrl.enabled ? (
                    <>
                      <Pause size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
                      Pause
                    </>
                  ) : (
                    <>
                      <Play size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
                      Enable
                    </>
                  )}
                </Btn>
                <Btn
                  onClick={() => {
                    const next = !selectedCtrl.drain;
                    patchControl(selected.id, { drain: next });
                    appendAudit(`${next ? "DRAIN_ON" : "DRAIN_OFF"} ${selected.id}`);
                    push(`${selected.id} drain ${next ? "ON" : "OFF"}`, "warn");
                  }}
                >
                  {selectedCtrl.drain ? "Exit drain" : "Drain"}
                </Btn>
                <Btn
                  onClick={() => {
                    appendAudit(`RESTART_REQUEST ${selected.id}`);
                    push(`Restart requested · ${selected.id}`, "warn");
                  }}
                >
                  <RefreshCw size={14} style={{ marginRight: 4, verticalAlign: "middle" }} />
                  Restart
                </Btn>
                <Btn
                  variant="danger"
                  onClick={() => {
                    appendAudit(`HALT_PIPELINE_AFFINITY ${selected.id}`);
                    push(`Halt pipeline affinity · ${selected.id} (advisory)`, "danger");
                  }}
                >
                  Halt affinity
                </Btn>
              </div>

              <div className="field" style={{ marginTop: 14 }}>
                <label>Priority (advisory display)</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={selectedCtrl.priority}
                  onChange={(e) => {
                    const n = Math.min(5, Math.max(1, Number(e.target.value) || 1));
                    patchControl(selected.id, { priority: n });
                  }}
                />
              </div>
              <p className="muted small" style={{ marginBottom: 0 }}>
                Slot weight (roster):{" "}
                <span className="mono">{selected.slotWeight.toFixed(2)}</span> — display only
              </p>
            </>
          ) : (
            <div className="empty">Select an agent</div>
          )}
        </Card>
      </div>

      {/* Topology + BFT + tier map */}
      <div className="grid grid-3" style={{ marginBottom: 14 }}>
        <Card
          title="Team topology"
          action={<Network size={14} style={{ color: "var(--muted)" }} />}
        >
          <pre
            className="mono small"
            style={{
              margin: 0,
              whiteSpace: "pre-wrap",
              lineHeight: 1.55,
              color: "var(--text)",
            }}
          >
{`HYPERION  (operator UI · off critical path)
    │
 ARCHON ──► tier agents / A2A
    │
 GUARDIAN ── veto / Kelly (Tier 1)
    │
 TRENCH-OPS ──► edge PoPs (TKY/SIN/FRA/USE/AMS)
    │            in-process SigningNode
 AUGUR + PREDATOR + ATLAS
    └── 2-of-3 trade BFT (advisory)`}
          </pre>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 10 }}>
            Risk kernel <span className="mono">:19001</span> remains authoritative DENY.
          </p>
        </Card>

        <Card
          title="BFT voters"
          action={
            <Tag kind={agentBftStatus.consensus === "AUTHORIZE" ? "healthy" : "watch"}>
              {agentBftStatus.consensus}
            </Tag>
          }
        >
          <p className="muted small" style={{ marginTop: 0 }}>
            Trade votes · {agentBftStatus.threshold} · {commitVotes}/
            {agentBftStatus.tradeVoters.length} COMMIT
          </p>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Voter</th>
                  <th>Vote</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {agentBftStatus.tradeVoters.map((v) => (
                  <tr key={v.id}>
                    <td className="mono">{v.id}</td>
                    <td>
                      <Tag kind={v.vote === "COMMIT" ? "healthy" : "watch"}>{v.vote}</Tag>
                    </td>
                    <td className="small muted">{v.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small" style={{ marginTop: 10, marginBottom: 0 }}>
            {agentBftStatus.orchNote}
          </p>
          <p className="mono small" style={{ marginTop: 8, marginBottom: 0 }}>
            gate · {agentBftStatus.authoritativeGate}
          </p>
        </Card>

        <Card title="Model / tier map" action={<Cpu size={14} style={{ color: "var(--muted)" }} />}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {agentInferencePorts.map((p) => (
              <div key={p.port}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span className="mono">{p.port}</span>
                  <Tag kind={p.status === "UP" ? "healthy" : "watch"}>{p.status}</Tag>
                </div>
                <div className="muted small">{p.label}</div>
                <div className="mono small" style={{ marginTop: 4, lineHeight: 1.5 }}>
                  {p.agents.join(" · ") || "—"}
                </div>
              </div>
            ))}
          </div>
          <Link className="btn" to="/models" style={{ marginTop: 12, display: "inline-flex" }}>
            Open Model Tiers
          </Link>
        </Card>
      </div>

      {/* Quick links + audit */}
      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Related surfaces">
          <div className="option-grid">
            <Link className="option-tile" to="/models">
              <strong>
                <Cpu size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Model Tiers
              </strong>
              <span>inference map · BFT note</span>
            </Link>
            <Link className="option-tile" to="/manual-control">
              <strong>
                <SlidersHorizontal size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Manual Control
              </strong>
              <span>HMAC mutators · kill / freeze</span>
            </Link>
            <Link className="option-tile" to="/health">
              <strong>
                <HeartPulse size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Health & Verify
              </strong>
              <span>verify.sh · :19003 probe</span>
            </Link>
            <Link className="option-tile" to="/signing">
              <strong>
                <KeyRound size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Signing
              </strong>
              <span>in-process · no :19010 required</span>
            </Link>
            <Link className="option-tile" to="/identity">
              <strong>
                <Fingerprint size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Identity
              </strong>
              <span>autonomy matrix · 20 agents</span>
            </Link>
            <Link className="option-tile" to="/agents">
              <strong>
                <BrainCircuit size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
                Agent Teams
              </strong>
              <span>lighter card grid · spawn</span>
            </Link>
          </div>
        </Card>

        <Card
          title="Session audit"
          action={
            <Btn
              variant="ghost"
              onClick={() => {
                setDraft({ ...draft, audit: [] });
                push("Audit cleared");
              }}
            >
              Clear
            </Btn>
          }
        >
          {(draft.audit ?? []).length === 0 ? (
            <div className="empty">Advisory actions log here (local draft until Save).</div>
          ) : (
            <div className="mono small" style={{ maxHeight: 220, overflow: "auto", lineHeight: 1.6 }}>
              {(draft.audit ?? []).map((line) => (
                <div key={line}>{line}</div>
              ))}
            </div>
          )}
          <p className="muted small" style={{ marginBottom: 0, marginTop: 10 }}>
            <Shield size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
            Advisory only — does not control live OpenClaw processes unless wired to titan-safety.
          </p>
        </Card>
      </div>

      <Drawer
        open={drawerOpen && !!selected}
        onClose={() => setDrawerOpen(false)}
        title={selected?.id ?? ""}
        subtitle={selected?.role}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setDrawerOpen(false)}>
              Close
            </Btn>
            <Btn
              onClick={() => {
                if (!selected) return;
                appendAudit(`RESTART_REQUEST ${selected.id}`);
                push(`Restart requested · ${selected.id}`, "warn");
              }}
            >
              Restart
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                if (!selected) return;
                const next = !selectedCtrl.enabled;
                patchControl(selected.id, { enabled: next });
                appendAudit(`${next ? "ENABLE" : "PAUSE"} ${selected.id}`);
                push(`${selected.id} ${next ? "enabled" : "paused"} (advisory)`);
              }}
            >
              {selectedCtrl.enabled ? "Pause" : "Enable"}
            </Btn>
          </>
        }
      >
        {selected ? (
          <DetailGrid
            rows={[
              { label: "Port", value: selected.port },
              { label: "Model", value: selected.model },
              { label: "Status", value: selected.runStatus },
              { label: "Confidence", value: selected.confidence.toFixed(2) },
              { label: "Activity", value: selected.lastActivity },
            ]}
          />
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
