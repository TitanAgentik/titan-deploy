import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { automations } from "@/lib/data";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { ToastStack, useToasts } from "@/components/interactive";

const AUTOMATION_DEFAULTS = {
  enabled: Object.fromEntries(automations.map((a) => [a.id, a.enabled])) as Record<string, boolean>,
};

export function Automations() {
  const { toasts, push, dismiss } = useToasts();
  const {
    draft,
    setDraft,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("automations", AUTOMATION_DEFAULTS);

  const rows = automations.map((a) => ({
    ...a,
    enabled: draft.enabled[a.id] ?? a.enabled,
  }));

  const toggle = (id: string) =>
    setDraft((d) => ({
      ...d,
      enabled: { ...d.enabled, [id]: !(d.enabled[id] ?? true) },
    }));

  return (
    <>
      <PageHeader
        title="Automations"
        subtitle="Scheduled and event-driven control loops — profit sweep, DMS, TCA defund, evolution freeze."
        actions={<Btn variant="primary">New automation</Btn>}
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        onSave={() => {
          save();
          push("Saved locally", "ok");
        }}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
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
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
