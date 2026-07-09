import { Link } from "react-router-dom";
import { PageHeader, Card, Tag, Metric } from "@/components/ui";
import { edgeMesh, edgePops, edgeStrategyRouting, latencyBudget } from "@/lib/data";

export function EdgeMesh() {
  return (
    <>
      <PageHeader
        title="Edge Mesh"
        subtitle="Full 5-PoP mesh — paper + live use identical routing (latency_faithful). Stateless TRENCH-OPS workers, sub-ms to DEX / sequencers / builders."
        actions={
          <Link className="btn primary" to="/latency">
            Open Latency
          </Link>
        }
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Mode" value={edgeMesh.mode.replace("_", " ").toUpperCase()} />
        <Metric label="Active PoPs" value={String(edgeMesh.activePops)} />
        <Metric label="Default PoP" value={edgeMesh.defaultPop} />
        <Metric label="Paper routing" value={edgeMesh.paperLatencyFaithful ? "FAITHFUL" : "OFF"} />
      </div>

      <Card title="PoP inventory">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>PoP</th>
                <th>Region</th>
                <th>WireGuard</th>
                <th>Primary targets</th>
                <th>RTT p95</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {edgePops.map((e) => (
                <tr key={e.id}>
                  <td>{e.id}</td>
                  <td>{e.region}</td>
                  <td className="mono small">{e.wg}</td>
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

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <Card title="Strategy → PoP routing">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Primary</th>
                  <th>Fallback</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {edgeStrategyRouting.map((r) => (
                  <tr key={r.strategy}>
                    <td>{r.strategy}</td>
                    <td>{r.primary}</td>
                    <td>{r.fallback}</td>
                    <td className="muted small">{r.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Latency budget (hot path)">
          <DetailList
            rows={[
              { k: "Gate p95", v: `${latencyBudget.hotPathGateP95Ms} ms` },
              { k: "Submit p95", v: `${latencyBudget.hotPathSubmitP95Ms} ms` },
              { k: "Home → edge", v: `${latencyBudget.homeToEdgeP95Ms} ms` },
              { k: "Edge → DEX / sequencer", v: `${latencyBudget.edgeToExchangeP95Ms} ms` },
              { k: "Nostr dispatch", v: `${latencyBudget.nostrDispatchMs} ms` },
              { k: "Hot pipelines", v: latencyBudget.hotPipelines.join(", ") },
            ]}
          />
          <p className="muted small" style={{ marginTop: 12, marginBottom: 0 }}>
            CLI: <span className="mono">titan-safety edge route --venue jito --strategy P22</span>
          </p>
        </Card>
      </div>

      <Card title="Dispatch path" style={{ marginTop: 14 }}>
        <p className="muted small" style={{ margin: 0 }}>
          TRENCH-OPS → lowest live p50 RTT PoP from <span className="mono">edge_mesh.yaml</span> → Nostr
          NIP-44 (Kind 1059) → edge worker broadcast ≤{latencyBudget.nostrDispatchMs} ms. Bootstrap:{" "}
          <span className="mono">POP=EDGE-* bash edge_pop_bootstrap.sh</span>
        </p>
      </Card>
    </>
  );
}

function DetailList({ rows }: { rows: { k: string; v: string }[] }) {
  return (
    <dl className="muted small" style={{ margin: 0, display: "grid", gap: 8 }}>
      {rows.map((r) => (
        <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <dt>{r.k}</dt>
          <dd className="mono" style={{ margin: 0, textAlign: "right" }}>
            {r.v}
          </dd>
        </div>
      ))}
    </dl>
  );
}
