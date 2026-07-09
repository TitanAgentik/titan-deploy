import { useState } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import {
  ActionMenu,
  DetailGrid,
  Drawer,
  Modal,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import { agents } from "@/lib/data";

type Agent = (typeof agents)[number];

export function AgentTeams() {
  const { toasts, push, dismiss } = useToasts();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [spawn, setSpawn] = useState(false);
  const [parent, setParent] = useState("ARCHON");
  const [task, setTask] = useState("Investigate P12 WATCH lane");

  return (
    <>
      <PageHeader
        title="Agent Teams"
        subtitle="Click an agent card for controls — spawn, restart, route, or inspect load."
        actions={
          <Btn variant="primary" onClick={() => setSpawn(true)}>
            Spawn sub-agent…
          </Btn>
        }
      />
      <div className="grid grid-3">
        {agents.map((a) => (
          <div
            key={a.id}
            className="card metric-click"
            style={{ cursor: "pointer" }}
            onClick={() => setAgent(a)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") setAgent(a);
            }}
            role="button"
            tabIndex={0}
          >
            <div className="card-title" onClick={(e) => e.stopPropagation()}>
              <span>{a.id}</span>
              <ActionMenu
                label="⋯"
                variant="ghost"
                items={[
                  { label: "Open", onClick: () => setAgent(a) },
                  { label: "Restart session", onClick: () => push(`Restart ${a.id}`) },
                  {
                    label: "Spawn child",
                    disabled: a.status === "dormant",
                    onClick: () => {
                      setParent(a.id);
                      setSpawn(true);
                    },
                  },
                ]}
              />
            </div>
            <div className="muted small">{a.role}</div>
            <div className="mono" style={{ marginTop: 8, fontSize: 13 }}>
              {a.tier}
            </div>
            <div
              style={{
                marginTop: 10,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Tag
                kind={
                  a.status === "online" ? "healthy" : a.status === "dormant" ? "neutral" : "watch"
                }
              >
                {a.status}
              </Tag>
              <span className="mono small muted">load {a.load}%</span>
            </div>
            <div className="progress" style={{ marginTop: 10 }}>
              <span style={{ width: `${a.load}%` }} />
            </div>
          </div>
        ))}
      </div>

      <Drawer
        open={!!agent}
        onClose={() => setAgent(null)}
        title={agent?.id ?? ""}
        subtitle={agent?.role}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setAgent(null)}>
              Close
            </Btn>
            <Btn
              disabled={agent?.status === "dormant"}
              onClick={() => {
                push(`Restart ${agent?.id}`);
                setAgent(null);
              }}
            >
              Restart
            </Btn>
            <Btn
              variant="primary"
              disabled={agent?.status === "dormant"}
              onClick={() => {
                if (agent) setParent(agent.id);
                setAgent(null);
                setSpawn(true);
              }}
            >
              Spawn child
            </Btn>
          </>
        }
      >
        {agent ? (
          <>
            <DetailGrid
              rows={[
                { label: "Tier", value: agent.tier },
                { label: "Status", value: agent.status },
                { label: "Load", value: `${agent.load}%` },
                { label: "Prompt mode", value: "sub-agents: AGENTS+TOOLS only" },
              ]}
            />
            <div className="option-grid" style={{ marginTop: 14 }}>
              <button type="button" className="option-tile" onClick={() => push(`Tail log ${agent.id}`)}>
                <strong>Tail AI log</strong>
                <span>filter agent</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push(`Pin model ${agent.tier}`)}>
                <strong>Pin model</strong>
                <span>no hot-swap</span>
              </button>
            </div>
          </>
        ) : null}
      </Drawer>

      <Modal
        open={spawn}
        onClose={() => setSpawn(false)}
        title="Spawn sub-agent"
        subtitle="Max depth 2 · max 5 children per parent"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSpawn(false)}>
              Cancel
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                push(`Spawned under ${parent}: ${task}`);
                setSpawn(false);
              }}
            >
              Spawn
            </Btn>
          </>
        }
      >
        <div className="form-row">
          <div className="field">
            <label>Parent</label>
            <select value={parent} onChange={(e) => setParent(e.target.value)}>
              {agents
                .filter((a) => a.status !== "dormant")
                .map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.id}
                  </option>
                ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1, minWidth: 220 }}>
            <label>Task</label>
            <input value={task} onChange={(e) => setTask(e.target.value)} />
          </div>
        </div>
      </Modal>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
