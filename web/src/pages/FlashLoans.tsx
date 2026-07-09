import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { flashLoanRouter } from "@/lib/data";

const FLASH_LOANS_DEFAULTS = { showPaperOnly: false };

export function FlashLoans() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("flashLoans", FLASH_LOANS_DEFAULTS);
  const fl = flashLoanRouter;
  const composes = fl.recentComposes;

  return (
    <>
      <PageHeader
        title="Flash Loan Router"
        subtitle="§FL multi-source routing — ALCHEMY composes, TRENCH-OPS executes. Live requires promotion YES + typed_data signing."
        actions={
          <>
            <Btn
              variant={draft.showPaperOnly ? "primary" : "ghost"}
              onClick={() => update({ showPaperOnly: !draft.showPaperOnly })}
            >
              {draft.showPaperOnly ? "All composes" : "Paper only"}
            </Btn>
            <Btn onClick={() => push("Paper sim queued (demo)", "ok")}>Run paper sim</Btn>
            <Btn
              variant="primary"
              disabled={!fl.promotionApproved}
              onClick={() => push("Enable live — set flashLoanRouter.enabled in openclaw.json", "warn")}
            >
              Request live YES
            </Btn>
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

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Status" value={fl.enabled ? "LIVE" : "CATALOG"} />
        <Metric label="Promotion" value={fl.promotionApproved ? "YES" : "PENDING"} />
        <Metric label="Paper sim pass" value={`${(fl.paperSimPassRate * 100).toFixed(0)}%`} delta={`n=${fl.paperSimCount}`} />
        <Metric label="Max borrow" value={`$${(fl.maxAmountUsd / 1000).toFixed(0)}k`} />
      </div>

      <div className="grid grid-2">
        <Card title="Source priority (lowest fee first)">
          {Object.entries(fl.sourcePriority).map(([chain, sources]) => (
            <div key={chain} style={{ marginBottom: 12 }}>
              <div className="mono small" style={{ marginBottom: 4, textTransform: "capitalize" }}>
                {chain}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {sources.map((s, i) => (
                  <Tag key={s} kind={i === 0 ? "healthy" : "info"}>
                    {i + 1}. {s}
                  </Tag>
                ))}
              </div>
            </div>
          ))}
        </Card>

        <Card title="Agents & gates">
          <DetailList
            rows={[
              { k: "Compose", v: fl.composeAgent },
              { k: "Execute", v: fl.executeAgent },
              { k: "Skill", v: fl.skill },
              { k: "CLI", v: "titan-safety flashloan" },
              { k: "Kernel", v: "DENY if flash_loan_live not approved" },
              { k: "Signing", v: "typed_data required — no blind-sign" },
            ]}
          />
        </Card>
      </div>

      <Card title="Flash-enabled pipelines" style={{ marginTop: 14 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {fl.pipelines.map((p) => (
            <Tag key={p} kind="info">
              {p}
            </Tag>
          ))}
        </div>
      </Card>

      <Card title={draft.showPaperOnly ? "Recent paper composes" : "Recent composes (all)"} style={{ marginTop: 14 }}>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Time</th>
                <th>Chain</th>
                <th>Source</th>
                <th>Strategy</th>
                <th>Amount</th>
                <th>Est. profit</th>
              </tr>
            </thead>
            <tbody>
              {composes.map((c) => (
                <tr key={c.ts}>
                  <td className="mono small">{c.ts.replace("T", " ").slice(0, 19)}</td>
                  <td>{c.chain}</td>
                  <td>{c.source}</td>
                  <td>{c.strategy}</td>
                  <td>${c.amountUsd.toLocaleString()}</td>
                  <td>
                    <Tag kind="healthy">+${c.profitUsd.toFixed(2)}</Tag>
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

function DetailList({ rows }: { rows: { k: string; v: string }[] }) {
  return (
    <dl className="muted small" style={{ margin: 0, display: "grid", gap: 8 }}>
      {rows.map((r) => (
        <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <dt>{r.k}</dt>
          <dd className="mono" style={{ margin: 0, textAlign: "right" }}>
            {r.v}
          </dd>
        </div>
      ))}
    </dl>
  );
}
