import { useMemo } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { skills } from "@/lib/data";

type StatusFilter = "all" | "live" | "shadow" | "staging";

const SKILLS_DEFAULTS = { statusFilter: "all" as StatusFilter };

const STATUS_TABS: { id: StatusFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "live", label: "Live" },
  { id: "shadow", label: "Shadow" },
  { id: "staging", label: "Staging" },
];

export function SkillFactory() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("skills", SKILLS_DEFAULTS);

  const rows = useMemo(() => {
    if (draft.statusFilter === "all") return skills;
    return skills.filter((s) => s.status === draft.statusFilter);
  }, [draft.statusFilter]);

  return (
    <>
      <PageHeader
        title="Skill Factory"
        subtitle="Skill inventory, staging → live promotion (Phase 5 YES), and shadow evolution packages."
        actions={<Btn variant="primary">Import skill</Btn>}
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

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {STATUS_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn${draft.statusFilter === t.id ? " primary" : ""}`}
            onClick={() => update({ statusFilter: t.id })}
          >
            {t.label}
          </button>
        ))}
      </div>

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
              {rows.map((s) => (
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

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
