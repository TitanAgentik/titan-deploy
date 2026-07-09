import { useState } from "react";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { Drawer, ToastStack, useToasts } from "@/components/interactive";
import { memecoinTrench } from "@/lib/data";

type Candidate = (typeof memecoinTrench.recentCandidates)[number];

export function MemecoinTrench() {
  const { toasts, push, dismiss } = useToasts();
  const mc = memecoinTrench;
  const [selected, setSelected] = useState<Candidate | null>(null);
  const solPct = Math.min(100, (mc.dailySolUsed / mc.dailySolCap) * 100);

  return (
    <>
      <PageHeader
        title="Memecoin Trench"
        subtitle="P22 Solana Pump.fun lifecycle — PREDATOR six-gate filter, TRENCH-OPS Jito bundles via EDGE-FRA. Paper active; live requires Phase 5 YES."
        actions={
          <>
            <Btn onClick={() => push("Memecoin sim queued — titan-safety memecoin sim", "ok")}>
              Run paper sim
            </Btn>
            <Btn
              variant="primary"
              disabled={mc.promotionApproved}
              onClick={() => push("Open Promotions → P22 Memecoin Trench YES", "warn")}
            >
              Request live YES
            </Btn>
          </>
        }
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Mode" value={mc.enabled ? "LIVE" : mc.mode.toUpperCase()} />
        <Metric label="Promotion" value={mc.promotionApproved ? "YES" : "PENDING"} />
        <Metric label="Filter pass (24h)" value={String(mc.filtersPassed24h)} delta={`${mc.filtersRejected24h} rejected`} />
        <Metric label="Paper sim" value={`${(mc.paperSimPassRate * 100).toFixed(0)}%`} delta={`n=${mc.paperSimCount}`} />
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Daily SOL" value={`${mc.dailySolUsed}/${mc.dailySolCap}`} delta={`${solPct.toFixed(0)}% cap`} />
        <Metric label="Max snipe" value={`${mc.maxSnipePctEquity}%`} delta="equity" />
        <Metric label="Edge PoP" value={mc.edgePop} />
        <Metric label="Hot path" value={`≤${mc.hotPathMs}ms`} delta="fast_validate" />
      </div>

      <div className="grid grid-2">
        <Card title="Six-gate filter (all must PASS)">
          <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.9 }}>
            {mc.sixGates.map((g) => (
              <li key={g.id}>
                <span className="mono">{g.id}</span> — {g.name}
              </li>
            ))}
          </ol>
          <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
            CLI: <span className="mono">titan-safety memecoin filter --mint-json '&#123;…&#125;'</span>
          </p>
        </Card>

        <Card title="Agents & infra">
          <DetailList
            rows={[
              { k: "Scan / filter", v: mc.scanAgent },
              { k: "Execute", v: mc.executeAgent },
              { k: "Feeds", v: mc.feedsAgent },
              { k: "Sizing", v: mc.sizeAgent },
              { k: "Jito", v: "EDGE-FRA block engine" },
              { k: "Geyser", v: mc.geyserConfigured ? "connected" : "configure GEYSER_GRPC_URL" },
              { k: "Drawdown tiers", v: mc.drawdownExempt ? "EXEMPT (lane CBs)" : "standard" },
              { k: "Venues", v: "solana_pumpfun, jito, paper" },
            ]}
          />
        </Card>
      </div>

      <Card title="Lifecycle strategies" style={{ marginTop: 14 }}>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Phase</th>
                <th>When</th>
                <th>Max size</th>
              </tr>
            </thead>
            <tbody>
              {mc.strategies.map((s) => (
                <tr key={s.id}>
                  <td className="mono">{s.id}</td>
                  <td>{s.phase}</td>
                  <td>{s.when}</td>
                  <td>{s.maxPctEquity}% equity</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <Card title="Recent filter results · click row">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Mint</th>
                  <th>Result</th>
                  <th>Strategy</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {mc.recentCandidates.map((c) => (
                  <tr
                    key={c.ts + c.mint}
                    className="row-click"
                    onClick={() => setSelected(c)}
                  >
                    <td className="mono small">{c.ts.replace("T", " ").slice(11, 19)}</td>
                    <td className="mono">{c.mint}</td>
                    <td>
                      <Tag kind={c.passed ? "healthy" : "bleeding"}>{c.passed ? "PASS" : "REJECT"}</Tag>
                    </td>
                    <td>{c.strategy}</td>
                    <td>{c.notionalUsd > 0 ? `$${c.notionalUsd}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Paper trades (shadow lane)">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Mint</th>
                  <th>Strategy</th>
                  <th>Notional</th>
                  <th>PnL</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {mc.paperTrades.map((t) => (
                  <tr key={t.ts + t.mint}>
                    <td className="mono small">{t.ts.replace("T", " ").slice(11, 19)}</td>
                    <td className="mono">{t.mint}</td>
                    <td>{t.strategy}</td>
                    <td>${t.notionalUsd}</td>
                    <td>
                      {t.pnlUsd == null ? (
                        "—"
                      ) : (
                        <Tag kind={t.pnlUsd >= 0 ? "healthy" : "bleeding"}>
                          {t.pnlUsd >= 0 ? "+" : ""}${t.pnlUsd.toFixed(1)}
                        </Tag>
                      )}
                    </td>
                    <td>
                      <Tag kind={t.status === "open" ? "watch" : t.status === "stopped" ? "bleeding" : "info"}>
                        {t.status}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card title="Lane circuit breakers" style={{ marginTop: 14 }}>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>ID</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {mc.circuitBreakers.map((cb) => (
                <tr key={cb.id}>
                  <td className="mono small">{cb.id}</td>
                  <td>{cb.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
          Exits: {mc.exits.stopLossPct}% SL · {mc.exits.trailingStopPct}% trail · ladder{" "}
          {mc.exits.takeProfitLadder.join("/")} · {mc.exits.timeExitMinutes}m time exit
        </p>
      </Card>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.mint ?? ""}
        subtitle={selected ? `${selected.strategy} · conf ${selected.confidence.toFixed(2)}` : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSelected(null)}>
              Close
            </Btn>
            {selected?.passed ? (
              <Btn variant="primary" onClick={() => push(`Paper buy queued · ${selected.mint}`, "ok")}>
                Paper buy
              </Btn>
            ) : (
              <Btn disabled>Rejected</Btn>
            )}
          </>
        }
      >
        {selected ? (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Gate</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(selected.gates).map(([gate, result]) => (
                  <tr key={gate}>
                    <td className="mono small">{gate}</td>
                    <td>
                      <Tag kind={result === "PASS" ? "healthy" : result === "FAIL" ? "bleeding" : "info"}>
                        {result}
                      </Tag>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {"rejectReason" in selected && selected.rejectReason ? (
              <p className="muted small" style={{ marginTop: 12 }}>
                Reject: {selected.rejectReason}
              </p>
            ) : null}
          </div>
        ) : null}
      </Drawer>

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
