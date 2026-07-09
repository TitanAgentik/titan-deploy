import { useMemo } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { workspaceFiles } from "@/lib/data";

type RoleFilter = "all" | "bootstrap" | "ref";

const WORKSPACE_DEFAULTS = { roleFilter: "all" as RoleFilter, sortBy: "path" as "path" | "bytes" };

const ROLE_TABS: { id: RoleFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "bootstrap", label: "Bootstrap" },
  { id: "ref", label: "Refs" },
];

export function Workspace() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("workspace", WORKSPACE_DEFAULTS);

  const rows = useMemo(() => {
    let list = workspaceFiles;
    if (draft.roleFilter !== "all") {
      list = list.filter((f) => f.role === draft.roleFilter);
    }
    return [...list].sort((a, b) =>
      draft.sortBy === "path" ? a.path.localeCompare(b.path) : b.bytes - a.bytes,
    );
  }, [draft.roleFilter, draft.sortBy]);

  return (
    <>
      <PageHeader
        title="Workspace"
        subtitle="OpenClaw / Hermes bootstrap files and refs companions — what agents actually load into context."
        actions={
          <>
            <Btn
              variant={draft.sortBy === "path" ? "primary" : "ghost"}
              onClick={() => update({ sortBy: "path" })}
            >
              Sort path
            </Btn>
            <Btn
              variant={draft.sortBy === "bytes" ? "primary" : "ghost"}
              onClick={() => update({ sortBy: "bytes" })}
            >
              Sort size
            </Btn>
            <Btn variant="primary">Open in editor</Btn>
          </>
        }
      />

      <SaveBar
        dirty={dirty}
        lastSavedAt={lastSavedAt}
        onSave={() => {
          save();
          push("Saved locally (cockpit)", "ok");
        }}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
      />

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {ROLE_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn${draft.roleFilter === t.id ? " primary" : ""}`}
            onClick={() => update({ roleFilter: t.id })}
          >
            {t.label}
          </button>
        ))}
      </div>

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
              {rows.map((f) => (
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

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
