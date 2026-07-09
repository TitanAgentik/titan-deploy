import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bookmark,
  CheckCircle2,
  Clock,
  ExternalLink,
  Globe,
  RefreshCw,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { PageHeader, Card, Tag, Btn, Metric } from "@/components/ui";
import { Drawer, ToastStack, useToasts } from "@/components/interactive";
import {
  cryptoNews,
  newsCategoryLabels,
  type NewsCategory,
  type NewsImpact,
} from "@/lib/data";
import { SaveBar } from "@/components/SaveBar";
import { useCockpitDraft } from "@/lib/useCockpitDraft";

type Article = (typeof cryptoNews.articles)[number];
type CategoryId = (typeof cryptoNews.categories)[number]["id"];

const CATEGORY_ACCENT: Record<NewsCategory, string> = {
  breaking: "#ef4444",
  macro: "#6366f1",
  regulation: "#8b5cf6",
  markets: "#3b82f6",
  defi: "#10b981",
  layer2: "#06b6d4",
  security: "#f59e0b",
  protocol: "#ec4899",
  etf: "#14b8a6",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function impactKind(impact: NewsImpact): "healthy" | "bleeding" | "neutral" {
  if (impact === "bullish") return "healthy";
  if (impact === "bearish") return "bleeding";
  return "neutral";
}

function sourceTierLabel(tier: Article["source"]["tier"]): string {
  if (tier === "wire") return "Wire";
  if (tier === "tier1") return "Tier 1";
  return "Tier 2";
}

export function CryptoNews() {
  const cn = cryptoNews;
  const { toasts, push, dismiss } = useToasts();
  const {
    draft: newsPrefs,
    update: updateNews,
    setDraft: setNewsDraft,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  } = useCockpitDraft("cryptoNews", {
    category: "all" as CategoryId,
    query: "",
    savedIds: [] as string[],
  });
  const category = newsPrefs.category;
  const query = newsPrefs.query;
  const setCategory = (v: CategoryId) => updateNews({ category: v });
  const setQuery = (v: string) => updateNews({ query: v });
  const saved = useMemo(() => new Set(newsPrefs.savedIds), [newsPrefs.savedIds]);
  const setSaved = (updater: Set<string> | ((prev: Set<string>) => Set<string>)) => {
    const next = typeof updater === "function" ? updater(saved) : updater;
    updateNews({ savedIds: Array.from(next) });
  };
  const [selected, setSelected] = useState<Article | null>(null);

  const featured = useMemo(
    () => cn.articles.filter((a) => cn.featuredIds.includes(a.id)),
    [cn.articles, cn.featuredIds],
  );

  const articles = useMemo(() => {
    let out = cn.articles;
    if (category !== "all") {
      out = out.filter((a) => a.category === category || (category === "breaking" && a.breaking));
    }
    const q = query.trim().toLowerCase();
    if (q) {
      out = out.filter(
        (a) =>
          a.headline.toLowerCase().includes(q) ||
          a.dek.toLowerCase().includes(q) ||
          a.summary.toLowerCase().includes(q) ||
          a.source.name.toLowerCase().includes(q) ||
          a.assets.some((x) => x.toLowerCase().includes(q)),
      );
    }
    return [...out].sort((a, b) => b.ts.localeCompare(a.ts));
  }, [cn.articles, category, query]);

  const aggLabel =
    cn.aggregateImpact > 0.2 ? "Net bullish" : cn.aggregateImpact < -0.2 ? "Net bearish" : "Mixed";

  const toggleSave = (id: string) => {
    setSaved((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <>
      <PageHeader
        eyebrow="NARRATIVE · News Analyst"
        title="Crypto News"
        subtitle="Tier-1 wires and desks — impact-classified, cross-validated, ORACLE NewsReport-ready. Not social noise."
        actions={
          <>
            <Link className="btn" to="/crypto-twitter">
              Crypto Twitter
            </Link>
            <Btn variant="primary" onClick={() => push("News wire refresh queued", "ok")}>
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
          push("Saved locally (cockpit)", "ok");
        }}
        onDiscard={discard}
        onResetDefaults={resetDefaults}
      />

      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric
          label="News impact (24h)"
          value={aggLabel}
          delta={`score ${cn.aggregateImpact >= 0 ? "+" : ""}${cn.aggregateImpact.toFixed(2)}`}
          deltaDir={cn.aggregateImpact >= 0 ? "up" : "down"}
        />
        <Metric label="Articles / hour" value={String(cn.articlesPerHour)} delta="deduped ingest" />
        <Metric
          label="Cross-validated"
          value={String(cn.crossValidated24h)}
          delta="≥3 sources · R17 gate"
        />
        <Metric
          label="Last ingest"
          value={cn.feedStatus.toUpperCase()}
          delta={relativeTime(cn.lastIngestTs)}
        />
      </div>

      {/* Featured hero */}
      {category === "all" && !query && featured.length >= 2 ? (
        <div className="grid grid-2" style={{ marginBottom: 14, gap: 14 }}>
          {featured.map((a, i) => (
            <FeaturedCard
              key={a.id}
              article={a}
              large={i === 0}
              onOpen={() => setSelected(a)}
              onSave={() => toggleSave(a.id)}
              saved={saved.has(a.id)}
            />
          ))}
        </div>
      ) : null}

      <div className="split" style={{ marginBottom: 14 }}>
        <Card title="News desk" style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            {cn.categories.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`btn${category === c.id ? " primary" : ""}`}
                onClick={() => setCategory(c.id)}
              >
                {c.label}
                <span className="nav-badge" style={{ marginLeft: 4 }}>
                  {c.count}
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
              placeholder="Search headlines, tickers, sources…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ border: "none", background: "transparent", width: "100%" }}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {articles.length === 0 ? (
              <p className="muted small">No articles match this filter.</p>
            ) : (
              articles.map((a) => (
                <ArticleRow
                  key={a.id}
                  article={a}
                  onOpen={() => setSelected(a)}
                  onSave={() => toggleSave(a.id)}
                  saved={saved.has(a.id)}
                />
              ))
            )}
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Card title="Market pulse">
            <div className="grid grid-2" style={{ gap: 10, marginBottom: 12 }}>
              {[
                { label: "BTC 24h", value: cn.marketPulse.btc24hPct },
                { label: "ETH 24h", value: cn.marketPulse.eth24hPct },
                { label: "SOL 24h", value: cn.marketPulse.sol24hPct },
                { label: "DXY 24h", value: cn.marketPulse.dxy24hPct },
              ].map((m) => (
                <div key={m.label} className="option-tile" style={{ padding: 10, textAlign: "left" }}>
                  <span className="muted small">{m.label}</span>
                  <div
                    className="mono"
                    style={{
                      fontSize: 16,
                      color: m.value >= 0 ? "var(--titan-mint)" : "var(--titan-coral)",
                    }}
                  >
                    {m.value >= 0 ? "+" : ""}
                    {m.value.toFixed(2)}%
                  </div>
                </div>
              ))}
            </div>
            <p className="muted small" style={{ margin: "0 0 8px" }}>
              Fear &amp; Greed: <strong>{cn.marketPulse.fearGreedIndex}</strong> · VIX{" "}
              {cn.marketPulse.vix}
            </p>
            <p className="muted small" style={{ margin: 0, lineHeight: 1.6 }}>
              Dominant narrative: {cn.marketPulse.dominantNarrative}
            </p>
          </Card>

          <Card title="Macro calendar">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Event</th>
                    <th>Impact</th>
                  </tr>
                </thead>
                <tbody>
                  {cn.calendar.map((e) => (
                    <tr key={e.ts + e.event}>
                      <td className="mono small">{e.ts.replace("T", " ").slice(5, 16)}</td>
                      <td className="small">{e.event}</td>
                      <td>
                        <Tag kind={e.impact === "high" ? "bleeding" : "watch"}>{e.impact}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Source reliability (24h)">
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Tier</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {cn.sources.map((s) => (
                    <tr key={s.id}>
                      <td>{s.name}</td>
                      <td>
                        <Tag kind={s.tier === "wire" ? "healthy" : s.tier === "tier1" ? "info" : "neutral"}>
                          {sourceTierLabel(s.tier)}
                        </Tag>
                      </td>
                      <td className="mono">{(s.reliability * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="ORACLE NewsReport pipeline">
            <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
              <li>Ingest Reuters, Bloomberg, CoinDesk, The Block, Blockworks</li>
              <li>Classify impact: bullish / bearish / neutral per event</li>
              <li>Cross-validate ≥3 sources before trade promotion (R17)</li>
              <li>CORTEX hallucination-guard on high-impact headlines</li>
              <li>CB: <span className="mono">CB_NARRATIVE_FEED_STALE</span> if &gt;60s</li>
            </ul>
          </Card>
        </div>
      </div>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.headline ?? ""}
        subtitle={selected ? `${selected.source.name} · ${relativeTime(selected.ts)}` : ""}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setSelected(null)}>
              Close
            </Btn>
            {selected ? (
              <Btn onClick={() => window.open(selected.source.url, "_blank", "noopener,noreferrer")}>
                <ExternalLink size={14} /> Source
              </Btn>
            ) : null}
            <Btn
              variant="primary"
              onClick={() => selected && push(`NewsReport cite queued · ${selected.id}`, "ok")}
            >
              Cite in ORACLE
            </Btn>
          </>
        }
      >
        {selected ? (
          <>
            <p className="muted" style={{ marginTop: 0, fontSize: 15, lineHeight: 1.5 }}>
              {selected.dek}
            </p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
              <Tag kind={impactKind(selected.impact)}>{selected.impact}</Tag>
              <Tag kind="info">{newsCategoryLabels[selected.category]}</Tag>
              <Tag kind={sourceTierLabel(selected.source.tier) === "Wire" ? "healthy" : "info"}>
                {selected.source.name}
              </Tag>
              {selected.crossValidated ? (
                <Tag kind="healthy">
                  <CheckCircle2 size={12} style={{ marginRight: 4, verticalAlign: -2 }} />
                  {selected.corroborationCount} sources
                </Tag>
              ) : (
                <Tag kind="watch">single source</Tag>
              )}
              {selected.assets.map((t) => (
                <Tag key={t} kind="neutral">
                  ${t}
                </Tag>
              ))}
            </div>

            <p style={{ lineHeight: 1.65, marginBottom: 16 }}>{selected.summary}</p>

            <strong className="small">Key points</strong>
            <ul style={{ margin: "8px 0 16px", paddingLeft: 20, lineHeight: 1.7 }}>
              {selected.bullets.map((b) => (
                <li key={b} className="small">
                  {b}
                </li>
              ))}
            </ul>

            {"quote" in selected && selected.quote ? (
              <blockquote
                style={{
                  margin: "0 0 16px",
                  padding: "12px 16px",
                  borderLeft: `3px solid ${CATEGORY_ACCENT[selected.category]}`,
                  background: "var(--titan-panel)",
                  borderRadius: "0 8px 8px 0",
                }}
              >
                <p style={{ margin: 0, fontStyle: "italic", lineHeight: 1.6 }}>
                  &ldquo;{selected.quote.text}&rdquo;
                </p>
                <footer className="muted small" style={{ marginTop: 8 }}>
                  — {selected.quote.attribution}
                </footer>
              </blockquote>
            ) : null}

            <DetailRows
              rows={[
                { k: "Article ID", v: selected.id },
                { k: "Published", v: selected.ts },
                { k: "Impact score", v: selected.impactScore.toFixed(2) },
                { k: "Confidence", v: `${(selected.confidence * 100).toFixed(0)}%` },
                { k: "Read time", v: `${selected.readMin} min` },
                { k: "Regions", v: selected.regions.join(", ") },
                { k: "Market reaction", v: selected.marketReaction },
                {
                  k: "Corroboration",
                  v: selected.crossValidated
                    ? selected.corroborationSources.join(", ")
                    : "Awaiting 2nd source",
                },
                {
                  k: "Pipelines",
                  v: selected.pipelines.join(", "),
                },
              ]}
            />
          </>
        ) : null}
      </Drawer>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </>
  );
}

function FeaturedCard({
  article: a,
  large,
  onOpen,
  onSave,
  saved,
}: {
  article: Article;
  large?: boolean;
  onOpen: () => void;
  onSave: () => void;
  saved: boolean;
}) {
  const accent = CATEGORY_ACCENT[a.category];
  return (
    <article
      className="card"
      style={{
        cursor: "pointer",
        padding: 0,
        overflow: "hidden",
        border: a.breaking ? `1px solid ${accent}44` : undefined,
      }}
      onClick={onOpen}
      onKeyDown={(e) => e.key === "Enter" && onOpen()}
      role="button"
      tabIndex={0}
    >
      <div
        style={{
          height: large ? 6 : 4,
          background: `linear-gradient(90deg, ${accent}, ${accent}66)`,
        }}
      />
      <div style={{ padding: large ? 20 : 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 10 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {a.breaking ? <Tag kind="bleeding">BREAKING</Tag> : null}
            <Tag kind="info">{newsCategoryLabels[a.category]}</Tag>
            <Tag kind={impactKind(a.impact)}>{a.impact}</Tag>
          </div>
          <button
            type="button"
            className="btn ghost"
            style={{ padding: 4 }}
            onClick={(e) => {
              e.stopPropagation();
              onSave();
            }}
            aria-label="Save article"
          >
            <Bookmark size={16} fill={saved ? "currentColor" : "none"} />
          </button>
        </div>
        <h3 style={{ margin: "0 0 8px", fontSize: large ? 20 : 17, lineHeight: 1.35 }}>
          {a.headline}
        </h3>
        <p className="muted small" style={{ margin: "0 0 12px", lineHeight: 1.55 }}>
          {a.dek}
        </p>
        <footer
          className="muted small"
          style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}
        >
          <strong>{a.source.name}</strong>
          <span>·</span>
          <span>{relativeTime(a.ts)}</span>
          <span>·</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Clock size={12} /> {a.readMin} min read
          </span>
          {a.crossValidated ? (
            <>
              <span>·</span>
              <span style={{ color: "var(--titan-mint)" }}>{a.corroborationCount} sources</span>
            </>
          ) : null}
        </footer>
      </div>
    </article>
  );
}

function ArticleRow({
  article: a,
  onOpen,
  onSave,
  saved,
}: {
  article: Article;
  onOpen: () => void;
  onSave: () => void;
  saved: boolean;
}) {
  const accent = CATEGORY_ACCENT[a.category];
  return (
    <article
      className="option-tile"
      style={{
        textAlign: "left",
        cursor: "pointer",
        padding: 14,
        display: "flex",
        gap: 14,
        alignItems: "stretch",
      }}
      onClick={onOpen}
      onKeyDown={(e) => e.key === "Enter" && onOpen()}
      role="button"
      tabIndex={0}
    >
      <div
        style={{
          width: 4,
          borderRadius: 2,
          background: accent,
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 12,
            marginBottom: 6,
          }}
        >
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            <Tag kind="info">{newsCategoryLabels[a.category]}</Tag>
            <Tag kind={impactKind(a.impact)}>{a.impact}</Tag>
            {a.crossValidated ? (
              <Tag kind="healthy">{a.corroborationCount} src</Tag>
            ) : (
              <Tag kind="watch">unconfirmed</Tag>
            )}
            {a.assets.slice(0, 3).map((t) => (
              <Tag key={t} kind="neutral">
                ${t}
              </Tag>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
            {a.impact === "bullish" ? (
              <TrendingUp size={16} style={{ color: "var(--titan-mint)" }} />
            ) : a.impact === "bearish" ? (
              <TrendingDown size={16} style={{ color: "var(--titan-coral)" }} />
            ) : null}
            <button
              type="button"
              className="btn ghost"
              style={{ padding: 2 }}
              onClick={(e) => {
                e.stopPropagation();
                onSave();
              }}
              aria-label="Save"
            >
              <Bookmark size={14} fill={saved ? "currentColor" : "none"} />
            </button>
          </div>
        </header>
        <h4 style={{ margin: "0 0 6px", fontSize: 15, lineHeight: 1.4 }}>{a.headline}</h4>
        <p className="muted small" style={{ margin: "0 0 8px", lineHeight: 1.55 }}>
          {a.dek}
        </p>
        <footer
          className="muted small"
          style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}
        >
          <Globe size={12} />
          <strong>{a.source.name}</strong>
          <Tag kind={a.source.tier === "wire" ? "healthy" : "info"}>{sourceTierLabel(a.source.tier)}</Tag>
          <span>{relativeTime(a.ts)}</span>
          <span>· {a.readMin} min</span>
          {a.pipelines.length > 0 ? (
            <span className="mono">→ {a.pipelines.join(", ")}</span>
          ) : null}
        </footer>
      </div>
    </article>
  );
}

function DetailRows({ rows }: { rows: { k: string; v: string }[] }) {
  return (
    <dl className="muted small" style={{ margin: 0, display: "grid", gap: 10 }}>
      {rows.map((r) => (
        <div key={r.k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <dt>{r.k}</dt>
          <dd className="mono" style={{ margin: 0, textAlign: "right", maxWidth: "60%" }}>
            {r.v}
          </dd>
        </div>
      ))}
    </dl>
  );
}
