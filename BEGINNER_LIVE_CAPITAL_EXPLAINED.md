# Live Capital Explained — A Beginner’s Teaching Guide

> **What this is:** A long, patient explanation of how Titan handles *real money* — written for a smart beginner who has never run a production trading stack.  
> **What this is not:** A checkbox ceremony or a switch that turns live trading on. For the operational checklist, see [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md).  
> **Honesty first:** This repo ships a **fail-closed control plane**. Several live adapters are still unfinished. The system is **not** “ready for capital” just because the software is installed. Blockers are explained in plain English below.

**Aligned with:** `LIVE_CAPITAL_PRODUCTION_GUIDE.md`, `SYSTEM.md`, `AGENTS.md` (Bounded Autonomy Matrix), `templates/risk_kernel/policy.yaml`, `PRODUCTION_READINESS.md`, in-process signing architecture.

---

## How to read this document

Imagine you are sitting with someone who built a careful vault around a team of very smart, very fallible assistants. The assistants can *suggest* what to do with money. They cannot open the vault door themselves. You (Hyperion) hold the only keys that matter for “go live,” and a separate machine — not an AI — decides whether any single order is allowed.

This guide walks that story from the beginning: what Titan is trying to do, how the pieces fit, why the pretty web dashboard can look “live” without spending a dollar, what paper and shadow mean, what Phase 5 YES actually commits you to, what must be true before a first real order, what is still broken or unfinished today, how one tiny live trade would feel end-to-end, what happens when things go wrong, and where to start tomorrow morning.

Take your time. Length is intentional.

---

## 1. What Titan is trying to do with your money (and what it must never do)

Titan (also called Titan Agentik) is a **local-first crypto trading control plane**. In plain language: it is software that runs on *your* machines, uses *local* AI models (not ChatGPT-in-the-cloud on the live path), watches markets, proposes trades, and — only if many safety checks pass — can eventually send real orders to decentralized exchanges (DEXes).

**What it is trying to do**

- Preserve capital first. Profit is secondary to not blowing up.
- Let many specialized AI agents (twenty of them) research, debate, and propose.
- Force every real-money action through deterministic safety services that do not “feel” or “negotiate.”
- Trade only on **DEX-only** paths for live capital — Uniswap, Curve, Aave, Hyperliquid, Jupiter, Jito, Flashbots Protect, intent solvers, and similar shielded venues — not by handing API keys to a centralized exchange for the live signing/recon path.
- Keep signing of transactions in a narrow, boring safety process — never inside the chatty LLM that just wrote a bullish thesis.
- Require *you* to say an explicit **YES** before strategies graduate from practice to real capital.

**What it must never do**

- Auto-promote a strategy because three days passed on the calendar. Calendar days are targets, not gates.
- Treat silence, timeout, or “looks good” as approval. **TIMEOUT = HOLD / de-risk.** Never auto-promote.
- Let an agent override a **DENY** from the risk kernel. DENY is absolute.
- Sign trades without a fresh gate receipt (a short-lived proof that the safety pipeline just said ALLOW).
- Use public RPC endpoints or unshielded venues for live capital (that is what **ghost evasion** forbids — more on that later).
- Put closed/cloud models on the live voting or execution path.
- Enable every pipeline in the catalog “because production.” Catalog ≠ checklist. Fund a few HEALTHY lanes, not the whole zoo.
- Spend real money because the cockpit UI is in “live” data mode. UI live ≠ capital live.

Think of Titan as a research lab attached to a bank vault. The lab can write brilliant memos. The vault only opens when the lock mechanism agrees — and you still had to authorize putting money in the vault in the first place.

---

## 2. The big picture: brain, body, hands, and eyes

A useful mental model has four layers.

### The brain — agents (propose, debate, advise)

There are **20 classical agents**. Quantum agents (QCC / QSA / QRP) are **removed**; `quantum.enabled` is false. The fleet looks like this:

