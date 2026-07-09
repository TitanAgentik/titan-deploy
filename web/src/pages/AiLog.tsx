import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { aiLog } from "@/lib/data";

export function AiLog() {
  return (
    <>
      <PageHeader
        title="AI Log"
        subtitle="Structured decision / agent event stream — mirrors decision_log.jsonl style audit trail."
        actions={
          <>
            <Btn variant="ghost">Filter</Btn>
            <Btn>Tail live</Btn>
          </>
        }
      />
      <Card>
        <div className="timeline">
          {aiLog.map((e) => (
            <div className="timeline-item" key={e.ts + e.msg}>
              <div
                className="rail"
                style={{
                  background:
                    e.level === "warn" ? "var(--warn)" : e.level === "error" ? "var(--danger)" : "var(--accent)",
                }}
              />
              <div>
                <div className="when">
                  {e.ts} · <Tag kind="info">{e.agent}</Tag>{" "}
                  <Tag kind={e.level === "warn" ? "watch" : "neutral"}>{e.level}</Tag>
                </div>
                <div className="what">{e.msg}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
