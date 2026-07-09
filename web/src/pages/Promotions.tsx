import { useState } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import {
  ActionMenu,
  DetailGrid,
  Drawer,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import { promotions } from "@/lib/data";

type Promo = (typeof promotions)[number];

export function Promotions() {
  const { toasts, push, dismiss } = useToasts();
  const [selected, setSelected] = useState<Promo | null>(promotions[0] ?? null);
  const [drawer, setDrawer] = useState<Promo | null>(null);

  const decide = (p: Promo, action: "YES" | "HOLD" | "NO") => {
    push(`${action} · ${p.id} · ${p.strategy}`, action === "NO" ? "danger" : action === "HOLD" ? "warn" : "ok");
    setDrawer(null);
  };

  return (
    <>
      <PageHeader
        title="Promotions"
        subtitle="Select a strategy, then YES / HOLD / NO — or open the detail drawer for scorecard options."
        actions={
          <>
            <ActionMenu
              label="Bulk"
              items={[
                { label: "HOLD all pending", onClick: () => push("HOLD all PENDING", "warn") },
                { label: "Export queue CSV", onClick: () => push("Export promotions CSV") },
              ]}
            />
            <Btn
              variant="primary"
              disabled={!selected}
              onClick={() => selected && decide(selected, "YES")}
            >
              YES
            </Btn>
            <Btn disabled={!selected} onClick={() => selected && decide(selected, "HOLD")}>
              HOLD
            </Btn>
            <Btn
              variant="danger"
              disabled={!selected}
              onClick={() => selected && decide(selected, "NO")}
            >
              NO · archive
            </Btn>
          </>
        }
      />
      <Card title="Queue · click to select · ⋯ for details">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th />
                <th>ID</th>
                <th>Strategy</th>
                <th>Phase</th>
                <th>Status</th>
                <th>Score</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {promotions.map((p) => (
                <tr
                  key={p.id}
                  className="row-click"
                  onClick={() => setSelected(p)}
                  style={
                    selected?.id === p.id
                      ? { outline: "1px solid rgba(45,212,168,0.45)" }
                      : undefined
                  }
                >
                  <td>
                    <input
                      type="radio"
                      checked={selected?.id === p.id}
                      onChange={() => setSelected(p)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  <td>{p.id}</td>
                  <td>{p.strategy}</td>
                  <td>{p.phase}/6</td>
                  <td>
                    <Tag kind={p.status.includes("PENDING") ? "watch" : "info"}>{p.status}</Tag>
                  </td>
                  <td>{p.score.toFixed(2)}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <ActionMenu
                      label="⋯"
                      variant="ghost"
                      items={[
                        { label: "Open detail", onClick: () => setDrawer(p) },
                        { label: "YES", onClick: () => decide(p, "YES") },
                        { label: "HOLD", onClick: () => decide(p, "HOLD") },
                        { label: "NO · archive", danger: true, onClick: () => decide(p, "NO") },
                        { label: "Extend paper", onClick: () => push(`EXTEND · ${p.id}`) },
                      ]}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="Gates" style={{ marginTop: 14 }}>
        <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
          <li>3-day paper minimum + backtest before live</li>
          <li>Red Team gauntlet before promotion</li>
          <li>TIMEOUT = HOLD/de-risk — never auto-promote</li>
          <li>Evolution freeze blocks live promotions while capital at risk</li>
          <li>Flash-loan live requires separate <span className="mono">flash_loan_live</span> YES</li>
          <li>P22 memecoin live requires <span className="mono">memecoin_trench</span> Phase 5 YES + Geyser configured</li>
        </ul>
      </Card>

      <Drawer
        open={!!drawer}
        onClose={() => setDrawer(null)}
        title={drawer?.strategy ?? ""}
        subtitle={drawer ? `${drawer.id} · phase ${drawer.phase}/6` : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setDrawer(null)}>
              Close
            </Btn>
            <Btn variant="danger" onClick={() => drawer && decide(drawer, "NO")}>
              NO
            </Btn>
            <Btn onClick={() => drawer && decide(drawer, "HOLD")}>HOLD</Btn>
            <Btn variant="primary" onClick={() => drawer && decide(drawer, "YES")}>
              YES
            </Btn>
          </>
        }
      >
        {drawer ? (
          <>
            <DetailGrid
              rows={[
                { label: "Status", value: drawer.status },
                { label: "Score", value: drawer.score.toFixed(2) },
                { label: "Timeout", value: "hold_derisk" },
              ]}
            />
            <div className="option-grid" style={{ marginTop: 14 }}>
              <button type="button" className="option-tile" onClick={() => push("Scorecard PDF")}>
                <strong>Scorecard</strong>
                <span>cross-phase Sharpe</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push("Red Team log")}>
                <strong>Red Team</strong>
                <span>gauntlet log</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push("EXTEND paper")}>
                <strong>EXTEND</strong>
                <span>back to paper</span>
              </button>
              <button type="button" className="option-tile" onClick={() => push("Watch mode 24h")}>
                <strong>Watch mode</strong>
                <span>24h arm on YES</span>
              </button>
            </div>
          </>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