| Group | Agents | Job in plain English |
|-------|--------|----------------------|
| Operator interface | HYPERION | You / your Telegram-facing interface |
| Orchestrator / risk / security | ARCHON, CORTEX, GUARDIAN, SENTINEL | Coordinate, deep-think, risk-advise, audit |
| Signals | ORACLE, WRAITH, PREDATOR, AUGUR, NARRATIVE | Fundamentals, on-chain, sniper/mempool, macro regime, catalysts |
| Coding / execution / research | TRENCH-OPS, LAMARCK, DARWIN_GODEL | Execute trades, learn after trades, evolve strategies in shadow |
| Utility (TITANSPARK) | HERALD, NEXUS, FORGE, ALCHEMY, ATLAS, QUANT, ARBITER, HORIZON | Alerts, data, infra health, DeFi ops, portfolio, stats, backtests, R&D metrology |

These agents run on local model tiers (ports like `:30000`, `:30001`, `:30002`). They are the **brain**: they can be wrong, correlated, overconfident, or brilliant. They are *not* the final authority on spending money.

### The body — safety services (veto, measure, halt)

Separate processes listen on ports **`:19001`–`:19008`**. They are not LLMs. They are deterministic programs. If they are down, the system is designed to **fail closed** — meaning “no trade,” not “hope for the best.”

| Port | Name | Beginner meaning |
|------|------|------------------|
| `:19001` | Risk kernel | The locked vault door. Final boss for trade validation. |
| `:19002` | Reconciliation | “Do we actually hold what we think we hold?” |
| `:19003` | Status aggregator | One health dashboard for the safety stack |
| `:19004` | Portfolio risk | Whole-portfolio VaR / correlation checks when wired |
| `:19005` | Dead-man’s switch | If the operator disappears too long → de-risk / flatten |
| `:19006` | Allocator | Suggests (or later enforces) how much capital each strategy gets |
| `:19007` | TCA | Transaction Cost Analysis — was execution quality good? |
| `:19008` | Security ops | Hardening, lockdown, honeypot posture |

**ExecutionGate** is the unbypassable pre-trade pipeline: reconciliation → risk kernel → (portfolio risk when wired) → a short-lived **gate receipt** (`X-Titan-Gate-Receipt`). Without a fresh receipt, signing must refuse.

### The hands — signing + edge broadcast

After ALLOW + receipt, **in-process signing** happens inside `titan-safety` via `SigningNode` (`titan-safety gate sign`). “In-process” means: same safety process on TITANHOME, not a separate mandatory daemon on `:19010`. Legacy HTTP signing exists but is **optional and not required**.

The Mac Mini vault holds key *metadata* and runs **Trezor ceremonies** (cold / harvest workflows). It does **not** sit on the hot path signing every trade.

Then an **edge PoP** (Point of Presence — a small server near the exchange) broadcasts the signed intent/tx on a shielded path. There are five: EDGE-FRA, EDGE-TKY, EDGE-SIN, EDGE-USE, EDGE-AMS. Same-AZ placement aims for sub-millisecond RTT to Hyperliquid, BSC, Solana-EU, L2 sequencers, etc.

### The eyes — cockpit + CLI

The **cockpit** (web UI) and **CLI** (`titan-safety …`) let *you* watch health, promotions, security, capital balances, and kill-switch state. They are operator surfaces. They are **not** a substitute for the risk kernel. A green UI can still be soft-failing with fixture data marked `advisory: true`. Always verify with `curl` to `:19003` when money is involved.

```text
You (YES gates)
      │
      ▼
Agents propose ──► BFT votes (advisory)
      │
      ▼
ExecutionGate ──► recon :19002 ──► kernel :19001 ──► portfolio :19004
      │
      │ ALLOW + gate receipt
      ▼
In-process SigningNode
      │
      ▼
Edge PoP ──► shielded DEX / intent / Jito / Flashbots
```

If any stage fails or is unreachable → **DENY**. There is no “production urgency bypass.”

---

## 3. Why “live” in the web UI is NOT the same as live capital

This is the single most common beginner trap.

When the cockpit is configured with something like `VITE_DATA_MODE=live`, it means: “please fetch real JSON from the safety APIs on my machine.” It does **not** mean: “real wallets are authorized to trade.”

