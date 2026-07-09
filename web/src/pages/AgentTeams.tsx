import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { agents } from "@/lib/data";

export function AgentTeams() {
  return (
    <>
      <PageHeader
        title="Agent Teams"
        subtitle="23-agent roster — tiers, load, and BFT voter roles. Quantum agents remain DORMANT."
        actions={<Btn>Spawn sub-agent</Btn>}
      />
      <div className="grid grid-3">
        {agents.map((a) => (
          <Card key={a.id} title={a.id}>
            <div className="muted small">{a.role}</div>
            <div className="mono" style={{ marginTop: 8, fontSize: 13 }}>
              {a.tier}
            </div>
            <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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
          </Card>
        ))}
      </div>
    </>
  );
}
