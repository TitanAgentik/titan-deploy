# Hourly performance digest (§TGCMD.2)

{json_block}

📊 *HOURLY REPORT — {window_start}–{window_end} UTC*
━━━━━━━━━━━━━━━━━━━━━━━━━━
*SUMMARY*
P&L Hour: *{sign}{hour_pnl_usd}* ({sign}{hour_pnl_pct}%)
P&L Daily: {sign}{daily_pnl_usd} ({sign}{daily_pnl_pct}%)
Trades: {trades_count} (W:{wins} L:{losses})
Win Rate: {win_rate}%
Exposure: {exposure_pct}% ({open_positions} open)
Unrealized: {sign}{unrealized_pnl_usd}
Gas/Fees: ${gas_fees_usd}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{strategy_blocks}
{health_block}
{flags_block}
