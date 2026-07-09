import { useState } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import {
  ActionMenu,
  DetailGrid,
  Drawer,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import { questions } from "@/lib/data";

type Q = (typeof questions)[number];

export function Questions() {
  const { toasts, push, dismiss } = useToasts();
  const [draft, setDraft] = useState("");
  const [target, setTarget] = useState("CORTEX");
  const [selected, setSelected] = useState<Q | null>(null);
  const [drawer, setDrawer] = useState<Q | null>(null);

  const answer = (q: Q, action: string) => {
    push(`${action} · ${q.id}`, action.startsWith("NO") ? "danger" : action.startsWith("HOLD") ? "warn" : "ok");
    setDrawer(null);
  };

  return (
    <>
      <PageHeader
        title="Questions"
        subtitle="Click a question for full context and reply options. Ask Titan Agentik with a target agent."
      />

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card title="Open queue">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>From</th>
                  <th>Question</th>
                  <th>Priority</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => (
                  <tr
                    key={q.id}
                    className="row-click"
                    onClick={() => {
                      setSelected(q);
                      setDrawer(q);
                    }}
                  >
                    <td>{q.id}</td>
                    <td>{q.from}</td>
                    <td style={{ fontFamily: "var(--font)", maxWidth: 240 }}>{q.text}</td>
                    <td>
                      <Tag
                        kind={
                          q.priority === "critical"
                            ? "bleeding"
                            : q.priority === "high"
                              ? "watch"
                              : "info"
                        }
                      >
                        {q.priority}
                      </Tag>
                    </td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <ActionMenu
                        label="Reply"
                        variant="ghost"
                        items={[
                          { label: "Open", onClick: () => setDrawer(q) },
                          { label: "YES · promote", onClick: () => answer(q, "YES") },
                          { label: "HOLD / de-risk", onClick: () => answer(q, "HOLD") },
                          { label: "NO · archive", danger: true, onClick: () => answer(q, "NO") },
                          { label: "Ask follow-up", onClick: () => { setDraft(`Re: ${q.id} — `); push("Draft started"); } },
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            <Btn
              variant="primary"
              disabled={!selected}
              onClick={() => selected && answer(selected, "YES")}
            >
              YES · promote
            </Btn>
            <Btn disabled={!selected} onClick={() => selected && answer(selected, "HOLD")}>
              HOLD / de-risk
            </Btn>
            <Btn
              variant="danger"
              disabled={!selected}
              onClick={() => selected && answer(selected, "NO")}
            >
              NO · archive
            </Btn>
          </div>
        </Card>

        <Card title="Ask Titan Agentik">
          <div className="option-grid" style={{ marginBottom: 12 }}>
            {["CORTEX", "ARCHON", "GUARDIAN", "ARBITER"].map((a) => (
              <button
                key={a}
                type="button"
                className={`option-tile${target === a ? " active" : ""}`}
                onClick={() => setTarget(a)}
              >
                <strong>{a}</strong>
                <span>route to</span>
              </button>
            ))}
          </div>
          <div className="field">
            <label>Question</label>
            <textarea
              rows={5}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask — uncertain answers escalate into this queue"
            />
          </div>
          <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
            <Btn
              variant="primary"
              disabled={!draft.trim()}
              onClick={() => {
                push(`Asked ${target}: ${draft.slice(0, 48)}…`);
                setDraft("");
              }}
            >
              Submit to {target}
            </Btn>
            <ActionMenu
              label="Templates"
              items={[
                {
                  label: "Phase 5 review",
                  onClick: () => setDraft("Should we YES Phase 5 for the selected strategy?"),
                },
                {
                  label: "Lane defund?",
                  onClick: () => setDraft("Is auto-defund correct for the BLEEDING lane?"),
                },
                {
                  label: "Unfreeze evolution?",
                  onClick: () => setDraft("Safe to unfreeze evolution for shadow-only GEPA?"),
                },
              ]}
            />
          </div>
        </Card>
      </div>

      <Drawer
        open={!!drawer}
        onClose={() => setDrawer(null)}
        title={drawer?.id ?? ""}
        subtitle={drawer ? `${drawer.from} · ${drawer.priority}` : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setDrawer(null)}>
              Close
            </Btn>
            <Btn variant="danger" onClick={() => drawer && answer(drawer, "NO")}>
              NO
            </Btn>
            <Btn onClick={() => drawer && answer(drawer, "HOLD")}>HOLD</Btn>
            <Btn variant="primary" onClick={() => drawer && answer(drawer, "YES")}>
              YES
            </Btn>
          </>
        }
      >
        {drawer ? (
          <>
            <p style={{ marginTop: 0, lineHeight: 1.5 }}>{drawer.text}</p>
            <DetailGrid
              rows={[
                { label: "Status", value: drawer.status },
                { label: "Priority", value: drawer.priority },
                { label: "From", value: drawer.from },
              ]}
            />
            <div className="option-grid" style={{ marginTop: 14 }}>
              <button
                type="button"
                className="option-tile"
                onClick={() => push("Assigned to GUARDIAN")}
              >
                <strong>Assign GUARDIAN</strong>
                <span>risk review</span>
              </button>
              <button
                type="button"
                className="option-tile"
                onClick={() => push("Snooze 1h")}
              >
                <strong>Snooze 1h</strong>
                <span>keep open</span>
              </button>
            </div>
          </>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