| Phrase you might see | What it actually means | What it does *not* mean |
|----------------------|------------------------|-------------------------|
| Cockpit “live” mode | UI talks to `/api/*` / safety ports | Real capital is authorized |
| `capital_profile: live` in policy | Live *rules* apply (mocks banned, stealth enforced) | Every pipeline is funded and broadcasting |
| Paper venue | Simulated fills; no real tx broadcast | Strategy is proven forever |
| Shadow / dry-run | Live market data + full gate path; **no** capital broadcast | Phase 5 already approved |
| BFT 2-of-3 ALLOW | Advisory authorization among agents | Override of kernel DENY |
| Kernel DENY | Absolute stop | Something an LLM can talk past |
| Phase 5 YES | Explicit Hyperion `YES` in the promotion audit log | Silence, TIMEOUT, or vibes |

Analogy: putting your car’s dashboard in “sport display mode” does not put the car in gear. It only changes what the gauges show.

Also: soft-fail fixtures can make the UI look healthy when backends are down. Treat green-with-`advisory: true` as a warning sticker, not a green light for capital.

---

## 4. Who may say YES to real money vs what agents may auto-do

Titan uses a **Bounded Autonomy Matrix** — a table of what software may do alone versus what requires Hyperion’s explicit YES.

### You / Hyperion must say YES for

- **Phase 5** go / no-go (full live readiness for a subject strategy or phase)
- **New pipeline activation** (turning on a new strategy lane)
- **Model / skill promotion to live**
- **Evolution deploy** to live (DGM-H, GEPA, etc. — shadow only until YES)
- **Leverage change**
- **Flash-loan live**
- Trades / promotions above policy thresholds (e.g. **>1% of equity** goes through promotion-style gates)

Anything other than the exact word **YES** on a promotion prompt is not approval. Empty, TIMEOUT, “ok,” “lgtm” → **HOLD / de-risk**. Never auto-promote.

### Agents may auto-do (within policy)

- Routine trades **under 1% equity** (still subject to kernel DENY, stops, stealth, confidence gates)
- Rebalances under 1% equity
- Circuit-breaker responses that policy allows (notify, reduce, etc.)
- Drawdown **velocity** breach → kernel **HALT** (and alert you)

### Confidence gate (how sure the agents claim to be)

| Confidence score | What happens |
|------------------|--------------|
| ≥ 0.70 | Full size (still capped by policy) |
| 0.50–0.69 | Reduced size ≈ confidence × target |
| 0.30–0.49 | Escalate to ARCHON |
| < 0.30 | Reject |

### Kelly sizing (brief)

**Kelly** is a formula from gambling/investing theory that suggests an “optimal” fraction of bankroll to bet given an edge. Titan uses a **fractional Kelly** (template default often **0.25** — quarter-Kelly) so sizing is more conservative than full Kelly. Agents propose sizes; the kernel and position limits still cap them.

### BFT vote (advisory)

**BFT** here means a Byzantine-fault-tolerant *style* vote: **AUGUR + PREDATOR + ATLAS** cast votes; **2-of-3** is needed for advisory trade authorization on larger / gated paths. These votes are **advisory**. They do not override kernel DENY. They are also not cryptographic magic that makes correlated models independent — GUARDIAN / ARCHON / CORTEX use different model tiers for orchestrator-level heterogeneity, but the authoritative gate remains `:19001`.

Analogy: three advisors raise their hands. The vault door still has its own lock.

---

## 5. The risk kernel (`:19001`) as the final boss

The **risk kernel** is an out-of-process service on port **19001**. “Out-of-process” means it runs as its own program, separate from the agent chat runtime, so a confused agent cannot quietly edit the rules mid-sentence.

**DENY** means: this trade is refused. Full stop. No negotiation. No “but the thesis is strong.”

**ALLOW** means: this trade cleared the deterministic checks *right now* — size, venue, stealth, velocity, kill-switch state, and whatever else policy encodes — and the ExecutionGate may mint a short-lived receipt so signing can proceed.

