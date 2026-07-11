import { useMemo } from "react";
import { PageHeader, Card, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { goals } from "@/lib/data";

type SortBy = "progress" | "eta";

const GOALS_DEFAULTS = { sortBy: "progress" as SortBy };

export function GoalsLab() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("goals", GOALS_DEFAULTS);

  const sorted = useMemo(() => {
    const list = [...goals];
    if (draft.sortBy === "progress") {
      return list.sort((a, b) => b.progress - a.progress);
    }
    return list.sort((a, b) => a.eta.localeCompare(b.eta));
  }, [draft.sortBy]);

  return (
    <>
      <PageHeader
        title="Goals Lab"
        subtitle="Operator OKRs mapped to capital milestones, fill quotas, and pre-live gates."
        actions={
          <>
            <Btn
              variant={draft.sortBy === "progress" ? "primary" : "ghost"}
              onClick={() => update({ sortBy: "progress" })}
            >
              By progress
            </Btn>
            <Btn
              variant={draft.sortBy === "eta" ? "primary" : "ghost"}
              onClick={() => update({ sortBy: "eta" })}
            >
              By ETA
            </Btn>
            <Btn variant="primary">Add goal</Btn>
          </>
        }
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

      <div className="grid grid-2">
        {sorted.map((g) => (
          <Card key={g.id} title={g.title}>
            <div className="mono" style={{ fontSize: 28, marginBottom: 8 }}>
              {g.progress}%
            </div>
            <div className="progress">
              <span style={{ width: `${g.progress}%` }} />
            </div>
            <div
              className="muted small"
              style={{ marginTop: 10, display: "flex", justifyContent: "space-between" }}
            >
              <span>Target · {g.target}</span>
              <span>ETA · {g.eta}</span>
            </div>
          </Card>
        ))}
      </div>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
