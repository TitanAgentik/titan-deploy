import { useMemo } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { modelTiers } from "@/lib/data";

const MODELS_DEFAULTS = { liveOnly: false };

export function Models() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("models", MODELS_DEFAULTS);

  const rows = useMemo(
    () => (draft.liveOnly ? modelTiers.filter((m) => m.live) : modelTiers),
    [draft.liveOnly],
  );

  return (
    <>
      <PageHeader
        title="Model Tiers"
        subtitle="Local open-weights only on the live path. No Claude / GPT / Gemini on TRENCH-OPS, GUARDIAN, or EXECUTOR."
        actions={
          <>
            <Link className="btn" to="/agent-manager">
              Agent Manager
            </Link>
            <Link className="btn" to="/agents">
              Agent Teams
            </Link>
            <Btn
              variant={draft.liveOnly ? "primary" : "ghost"}
              onClick={() => update({ liveOnly: !draft.liveOnly })}
            >
              {draft.liveOnly ? "Show all tiers" : "Live path only"}
            </Btn>
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

      <Card>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Port</th>
                <th>Model</th>
                <th>Role</th>
                <th>Live path</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.tier}>
                  <td>{m.tier}</td>
                  <td>{m.port}</td>
                  <td>{m.model}</td>
                  <td style={{ fontFamily: "var(--font)" }}>{m.role}</td>
                  <td>
                    <Tag kind={m.live ? "healthy" : "neutral"}>
                      {m.live ? "YES" : "R&D only"}
                    </Tag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="BFT voters" style={{ marginTop: 14 }}>
        <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>GUARDIAN → Tier 1 :30000 (critical path)</li>
          <li>ARCHON → Tier 2 :30001</li>
          <li>CORTEX → DeepSeek :30005 when up; fallback Tier 2</li>
          <li>Trade votes AUGUR + PREDATOR + ATLAS — advisory; risk kernel DENY wins</li>
        </ul>
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
