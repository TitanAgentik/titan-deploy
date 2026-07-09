import { Link } from "react-router-dom";
import { PageHeader, Card, Metric, Tag, Btn } from "@/components/ui";
import { SaveBar } from "@/components/SaveBar";
import { ToastStack, useToasts } from "@/components/interactive";
import { useCockpitDraft } from "@/lib/useCockpitDraft";
import {
  circuitBreakerCatalog,
  circuitBreakers,
  drawdownPolicy,
  latencyBudget,
  portfolio,
} from "@/lib/data";

type RiskTab = "drawdown" | "catalog";
type FamilyFilter = "all" | "security" | "stealth" | "memecoin" | "endgame" | "power" | "memory";

const RISK_DEFAULTS = {
  showVelocity: true,
  tab: "drawdown" as RiskTab,
  family: "all" as FamilyFilter,
};

export function Risk() {
  const { toasts, push, dismiss } = useToasts();
  const { draft, update, dirty, lastSavedAt, save, discard, resetDefaults } =
    useCockpitDraft("risk", RISK_DEFAULTS);

  const catalog =
    draft.family === "all"
      ? circuitBreakerCatalog
      : circuitBreakerCatalog.filter((c) => c.family === draft.family);
  const armed = circuitBreakerCatalog.filter((c) => c.armed).length;

  return (
    <>
      <PageHeader
        title="Risk & Circuit Breakers"
        subtitle="GUARDIAN + out-of-process risk kernel (:19001) and portfolio risk (:19004). Drawdown tiers notify-only — trading continues; velocity breakers still halt."
        actions={
          <>
            <Link className="btn" to="/dms">
              Dead Man&apos;s Switch
            </Link>
            <Btn
              variant={draft.showVelocity ? "primary" : "ghost"}
              onClick={() => update({ showVelocity: !draft.showVelocity })}
            >
              {draft.showVelocity ? "Hide" : "Show"} velocity gates
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

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {(
          [
            ["drawdown", "Drawdown & gates"],
            ["catalog", "CB catalog"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn${draft.tab === id ? " primary" : ""}`}
            onClick={() => update({ tab: id })}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="Drawdown" value={`${portfolio.drawdownPct}%`} delta="notify-only" />
        <Metric label="Regime" value={portfolio.regime} />
        <Metric label="Kill switch" value={portfolio.killActive ? "ACTIVE" : "CLEAR"} />
        <Metric
          label="DMS heartbeat"
          value={`${portfolio.dmsHoursSinceHeartbeat}h`}
          delta="derisk 48h / flatten 72h"
        />
      </div>

      {draft.tab === "drawdown" ? (
        <>
          <div className="grid grid-2">
            <Card title="5-tier drawdown — HERALD notify only">
              <p className="muted small" style={{ marginTop: 0 }}>
                {drawdownPolicy.note}
              </p>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Tier</th>
                      <th>Action</th>
                      <th>State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {circuitBreakers.map((cb) => (
                      <tr key={cb.pct}>
                        <td>{cb.pct}%</td>
                        <td style={{ fontFamily: "var(--font)" }}>{cb.action}</td>
                        <td>
                          <Tag kind={portfolio.drawdownPct >= cb.pct ? "watch" : "healthy"}>
                            {portfolio.drawdownPct >= cb.pct ? "NOTIFIED" : cb.state}
                          </Tag>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
                Volatile exempt: {drawdownPolicy.volatileExemptPipelines.join(", ")} — lane-local
                CBs only
              </p>
            </Card>
            <Card title="Pre-trade gates">
              <ol className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
                <li>Autonomous BFT 2-of-3 above 1% equity (AUGUR/PREDATOR/ATLAS)</li>
                <li>Confidence ≥0.70 full · 0.50–0.69 reduced · &lt;0.30 reject</li>
                <li>
                  Hot path: <span className="mono">POST /v1/fast_validate</span> ≤
                  {latencyBudget.hotPathGateP95Ms}ms p95
                </li>
                <li>Flash-loan live → promotion YES + typed_data signing</li>
                <li>ExecutionGate: recon → kernel → gate receipt → signing_node</li>
                {draft.showVelocity ? (
                  <li>
                    Velocity: ${drawdownPolicy.velocityHalt60s}/60s · $
                    {drawdownPolicy.velocityHalt15m}/15m → HALT
                  </li>
                ) : null}
              </ol>
            </Card>
          </div>

          {draft.showVelocity ? (
            <Card title="Drawdown velocity breakers" style={{ marginTop: 14 }}>
              <p className="muted small" style={{ marginTop: 0 }}>
                Velocity breaches bypass notify-only drawdown tiers — kernel HALT is authoritative.
              </p>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Window</th>
                      <th>Threshold</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>60s</td>
                      <td>${drawdownPolicy.velocityHalt60s.toLocaleString()}</td>
                      <td>
                        <Tag kind="bleeding">HALT</Tag>
                      </td>
                    </tr>
                    <tr>
                      <td>15m</td>
                      <td>${drawdownPolicy.velocityHalt15m.toLocaleString()}</td>
                      <td>
                        <Tag kind="bleeding">HALT</Tag>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Card>
          ) : null}
        </>
      ) : (
        <>
          <div className="grid grid-4" style={{ marginBottom: 14 }}>
            <Metric label="Catalog size" value={String(circuitBreakerCatalog.length)} />
            <Metric label="Armed" value={String(armed)} delta="policy.yaml" />
            <Metric
              label="Endgame (dormant)"
              value={String(circuitBreakerCatalog.filter((c) => c.family === "endgame").length)}
              delta="phase unlock"
            />
            <Metric label="Shown" value={String(catalog.length)} />
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
            {(
              [
                ["all", "All"],
                ["security", "Security"],
                ["stealth", "Stealth"],
                ["memecoin", "Memecoin"],
                ["power", "Power"],
                ["memory", "Memory"],
                ["endgame", "Endgame"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={`btn${draft.family === id ? " primary" : ""}`}
                onClick={() => update({ family: id })}
              >
                {label}
              </button>
            ))}
          </div>
          <Card title="Circuit breaker catalog · policy.yaml">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Family</th>
                    <th>Action</th>
                    <th>Armed</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.map((cb) => (
                    <tr key={cb.id}>
                      <td className="mono">{cb.id}</td>
                      <td>
                        <Tag kind="info">{cb.family}</Tag>
                      </td>
                      <td className="mono small">{cb.action}</td>
                      <td>
                        <Tag kind={cb.armed ? "healthy" : "neutral"}>
                          {cb.armed ? "ARMED" : "DORMANT"}
                        </Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginBottom: 0, marginTop: 12 }}>
              Endgame CBs unlock with capital.endgame_phase_unlock — documented, not all wired.
              Ghost / stealth CBs enforce no public RPC on live path.
            </p>
          </Card>
        </>
      )}

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
