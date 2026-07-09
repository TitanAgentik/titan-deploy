import { useState } from "react";
import { PageHeader, Card, Btn, Tag } from "@/components/ui";
import { portfolio } from "@/lib/data";

export function CommandCenter() {
  const [kill, setKill] = useState(portfolio.killActive);
  const [frozen, setFrozen] = useState(portfolio.evolutionFrozen);
  const [log, setLog] = useState<string[]>([]);

  const push = (msg: string) => setLog((l) => [`${new Date().toISOString()}  ${msg}`, ...l].slice(0, 12));

  return (
    <>
      <PageHeader
        title="Command Center"
        subtitle="Operator kill switch, flatten, evolution freeze, and capital ledger actions. Mutating calls require HMAC in production."
      />

      <div className="grid grid-3" style={{ marginBottom: 14 }}>
        <Card title="Kill switch">
          <p className="muted small" style={{ marginTop: 0 }}>
            Global halt. Deactivate requires signed RESUME token.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <Btn
              variant="danger"
              onClick={() => {
                setKill(true);
                push("KILL activated — scope=global");
              }}
            >
              Activate kill
            </Btn>
            <Btn
              disabled={!kill}
              onClick={() => {
                setKill(false);
                push("RESUME signed — kill deactivated (demo)");
              }}
            >
              Signed resume
            </Btn>
          </div>
          <div style={{ marginTop: 12 }}>
            <Tag kind={kill ? "bleeding" : "healthy"}>{kill ? "ACTIVE" : "CLEAR"}</Tag>
          </div>
        </Card>

        <Card title="Flatten / wind-down">
          <p className="muted small" style={{ marginTop: 0 }}>
            Enqueues closes via FlattenExecutor + sets SIGNING_HALTED.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <Btn
              variant="danger"
              onClick={() => push("POST /v1/flatten — revoke_keys=true (demo)")}
            >
              Flatten all
            </Btn>
            <Btn onClick={() => push("Wind-down derisk started (demo)")}>Start derisk</Btn>
          </div>
        </Card>

        <Card title="Evolution freeze">
          <p className="muted small" style={{ marginTop: 0 }}>
            Blocks live promotions while capital is at risk.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <Btn
              onClick={() => {
                setFrozen(true);
                push("evolution freeze ON");
              }}
            >
              Freeze
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                setFrozen(false);
                push("evolution unfrozen");
              }}
            >
              Unfreeze
            </Btn>
          </div>
          <div style={{ marginTop: 12 }}>
            <Tag kind={frozen ? "watch" : "healthy"}>{frozen ? "FROZEN" : "OPEN"}</Tag>
          </div>
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="Capital ledger (≠ profit)">
          <div className="form-row">
            <div className="field">
              <label>Amount USD</label>
              <input defaultValue="2500" />
            </div>
            <div className="field">
              <label>Asset</label>
              <select defaultValue="USDC">
                <option>USDC</option>
                <option>USDT</option>
                <option>ETH</option>
              </select>
            </div>
            <Btn
              variant="primary"
              onClick={() => push("capital deposit credited equity/available (demo)")}
            >
              Deposit
            </Btn>
            <Btn
              onClick={() =>
                push("withdraw requires --confirm-yes + signing_node receipt (demo)")
              }
            >
              Withdraw
            </Btn>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>
            Deposits credit equity_usd / available_usd. Trading PnL is TCA / weekly_profit — do not
            confuse with deposits.
          </p>
        </Card>

        <Card title="Operator heartbeat (DMS)">
          <p className="muted small" style={{ marginTop: 0 }}>
            Hours since last heartbeat:{" "}
            <span className="mono">{portfolio.dmsHoursSinceHeartbeat}</span> · derisk @ 48h · flatten
            @ 72h
          </p>
          <Btn
            variant="primary"
            onClick={() => push("HEARTBEAT signed — DMS timer reset (demo)")}
          >
            Send heartbeat
          </Btn>
        </Card>
      </div>

      <Card title="Command audit" className="panel-stack" style={{ marginTop: 14 }}>
        {log.length === 0 ? (
          <div className="empty">No commands yet this session.</div>
        ) : (
          <div className="timeline">
            {log.map((line) => (
              <div className="timeline-item" key={line}>
                <div className="rail" />
                <div>
                  <div className="when mono">{line.slice(0, 20)}</div>
                  <div className="what mono">{line.slice(21)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
