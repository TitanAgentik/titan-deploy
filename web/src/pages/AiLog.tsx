import { useMemo } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { aiLog } from "@/lib/data";

type LevelFilter = "all" | "info" | "warn" | "error";

const AI_LOG_DEFAULTS = { levelFilter: "all" as LevelFilter };

const LEVEL_TABS: { id: LevelFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "info", label: "Info" },
  { id: "warn", label: "Warn" },
  { id: "error", label: "Error" },
];

export function AiLog() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("aiLog", AI_LOG_DEFAULTS);

  const entries = useMemo(() => {
    if (draft.levelFilter === "all") return aiLog;
    return aiLog.filter((e) => e.level === draft.levelFilter);
  }, [draft.levelFilter]);

  return (
    <>
      <PageHeader
        title="AI Log"
        subtitle="Structured decision / agent event stream — mirrors decision_log.jsonl style audit trail."
        actions={
          <>
            <Btn variant="ghost">Tail live</Btn>
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

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {LEVEL_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn${draft.levelFilter === t.id ? " primary" : ""}`}
            onClick={() => update({ levelFilter: t.id })}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Card>
        {entries.length === 0 ? (
          <div className="empty">No entries match this filter.</div>
        ) : (
          <div className="timeline">
            {entries.map((e) => (
              <div className="timeline-item" key={e.ts + e.msg}>
                <div
                  className="rail"
                  style={{
                    background:
                      e.level === "warn"
                        ? "var(--warn)"
                        : e.level === "error"
                          ? "var(--danger)"
                          : "var(--accent)",
                  }}
                />
                <div>
                  <div className="when">
                    {e.ts} · <Tag kind="info">{e.agent}</Tag>{" "}
                    <Tag kind={e.level === "warn" ? "watch" : "neutral"}>{e.level}</Tag>
                  </div>
                  <div className="what">{e.msg}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
