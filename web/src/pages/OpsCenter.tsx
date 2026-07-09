import { Link } from "react-router-dom";
import { PageHeader, Card, Tag, Metric, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import { lanes, portfolio } from "@/lib/data";

type Focus = "recon" | "tca" | "allocator";

const OPS_DEFAULTS = { focus: "recon" as Focus };

const FOCUS_TABS: { id: Focus; label: string }[] = [
  { id: "recon", label: "Reconciliation" },
  { id: "tca", label: "TCA lanes" },
  { id: "allocator", label: "Allocator" },
];

export function OpsCenter() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("ops", OPS_DEFAULTS);

  return (
    <>
      <PageHeader
        title="Ops Center"
        subtitle="Live execution ops: reconciliation, TCA lanes, allocator concentration, and signing gate."
        actions={
          <>
            <Link className="btn" to="/tca">
              TCA & Allocator
            </Link>
            <Link className="btn" to="/signing">
              Signing
            </Link>
            <Link className="btn" to="/health">
              Health
            </Link>
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
        {FOCUS_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn${draft.focus === t.id ? " primary" : ""}`}
            onClick={() => update({ focus: t.id })}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Capital profile" value={portfolio.capitalProfile.toUpperCase()} />
        <Metric label="Regime" value={portfolio.regime} />
        <Metric label="Max active pipelines" value="4" delta="allocator cap" />
        <Metric label="Gate receipt TTL" value="30s" delta="in-process" />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 14 }}>
        <Card
          title="Reconciliation"
          style={draft.focus === "recon" ? { outline: "2px solid var(--accent)" } : undefined}
        >
          <p className="muted small" style={{ marginTop: 0 }}>
            Believed vs DEX / on-chain. Mock adapter banned when capital_profile=live. Strict DEX-only (R02 / R46).
          </p>
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Venue</th>
                  <th>Believed</th>
                  <th>Actual</th>
                  <th>Δ USD</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>uniswap / curve</td>
                  <td>$6,200</td>
                  <td>$6,198</td>
                  <td>
                    <Tag kind="healthy">−2.00</Tag>
                  </td>
                </tr>
                <tr>
                  <td>hyperliquid DEX</td>
                  <td>$3,890</td>
                  <td>$3,890</td>
                  <td>
                    <Tag kind="healthy">0.00</Tag>
                  </td>
                </tr>
                <tr>
                  <td>solana / jito</td>
                  <td>$420</td>
                  <td>$418</td>
                  <td>
                    <Tag kind="watch">−2.00</Tag>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="In-process signing pre-sign gates">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
            <li>Mock-adapter ban (live)</li>
            <li>Reconciliation :19002</li>
            <li>Risk kernel :19001</li>
            <li>Issue X-Titan-Gate-Receipt</li>
            <li>titan-safety SigningNode (same process · receipt ≤30s)</li>
          </ol>
          <p className="mono small" style={{ marginTop: 14 }}>
            mode · in-process · no :19010 hop required
          </p>
        </Card>
      </div>

      <Card
        title="TCA → allocator profit loop"
        style={draft.focus === "tca" || draft.focus === "allocator" ? { outline: "2px solid var(--accent)" } : undefined}
      >
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Lane</th>
                <th>Net bps</th>
                <th>Sample</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {lanes.map((l) => (
                <tr key={l.id}>
                  <td>
                    {l.id} · {l.name}
                  </td>
                  <td>{l.netBps.toFixed(1)}</td>
                  <td>{l.trades}</td>
                  <td>
                    {l.health === "BLEEDING" ? (
                      <Tag kind="bleeding">AUTO DEFUND</Tag>
                    ) : l.health === "WATCH" ? (
                      <Tag kind="watch">HOLD SIZE</Tag>
                    ) : (
                      <Tag kind="healthy">FUND</Tag>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {draft.focus === "allocator" ? (
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            Concentration cap: ≤4 funded HEALTHY lanes via allocator — soft-highlight active.
          </p>
        ) : null}
      </Card>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
