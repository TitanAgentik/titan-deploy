import { useState } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { automations } from "@/lib/data";

export function Automations() {
  const [rows, setRows] = useState(automations);

  const toggle = (id: string) =>
    setRows((r) => r.map((a) => (a.id === id ? { ...a, enabled: !a.enabled } : a)));

  return (
    <>
      <PageHeader
        title="Automations"
        subtitle="Scheduled and event-driven control loops — profit sweep, DMS, TCA defund, evolution freeze."
        actions={<Btn variant="primary">New automation</Btn>}
      />
      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Name</th>
                <th>Schedule</th>
                <th>State</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{a.name}</td>
                  <td>{a.schedule}</td>
                  <td>
                    <Tag kind={a.enabled ? "healthy" : "neutral"}>
                      {a.enabled ? "ENABLED" : "OFF"}
                    </Tag>
                  </td>
                  <td>
                    <Btn variant="ghost" onClick={() => toggle(a.id)}>
                      {a.enabled ? "Disable" : "Enable"}
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