**Fail-closed** means: if the kernel is unreachable, the answer is DENY (or connection failure treated as no-trade) — never “allow because we can’t ask.” Before live capital, you are expected to *prove* this: stop the kernel, attempt a validate/sign, confirm you do **not** get ALLOW, then restart.

Analogy: the risk kernel is a locked vault door that agents cannot pick. BFT votes are advisors standing outside. ExecutionGate is the security checkpoint that stamps your wristband. Signing is the clerk who only opens the drawer if your wristband is fresh. Edge PoPs are the armored trucks that deliver the package on approved roads only.

**HMAC** (Hash-based Message Authentication Code) is a cryptographic signature using a shared secret. Mutating control-plane actions (flatten, lockdown, some heartbeats, etc.) require operator HMAC (`X-Titan-Auth`). An LLM alone must not be able to lockdown or flatten by chatting sweetly.

---

## 6. Paper trading: practice money, real discipline

**Paper trading** means the system runs the same decision logic and (ideally) the same data feeds, but fills are **simulated**. No real transaction is broadcast to a chain or venue. The venue name is often literally `paper`.

### Why ≥ 3 days?

Policy sets `promotion_gates.paper_minimum_days: 3`. Three calendar days is a **minimum**, not a graduation diploma. You also want enough fills to approach statistical gates (often hundreds of trades for promotion stats), regime diversity, and evidence that kill switch, dead-man’s switch, and reconciliation paths work with **zero** live keys.

ARBITER and the §DEPLOY_LIFECYCLE can automate evidence collection through early phases. **Phase 5 never auto-YES.**

### What “success” looks like for a beginner

Success is not “I made paper profit.” Success looks more like:

1. You can explain what each safety port does.
2. Kernel validates paper smokes without drama.
3. You kept a daily note (Telegram digest + a small JSON file) with trades, PnL, max drawdown, divergence vs backtest, kernel DENYs, and incidents.
4. Kill switch drill worked: activate → trades DENY → signed RESUME only with proper procedure.
5. You did **not** enable P22, flash-loans, and twelve pipelines at once. One or two candidate lanes.
6. Divergence vs backtest is in a sane band (docs often cite rough thresholds like PnL ±15%, trade count ±25%, win rate ±20% — treat these as investigation triggers, not magic).
7. You still feel slightly bored — because nothing real was at risk — and that boredom is healthy.

Analogy: paper is a flight simulator. Crashing the sim is education. Crashing the real plane because you skipped the sim is negligence.

---

## 7. Shadow mode: live markets, no broadcast

**Shadow** (sometimes called dry-run) means: live prices, live mempool/routing decisions, full gate path — but **no capital broadcast**. The system practices aiming at a moving target without firing a live round.

This matters because paper can still be “too clean.” Shadow exposes latency, venue weirdness, and decision quality against real tape while keeping wallets untouched.

**Evolution** outputs (DGM-H, GEPA, HyEvo, SIA, EurekAgent, and friends) stay **shadow-only** until a separate evolution YES. While you are protecting live capital elsewhere, freeze evolution (`titan-safety evolution freeze`).

**Micro-live** is a later cousin: real capital at tiny size (≤ **0.1% equity**), still not “full live.” Do not jump from day-one paper to full size.

Analogy: shadow is dry-firing at a real range — same sights, same trigger discipline, empty chamber for capital.

---

## 8. Phase 5 YES ceremony: what you are actually agreeing to

**Phase 5** is the human go / no-go gate at the end of the deploy lifecycle. When you run something like:

```bash
titan-safety promotion approve \
  --category phase5_go_nogo \
  --subject P5 \
  --response YES \
  --operator hyperion \
  --request-id "phase5-..."
```

you are saying: **this subject** may leave `PENDING_PROMOTION_APPROVAL` and touch live capital **within** kernel limits.

You are **not** saying:

- Disable `:19001`
- Approve every pipeline in the catalog
- Approve evolution forever
- Approve P22 memecoin trench or flash-loans (those need their own categories / flags)
- Approve closed/cloud models on the live path
- That residual engineering blockers magically disappeared

Preconditions (conceptually — all must be true on the live host):

