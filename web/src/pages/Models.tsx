import { PageHeader, Card, Tag } from "@/components/ui";
import { modelTiers } from "@/lib/data";

export function Models() {
  return (
    <>
      <PageHeader
        title="Model Tiers"
        subtitle="Local open-weights only on the live path. No Claude / GPT / Gemini on TRENCH-OPS, GUARDIAN, or EXECUTOR."
      />
      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Port</th>
                <th>Model</th>
                <th>Role</th>
                <th>Live path</th>
              </tr>
            </thead>
            <tbody>
              {modelTiers.map((m) => (
                <tr key={m.tier}>
                  <td>{m.tier}</td>
                  <td>{m.port}</td>
                  <td>{m.model}</td>
                  <td style={{ fontFamily: "var(--font)" }}>{m.role}</td>
                  <td>
                    <Tag kind={m.live ? "healthy" : "neutral"}>
                      {m.live ? "YES" : "R&D only"}
                    </Tag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="BFT voters" style={{ marginTop: 14 }}>
        <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>GUARDIAN → Tier 1 :30000 (critical path)</li>
          <li>ARCHON → Tier 2 :30001</li>
          <li>CORTEX → DeepSeek :30005 when up; fallback Tier 2</li>
          <li>Trade votes AUGUR + PREDATOR + ATLAS — advisory; risk kernel DENY wins</li>
        </ul>
      </Card>
    </>
  );
}
