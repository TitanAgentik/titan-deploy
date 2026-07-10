import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { Drawer, Modal, ToastStack, useToasts } from "@/components/interactive";
import { formatPnl, portfolio, walletTracker } from "@/lib/data";
import {
  WATCH_CATEGORIES,
  WATCH_CHAINS,
  categoryTagKind,
  createCustomWallet,
  customToAccount,
  loadCustomWatchedWallets,
  presetToAccount,
  saveCustomWatchedWallets,
  selfToAccount,
  validateWatchAddress,
  type AddWalletInput,
  type CustomWatchedWallet,
  type TrackerAccount,
  type WatchCategory,
} from "@/lib/walletWatchlist";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";

type Flow = (typeof walletTracker.recentFlows)[number];
type View = "portfolio" | "watchlist";
type SelfFilter = "all" | "hot" | "cold" | "edge" | "dex";
type WatchFilter = "all" | WatchCategory;

const CHART_COLORS = ["#06b6d4", "#10b981", "#e8a317", "#6366f1", "#f59e0b", "#8b5cf6"];

function statusTag(status: TrackerAccount["status"]) {
  if (status === "synced") return "healthy" as const;
  if (status === "lagging") return "watch" as const;
  return "bleeding" as const;
}

function kindTag(account: TrackerAccount) {
  if (account.owner === "external") return categoryTagKind(account.category ?? "custom");
  if (account.kind === "hot") return "healthy" as const;
  if (account.kind === "cold") return "info" as const;
  if (account.kind === "edge") return "watch" as const;
  return "neutral" as const;
}