- Paper ≥ 3 days for that lane
- Shadow evidence + red-team review
- Statistical gate when required (≥200 trades, strong deflated Sharpe / PSR, cost realism, shadow divergence ≤15%)
- Safety `:19001`–`:19008` healthy; fail-closed drill done
- Kill switch drill done
- UPS + power-loss HALT drill done
- Live recon wired; mocks not used on live profile
- Signing path understood; `TITAN_LIVE_SIGNING_READY` still `0` until you intentionally arm
- Residual risks in `PRODUCTION_READINESS.md` accepted
- Evolution frozen if protecting live

Audit trail: append-only promotion audit log (typically under `~/.openclaw/safety/`).

Analogy: Phase 5 YES is signing the lease to move into a secured building. It is not removing the locks, not giving every roommate a master key, and not promising the elevators are finished if the punch list still lists broken elevators.

---

## 9. What must be true before the first real order

Before any real order, treat these as non-negotiable. If any fail, stay on paper/shadow.

### UPS (Uninterruptible Power Supply)

A battery backup for TITANHOME (and vault duties). Policy expects something like a ≥3000VA-class UPS and **`ups_required_for_live_capital: true`**. On battery / mains loss: **halt trading**. Drill it: simulate battery → confirm HALT + CRITICAL alert → resume only with operator ack.

Why: a mid-trade power blip without a plan is how you get half-signed chaos and silent positions.

### Trezor

A hardware wallet (here: **Trezor Safe 7** ceremonies on the Mac Mini vault) for cold / harvest workflows. Hot-path trade signing is in-process on TITANHOME after gate ALLOW — not “the LLM has the seed.” Seeds and session keys must never be written into agent memory.

Weekly profit sweep (**R23**): below **$15K** portfolio value → growth phase, **100% reinvest**, sweeps paused. At/above **$15K** → harvest **20% of weekly profit** every 7 days to Trezor Safe 7. Capital injections continue regardless.

### Fail-closed signing

`TITAN_LIVE_SIGNING_READY=0` until bridge + signing health are real. Then `=1`. If signing is not wired, expect **fail-closed** errors — that is correct. Do not mock-sign on a live profile.

### Ghost RPC / ghost evasion

**Ghost evasion** is the stealth policy: live capital forbids public RPC, public mempool exposure, and unshielded CEX-direct venues. Use private/shielded routes (Erigon on EDGE-FRA, Jito, Flashbots Protect, intent solvers, etc.). Cheat codes you will see: `STEALTH_PUBLIC_PATH`, `STEALTH_UNSHIELDED_VENUE`.

### Verify

`./verify.sh`, `curl :19003/health`, individual port health for `:19001`–`:19008`, quantum off, classical 20 agents only, in-process signing mode confirmed. Do **not** require `:19010` healthy unless you deliberately chose legacy HTTP signing.

### Capital limits (template defaults — verify your deployed file)

Illustrative template knobs: max ~$500 notional per trade, ~$2500 aggregate exposure, ~$2500 declared equity, max ~2% equity per trade, human/BFT path above ~1%, max 4 active pipelines, allocator often still **advisory**. Every position needs a **hard stop-loss** (R16) — mental stops do not count.

### DEX-only posture

Live env examples are explicit: no CEX API keys for the live recon/signing path. CEX names may appear in historical allow-lists; live posture is DEX + shielded routes.

---

## 10. Honest blockers today (plain English)

The control plane is real. Several “last mile” pieces are **not** silently finished by `deploy.sh` or by reading a guide. Do **not** claim the system is ready for capital while these remain.

### Trezor `live_signer` RPC

Even if environment variables point at a Trezor bridge, the live signing RPC may still **raise / fail closed** until `openclaw-trezor-bridge` (or equivalent) is actually installed and the signing health check passes. Arming `TITAN_LIVE_SIGNING_READY=1` without that is theater. Treat wiring as an engineering milestone.

### Recon URL

**Reconciliation** needs a source of position truth. Preferred path: `TITAN_RECON_FETCHER_URL` returning positions JSON. Direct “ask every chain ourselves” aggregation is not fully implemented as a free lunch. Without recon, you can believe a fill that never happened — or miss a fill that did.

