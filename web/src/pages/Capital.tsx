import { useMemo, useState } from "react";
import { PageHeader, Card, Tag, Btn } from "@/components/ui";
import {
  ActionMenu,
  ClickableMetric,
  DetailGrid,
  Drawer,
  Modal,
  ToastStack,
  useToasts,
} from "@/components/interactive";
import {
  capitalLedger,
  capitalTxns,
  portfolio,
  wallets,
} from "@/lib/data";

type Tab = "overview" | "deposit" | "withdraw" | "wallets" | "sweep";
type Wallet = (typeof wallets)[number];
type Txn = (typeof capitalTxns)[number];

const PRESETS = ["500", "1000", "2500", "5000"];

export function Capital() {
  const { toasts, push: toast, dismiss } = useToasts();
  const [tab, setTab] = useState<Tab>("overview");
  const [amount, setAmount] = useState("2500");
  const [asset, setAsset] = useState("USDC");
  const [confirmYes, setConfirmYes] = useState(false);
  const [address, setAddress] = useState("trezor:safe-7");
  const [note, setNote] = useState("Biweekly injection");
  const [log, setLog] = useState<string[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [txn, setTxn] = useState<Txn | null>(null);
  const [depositConfirm, setDepositConfirm] = useState(false);
  const [withdrawConfirm, setWithdrawConfirm] = useState(false);
  const [sweepModal, setSweepModal] = useState(false);
  const [ceremony, setCeremony] = useState(false);
  const [adapter, setAdapter] = useState(capitalLedger.withdrawalAdapter);

  const toUnlock = Math.max(0, capitalLedger.sweepThresholdUsd - portfolio.equityUsd);
  const progress = Math.min(
    100,
    Math.round((portfolio.equityUsd / capitalLedger.sweepThresholdUsd) * 100),
  );
  const nextSweepEstimate = useMemo(() => {
    if (capitalLedger.growthPhase) return 0;
    return (capitalLedger.weeklyProfitUsd * capitalLedger.sweepPct) / 100;
  }, []);

  const push = (msg: string) => {
    setLog((l) => [`${new Date().toISOString()}  ${msg}`, ...l].slice(0, 16));
    toast(msg);
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "deposit", label: "Deposit" },
    { id: "withdraw", label: "Withdraw" },
    { id: "wallets", label: "Wallets" },
    { id: "sweep", label: "Trezor Safe 7 · Sweeps" },
  ];

  return (
    <>
      <PageHeader
        title="Capital & Wallets"
        subtitle="Click metrics, rows, and action menus for deposit / withdraw / wallet / Safe 7 options. Deposits ≠ trading profit."
        actions={
          <ActionMenu
            label="Quick actions"
            variant="primary"
            items={[
              { label: "New deposit", onClick: () => setTab("deposit") },
              { label: "New withdraw", onClick: () => setTab("withdraw") },
              { label: "Open Safe 7 sweep", onClick: () => setTab("sweep") },
              { label: "Copy CLI deposit", hint: "clipboard", onClick: () => push("Copied: titan-safety capital deposit --amount 2500 --asset USDC") },
            ]}
          />
        }
      />

      <div className="alert-banner">
        Deposits credit equity_usd / available_usd. Trading PnL is TCA / weekly_profit — never treat a
        deposit as profit attribution.
      </div>

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <ClickableMetric
          label="Equity"
          value={`$${portfolio.equityUsd.toLocaleString()}`}
          onClick={() => toast("Equity includes deposits + trading PnL mark")}
        />
        <ClickableMetric
          label="Available"
          value={`$${portfolio.availableUsd.toLocaleString()}`}
          onClick={() => setTab("withdraw")}
        />
        <ClickableMetric
          label="Deposited (ledger)"
          value={`$${capitalLedger.depositedUsd.toLocaleString()}`}
          delta="≠ PnL"
          onClick={() => setTab("deposit")}
        />
        <ClickableMetric
          label="Sweep unlock"
          value={`$${toUnlock.toLocaleString()}`}
          delta={`${progress}% of $35K`}
          onClick={() => setTab("sweep")}
        />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn${tab === t.id ? " primary" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid grid-2">
          <Card
            title="Ledger policy"
            action={
              <ActionMenu
                label="Docs"
                variant="ghost"
                items={[
                  { label: "Open COCKPIT_detail", onClick: () => toast("refs/COCKPIT_detail.md") },
                  { label: "Show Telegram /deposit", onClick: () => toast("/deposit 2500 USDC") },
                ]}
              />
            }
          >
            <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
              <li>Starting capital + biweekly injections tracked as <strong>deposits</strong></li>
              <li>Withdrawals require <span className="kbd">--confirm-yes</span></li>
              <li>
                Live withdrawals via signing_node (
                <button type="button" className="kbd" onClick={() => setTab("withdraw")}>
                  change adapter
                </button>
                )
              </li>
              <li>Max single withdrawal: {capitalLedger.maxSingleWithdrawalPct}% of equity</li>
            </ul>
          </Card>
          <Card title="Recent ledger · click row">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {capitalTxns.map((tx) => (
                    <tr
                      key={tx.ts + tx.type + tx.amount}
                      className="row-click"
                      onClick={() => setTxn(tx)}
                    >
                      <td>{tx.ts.slice(0, 10)}</td>
                      <td>
                        <Tag
                          kind={
                            tx.type === "deposit" ? "healthy" : tx.type === "sweep" ? "info" : "watch"
                          }
                        >
                          {tx.type}
                        </Tag>
                      </td>
                      <td>
                        ${tx.amount.toLocaleString()} {tx.asset}
                      </td>
                      <td>
                        <Tag kind={tx.status === "cleared" ? "healthy" : "neutral"}>{tx.status}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {tab === "deposit" && (
        <Card title="Deposit (ledger credit)">
          <p className="muted small" style={{ marginTop: 0 }}>
            Choose a preset or enter a custom amount, then confirm.
          </p>
          <div className="option-grid" style={{ marginBottom: 14 }}>
            {PRESETS.map((p) => (
              <button
                key={p}
                type="button"
                className={`option-tile${amount === p ? " active" : ""}`}
                onClick={() => setAmount(p)}
              >
                <strong>${p}</strong>
                <span>USD preset</span>
              </button>
            ))}
          </div>
          <div className="form-row">
            <div className="field">
              <label>Amount USD</label>
              <input value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div className="field">
              <label>Asset</label>
              <select value={asset} onChange={(e) => setAsset(e.target.value)}>
                <option>USDC</option>
                <option>USDT</option>
                <option>ETH</option>
              </select>
            </div>
            <div className="field" style={{ minWidth: 200 }}>
              <label>Note</label>
              <input value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            <div className="field">
              <label>Operator</label>
              <input defaultValue="Hyperion" />
            </div>
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn variant="primary" onClick={() => setDepositConfirm(true)}>
              Review &amp; credit deposit
            </Btn>
            <ActionMenu
              label="More"
              items={[
                { label: "Schedule biweekly", onClick: () => push("Biweekly injection scheduled") },
                { label: "Mark on-chain funded", onClick: () => push("On-chain funding noted (hot ops)") },
                { label: "Copy CLI", onClick: () => push(`titan-safety capital deposit --amount ${amount} --asset ${asset}`) },
              ]}
            />
          </div>
        </Card>
      )}

      {tab === "withdraw" && (
        <Card title="Withdraw (confirm-yes required)">
          <p className="muted small" style={{ marginTop: 0 }}>
            Pick destination wallet, adapter, then confirm.
          </p>
          <div className="option-grid" style={{ marginBottom: 14 }}>
            {wallets
              .filter((w) => w.kind === "cold" || w.id === "hot-ops")
              .map((w) => (
                <button
                  key={w.id}
                  type="button"
                  className={`option-tile${address === w.address ? " active" : ""}`}
                  onClick={() => setAddress(w.address)}
                >
                  <strong>{w.label}</strong>
                  <span>{w.address}</span>
                </button>
              ))}
          </div>
          <div className="form-row">
            <div className="field">
              <label>Amount USD</label>
              <input value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div className="field">
              <label>Asset</label>
              <select value={asset} onChange={(e) => setAsset(e.target.value)}>
                <option>USDC</option>
                <option>USDT</option>
                <option>ETH</option>
              </select>
            </div>
            <div className="field">
              <label>Adapter</label>
              <select value={adapter} onChange={(e) => setAdapter(e.target.value as typeof adapter)}>
                <option value="mock">mock (paper)</option>
                <option value="trezor_signing">trezor_signing / signing_node</option>
              </select>
            </div>
            <div className="field" style={{ minWidth: 220 }}>
              <label>Destination</label>
              <input value={address} onChange={(e) => setAddress(e.target.value)} />
            </div>
          </div>
          <label
            className="muted small"
            style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}
          >
            <input
              type="checkbox"
              checked={confirmYes}
              onChange={(e) => setConfirmYes(e.target.checked)}
            />
            I confirm this withdrawal (<span className="mono">--confirm-yes</span>)
          </label>
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn
              variant="danger"
              disabled={!confirmYes || !Number(amount)}
              onClick={() => setWithdrawConfirm(true)}
            >
              Review &amp; submit
            </Btn>
            <Btn
              variant="ghost"
              onClick={() => push("Pending withdrawal REQUEST_ID=wd-demo-001")}
            >
              Create pending request
            </Btn>
            <ActionMenu
              label="Limits"
              items={[
                {
                  label: `Max ${capitalLedger.maxSingleWithdrawalPct}% equity`,
                  onClick: () =>
                    setAmount(
                      String(
                        Math.floor(
                          (portfolio.equityUsd * capitalLedger.maxSingleWithdrawalPct) / 100,
                        ),
                      ),
                    ),
                },
                { label: "Use 25% available", onClick: () => setAmount(String(Math.floor(portfolio.availableUsd * 0.25))) },
                { label: "Use 50% available", onClick: () => setAmount(String(Math.floor(portfolio.availableUsd * 0.5))) },
              ]}
            />
          </div>
        </Card>
      )}

      {tab === "wallets" && (
        <Card title="Wallet inventory · click row or ⋯">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Wallet</th>
                  <th>Kind</th>
                  <th>Address</th>
                  <th>Balance</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {wallets.map((w) => (
                  <tr key={w.id} className="row-click" onClick={() => setWallet(w)}>
                    <td>{w.label}</td>
                    <td>
                      <Tag kind={w.kind === "cold" ? "info" : "watch"}>{w.kind}</Tag>
                    </td>
                    <td>{w.address}</td>
                    <td>${w.balanceUsd.toLocaleString()}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <ActionMenu
                        label="⋯"
                        variant="ghost"
                        items={[
                          { label: "Open details", onClick: () => setWallet(w) },
                          { label: "Copy address", onClick: () => push(`Copied ${w.address}`) },
                          {
                            label: "Set as withdraw dest",
                            onClick: () => {
                              setAddress(w.address);
                              setTab("withdraw");
                              toast(`Destination → ${w.label}`);
                            },
                          },
                          {
                            label: "Start Trezor ceremony",
                            disabled: w.id !== "trezor-safe-7",
                            onClick: () => setCeremony(true),
                          },
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "sweep" && (
        <div className="grid grid-2">
          <Card
            title="Trezor Safe 7 · weekly profit sweep (R23)"
            action={
              <ActionMenu
                label="Policy"
                variant="ghost"
                items={[
                  { label: "Edit threshold ($35K)", onClick: () => toast("Threshold locked in policy.yaml") },
                  { label: "Change sweep day", onClick: () => toast("sweep_day_utc=Sunday") },
                  { label: "Change %", onClick: () => toast("sweep_pct_of_weekly_profit=20") },
                ]}
              />
            }
          >
            <div className="mono" style={{ fontSize: 22, marginBottom: 8 }}>
              Harvest @ ${capitalLedger.sweepThresholdUsd.toLocaleString()}
            </div>
            <div className="progress">
              <span style={{ width: `${progress}%` }} />
            </div>
            <p className="muted small" style={{ marginTop: 12 }}>
              {capitalLedger.growthPhase ? (
                <>
                  <Tag kind="watch">GROWTH PHASE</Tag> Equity below $35K →{" "}
                  <strong>100% reinvest</strong>, sweep paused.
                </>
              ) : (
                <>
                  <Tag kind="healthy">SWEEP ARMED</Tag> Every {capitalLedger.sweepDayUtc} ·{" "}
                  {capitalLedger.sweepPct}% of weekly profit.
                </>
              )}
            </p>
            <div className="option-grid" style={{ marginTop: 12 }}>
              <button type="button" className="option-tile" onClick={() => setSweepModal(true)}>
                <strong>Preview sweep</strong>
                <span>${nextSweepEstimate.toFixed(2)} est.</span>
              </button>
              <button type="button" className="option-tile" onClick={() => setCeremony(true)}>
                <strong>Trezor ceremony</strong>
                <span>Mac Mini + Safe 7</span>
              </button>
              <button
                type="button"
                className="option-tile"
                onClick={() => push("Force reinvest mode (demo)")}
              >
                <strong>Force reinvest</strong>
                <span>ignore unlock</span>
              </button>
              <button
                type="button"
                className="option-tile"
                onClick={() => push("Simulate equity ≥ $35K (demo)")}
              >
                <strong>Simulate unlock</strong>
                <span>preview armed state</span>
              </button>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
              <Btn
                variant="primary"
                disabled={capitalLedger.growthPhase}
                onClick={() => setSweepModal(true)}
              >
                Run sweep…
              </Btn>
            </div>
          </Card>
          <Card title="Safe 7 status">
            <DetailGrid
              rows={[
                { label: "Device", value: "Trezor Safe 7" },
                { label: "Cold balance", value: "$0.00 · awaiting first harvest" },
                { label: "Last ceremony", value: "— · not yet" },
                { label: "Path", value: "UPS signing_node · cold separate" },
              ]}
            />
            <div style={{ marginTop: 12 }}>
              <Btn onClick={() => setCeremony(true)}>Start ceremony wizard</Btn>
            </div>
          </Card>
        </div>
      )}

      {log.length > 0 && (
        <Card title="Session capital audit" style={{ marginTop: 14 }}>
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
        </Card>
      )}

      <Modal
        open={depositConfirm}
        onClose={() => setDepositConfirm(false)}
        title="Confirm deposit"
        subtitle="Credits operator ledger only — not on-chain transfer"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setDepositConfirm(false)}>
              Cancel
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                push(`DEPOSIT $${amount} ${asset} · ${note}`);
                setDepositConfirm(false);
              }}
            >
              Credit ${amount} {asset}
            </Btn>
          </>
        }
      >
        <DetailGrid
          rows={[
            { label: "Amount", value: `$${amount} ${asset}` },
            { label: "Note", value: note },
            { label: "Operator", value: "Hyperion" },
            { label: "Effect", value: "equity_usd + available_usd" },
          ]}
        />
      </Modal>

      <Modal
        open={withdrawConfirm}
        onClose={() => setWithdrawConfirm(false)}
        title="Confirm withdrawal"
        subtitle="Requires --confirm-yes · live uses gate receipt"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setWithdrawConfirm(false)}>
              Cancel
            </Btn>
            <Btn
              variant="danger"
              onClick={() => {
                push(`WITHDRAW $${amount} ${asset} → ${address} via ${adapter}`);
                setWithdrawConfirm(false);
                setConfirmYes(false);
              }}
            >
              Submit withdrawal
            </Btn>
          </>
        }
      >
        <DetailGrid
          rows={[
            { label: "Amount", value: `$${amount} ${asset}` },
            { label: "Destination", value: address },
            { label: "Adapter", value: adapter },
            {
              label: "% of equity",
              value: `${((Number(amount) / portfolio.equityUsd) * 100).toFixed(2)}%`,
            },
          ]}
        />
      </Modal>

      <Modal
        open={sweepModal}
        onClose={() => setSweepModal(false)}
        title="Weekly profit sweep"
        subtitle="Profit only — never deposits"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSweepModal(false)}>
              Cancel
            </Btn>
            <Btn
              variant="primary"
              disabled={capitalLedger.growthPhase}
              onClick={() => {
                push("WEEKLY SWEEP → Trezor Safe 7 (demo)");
                setSweepModal(false);
              }}
            >
              Execute sweep
            </Btn>
          </>
        }
      >
        <DetailGrid
          rows={[
            { label: "Growth phase", value: capitalLedger.growthPhase ? "YES · skip" : "NO · armed" },
            { label: "Weekly profit", value: `$${capitalLedger.weeklyProfitUsd}` },
            { label: "Sweep %", value: `${capitalLedger.sweepPct}%` },
            { label: "Estimated", value: `$${nextSweepEstimate.toFixed(2)}` },
            { label: "Destination", value: "Trezor Safe 7" },
          ]}
        />
      </Modal>

      <Modal
        open={ceremony}
        onClose={() => setCeremony(false)}
        title="Trezor Safe 7 ceremony"
        subtitle="Mac Mini vault metadata + physical confirm"
        width={520}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setCeremony(false)}>
              Abort
            </Btn>
            <Btn
              variant="primary"
              onClick={() => {
                push("Ceremony step complete · awaiting device confirm (demo)");
                setCeremony(false);
              }}
            >
              Mark step done
            </Btn>
          </>
        }
      >
        <div className="option-grid">
          {[
            ["1 · Unlock Mac Mini vault", "metadata only"],
            ["2 · Connect Safe 7", "USB / bridge"],
            ["3 · Verify address", "show on device"],
            ["4 · Confirm transfer", "physical button"],
          ].map(([t, h]) => (
            <button
              key={t}
              type="button"
              className="option-tile"
              onClick={() => toast(t)}
            >
              <strong>{t}</strong>
              <span>{h}</span>
            </button>
          ))}
        </div>
      </Modal>

      <Drawer
        open={!!wallet}
        onClose={() => setWallet(null)}
        title={wallet?.label ?? ""}
        subtitle={wallet?.role}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setWallet(null)}>
              Close
            </Btn>
            <Btn onClick={() => { push(`Copied ${wallet?.address}`); }}>Copy address</Btn>
            <Btn
              variant="primary"
              onClick={() => {
                if (wallet) setAddress(wallet.address);
                setWallet(null);
                setTab("withdraw");
              }}
            >
              Withdraw here
            </Btn>
          </>
        }
      >
        {wallet ? (
          <DetailGrid
            rows={[
              { label: "Kind", value: wallet.kind },
              { label: "Chain", value: wallet.chain },
              { label: "Address", value: wallet.address },
              { label: "Balance", value: `$${wallet.balanceUsd.toLocaleString()}` },
              { label: "Role", value: wallet.role },
            ]}
          />
        ) : null}
      </Drawer>

      <Drawer
        open={!!txn}
        onClose={() => setTxn(null)}
        title={txn ? `${txn.type} · ${txn.asset}` : ""}
        subtitle={txn?.ts}
        footer={
          <Btn variant="ghost" onClick={() => setTxn(null)}>
            Close
          </Btn>
        }
      >
        {txn ? (
          <DetailGrid
            rows={[
              { label: "Amount", value: `$${txn.amount} ${txn.asset}` },
              { label: "Status", value: txn.status },
              { label: "Note", value: txn.note },
            ]}
          />
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}
