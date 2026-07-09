import { PageHeader, Card, Btn } from "@/components/ui";
import { goals } from "@/lib/data";

export function GoalsLab() {
  return (
    <>
      <PageHeader
        title="Goals Lab"
        subtitle="Operator OKRs mapped to capital milestones, fill quotas, and pre-live gates."
        actions={<Btn variant="primary">Add goal</Btn>}
      />
      <div className="grid grid-2">
        {goals.map((g) => (
          <Card key={g.id} title={g.title}>
            <div className="mono" style={{ fontSize: 28, marginBottom: 8 }}>
              {g.progress}%
            </div>
            <div className="progress">
              <span style={{ width: `${g.progress}%` }} />
            </div>
            <div
              className="muted small"
              style={{ marginTop: 10, display: "flex", justifyContent: "space-between" }}
            >
              <span>Target · {g.target}</span>
              <span>ETA · {g.eta}</span>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