### Withdraw / revoke

Capital withdraw / Trezor sweep adapters are often still **mock** until ops wiring. Key revoke at venue may return `revoke_pending` — meaning the software set a flag, but **you** may still need to disable keys in a venue UI until revoke RPC exists. Do not assume “keys_revoked” in a log equals “keys dead everywhere.”

### P22 gated

**P22** is the memecoin trench (Pump.fun lifecycle). It stays catalog / disabled (`memecoin_trench.enabled: false`) until Phase 5 / memecoin YES, Geyser/Jito, live profile flags, and toxicity filters. It is a high-toxicity lane — not a beginner first trade.

### Allocator advisory

`allocator.advisory_mode: true` means the allocator **logs** target weights / envelopes but does not automatically de-fund you into compliance. Set `false` only when you consciously accept automated de-fund behavior.

### Drawdown notify vs halt

Doctrine / AGENTS talk about a 5-tier circuit breaker ladder culminating in halt around 12% drawdown. The **current template** sets `drawdown_notify_only: true` — tiers mostly **notify** (and at high tiers notify critically) while trading may **continue**. Separately, **drawdown velocity** breakers (e.g. losing too many dollars in 60 seconds / 15 minutes) still DENY/HALT. Before live capital, Hyperion must **consciously choose** whether notify-only is acceptable or whether halt-on-tier should be enforced in the *deployed* policy. Do not assume the template matches the doctrine without reading the live file.

### Other residual gaps (short)

Edge PoPs need real WireGuard + bootstrap. AUGUR regime feed may still be file/stub. Agent skills must be code-reviewed so nothing skips `preTradeValidationUrl`. Grafana/BusKill are optional hardening, not substitutes for the kernel.

**Bottom line:** Software controls are **necessary**. Paper/shadow evidence, UPS, live adapters, stealth routes, and explicit YES are what make a go-live decision defensible. Residual risks live in `PRODUCTION_READINESS.md`.

---

## 11. First tiny live trade story (end-to-end, plain language)

Imagine Phase 5 YES is recorded, UPS is proven, signing is truly armed, recon returns real positions, ghost routes are up, evolution is frozen, and you chose one calm lane (say **P5**) — not P22.

**Morning.** You check `:19003` health. Kill switch inactive. Dead-man’s heartbeat OK. Security posture HARDENED. You decide the first trade will be **≤ 0.1% of equity** — maybe a few dollars of notional — with a hard stop attached before submit. Confidence should be ≥ 0.70 or you shrink size.

**Signal.** ORACLE / WRAITH / others produce structured reports. For non-arbitrage lanes, a TradingAgents-style debate may run: bull vs bear, then risk agents argue aggressive vs conservative. This is research theater with schemas — useful, not authoritative.

**Vote.** If size/policy requires it, AUGUR, PREDATOR, and ATLAS cast advisory votes. Two of three say go. GUARDIAN may still advise caution. None of them can force the vault open.

**Gate.** TRENCH-OPS does **not** sign inside the LLM process. It calls ExecutionGate / `titan-safety gate sign`. Reconciliation checks believed vs actual. Risk kernel validates venue, size, stealth, velocity, kill state. Portfolio risk may add VaR/correlation checks. On success: **ALLOW** + fresh **gate receipt**.

**Sign.** In-process `SigningNode` signs only with that receipt. If signing isn’t wired, you get a hard error — good. You fix wiring; you do not invent a bypass flag.

**Broadcast.** The signed payload goes to the best edge PoP (lowest live p50 RTT to the target). Target latency for dispatch is aggressive (on the order of milliseconds). Path must be MEV-shielded per ghost policy.

**After.** Reconciliation confirms the position. TCA records whether you paid a stupid amount of slippage. HERALD may ping Telegram. You watch for unexpected ALLOW-with-kernel-down (bypass bug), recon divergence, velocity trips, stealth DENYs ignored by a buggy skill, UPS on battery, or signing without receipt — any of those → abort immediately (see next section).