function formatBalance(usd: number): string {
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(2)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(1)}k`;
  return `$${usd.toLocaleString()}`;
}

const EMPTY_ADD: AddWalletInput = {
  label: "",
  address: "",
  chain: "ethereum",
  category: "whale",
  notes: "",
  alertsEnabled: true,
};

export function WalletTracker() {
  const wt = walletTracker;
  const { toasts, push, dismiss } = useToasts();
  const {
    draft: wtPrefs,
    update: updateWt,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("walletTracker", {
    view: "portfolio" as View,
    selfFilter: "all" as SelfFilter,
    watchFilter: "all" as WatchFilter,
    query: "",
  });
  const view = wtPrefs.view;
  const selfFilter = wtPrefs.selfFilter;
  const watchFilter = wtPrefs.watchFilter;
  const query = wtPrefs.query;
  const setView = (v: View) => updateWt({ view: v });
  const setSelfFilter = (v: SelfFilter) => updateWt({ selfFilter: v });
  const setWatchFilter = (v: WatchFilter) => updateWt({ watchFilter: v });
  const setQuery = (v: string) => updateWt({ query: v });
  const [selected, setSelected] = useState<TrackerAccount | null>(null);
  const [flow, setFlow] = useState<Flow | null>(null);
  const [customWallets, setCustomWallets] = useState<CustomWatchedWallet[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState<AddWalletInput>(EMPTY_ADD);
  const [addError, setAddError] = useState<string | null>(null);

  useEffect(() => {
    setCustomWallets(loadCustomWatchedWallets());
  }, []);

  const watchedAccounts = useMemo(() => {
    const presets = wt.watchedPresets.map(presetToAccount);
    const custom = customWallets.map(customToAccount);
    return [...presets, ...custom];
  }, [customWallets, wt.watchedPresets]);

  const selfAccounts = useMemo(
    () => wt.accounts.map(selfToAccount),
    [wt.accounts],
  );

  const allFlows = useMemo(
    () => [...wt.recentFlows, ...wt.watchedFlows].sort((a, b) => b.ts.localeCompare(a.ts)),
    [wt.recentFlows, wt.watchedFlows],
  );

  const accountById = useMemo(() => {
    const map: Record<string, TrackerAccount> = {};
    for (const a of [...selfAccounts, ...watchedAccounts]) map[a.id] = a;
    return map;
  }, [selfAccounts, watchedAccounts]);

  const watchedTotalUsd = watchedAccounts.reduce((s, a) => s + a.balanceUsd, 0);

  const filterList = useCallback(
    (list: TrackerAccount[], mode: View) => {
      let out = list;
      if (mode === "portfolio") {
        out = out.filter((a) => a.balanceUsd > 0 || a.kind === "deposit");
        if (selfFilter === "hot") out = out.filter((a) => a.kind === "hot");
        else if (selfFilter === "cold") out = out.filter((a) => a.kind === "cold");
        else if (selfFilter === "edge") out = out.filter((a) => a.kind === "edge");
        else if (selfFilter === "dex") out = out.filter((a) => a.group === "DEX");
      } else {
        if (watchFilter !== "all") out = out.filter((a) => a.category === watchFilter);
      }
      const q = query.trim().toLowerCase();
      if (q) {
        out = out.filter(
          (a) =>
            a.label.toLowerCase().includes(q) ||
            a.address.toLowerCase().includes(q) ||
            a.addressFull.toLowerCase().includes(q) ||
            a.group.toLowerCase().includes(q) ||
            a.chains.some((c) => c.includes(q)),
        );
      }
      return out.sort((a, b) => b.balanceUsd - a.balanceUsd);
    },
    [query, selfFilter, watchFilter],
  );

  const displayAccounts = filterList(
    view === "portfolio" ? selfAccounts : watchedAccounts,
    view,
  );

  const displayFlows =
    view === "watchlist"
      ? allFlows.filter((f) => watchedAccounts.some((a) => a.id === f.walletId))
      : allFlows.filter((f) => selfAccounts.some((a) => a.id === f.walletId));

  const selectedFlows = selected ? allFlows.filter((f) => f.walletId === selected.id) : [];

  const handleAddWallet = () => {
    const err = validateWatchAddress(addForm.address, addForm.chain);
    if (err) {
      setAddError(err);
      return;
    }
    if (!addForm.label.trim()) {
      setAddError("Label is required");
      return;
    }
    const dup = [...customWallets, ...wt.watchedPresets].some(
      (w) => w.addressFull.toLowerCase() === addForm.address.trim().toLowerCase(),
    );
    if (dup) {
      setAddError("Address already on watchlist");
      return;
    }
    const next = [...customWallets, createCustomWallet(addForm)];
    setCustomWallets(next);
    saveCustomWatchedWallets(next);
    setAddOpen(false);
    setAddForm(EMPTY_ADD);
    setAddError(null);
    push(`Added ${addForm.label.trim()} to watchlist`, "ok");
    setView("watchlist");
  };

  const handleRemoveCustom = (id: string) => {
    const next = customWallets.filter((w) => w.id !== id);
    setCustomWallets(next);
    saveCustomWatchedWallets(next);
    setSelected(null);
    push("Removed from watchlist", "ok");
  };

  return (
    <>
      <PageHeader
        eyebrow="Treasury · DEX-only"
        title="Wallet Tracker"
        subtitle="On-chain + DEX wallets only (R02 / R46) — plus whale & smart-money watchlists. PREDATOR/WRAITH mirror for P22."
        actions={
          <>
            {view === "watchlist" ? (
              <Btn onClick={() => setAddOpen(true)}>
                <Plus size={14} /> Add wallet
              </Btn>
            ) : null}
            <Link className="btn" to="/capital">
              Capital ops
            </Link>
            <Btn
              variant="primary"
              onClick={() => push(`Re-sync queued · last ${wt.reconLagSeconds}s ago`, "ok")}
            >
              <RefreshCw size={14} /> Sync
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

      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        <button
          type="button"
          className={`btn${view === "portfolio" ? " primary" : ""}`}
          onClick={() => setView("portfolio")}
        >
          Your wallets
        </button>
        <button
          type="button"
          className={`btn${view === "watchlist" ? " primary" : ""}`}
          onClick={() => setView("watchlist")}
        >
          Whales &amp; watchlist
          <span className="nav-badge" style={{ marginLeft: 6 }}>
            {watchedAccounts.length}
          </span>
        </button>
      </div>

      {view === "portfolio" ? (
        <>
          <div className="grid grid-4" style={{ marginBottom: 14 }}>
            <Metric
              label="Total AUM"
              value={`$${wt.totalAumUsd.toLocaleString()}`}
              delta={`${formatPnl(wt.change24hUsd)} (${wt.change24hPct}%) 24h`}
              deltaDir={wt.change24hUsd >= 0 ? "up" : "down"}
            />
            <Metric label="Hot + edge" value={`$${wt.hotAumUsd.toLocaleString()}`} delta={`${((wt.hotAumUsd / wt.totalAumUsd) * 100).toFixed(0)}% of AUM`} />
            <Metric label="Cold vault" value={`$${wt.coldAumUsd.toLocaleString()}`} delta="Trezor Safe 7" />
            <Metric
              label="Recon lag"
              value={`${wt.reconLagSeconds}s`}
              delta={wt.reconLagSeconds < 30 ? "healthy" : "investigate"}
              deltaDir={wt.reconLagSeconds < 30 ? "up" : "down"}
            />
          </div>

          <div className="grid grid-2" style={{ marginBottom: 14 }}>
            <Card title="Chain allocation">
              <div style={{ width: "100%", height: 200 }}>
                <ResponsiveContainer>
                  <BarChart data={wt.chainAllocation} layout="vertical" margin={{ left: 8, right: 8 }}>
                    <CartesianGrid stroke="rgba(11,21,40,0.08)" strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" stroke="#7b8798" fontSize={11} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="chain" stroke="#7b8798" fontSize={11} width={72} />
                    <Tooltip
                      formatter={(v: number) => [`$${v.toLocaleString()}`, "USD"]}
                      contentStyle={{
                        background: "var(--bg-2)",
                        border: "1px solid var(--border-strong)",
                        borderRadius: 8,
                        color: "var(--text)",
                      }}
                    />
                    <Bar dataKey="usd" radius={[0, 4, 4, 0]}>
                      {wt.chainAllocation.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="Portfolio context">
              <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
                {[
                  { k: "Mark equity", v: `$${portfolio.equityUsd.toLocaleString()}` },
                  { k: "Watched external", v: `${watchedAccounts.length} · ${formatBalance(watchedTotalUsd)}` },
                  { k: "Last sync", v: wt.lastSyncTs.replace("T", " ").slice(0, 19) + " UTC" },
                ].map((r) => (
                  <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <dt>{r.k}</dt>
                    <dd className="mono" style={{ margin: 0, textAlign: "right" }}>
                      {r.v}
                    </dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
        </>
      ) : (
        <div className="grid grid-4" style={{ marginBottom: 14 }}>
          <Metric label="Wallets watched" value={String(watchedAccounts.length)} delta={`${customWallets.length} custom`} />
          <Metric label="Combined balance" value={formatBalance(watchedTotalUsd)} delta="external only" />
          <Metric label="Smart money" value={String(watchedAccounts.filter((a) => a.category === "smart_money").length)} delta="P22 mirror" />
          <Metric label="Whales" value={String(watchedAccounts.filter((a) => a.category === "whale").length)} delta="large flow alerts" />
        </div>
      )}

      <WalletTable
        title={view === "portfolio" ? "Your wallet inventory" : "Whales & external watchlist"}
        accounts={displayAccounts}
        query={query}
        onQueryChange={setQuery}
        onSelect={setSelected}
        showOwner={view === "watchlist"}
        filters={
          view === "portfolio" ? (
            <>
              {(
                [
                  ["all", "All"],
                  ["hot", "Hot"],
                  ["cold", "Cold"],
                  ["edge", "Edge"],
                  ["dex", "DEX"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={`btn${selfFilter === id ? " primary" : ""}`}
                  onClick={() => setSelfFilter(id)}
                >
                  {label}
                </button>
              ))}
            </>
          ) : (
            <>
              {(["all", ...WATCH_CATEGORIES.map((c) => c.id)] as WatchFilter[]).map((id) => (
                <button
                  key={id}
                  type="button"
                  className={`btn${watchFilter === id ? " primary" : ""}`}
                  onClick={() => setWatchFilter(id)}
                >
                  {id === "all" ? "All" : WATCH_CATEGORIES.find((c) => c.id === id)?.label}
                </button>
              ))}
            </>
          )
        }
        allocColumn={view === "portfolio"}
      />

      <Card title={view === "watchlist" ? "Whale & watchlist activity" : "Your recent flows · click row"} style={{ marginTop: 14 }}>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Time</th>
                <th>Wallet</th>
                <th>Dir</th>
                <th>Asset</th>
                <th>USD</th>
                <th>Type</th>
                <th>Tx</th>
              </tr>
            </thead>
            <tbody>
              {displayFlows.slice(0, 12).map((f) => (
                <tr key={f.ts + f.txHash} className="row-click" onClick={() => setFlow(f)}>
                  <td className="mono small">{f.ts.replace("T", " ").slice(11, 19)}</td>
                  <td>{accountById[f.walletId]?.label ?? f.walletId}</td>
                  <td>
                    <Tag kind={f.direction === "in" ? "healthy" : "watch"}>{f.direction}</Tag>
                  </td>
                  <td className="mono">{f.asset}</td>
                  <td>${f.amountUsd.toLocaleString()}</td>
                  <td>{f.flowType.replace(/_/g, " ")}</td>
                  <td className="mono small">{f.txHash}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.label ?? ""}
        subtitle={
          selected
            ? `${selected.group}${selected.category ? ` · ${selected.category.replace(/_/g, " ")}` : ""}`
            : ""
        }
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSelected(null)}>
              Close
            </Btn>
            {selected?.custom ? (
              <Btn variant="danger" onClick={() => selected && handleRemoveCustom(selected.id)}>
                <Trash2 size={14} /> Remove
              </Btn>
            ) : null}
            <Btn onClick={() => selected && push(`Copied ${selected.addressFull}`)}>Copy address</Btn>
            {selected?.owner === "self" && (selected.kind === "hot" || selected.kind === "deposit") ? (
              <Link className="btn primary" to="/capital" onClick={() => setSelected(null)}>
                Capital ops
              </Link>
            ) : selected?.owner === "external" ? (
              <Btn
                variant="primary"
                onClick={() => push(`Mirror signal queued · ${selected.label} (P22 demo)`)}
              >
                Mirror to P22
              </Btn>
            ) : null}
          </>
        }
      >
        {selected ? <WalletDetail account={selected} flows={selectedFlows} /> : null}
      </Drawer>

      <Drawer
        open={!!flow}
        onClose={() => setFlow(null)}
        title="Flow detail"
        subtitle={flow ? accountById[flow.walletId]?.label : ""}
        footer={<Btn variant="ghost" onClick={() => setFlow(null)}>Close</Btn>}
      >
        {flow ? (
          <DetailRows
            rows={[
              { k: "Timestamp", v: flow.ts },
              { k: "Direction", v: flow.direction },
              { k: "Asset", v: `${flow.amount} ${flow.asset}` },
              { k: "USD", v: `$${flow.amountUsd.toLocaleString()}` },
              { k: "Type", v: flow.flowType },
              { k: "Tx hash", v: flow.txHash },
              { k: "Status", v: flow.status },
            ]}
          />
        ) : null}
      </Drawer>

      <Modal
        open={addOpen}
        onClose={() => {
          setAddOpen(false);
          setAddError(null);
        }}
        title="Add wallet to watchlist"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setAddOpen(false)}>
              Cancel
            </Btn>
            <Btn variant="primary" onClick={handleAddWallet}>
              Add wallet
            </Btn>
          </>
        }
      >
        <p className="muted small">
          Track whales, KOLs, or competitors. Saved in this browser until live WRAITH/PREDATOR feed is wired.
        </p>
        {addError ? (
          <div className="alert-banner" style={{ marginBottom: 12 }}>
            {addError}
          </div>
        ) : null}
        <div className="form-row" style={{ flexDirection: "column", gap: 12 }}>
          <div className="field">
            <label>Label</label>
            <input
              placeholder="e.g. Wintermute alt · memecoin whale"
              value={addForm.label}
              onChange={(e) => setAddForm({ ...addForm, label: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Address</label>
            <input
              className="mono"
              placeholder="0x… or Solana base58"
              value={addForm.address}
              onChange={(e) => setAddForm({ ...addForm, address: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Primary chain</label>
            <select
              value={addForm.chain}
              onChange={(e) => setAddForm({ ...addForm, chain: e.target.value })}
            >
              {WATCH_CHAINS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Category</label>
            <select
              value={addForm.category}
              onChange={(e) => setAddForm({ ...addForm, category: e.target.value as WatchCategory })}
            >
              {WATCH_CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Notes (optional)</label>
            <input
              placeholder="Why you're watching this wallet"
              value={addForm.notes ?? ""}
              onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })}
            />
          </div>
          <label className="muted small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={addForm.alertsEnabled}
              onChange={(e) => setAddForm({ ...addForm, alertsEnabled: e.target.checked })}
            />
            HERALD alert on large moves (&gt;$50k demo threshold)
          </label>
        </div>
      </Modal>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}

function WalletTable({
  title,
  accounts,
  query,
  onQueryChange,
  onSelect,
  filters,
  showOwner,
  allocColumn,
}: {
  title: string;
  accounts: TrackerAccount[];
  query: string;
  onQueryChange: (q: string) => void;
  onSelect: (a: TrackerAccount) => void;
  filters: ReactNode;
  showOwner: boolean;
  allocColumn: boolean;
}) {
  return (
    <Card
      title={title}
      action={
        <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 180 }}>
          <Search size={14} className="muted" />
          <input
            placeholder="Search…"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            style={{ border: "none", background: "transparent", width: "100%" }}
          />
        </div>
      }
    >
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>{filters}</div>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Wallet</th>
              <th>{showOwner ? "Category" : "Group"}</th>
              <th>Chains</th>
              <th>Balance</th>
              <th>24h</th>
              {allocColumn ? <th>Alloc</th> : null}
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {accounts.length === 0 ? (
              <tr>
                <td colSpan={allocColumn ? 7 : 6} className="muted small">
                  No wallets match — add one with &quot;Add wallet&quot;.
                </td>
              </tr>
            ) : (
              accounts.map((a) => (
                <tr key={a.id} className="row-click" onClick={() => onSelect(a)}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {a.label}
                      {a.custom ? <Tag kind="neutral">custom</Tag> : null}
                    </div>
                    <div className="mono small muted">{a.address}</div>
                  </td>
                  <td>
                    {showOwner && a.category ? (
                      <Tag kind={categoryTagKind(a.category)}>{a.category.replace(/_/g, " ")}</Tag>
                    ) : (
                      a.group
                    )}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {a.chains.map((c) => (
                        <Tag key={c} kind="neutral">
                          {c}
                        </Tag>
                      ))}
                    </div>
                  </td>
                  <td className="mono">{formatBalance(a.balanceUsd)}</td>
                  <td>
                    {a.balanceUsd === 0 && a.owner === "self" ? (
                      "—"
                    ) : (
                      <Tag kind={a.change24hUsd >= 0 ? "healthy" : "bleeding"}>
                        {formatPnl(a.change24hUsd)} ({a.change24hPct}%)
                      </Tag>
                    )}
                  </td>
                  {allocColumn ? <td>{a.allocationPct.toFixed(1)}%</td> : null}
                  <td>
                    <Tag kind={statusTag(a.status)}>{a.status}</Tag>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function WalletDetail({ account, flows }: { account: TrackerAccount; flows: Flow[] }) {
  return (
    <>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        <Tag kind={kindTag(account)}>{account.owner === "external" ? "external" : account.kind}</Tag>
        {account.category ? (
          <Tag kind={categoryTagKind(account.category)}>{account.category.replace(/_/g, " ")}</Tag>
        ) : null}
        {account.alertsEnabled ? <Tag kind="watch">alerts on</Tag> : null}
      </div>
      <p className="muted small">{account.role}</p>
      {account.notes ? <p className="muted small">Note: {account.notes}</p> : null}
      <DetailRows
        rows={[
          { k: "Full address", v: account.addressFull },
          { k: "Balance", v: formatBalance(account.balanceUsd) },
          { k: "24h change", v: `${formatPnl(account.change24hUsd)} (${account.change24hPct}%)` },
          ...(account.owner === "self"
            ? [{ k: "Allocation", v: `${account.allocationPct}% of AUM` }]
            : []),
          { k: "Last activity", v: account.lastTxTs.replace("T", " ").slice(0, 19) + " UTC" },
          ...(account.signingPath ? [{ k: "Signing", v: account.signingPath }] : []),
          ...(account.edgePop ? [{ k: "Edge PoP", v: account.edgePop }] : []),
        ]}
      />
      {account.holdings.length > 0 ? (
        <>
          <h4 className="eyebrow" style={{ marginTop: 20, marginBottom: 8 }}>
            Holdings
          </h4>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Chain</th>
                  <th>Amount</th>
                  <th>USD</th>
                </tr>
              </thead>
              <tbody>
                {account.holdings.map((h) => (
                  <tr key={h.symbol + h.chain}>
                    <td>
                      <span className="mono">{h.symbol}</span>
                    </td>
                    <td>{h.chain}</td>
                    <td className="mono">{h.amount.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
                    <td>{formatBalance(h.usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      {flows.length > 0 ? (
        <>
          <h4 className="eyebrow" style={{ marginTop: 20, marginBottom: 8 }}>
            Recent activity
          </h4>
          <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.9 }}>
            {flows.map((f) => (
              <li key={f.ts + f.txHash}>
                {f.ts.slice(11, 19)} · {f.direction} {f.amount} {f.asset} · {f.flowType.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {account.owner === "external" ? (
        <p className="muted small" style={{ marginTop: 16, marginBottom: 0 }}>
          Live path: WRAITH/PREDATOR Geyser + Erigon labels · balances refresh on Sync
        </p>
      ) : null}
    </>
  );
}

function DetailRows({ rows }: { rows: { k: string; v: string }[] }) {
  return (
    <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
      {rows.map((r) => (
        <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <dt>{r.k}</dt>
          <dd className="mono" style={{ margin: 0, textAlign: "right", wordBreak: "break-all" }}>
            {r.v}
          </dd>
        </div>
      ))}
    </dl>
  );
}
