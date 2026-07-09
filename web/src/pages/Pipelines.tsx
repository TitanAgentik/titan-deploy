import { Link } from "react-router-dom";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { pipelinesCatalog } from "@/lib/data";

export function Pipelines() {
  return (
    <>
      <PageHeader
        title="Pipelines"
        subtitle="DEX-only strategy catalog (R02 / R46). Concentration cap: ≤4 funded HEALTHY lanes via allocator."
        actions={
          <>
            <Link className="btn" to="/qi-optimizer">
              QI Optimizer
            </Link>
            <Btn>Request activation</Btn>
          </>
        }
      />
      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Lifecycle</th>
                <th>Edge</th>
                <th>§FL</th>
                <th>P22</th>
              </tr>
            </thead>
            <tbody>
              {pipelinesCatalog.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.name}</td>
                  <td>
                    <Tag
                      kind={
                        p.phase === "funded"
                          ? "healthy"
                          : p.phase === "defunded"
                            ? "bleeding"
                            : p.phase === "pending_yes"
                              ? "watch"
                              : "info"
                      }
                    >
                      {p.phase}
                    </Tag>
                  </td>
                  <td>{p.edge}</td>
                  <td>{"flash" in p && p.flash ? <Tag kind="info">flash</Tag> : "—"}</td>
                  <td>{"memecoin" in p && p.memecoin ? <Tag kind="watch">P22</Tag> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
