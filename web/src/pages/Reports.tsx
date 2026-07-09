import { PageHeader, Card, Btn, Metric } from "@/components/ui";
import { portfolio, lanes } from "@/lib/data";

export function Reports() {
  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Crypto reporting — PnL attribution, TCA, drawdown, and weekly sweep readiness."
        actions={
          <>
            <Btn variant="ghost">PDF</Btn>
            <Btn variant="primary">Generate pack</Btn>
          </>
        }
      />
      <div className="grid grid-4" style={{ marginBottom: 14 }}>
        <Metric label="WTD PnL" value={`$${portfolio.weeklyPnlUsd}`} deltaDir="up" delta="trading" />
        <Metric label="Deposits YTD" value={`$${portfolio.depositedUsd.toLocaleString()}`} delta="ledger" />
        <Metric label="Sweep unlock" value="$35,000" delta={`${Math.round((portfolio.equityUsd / 35000) * 100)}%`} />
        <Metric label="Funded lanes" value={String(lanes.filter((l) => l.allocation > 0).length)} />
      </div>
      <div className="grid grid-2">
        <Card title="Weekly profit sweep policy">
          <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>Below $35K equity → 100% reinvest (no sweep)</li>
            <li>At/above $35K → 20% of weekly profit → Trezor Safe 7 every 7 days</li>
            <li>Injections continue regardless of sweep</li>
            <li>Do not confuse deposits with profit attribution</li>
          </ul>
        </Card>
        <Card title="Compliance pack contents">
          <ul className="muted small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.8 }}>
            <li>decision_log.jsonl excerpt (last 100)</li>
            <li>Kill / flatten / promotion audit</li>
            <li>TCA by lane + allocator exclusions</li>
            <li>Gate receipt + signing audit hashes</li>
          </ul>
        </Card>
      </div>
    </>
  );
}
