import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ExternalLink,
  Pause,
  Play,
  RefreshCw,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { Drawer, ToastStack, useToasts } from "@/components/interactive";
import { cryptoTwitter } from "@/lib/data";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";

type Post = (typeof cryptoTwitter.posts)[number];
type ListId = (typeof cryptoTwitter.lists)[number]["id"];

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function sentimentKind(s: Post["sentiment"]): "healthy" | "bleeding" | "neutral" | "watch" {
  if (s === "bullish") return "healthy";
  if (s === "bearish") return "bleeding";
  return "neutral";
}

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function CryptoTwitter() {
  const ct = cryptoTwitter;
  const { toasts, push, dismiss } = useToasts();
  const {
    draft: twPrefs,
    update: updateTw,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("cryptoTwitter", {
    list: "all" as ListId,
    query: "",
    paused: false,
  });
  const list = twPrefs.list;
  const query = twPrefs.query;
  const paused = twPrefs.paused;
  const setList = (v: ListId) => updateTw({ list: v });
  const setQuery = (v: string) => updateTw({ query: v });
  const setPaused = (v: boolean | ((p: boolean) => boolean)) =>
    updateTw({ paused: typeof v === "function" ? v(paused) : v });
  const [selected, setSelected] = useState<Post | null>(null);

  const posts = useMemo(() => {
    let out = ct.posts;
    if (list !== "all") out = out.filter((p) => p.list === list);
    const q = query.trim().toLowerCase();
    if (q) {
      out = out.filter(
        (p) =>
          p.text.toLowerCase().includes(q) ||
          p.handle.toLowerCase().includes(q) ||
          p.assets.some((a) => a.toLowerCase().includes(q)),
      );
    }
    return [...out].sort((a, b) => b.ts.localeCompare(a.ts));
  }, [ct.posts, list, query]);

  const aggLabel =
    ct.aggregateSentiment > 0.2
      ? "Bullish"
      : ct.aggregateSentiment < -0.2
        ? "Bearish"
        : "Neutral";

  return (
    <>
      <PageHeader
        eyebrow="NARRATIVE · X / Twitter"
        title="Crypto Twitter"
        subtitle="Grounded social feed for ORACLE sentiment analyst — every signal cites post + timestamp. Live via Browserbase stealth sessions when wired."
        actions={
          <>
            <Link className="btn" to="/crypto-news">
              Crypto News
            </Link>
            <Btn variant="ghost" onClick={() => setPaused((p) => !p)}>
              {paused ? <Play size={14} /> : <Pause size={14} />}
              {paused ? "Resume" : "Pause"} stream
            </Btn>
            <Btn variant="primary" onClick={() => push("NARRATIVE ingest refresh queued", "ok")}>
              <RefreshCw size={14} /> Refresh
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

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric
          label="Aggregate sentiment"
          value={aggLabel}
          delta={`score ${ct.aggregateSentiment >= 0 ? "+" : ""}${ct.aggregateSentiment.toFixed(2)} · conf ${(ct.sentimentConfidence * 100).toFixed(0)}%`}
          deltaDir={ct.aggregateSentiment >= 0 ? "up" : "down"}
        />
        <Metric label="Posts / hour" value={String(ct.postsPerHour)} delta="filtered ingest" />
        <Metric label="Tracked accounts" value={String(ct.trackedAccounts)} delta="150+ CT alpha" />
        <Metric
          label="Feed"
          value={paused ? "PAUSED" : ct.feedStatus.toUpperCase()}
          delta={relativeTime(ct.lastIngestTs)}
        />
      </div>

      <div className="split" style={{ marginBottom: 14 }}>
        <Card title="Timeline" style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            {ct.lists.map((l) => (
              <button
                key={l.id}
                type="button"
                className={`btn${list === l.id ? " primary" : ""}`}
                onClick={() => setList(l.id)}
              >
                {l.label}
                <span className="nav-badge" style={{ marginLeft: 4 }}>
                  {l.count}
                </span>
              </button>
            ))}
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 14,
              padding: "8px 12px",
              background: "var(--titan-panel)",
              borderRadius: 8,
            }}
          >
            <Search size={14} className="muted" />
            <input
              placeholder="Search posts, handles, tickers…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ border: "none", background: "transparent", width: "100%" }}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {posts.length === 0 ? (
              <p className="muted small">No posts match this filter.</p>
            ) : (
              posts.map((p) => (
                <article
                  key={p.id}
                  className="option-tile"
                  style={{
                    textAlign: "left",
                    cursor: "pointer",
                    padding: 14,
                    display: "block",
                  }}
                  onClick={() => setSelected(p)}
                  onKeyDown={(e) => e.key === "Enter" && setSelected(p)}
                  role="button"
                  tabIndex={0}
                >
                  <header
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 12,
                      marginBottom: 8,
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                        <strong>{p.displayName}</strong>
                        {p.verified ? <Tag kind="info">verified</Tag> : null}
                        <span className="mono muted small">@{p.handle}</span>
                        <span className="muted small">· {relativeTime(p.ts)}</span>
                      </div>
                      <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                        <Tag kind={sentimentKind(p.sentiment)}>{p.sentiment}</Tag>
                        {p.assets.map((a) => (
                          <Tag key={a} kind="neutral">
                            ${a}
                          </Tag>
                        ))}
                        {"pipelines" in p && p.pipelines
                          ? p.pipelines.map((pl) => (
                              <Tag key={pl} kind="watch">
                                {pl}
                              </Tag>
                            ))
                          : null}
                      </div>
                    </div>
                    {p.sentiment === "bullish" ? (
                      <TrendingUp size={18} style={{ color: "var(--titan-mint)", flexShrink: 0 }} />
                    ) : p.sentiment === "bearish" ? (
                      <TrendingDown size={18} style={{ color: "var(--titan-coral)", flexShrink: 0 }} />
                    ) : null}
                  </header>
                  <p style={{ margin: "0 0 10px", lineHeight: 1.55, fontSize: 14 }}>{p.text}</p>
                  <footer
                    className="muted small"
                    style={{ display: "flex", gap: 14, flexWrap: "wrap" }}
                  >
                    <span>{formatViews(p.metrics.views)} views</span>
                    <span>{p.metrics.reposts} reposts</span>
                    <span>{p.metrics.likes} likes</span>
                    <span className="mono">{p.catalyst.type.replace(/_/g, " ")}</span>
                  </footer>
                </article>
              ))
            )}
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Card title="Sentiment pulse">
            <div
              style={{
                height: 8,
                borderRadius: 4,
                background: "linear-gradient(90deg, var(--titan-coral) 0%, var(--titan-panel) 50%, var(--titan-mint) 100%)",
                position: "relative",
                marginBottom: 12,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: `${((ct.aggregateSentiment + 1) / 2) * 100}%`,
                  top: -4,
                  width: 4,
                  height: 16,
                  background: "var(--titan-navy)",
                  borderRadius: 2,
                  transform: "translateX(-50%)",
                }}
              />
            </div>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.7 }}>
              ORACLE SentimentReport range −1.0 to +1.0. Grounding rule: all trade-facing claims must
              cite this post ID + ISO timestamp.
            </p>
          </Card>

          <Card title="Top tracked accounts (24h)">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Handle</th>
                    <th>List</th>
                    <th>Posts</th>
                  </tr>
                </thead>
                <tbody>
                  {ct.topAccounts.map((a) => (
                    <tr key={a.handle}>
                      <td className="mono">@{a.handle}</td>
                      <td>{a.list}</td>
                      <td>{a.posts24h}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="NARRATIVE pipeline">
            <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
              <li>Ingest X / Farcaster / Discord / news wires</li>
              <li>Classify catalyst: type, assets, direction, magnitude</li>
              <li>Publish to <span className="mono">narrative:events:high</span></li>
              <li>CORTEX hallucination-guard on high-impact events</li>
              <li>CB: <span className="mono">CB_NARRATIVE_FEED_STALE</span> if &gt;60s</li>
            </ul>
          </Card>
        </div>
      </div>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected ? `@${selected.handle}` : ""}
        subtitle={selected ? selected.displayName : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSelected(null)}>
              Close
            </Btn>
            {selected ? (
              <Btn
                onClick={() => window.open(selected.url, "_blank", "noopener,noreferrer")}
              >
                <ExternalLink size={14} /> Open on X
              </Btn>
            ) : null}
            <Btn
              variant="primary"
              onClick={() => selected && push(`ORACLE citation queued · ${selected.id}`, "ok")}
            >
              Cite in ORACLE
            </Btn>
          </>
        }
      >
        {selected ? (
          <>
            <p style={{ lineHeight: 1.6, marginTop: 0 }}>{selected.text}</p>
            <DetailRows
              rows={[
                { k: "Post ID", v: selected.id },
                { k: "Timestamp", v: selected.ts },
                { k: "Sentiment score", v: selected.sentimentScore.toFixed(2) },
                { k: "Catalyst type", v: selected.catalyst.type },
                { k: "Direction", v: selected.catalyst.direction },
                { k: "Magnitude", v: selected.catalyst.magnitude },
                { k: "Novelty", v: selected.catalyst.novelty.toFixed(2) },
                { k: "Assets", v: selected.assets.join(", ") },
              ]}
            />
            {"pipelines" in selected && selected.pipelines ? (
              <p className="muted small" style={{ marginTop: 14 }}>
                Linked pipelines: {selected.pipelines.join(", ")}
              </p>
            ) : null}
          </>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}

function DetailRows({ rows }: { rows: { k: string; v: string }[] }) {
  return (
    <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
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
