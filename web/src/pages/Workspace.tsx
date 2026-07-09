import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { workspaceFiles } from "@/lib/data";

export function Workspace() {
  return (
    <>
      <PageHeader
        title="Workspace"
        subtitle="OpenClaw / Hermes bootstrap files and refs companions — what agents actually load into context."
        actions={<Btn variant="primary">Open in editor</Btn>}
      />
      <div className="alert-banner">
        Do not load TITAN.reconciled.md (~750KB) into agent context. Use bootstrap set + TITAN.digest.md.
      </div>
      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Path</th>
                <th>Bytes</th>
                <th>Role</th>
                <th>Limit</th>
              </tr>
            </thead>
            <tbody>
              {workspaceFiles.map((f) => (
                <tr key={f.path}>
                  <td>{f.path}</td>
                  <td>{f.bytes.toLocaleString()}</td>
                  <td>
                    <Tag kind={f.role === "bootstrap" ? "healthy" : "info"}>{f.role}</Tag>
                  </td>
                  <td>
                    {f.role === "bootstrap" ? (
                      <Tag kind={f.bytes <= 20000 ? "healthy" : "bleeding"}>
                        {f.bytes <= 20000 ? "≤20KB OK" : "OVER"}
                      </Tag>
                    ) : (
                      <Tag kind="neutral">ref</Tag>
                    )}
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
