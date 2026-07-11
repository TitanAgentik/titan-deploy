# Trade execution — entry or exit (§TGCMD.3 informational mode)
# Placeholders: see herald_notify/notify.py TRADE_EXECUTION_FIELDS

{json_block}

{icon} *{headline}*
━━━━━━━━━━━━━━━━━━━━━━━━━━
*{action_label}* `{direction}` `{size}` `{asset}` @ `{price}`
Chain: `{chain}` | Venue: `{venue}`
Pipeline: `{pipeline_id}` | Agent: `{agent_id}`
Confidence: {confidence_pct}% | Size: {position_pct}% equity
Reason: _{reason_summary}_
Codes: `{reason_codes_inline}`
{tx_line}
{risk_line}
{pnl_line}
{portfolio_footer}
