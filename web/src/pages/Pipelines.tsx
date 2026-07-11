import { useMemo } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { pipelinesCatalog } from "@/lib/data";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { advisoryLabel, usePipelinesProvider } from "@/lib/providers";

type PhaseFilter = "all" | "funded" | "pending_yes" | "catalog" | "defunded" | "paper";
type ViewMode = "table" | "compact";

type PipelinesPrefs = {
  phaseFilter: PhaseFilter;
  selectedId: string | null;
  viewMode: ViewMode;
};

const DEFAULTS: PipelinesPrefs = {
  phaseFilter: "all",
  selectedId: null,
  viewMode: "table",
};

const PHASES: { id: PhaseFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "funded", label: "Funded" },
  { id: "pending_yes", label: "Pending YES" },
  { id: "catalog", label: "Catalog" },
  { id: "paper", label: "Paper" },
  { id: "defunded", label: "Defunded" },
];

export function Pipelines() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("pipelines", DEFAULTS);
  const { result: pipelinesResult } = usePipelinesProvider();

  const catalog = pipelinesResult?.data.catalog ?? pipelinesCatalog;

  const rows = useMemo(() => {
    if (draft.phaseFilter === "all") return catalog;
    return catalog.filter((p) => p.phase === draft.phaseFilter);
  }, [draft.phaseFilter, catalog]);

  const onSave = () => {
    save();
    push("Pipelines view saved locally", "ok");
  };

  return (
    <>
      <PageHeader
        title="Pipelines"
        subtitle="DEX-only strategy catalog (R02 / R46). Concentration cap: ≤4 funded HEALTHY lanes via allocator."
        actions={
          <>
            <span className="chip">{advisoryLabel(pipelinesResult)}</span>
            <Link className="btn" to="/qi-optimizer">
              QI Optimizer
            </Link>
            <Btn onClick={() => push("Activation request queued (advisory)", "warn")}>
              Request activation
            </Btn>
          </>
        }
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        onSave={onSave}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
      />

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {PHASES.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`btn${draft.phaseFilter === p.id ? " primary" : ""}`}
            onClick={() => update({ phaseFilter: p.id })}
          >
            {p.label}
          </button>
        ))}
        <button
          type="button"
          className={`btn${draft.viewMode === "table" ? " primary" : ""}`}
          onClick={() => update({ viewMode: "table" })}
        >
          Table
        </button>
        <button
          type="button"
          className={`btn${draft.viewMode === "compact" ? " primary" : ""}`}
          onClick={() => update({ viewMode: "compact" })}
        >
          Compact
        </button>
      </div>

      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Lifecycle</th>
                {draft.viewMode === "table" ? (
                  <>
                    <th>Edge</th>
                    <th>§FL</th>
                    <th>P22</th>
                  </>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr
                  key={p.id}
                  className={draft.selectedId === p.id ? "row-selected" : undefined}
                  style={{
                    cursor: "pointer",
                    background:
                      draft.selectedId === p.id ? "rgba(56, 189, 248, 0.08)" : undefined,
                  }}
                  onClick={() =>
                    update({ selectedId: draft.selectedId === p.id ? null : p.id })
                  }
                >
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
                  {draft.viewMode === "table" ? (
                    <>
                      <td>{p.edge}</td>
                      <td>
                        {"flash" in p && p.flash ? <Tag kind="info">flash</Tag> : "—"}
                      </td>
                      <td>
                        {"memecoin" in p && p.memecoin ? (
                          <Tag kind="watch">P22</Tag>
                        ) : (
                          "—"
                        )}
                      </td>
                    </>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {draft.selectedId ? (
          <p className="muted small" style={{ marginBottom: 0, marginTop: 10 }}>
            Selected: {draft.selectedId} — Save to keep selection across navigation
          </p>
        ) : null}
      </Card>
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
