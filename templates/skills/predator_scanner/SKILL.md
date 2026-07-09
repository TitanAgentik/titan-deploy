---
name: predator_scanner
description: PREDATOR stalking + predatory modules — mempool hunt, copy-trade detect, honeypot feed, poison fills
metadata:
  openclaw:
    status: live
  skill_tuple:
    intent: predator_scanner
    method: hunt_classify_disrupt
    difficulty: high
  agent: PREDATOR
  tier: "1"
  model: ":30000"
---

# Predator Scanner

Owner: **PREDATOR** (Tier 1 `:30000` — critical path, never cloud models).

## Pillars owned

| Pillar | Responsibility |
|--------|----------------|
| Stalking | Mempool sandwich clusters, RPC probes, copy-trade lag wallets, phishing handoff to HERALD |
| Predatory | Hunt posture, counter-copy poison fills (&lt;1% equity auto; &gt;1% YES), feed BFT safety vote |

## Hunt loop (60s when `hunt_mode=true`)

1. Ingest edge shred / mempool streams (TKY/SIN/FRA/USE/AMS) — **we see them; they do not see us** (Ghost evasion on our execution path)  
2. Classify adversarial patterns → stalk target JSON (`memory/security/stalk_targets.jsonl`)  
3. Severity high → escalate ARCHON + HERALD CRITICAL  
4. Optional: sized decoy / poison fill if &lt;1% equity and policy allows — profit from adversary mistakes  

## Stealth coupling

- All live trades: TRENCH-OPS must use shielded venue (kernel DENY on `public_rpc` / unshielded)  
- P22 memecoin: Jito bundle + EDGE-FRA only (`STEALTH_PIPELINE_ROUTE`)  
- Fingerprint rotate every 168h; traffic jitter on edge heartbeats  

## Output schema

```json
{
  "agent": "PREDATOR",
  "pillar": "stalk|predatory",
  "targets": [{
    "id": "st-…",
    "label": "string",
    "severity": "low|medium|high",
    "status": "tracking|watching|quarantined|cleared",
    "note": "string"
  }],
  "hunt_mode": true,
  "bft_vote_hint": "ALLOW|DENY|ABSTAIN",
  "confidence": 0.0,
  "ts": "ISO-8601"
}
```

## Constraints

- No live signing — route via TRENCH-OPS + signing_node  
- Poison fills: % equity only; hard stop-loss; kernel DENY still authoritative  
- Do not engage capital &gt;1% without operator YES  

## Refs

- `refs/REAPER_detail.md`, `refs/GHOST_detail.md`, `refs/MEV_detail.md`
- AGENTS trade voting (PREDATOR advisory voter)
- Titan Agentik `/security` Stalking + Predatory tabs
