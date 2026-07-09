import { useState } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { questions } from "@/lib/data";

export function Questions() {
  const [draft, setDraft] = useState("");

  return (
    <>
      <PageHeader
        title="Questions"
        subtitle="Human-in-the-loop queue — ClawBuddy-style escalation for uncertain agent decisions and Phase 5 YES prompts."
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
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => (
                  <tr key={q.id}>
                    <td>{q.id}</td>
                    <td>{q.from}</td>
                    <td style={{ fontFamily: "var(--font)", maxWidth: 280 }}>{q.text}</td>
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
                    <td>
                      <Tag kind={q.status === "awaiting_yes" ? "watch" : "neutral"}>{q.status}</Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <Btn variant="primary">YES · promote</Btn>
            <Btn>HOLD / de-risk</Btn>
            <Btn variant="danger">NO · archive</Btn>
          </div>
        </Card>

        <Card title="Ask TITAN">
          <div className="field">
            <label>Question</label>
            <textarea
              rows={6}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask CORTEX / ARCHON — answers cite sources; uncertain → escalate here"
            />
          </div>
          <div style={{ marginTop: 10 }}>
            <Btn variant="primary" disabled={!draft.trim()}>
              Submit
            </Btn>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>
            Inspired by ClawBuddy hatchling↔buddy Q&amp;A with human review before publish.
          </p>
        </Card>
      </div>
    </>
  );
}