**Goal of the first trade:** one tiny real fill (or an intentional DENY) with full observability — **not** profit.

---

## 12. What happens when things go wrong

### HALT / kill switch

Fastest global stop:

```bash
titan-safety kill activate --operator hyperion --reason "live abort"
```

Trades must DENY while active. Resume only with a **signed RESUME** procedure — not a casual chat message.

### Circuit breakers (CB)

A **circuit breaker** is an automatic safety trip — like an electrical breaker that cuts power when current is too high. Examples:

- Loss velocity (too much $ lost too fast) → kernel DENY / HALT
- Drawdown tiers → notify (template) or halt (if you configured doctrine-style halt)
- Kernel unreachable → fail-closed DENY
- Stealth public path / unshielded venue → DENY
- Security lockdown → kill + freeze + signing halt + honeypot posture
- Keys / signing environment compromised → signing halted

### Dead-man’s switch

If operator heartbeat is missing too long (docs: >48h de-risk, >72h flatten), the system should reduce risk without promoting anything. It never promotes on your silence.

### Wind-down / lockdown / flatten / power loss

- **Wind-down safe mode:** controlled de-risk.
- **Security lockdown:** requires operator HMAC — never LLM-alone.
- **Flatten:** close positions; if adapters are incomplete, you may need manual close on a shielded path plus operational key revoke.
- **Power loss:** halt trading, flatten, revoke session keys, require operator ack to resume. Do not discretionary-sign during outage.

### Promotion rollback

Failed promotions revert toward the champion artifact in air-gapped staging. Keep champions.

When in doubt: kill activate, keep signing disarmed, stay paper, leave Phase 5 pending.

---

## 13. Cockpit and CLI: watch without becoming the risk kernel

Your job as operator is **oversight**, not replacing `:19001` with your gut.

**Cockpit** helps you see health, promotions, security, signing status, and manual control. Set HMAC in Settings for mutating calls. Remember soft-fail fixtures. Prefer confirming critical facts with CLI/curl.

**CLI essentials** (conceptual):

- `curl :19003/health` — safety stack pulse
- `titan-safety kill status`
- `titan-safety security status`
- `titan-safety evolution status`
- `titan-safety capital balance`
- `titan-safety memecoin status` — expect disabled until YES
- Portfolio simulate on `:19004` when wired

**Inference reminder:** Tier 1 `:30000` and Tier 2 `:30001` are the live critical/orchestration path. DeepSeek `:30005` and GLM `:30003` are R&D / optional deep votes — never TRENCH-OPS / GUARDIAN live execution brains. No closed/cloud models on live voters.

Analogy: cockpit and CLI are security cameras and intercoms. The vault lock is still the vault lock.

---

## 14. Where to start tomorrow morning

A gentle path — teaching first, ceremony second:

1. **Re-read this file** until brain / body / hands / eyes feels natural.
2. **Skim** `SYSTEM.md` §1–2 and the Bounded Autonomy Matrix in `AGENTS.md`.
3. **Open** `PRODUCTION_READINESS.md` and honestly mark which residual risks you accept vs must fix.
4. **Confirm** safety ports on the host (`:19001`–`:19008` via `:19003`) without enabling capital.
5. **Start or continue paper** on one lane; write a dated paper note each day.
6. **Do not** set `TITAN_LIVE_SIGNING_READY=1`, do not Phase 5 YES, do not enable P22/flash-loans “to see what happens.”
7. When you are ready for checkboxes and copy-paste ceremony commands, switch to:

→ **[`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md)** — the production walkthrough and go-live master checklist.

When in doubt: stay on paper, keep signing disarmed (`TITAN_LIVE_SIGNING_READY=0`), and leave Phase 5 pending.

---

## Closing

Titan’s production posture is **capital-preservation-first**: agents propose, deterministic safety vetoes, Hyperion owns promotion.

This teaching guide exists so you understand *why* the ceremony is long. The companion production guide exists so you can execute the ceremony without inventing steps. Neither document enables live trading in code. Neither document claims blockers are gone.

You are not behind for going slowly. You are operating the system as designed.
