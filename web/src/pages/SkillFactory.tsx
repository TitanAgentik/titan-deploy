import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { skills } from "@/lib/data";

export function SkillFactory() {
  return (
    <>
      <PageHeader
        title="Skill Factory"
        subtitle="Skill inventory, staging → live promotion (Phase 5 YES), and shadow evolution packages."
        actions={<Btn variant="primary">Import skill</Btn>}
      />
      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Skill</th>
                <th>Version</th>
                <th>Owner</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {skills.map((s) => (
                <tr key={s.name}>
                  <td>{s.name}</td>
                  <td>{s.version}</td>
                  <td>{s.owner}</td>
                  <td>
                    <Tag
                      kind={
                        s.status === "live" ? "healthy" : s.status === "shadow" ? "watch" : "info"
                      }
                    >
                      {s.status}
                    </Tag>
                  </td>
                  <td>
                    <Btn variant="ghost" disabled={s.status === "live"}>
                      Promote
                    </Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
