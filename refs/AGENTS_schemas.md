# §AGENTS_schemas.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `AGENTS_schemas.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Structured-output JSON schemas (debate, trader decision, risk debate, decision log) externalized from AGENTS.md to stay under the 20,000-byte bootstrap limit.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

```json  
  {  
    "thesis_direction": "bullish|bearish",  
    "confidence": 0.0-1.0,  
    "key_arguments": [{"claim": "...", "evidence_source": "fundamentals|sentiment|news|technical", "evidence_excerpt": "..."}],  
    "risk_factors": [{"risk": "...", "severity": "low|medium|high|critical", "mitigation": "..."}],  
    "price_target": {"entry": "...", "target": "...", "stop_loss": "..."},  
    "time_horizon": "1h|4h|24h|7d",  
    "counterargument_responses": [{"opponent_claim": "...", "rebuttal": "..."}]  
  }  
  ```

```json  
  {  
    "action": "strong_buy|buy|hold|sell|strong_sell",  
    "asset": "...",  
    "position_size_pct": 0.0-5.0,  
    "entry_price": "...",  
    "stop_loss": "...",  
    "take_profit": "...",  
    "rationale": "...",  
    "key_risk": "...",  
    "confidence": 0.0-1.0  
  }  
  ```

```json  
  {  
    "risk_adjusted_recommendation": "approve|approve_reduced|reject",  
    "position_size_adjustment": 0.0-1.0,  
    "risk_factors_accepted": ["..."],  
    "risk_factors_mitigated": ["..."],  
    "stop_loss_adjustment": "...",  
    "max_drawdown_contribution": "..."  
  }  
  ```

```json  
{  
  "id": "uuid",  
  "timestamp": "2026-06-13T04:00:00Z",  
  "asset": "ETH",  
  "chain": "ethereum",  
  "pipeline": "P1",  
  "rating": "strong_buy",  
  "confidence": 0.85,  
  "entry_price": 3450.00,  
  "stop_loss": 3350.00,  
  "take_profit": 3650.00,  
  "position_size_pct": 2.5,  
  "analyst_consensus": {"fundamentals": "bullish", "sentiment": "neutral", "news": "bullish", "technical": "bullish"},  
  "debate_winner": "bull",  
  "risk_assessment": "approve",  
  "bft_vote": "2/3 approve",  
  "status": "pending|resolved",  
  "realized_pnl": null,  
  "alpha_vs_btc": null,  
  "reflection": null,  
  "decision_text": "Full trade proposal text..."  
}  
```
