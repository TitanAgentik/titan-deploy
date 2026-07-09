import { PageHeader, Card, Tag } from "@/components/ui";
import { edgePops } from "@/lib/data";

export function EdgeMesh() {
  return (
    <>
      <PageHeader
        title="Edge Mesh"
        subtitle="Stateless TRENCH-OPS workers colocated with exchange matching engines — sub-ms RTT. Phase 1 single-PoP stretch; full mesh Phase 3+."
      />
      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>PoP</th>
                <th>Region</th>
                <th>Primary targets</th>
                <th>RTT</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {edgePops.map((e) => (
                <tr key={e.id}>
                  <td>{e.id}</td>
                  <td>{e.region}</td>
                  <td style={{ fontFamily: "var(--font)" }}>{e.targets}</td>
                  <td>{e.rtt}</td>
                  <td>
                    <Tag kind={e.status === "healthy" ? "healthy" : "watch"}>{e.status}</Tag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="Routing" style={{ marginTop: 14 }}>
        <p className="muted small" style={{ margin: 0 }}>
          TRENCH-OPS selects edge via routing table → Nostr NIP-44 Event Pub/Sub (Kind 1059) → edge
          worker broadcast within ~3 ms. Always pick lowest live p50 RTT to target chain.
        </p>
      </Card>
    </>
  );
}
