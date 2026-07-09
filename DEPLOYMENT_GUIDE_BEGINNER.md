# TITAN — The Beginner's Guide to Building, Deploying & Going Live

This is the long, plain-English version. If the other guide
(`DEPLOYMENT_GUIDE.md`) is the pilot's pre-flight checklist, this one is the
"how airplanes work and why each step matters" book. I assume you're technical
enough to run commands in a terminal, but I will **not** assume you already know
trading, MEV, systemd, or risk math. I'll explain each idea before I ask you to
do anything with it.

Take your time. Nothing here should be rushed, because at the end of it you are
pointing a computer program at real money and letting it press the buy/sell
button on its own.

---

## First: what is TITAN, really?

TITAN is a **robot trader**. It's a collection of programs ("agents") that watch
crypto markets, decide when to buy and sell, and then actually place those trades
by themselves. The big spec file (`source/TITAN.md`) describes a very ambitious
version: 23 agents, self-improving AI, global servers, fancy quantum stuff.

Here is the honest truth you need to internalize before spending a dollar:

- **Some of the spec is marketing/fantasy.** Model names like "GLM-5.2-753B" and
  income claims like "$356,700/day" are not real. If you build a system that
  *believes* those numbers, it will bet too big and blow up. We will replace
  fantasy with reality everywhere.
- **The dangerous idea in the spec is "full autonomy with no humans."** A robot
  that can rewrite its own safety rules and promote its own money-losing
  strategies, with nobody checking, is how you lose everything. This bundle
  deliberately puts a few human checkpoints back in — not to slow you down, but
  because those checkpoints are the only reason it's ever safe to add more money.
- **The way real trading desks make money is boring and disciplined:** a small
  number of well-understood strategies, executed carefully, sized correctly, with
  ruthless measurement of what's actually working. Not 46 half-baked strategies
  run by an unsupervised AI. This guide points you at the boring, profitable
  version.

The software in this folder (`titan-deploy`) is the **safety and profit
skeleton**: it enforces limits, measures execution quality, decides how much
money each strategy gets, and requires your approval before risky changes. Your
job in this guide is to stand up that skeleton correctly, then feed it real
infrastructure, data, and (eventually, carefully) money.

**A vocabulary starter kit** (we'll expand each later):
- **Agent:** one program with a job (e.g. the "risk" agent, the "execution" agent).
- **Pipeline / lane / strategy:** one way of making money (e.g. "capture funding
  payments," "grab liquidations"). I use these words interchangeably.
- **Live capital:** real money that can really be lost. The opposite is **paper**
  (pretend money) and **shadow** (real market, but no money committed).
- **Circuit breaker:** an automatic "STOP" rule, like the breaker in your home's
  electrical panel that trips before a fire starts.
- **Fail-closed:** when something breaks, the safe default is "do nothing / deny
  the trade," not "keep trading and hope." A door that locks when the power goes
  out is fail-closed.

---

## 1. Hardware & Compute Infrastructure Requirements

**What this section is about:** the physical computers TITAN runs on, and the
electricity that keeps them alive.

**Why it matters:** TITAN thinks using large AI models, which need powerful
graphics cards (GPUs). It also needs to hold the keys to your money extremely
securely, and it must never be caught mid-trade by a power cut. Weak hardware =
slow/bad decisions. Weak power/security = lost funds.

### The computers you need

1. **TITANHOME — the brain (required).** This is your main, powerful computer.
   It runs the AI models and all the safety programs.
   - **CPU (the general worker):** a high-core-count workstation chip. The spec
     dreams of a 64-core Threadripper PRO; realistically, aim for at least 32
     cores. More cores = more things happening at once (simulating trades,
     crunching data).
   - **GPU (the AI muscle):** this is the expensive part. AI models live in the
     GPU's memory ("VRAM"). The spec wants two huge cards (192 GB VRAM total).
     Realistic minimum to run a serious local model *and* simulate trades:
     roughly **48–96 GB VRAM**. If you have less, you either run a smaller AI
     model or rent AI online (Section 4) — but don't kid yourself that a tiny
     model is running a hedge fund.
   - **RAM (short-term memory):** 256 GB ideal, 128 GB minimum.
   - **Storage (disk):** two fast NVMe SSDs — one for the operating system and
     models, one for logs and records. Turn on **full-disk encryption** (so if
     the drive is stolen, the data is scrambled and useless).

2. **TITANSPARK — the helper (recommended).** A smaller computer that runs
   lighter AI tasks and acts as a backup way for you to talk to the system. It
   also lets you run a **second, different AI model** for double-checking risky
   decisions (more on why that matters in Section 4).

3. **The signing node — the money-key vault (required before real money).** A
   *separate, locked-down* computer whose only job is to cryptographically
   "sign" (approve) transactions that move money. Think of it as a safe bolted to
   the floor in a back room: nothing else runs on it, it has no web browsing, and
   the main AI can only slip a request under the door — it can never walk in and
   grab the keys.

4. **The vault node (required).** A small, always-on computer (the spec uses a
   Mac Mini) that handles your hardware wallet (a Trezor — a physical USB device
   that holds crypto keys) and the weekly "move profits to cold storage" step.

### Power — the part beginners skip and regret

- **UPS = Uninterruptible Power Supply.** It's a big battery between the wall and
  your computer. If the power flickers or dies, the UPS keeps the machine running
  for a few minutes so it can shut down cleanly.
- **Why it's a hard requirement:** imagine TITAN is halfway through a trade when
  the power cuts. It might think it sold something it didn't, and then act on
  wrong information — that's real money gone. So the rule is: **no UPS, no real
  money.** You need a UPS (at least 3000 VA, 15+ minutes of runtime) on the brain,
  the signing node, and the vault.
- The software already knows this: the risk rules say "on power loss →
  `halt_trading`, flatten all positions, revoke the money-keys." The verify step
  checks that a file literally says `live_capital_requires_ups: true`.

### GPU scheduling (sharing the AI muscle)

The same GPU is used for making live decisions *and* for background chores
(training, testing). The rule (`gpu_schedule.yaml`) is: **live decision-making
always wins.** Background chores must pause instantly when a real trade decision
needs the GPU. You never want the robot to be "thinking about yesterday's
homework" when it should be reacting to the market now.

---

## 2. Networking, Edge Mesh & Latency Requirements

**What this section is about:** how TITAN connects to the internet and to the
crypto exchanges, and how fast that connection is.

**Why it matters:** in trading, speed and reliability of your connection can be
the difference between profit and loss. But — importantly — **you can't win the
pure speed race**, so we'll aim your effort where speed matters *enough*.

### "Edge mesh" and "PoP" — start with ONE

- A **PoP** ("Point of Presence") is just a server in a specific city that sits
  close to an exchange to reduce delay. The spec wants 5 of them worldwide.
- **Beginner rule: launch with exactly one** — the one called **EDGE-FRA** (in
  Frankfurt, near a lot of crypto infrastructure). Running 5 servers on day one
  is 5× the things that can break and 5× the ways to get hacked, for basically no
  early benefit. The config is already set to `single_pop` / `EDGE-FRA`. Add more
  PoPs later, only if you prove a strategy genuinely needs them.

### The internet connection

- Get a business-grade fiber connection, and have a **backup** (a second provider
  or a 5G modem). If your one connection dies mid-day, you want the system to fail
  safe, not trade blind.
- Internally, the programs talk to each other over a lightweight message bus
  called **NATS** (`nats://localhost:4222`). You don't need to deeply understand
  it; just know it's the internal "chat channel" between agents.

### "Latency" — and being honest about speed

- **Latency** = delay. "Sub-millisecond" means "less than a thousandth of a
  second." Some trading strategies are pure speed races: whoever's computer
  reacts first wins, and everyone else loses money on that trade.
- **Hard truth:** professional firms (Jump, Wintermute) spend fortunes to be the
  fastest. You will not out-run them. So **don't fund strategies whose only edge
  is being fastest.** Instead, fund strategies that *react* to things that already
  happened — like grabbing a liquidation or backrunning a big swap — where being
  "fast enough" is plenty.

### Private order flow (don't get front-run)

- On public crypto networks, when you broadcast a trade, bots can see it and jump
  ahead of you ("front-running"), making your trade worse. The fix is to send
  trades through **private channels** (Flashbots Protect, Jito) that hide them
  until they execute.
- Rule: for any MEV/DEX strategy, **always** use private submission. There's a
  circuit breaker (`CB_MEV_LEAK`) that must **stop trading** if it detects your
  orders leaking to the public — not just write a note about it.

---

## 3. Operating System & Base Software Environment

**What this section is about:** the foundational software on the computer, and
the exact commands to build and install TITAN.

**Why it matters:** a clean, predictable base makes everything else reliable. This
is also where you'll spend your first hands-on hour.

### The operating system

- Use **Linux** (Ubuntu 24.04 LTS or Debian 12 are safe choices). It's what this
  software is built for.
- Create a **dedicated user account** just for TITAN (call it `titan`). Never run
  the trading software as the "root" (all-powerful admin) user — if something goes
  wrong or gets hacked, you want the damage contained.

### Base tools to install

You need: Python 3.12, `git`, `curl`, `jq` (a JSON viewer), plus the NVIDIA GPU
driver and CUDA (the software that lets programs use the GPU). Match the CUDA
version to your specific GPU. You'll also want Node.js/npm (for the "OpenClaw"
runtime) and pip (for the "Hermes" runtime).

### Building and installing TITAN, step by step

Open a terminal in the `titan-deploy` folder and run these **in order**. I'll
explain each.

```bash
# 1) Create an isolated Python environment ("venv") so TITAN's Python packages
#    don't collide with the rest of your system, then install its dependencies.
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2) Run the automated tests. This proves the safety code works BEFORE you rely
#    on it. You should see something like "97 passed".
.venv/bin/python -m pytest tests -q

# 3) "Dry run": show what WOULD be installed and where, without changing anything.
#    Read the output so there are no surprises.
./deploy.sh --dry-run

# 4) Actually install. This copies the built files into two hidden folders in your
#    home directory: ~/.openclaw (the main system) and ~/.hermes (a helper).
./deploy.sh --install-packages

# 5) Install the "systemd services" (explained below), which requires admin rights.
./deploy.sh --systemd

# 6) Put your secrets (bot token, etc.) into the .env file, then run the full
#    verification. It must end with "Verification PASSED".
$EDITOR ~/.openclaw/.env
./deploy.sh --verify
```

**What is `systemd`?** It's Linux's "service manager" — the thing that keeps
programs running in the background and automatically restarts them if they crash.
TITAN's safety programs (risk checker, allocator, etc.) are installed as systemd
services so they're always on. You don't have to babysit them.

**What does `--verify` actually do?** It's your safety inspector. It checks that
all the important files exist, the config has the safe settings (fail-closed,
no-auto-promote, UPS-required), runs the test suites, and runs "attack
simulations" (the adversarial and chaos harnesses). If it says **FAIL** anywhere,
**stop and fix it** — do not continue.

### One golden rule about editing files

There are three copies of things, and you must edit the right one:
- **`templates/`** = the *source*. **Edit here.**
- **`output/`** = auto-generated by the build. **Never edit** (it gets overwritten).
- **`~/.openclaw/`** = the *installed* copy. **Never edit by hand** (redeploy
  instead).

After editing anything in `templates/`, run `./deploy.sh --build` to regenerate
`output/`, then redeploy. Keep everything in git so you can undo mistakes.

---

## 4. LLM Inference & Model Serving Setup

**What this section is about:** the actual AI "brains" TITAN uses to reason, and
how to run them.

**Why it matters:** the quality and honesty of these models drives every decision.
Beginners often trust the model too much — we'll set it up so the model *advises*
but hard limits are enforced by dumb, reliable code.

### "LLM" and "inference" in plain terms

- **LLM** = Large Language Model — the kind of AI that reads and writes text and
  can reason (like the assistant you're talking to now).
- **Inference** = actually running the model to get an answer (as opposed to
  *training* it, which is teaching it).
- **Serving** = keeping a model loaded and ready to answer requests quickly.

### Use REAL models

The spec's model names are made up. Pick **real, currently available** models that
fit in your GPU's VRAM: a strong "big" model for the important reasoning
(orchestration and risk), and a smaller, faster model for routine chores
(sorting/labeling). Write down the exact model name and version — TITAN records
this "fingerprint" in its logs so you always know which brain made which decision.

### How to serve them

- Run the models locally using a serving tool like **vLLM**, **SGLang**, or
  **llama.cpp server**. They expose a local web address (URL) that TITAN calls.
- Put the "big" model on TITANHOME's GPU and the "small" model on TITANSPARK.
- In the config, set two important URLs so the system checks with the safety
  programs before every trade: `preTradeValidationUrl` (the risk checker) and
  `portfolioRiskUrl` (the portfolio risk checker).

### The "everyone agrees because they're the same person" problem

The spec brags about "BFT 2-of-3 voting" — three agents vote, majority wins,
sounds safe. **But in the spec all three use the same AI model.** That's like
asking one person the same question three times and calling it a committee. If the
model is wrong, all three are wrong *together*, and the system feels *more*
confident about a bad trade.

- Fix: run your **second risk-checker on a genuinely different model** (on
  TITANSPARK). Then a disagreement actually means something.
- Until you do that, treat the **deterministic risk kernel** (plain, non-AI code
  with hard limits) as the *real* authority — not the AI vote.

### Make it predictable

For risk and execution decisions, run the model at low "temperature" (less
randomness) so it behaves consistently. And if the model is slow or times out, the
system must **deny the trade**, never "go ahead anyway." The risk kernel doesn't
even read the model's words — it just enforces numeric limits no matter what the
model says. That's a feature: the dumb code can't be talked into a bad trade.

---

## 5. Security, Key Management & Hardening (Critical)

**What this section is about:** protecting the keys to your money and locking down
the machines. This is the section where mistakes are permanent.

**Why it matters:** in crypto, whoever holds the keys holds the money. If keys
leak, funds are gone instantly and irreversibly. There is no "call the bank."

### Keys, wallets, and the golden separation

- A **private key** is the secret that controls a crypto wallet. A **hardware
  wallet** (Trezor) keeps that secret on a physical device that never exposes it
  to the computer.
- **The golden rule:** the AI/trading programs must **never** be able to withdraw
  your money. Withdrawal keys live only on the hardware wallet / signing node. The
  trading programs get **session keys** — temporary, limited permissions (e.g.
  "can place trades on this exchange, cannot withdraw"), which auto-expire and get
  revoked automatically on any emergency.
- **Exchange API keys** (the credentials that let software use your exchange
  account) must be set to **trade-only with withdrawals disabled**, and locked to
  your server's IP address.

### Signing isolation (the safe in the back room)

All money-moving transactions are approved on the isolated **signing node**
(`:19010`). The trading programs send a request; the signing node checks it and
signs — and it will **refuse to "blind sign"** (approve something it can't
verify). If the signing environment looks compromised, it halts all signing. This
means even a fully hacked AI can't drain the wallet directly.

### Hardening the machines (basic hygiene, big payoff)

- Full-disk encryption on. SSH login by key only (no passwords). Firewall set to
  **deny by default**, allowing only the exact exchanges/data sources you use.
- The safety programs only listen on `127.0.0.1` (localhost) — meaning they're not
  reachable from the internet, only from the machine itself.
- Secrets go in `~/.openclaw/.env` (locked to your user, permissions `0600`), never
  in git, and get rotated periodically.

### Kill switches (the big red buttons) — practice these

You need multiple ways to instantly stop everything, and they must work even if
other parts are broken:
- **Software kill switch:** one command halts all trading; there are also
  portfolio-wide and per-strategy versions. They "fail closed" — when active, the
  risk kernel denies every trade.
- **Remote kill:** a cryptographically **signed** command so you can safely halt
  the system from your phone anywhere.
- **Hardware kill:** a "BusKill" USB cord — yank it out and the machine locks/halts.

Practice it now, before real money:
```bash
~/.openclaw/safety/bin/titan-safety kill activate --operator YOU --reason drill
~/.openclaw/safety/bin/titan-safety kill status      # should show active
~/.openclaw/safety/bin/titan-safety kill deactivate --operator YOU --signed "$(~/.openclaw/safety/bin/titan-safety kill sign --command RESUME --operator YOU)"
```

### Turn OFF the "quantum" and self-rewriting features for now

- The "quantum" features in the spec do nothing useful for live trading and just
  add risk. They must be **dormant** (off), and the related skills are moved to an
  archive folder. Use that GPU power for useful simulation instead.
- **Self-modification containment:** the AI is forbidden from editing its own
  safety rules, risk limits, or the core "constitution" files (`SOUL.md`,
  `iron-laws.md`, the risk kernel, execution code). This is enforced in code and
  tested with attack simulations. A robot that can loosen its own seatbelt is not
  one you leave alone with your money.

---

## 6. Capital Requirements & Phased Deployment Plan

**What this section is about:** how much money to start with, and the disciplined
schedule for adding more.

**Why it matters:** the #1 way beginners blow up is adding money too fast, before
they've *proven* the system actually makes money after costs. We scale by
evidence, not hope.

### Do NOT fund yet

Real money comes **after** everything in Sections 1–5 and 8–12 is green and
`--verify` passes. Until then, the money "adapter" stays on `mock` (pretend).

### How much to start with

- **$2,500–$10,000.** Big enough that real trading costs (fees, gas, slippage)
  show up honestly and you get enough trades to judge a strategy; small enough
  that a bug or bad day is a lesson, not a catastrophe.

### The phased plan (walk before you run)

Your operator directive set each phase to **2 days**. Be honest with yourself:
that's *aggressively short* — real validation (seeing how strategies behave across
different market moods) takes weeks. The software won't auto-advance; you still
have to pass every gate. Treat 2 days as a floor, not a target.

| Phase | Money | What you're doing | You may advance only when… |
|-------|-------|-------------------|----------------------------|
| **0 — Setup + Paper** | $0 | Everything running; trading with pretend money; watching execution-quality scorecards | Test/attack harnesses green; you've drilled the kill switch; every strategy has a scorecard |
| **1 — Micro-live** | $2.5–10K | Tiny real trades (≤0.1% of equity each); the allocator only *suggests* sizes | Each strategy passes the statistical evidence gate + you personally approve it; drawdown under 5%; the system's records match the exchange exactly |
| **2 — Validated scale** | $10–50K | Allocator now *enforces* sizing within your limits; live record-matching on | 48 hours of perfect record-matching; no "bleeding" strategy is funded; AI drift under control |
| **3 — Mature** | $50K+ | Fund only proven strategies; start moving profits to cold storage once ≥ $15K | You sign off; you've rehearsed the emergency playbooks |

### Handling money with the built-in ledger

```bash
titan-safety capital deposit --amount 2500 --asset USDC   # record a deposit
titan-safety capital balance                              # see balance
titan-safety capital verify-audit                         # confirm records untampered
titan-safety capital sweep --weekly-profit <usd>          # move a slice of profit to cold storage
```

Every deposit/withdrawal is written to a tamper-evident log (a "hash chain" —
if anyone edits history, the check fails).

### Who decides position sizes?

- **You** set the overall risk "envelope": the maximum total exposure, the cap per
  strategy, and how aggressive the sizing math is. Think of it as setting the speed
  limit.
- **The allocator** then drives *within* that limit, giving more money to
  strategies that are actually working and less to those that aren't.
- Changing the envelope (more leverage, bigger caps) is a **human-approved** action
  — the robot can't quietly raise its own speed limit.

---

## 7. Data Feeds, APIs & External Dependencies

**What this section is about:** the information TITAN needs (prices, market data)
and the accounts it needs to place trades.

**Why it matters:** garbage in, garbage out. Slow or wrong data leads to bad or
losing trades. And you only need data for the *few* strategies you actually run.

### The kinds of data/connections

- **Blockchain data (required):** ideally run your **own node** (a program that
  keeps a full copy of a blockchain) — "Erigon" for Ethereum-style chains, plus a
  Solana connection. Your own node is faster and more reliable than shared public
  ones, which rate-limit you at the worst moments.
- **"Mempool" feeds:** the mempool is the waiting room where transactions sit
  before they're finalized. Seeing it early is how MEV/liquidation strategies work
  (via Flashbots MEV-Share for Ethereum, ShredStream for Solana).
- **Exchange/venue accounts (one per strategy you fund):** e.g. Hyperliquid/dYdX
  for funding strategies; Uniswap/Curve for swaps; Aave/Morpho for liquidations.
  **Only set up feeds for the ~6 strategies you actually fund** — not all 46.

### Treat every feed as something that can fail

- Each data source needs a **health check** and a **fallback**. If a price feed
  goes stale or crazy, the affected strategy should pause — not the whole system,
  and definitely not "trade on the bad number."
- **Bridges** (which move assets between blockchains) are the single biggest
  source of crypto hacks. Rule: if a bridge's safety score is low, don't use it.

---

## 8. Testing, Validation & Pre-Live Pipeline Requirements

**What this section is about:** proving a strategy is genuinely good *before* it
touches real money.

**Why it matters:** almost any strategy can look amazing on past data by luck or
by accidental cheating ("overfitting"). This section is your lie-detector.

### The automated safety tests

```bash
.venv/bin/python -m pytest tests -q                      # unit tests (should all pass)
# Attack simulations (should say all scenarios passed):
PYTHONPATH=templates/safety .venv/bin/python tests/adversarial/adversarial_harness.py
PYTHONPATH=templates/safety .venv/bin/python tests/chaos/chaos_harness.py
```
The **adversarial** harness pretends to be an attacker (poisoned data, prompt
injection, trying to edit SOUL.md). The **chaos** harness simulates things
breaking (crashes, market shocks). Both must pass.

### The journey every strategy must complete

1. **Backtest** — test it on historical data, but **with realistic costs** (fees,
   gas, slippage). A backtest with zero costs is a fairy tale.
2. **Paper** — run it live on today's market with pretend money.
3. **Shadow** — run it against the real market through private channels, but don't
   actually commit money; this checks the edge is real *right now*.
4. **Micro-live** — tiny real trades (≤0.1% of equity), with a text alert on every
   trade and the kill switch armed.
5. **Statistical evidence gate** — the math lie-detector (next).
6. **Your explicit "YES"** — a human approval that is recorded. If you don't
   answer, the default is **no** (it holds/de-risks; it never assumes yes).

### The statistical evidence gate (the lie-detector), explained

The old spec promoted a strategy if it had a Sharpe ≥ 0 over just 20 trades. That
is basically "it didn't obviously lose over a tiny sample" — worthless. We replaced
it with real statistics:

- **Sharpe ratio:** reward per unit of risk. Higher is better. But a high Sharpe
  over few trades can be pure luck.
- **PSR (Probabilistic Sharpe Ratio):** the probability that the *true* skill is
  above zero, accounting for how noisy the returns are. We require ≥ 90%.
- **Deflated Sharpe Ratio (DSR):** the key one. If you try 1,000 strategies, some
  will look great by chance alone — like flipping 1,000 coins and celebrating the
  one that landed heads 10 times. DSR *penalizes* results for how many strategies
  you tried, so you can't fool it by mining lots of ideas. We require ≥ 90%.
- **At least 200 real trades**, **costs must be modeled**, **net profit after all
  costs must be positive**, and the **live results must match the backtest within
  15%** (if live behaves totally differently from the test, the test was a lie).

You can run it yourself:
```bash
titan-safety promotion-stats --stats '{"strategy_id":"P5","returns":[...],
  "trials":5,"num_trades":500,"gross_bps":18,"cost_bps":4,
  "backtest_sharpe":1.8,"shadow_sharpe":1.75}'
# exit code 0 = passed. With no evidence at all, the promotion is refused outright.
```

### Execution-quality check (TCA), explained

**TCA = Transaction Cost Analysis.** After trades happen, this measures whether you
*actually* made money after the real-world frictions:
- **Slippage:** the difference between the price you expected and the price you got.
- **Gas/tips:** fees you pay to get transactions processed/prioritized.
- **Fill rate:** how often your attempted trades actually complete vs. fail.
- **Tip efficiency:** what fraction of your profit you're paying away in tips (if
  it's over 40%, the strategy is "bleeding").

It produces a scorecard per strategy with a verdict: **HEALTHY**, **MARGINAL**, or
**BLEEDING**. Don't put more money into a BLEEDING strategy.
```bash
curl -s -X POST http://127.0.0.1:19007/v1/scorecard -d '{"pipeline_id":"P29"}'
```

---

## 9. Monitoring, Observability & Alerting Stack

**What this section is about:** being able to *see* what TITAN is doing, and being
*told* immediately when something important happens.

**Why it matters:** a trading robot you can't watch is a robot you can't trust.

### Health at a glance

Every TITAN safety/profit program answers a `/health` question, and one program
(the **status aggregator** at `:19003`) collects them all:
```bash
curl -s http://127.0.0.1:19003/health | jq
```
The programs and their "phone numbers" (ports):
- `19001` risk kernel (the trade approver)
- `19002` reconciliation (record-matcher)
- `19003` status aggregator (the dashboard)
- `19004` portfolio risk (whole-portfolio danger check)
- `19005` dead-man's switch (are-you-still-there check)
- `19006` **allocator** (who gets how much money)
- `19007` **TCA** (execution-quality scorecards)
- `19010` signing node (money-key approver)

### Metrics and dashboards

- Each program also exposes `/metrics` in a format that **Prometheus** (a metrics
  collector) understands, which you view in **Grafana** (a dashboard tool). There's
  a starter dashboard config in `playbooks/observability_grafana_stub.yaml`.
- Watch numbers like: how much total exposure you have, how much of your risk
  budget is used, how many strategies are "bleeding," and your portfolio's
  worst-case daily loss estimate (VaR).

### Logs and the audit trail

- All programs write structured logs. Critically, there's a **hash-chained decision
  log**: every important decision is recorded with a fingerprint of exactly which
  AI model/settings made it, in a way that can't be secretly altered. Copy these
  logs to another machine so they survive even if this one dies.

### Alerts (get told, don't go looking)

Set up Telegram alerts for anything that matters: every significant trade, every
blocked trade, drawdown warnings, record mismatches, a "bleeding" strategy, and
"are you alive?" reminders. These must reach a human 24/7.

---

## 10. Risk Management & Circuit Breaker Validation

**What this section is about:** the automatic rules that stop losses from spiraling.

**Why it matters:** this is the seatbelt-and-airbags system. It's what stands
between "a bad day" and "account wiped out."

### The independent risk kernel (the bouncer)

- The **risk kernel** is a plain, non-AI program that every trade must pass
  through, like a bouncer at a door. It enforces hard numeric limits: max size per
  trade, max total exposure, max leverage, how fast you're allowed to lose money
  (loss "velocity"), max number of open positions, max slippage, and an allow-list
  of approved exchanges/contracts.
- It is **fail-closed**: if the risk kernel is unreachable, **all trades are
  denied**. Test this by stopping it and confirming trades get denied (not waved
  through), then restart it.

### Portfolio-level risk (the whole-picture check)

- Individual trades can each look fine but together be dangerous (e.g. all secretly
  betting on Ethereum going up). The **portfolio risk** program (`:19004`) checks
  the whole book: worst-case loss estimates (VaR/CVaR), limits on how much can be in
  correlated strategies at once, and it shrinks your allowed exposure in scary
  market "regimes."

### Drawdown handling (stepping on the brakes gradually)

**Drawdown** = how far you're down from your peak. Instead of trading full-speed
until a cliff, TITAN eases off:
- The allocator's **de-grossing ladder** starts cutting exposure early (down 3% →
  use 75% of budget; 5% → 50%; 7% → 25%; 10% → 0%), while keeping market-neutral
  income strategies running.
- The kernel's hard tiers (2/5/8/10/12% in a day) escalate from "alert you" to
  "pause new entries" to "cut 50%" to "full halt and close everything."
- And remember: power loss = immediate halt + close positions + revoke keys.

### Prove the brakes work

Run the adversarial harness and confirm scenarios like "poisoned data → trade
denied," "someone tries to edit SOUL.md → blocked," and "sudden crash → velocity
breaker halts trading" all pass. Don't trust brakes you haven't tested.

---

## 11. Self-Improvement & Agent Evolution Safety Controls

**What this section is about:** TITAN's ability to "improve itself," and how to keep
that from becoming a self-inflicted disaster.

**Why it matters:** a system that rewrites itself while trading your money is
thrilling and terrifying. We keep the thrill and remove the terror by making all
self-improvement happen in a **sandbox** with humans on the final button.

### What "evolution loops" are

The spec has many self-improvement systems (with names like DGM-H, GEPA, HyEvo,
SIA). In plain terms, these are programs that try to invent better strategies or
tweak the AI. Left unchecked, they'll "learn" to game whatever score you give them
and deploy junk to live money.

### The safety rules (non-negotiable)

1. **Shadow-only by default:** all evolution runs in an isolated "staging" area
   with **no ability to place real orders**. It can only *suggest* improvements.
2. **No live self-editing of code:** a suggestion becomes real only by going
   through the same testing journey (Section 8) *and* your explicit approval. The
   core safety files can **never** be self-edited.
3. **Risk settings are frozen** to these loops: they may tweak minor things (like a
   signal threshold), never the risk limits or how big to bet.
4. **One change at a time:** make a change, let it "bake," measure it with TCA and
   attribution, then consider the next. Don't let ten experiments run into your
   live money at once.
5. **Automatic de-funding on decay:** if a live strategy's edge fades, the system
   pulls its money back and tells you — it doesn't quietly keep feeding a dying
   strategy.
6. **Fingerprinted rollback:** every deployed brain/strategy is tagged; if it
   causes an outsized drawdown, the system instantly reverts to the previous
   known-good version.

---

## 12. Operational Procedures & Human Oversight Model

**What this section is about:** the day-to-day division of labor between you and the
robot.

**Why it matters:** the right amount of human oversight is what makes high autonomy
*safe*, which is what lets you add more money. Too little oversight isn't "more
freedom" — it's "more ways to lose everything."

### Bounded autonomy (freedom inside a fence)

- The config defines a clear split: things the robot may do **automatically**
  (place normal trades within limits) vs. things that **require a human**
  (promoting a strategy, changing risk limits/leverage, moving to a bigger capital
  tier, turning on flash loans).
- Picture a dog on a long leash in a big yard: lots of freedom to run, but a fence
  it cannot cross without you opening the gate.

### "If you don't answer, the answer is NO"

- The dangerous spec idea was "if the operator doesn't respond, auto-approve." We
  flipped it: **TIMEOUT = hold/de-risk.** Your silence is never a yes. This is
  written into the config and the SOUL/USER files and checked by `--verify`.

### The dead-man's switch (are you still there?)

- You must "check in" at least every 48 hours (a heartbeat). Miss it → the system
  de-risks; after 72 hours → it closes everything. It never uses your absence as an
  excuse to do something risky.
```bash
titan-safety heartbeat --operator YOU     # schedule this (e.g. a daily cron job)
```

### Your daily and weekly routine

- **Daily:** glance at the health dashboard, review overnight trades and any blocked
  trades, look at the execution scorecards, and set today's risk envelope.
- **Weekly:** decide which strategies to promote, whether to increase capital, do
  the profit sweep, and review any incidents.

### Runbooks (pre-written emergency instructions)

The `playbooks/` folder has step-by-step guides for emergencies (kill switch,
drawdown breach, winding down, red-team checklist). **Rehearse each at least once**
before you scale up — the middle of a crisis is the wrong time to read instructions
for the first time.

---

## 13. Legal, Regulatory, Tax & Compliance Requirements

**What this section is about:** staying on the right side of the law and the
taxman. **This is not legal advice** — hire professionals.

**Why it matters:** autonomous crypto desks are more often killed by legal/tax/ban
problems than by the market. Ignoring this section can undo all your profits and
worse.

### Get professionals first

Before real money, talk to **a crypto-literate lawyer and accountant**. Ask whether
your activity triggers money-transmission, VASP, or fund-management rules where you
live, and whether you should trade through a company rather than personally.

### Strategies that are FORBIDDEN here

The spec includes manipulative strategies — things like faking market signals
("liquidity mirage"), deliberately trading against retail users, shady "dark
intelligence," and front-running token unlocks. **These are disabled and must stay
disabled.** Beyond being unethical, they carry catastrophic risk: frozen funds,
exchange bans, and legal liability that can wipe out everything at once. Normal
MEV/arbitrage is generally tolerated; manipulation is not.

### Behave well with venues

Keep your order flow private, don't spoof or wash-trade, and respect each
exchange's terms of service — they can revoke your API keys and freeze your account
if you break the rules.

### Taxes and records

- TITAN includes a **tax ledger** (`capital/tax_ledger.py`) that tracks your buys/
  sells in FIFO order and exports a CSV for your accountant. Reconcile every trade.
- The tamper-evident decision logs, approval records, and capital ledger are also
  your evidence for compliance and taxes. Keep them.

---

## 14. Performance Benchmarking & Success Criteria

**What this section is about:** how to judge, with numbers, whether TITAN is truly
succeeding — and only then give it more money.

**Why it matters:** "it feels like it's working" is how people lose money slowly.
We use hard, honest metrics.

### Every promotion and capital increase must clear ALL of these (per strategy):

- **Deflated Sharpe ≥ 0.90** and **PSR ≥ 0.90** — statistically real skill, not luck.
- **Positive net profit after ALL costs** (the TCA "net_bps" number).
- **Tip efficiency ≤ 40%**, **fill rate ≥ 80%**, and TCA verdict is not BLEEDING.
- **Live results match the backtest within 15%.**
- **The edge still works at the bigger size** (TCA "capacity pressure" isn't rising
  — some strategies stop working once you trade more).
- **The edge isn't fading** (decay slope not negative).
- **It's not too correlated** with what you already run.
- Healthy **Sortino/Calmar** (other reward-vs-risk measures) and a **max drawdown**
  and **recovery time** you can stomach.

### At the whole-portfolio level

You want steadily compounding equity, drawdowns that stay inside the de-grossing
ladder, sensible allocator usage (fractional-Kelly — betting a *fraction* of the
mathematically "optimal" amount, because full-optimal is too wild), no single
strategy or cluster over its cap, and your market-neutral income strategies earning
even during rough patches.

### What to ignore

Ignore the spec's fantasy targets like "$2,500 → $1M in 90 days." Chasing a fantasy
number makes you bet too big. Aim for **high but realistic** risk-adjusted returns
and let compounding do the slow, powerful work.

**One note on "Kelly," since it appears everywhere:** the Kelly formula tells you
the theoretically "growth-optimal" bet size. In the real world it's too aggressive
(one bad streak can ruin you), so professionals bet a *fraction* of it (we use 1/4).
TITAN's allocator does this automatically inside your risk envelope.

---

## 15. Final Go-Live Checklist

Only flip to real money when **every single box** is true. Print this. Tick it
honestly.

**Infrastructure & power**
- [ ] Brain (TITANHOME), signing node, and vault are set up; real AI models
      actually run locally.
- [ ] UPS installed on all three; you did a power-loss drill and the system halted
      correctly.
- [ ] GPU scheduling ensures live decisions are never starved by background jobs.

**Software & configuration**
- [ ] `./deploy.sh --verify` ends with **Verification PASSED**.
- [ ] Unit tests, adversarial harness, and chaos harness all pass.
- [ ] All services show healthy at `http://127.0.0.1:19003/health` (including
      allocator `:19006` and TCA `:19007`).
- [ ] Quantum features dormant; related skills archived.

**Security**
- [ ] Money-signing is isolated on `:19010`; blind-signing is refused.
- [ ] Withdrawal keys are NOT accessible to the trading programs; exchange keys are
      trade-only with withdrawals disabled.
- [ ] You've drilled the software, remote (signed), and hardware kill switches.
- [ ] Fail-closed verified: with the risk kernel stopped, trades are denied.

**Risk & autonomy**
- [ ] TIMEOUT = hold/de-risk (never auto-approve) everywhere.
- [ ] The autonomy fence (auto vs. human-required) is configured; risk settings are
      frozen against the self-improvement loops.
- [ ] All self-improvement runs shadow-only with no order authority.
- [ ] Drawdown tiers and the de-grossing ladder tested.
- [ ] Dead-man's switch tested; your heartbeat check-in is scheduled.

**Evidence & money**
- [ ] Every live strategy passed the statistical evidence gate (DSR/PSR/costs/
      shadow-match/≥200 trades) **and** has your recorded YES
      (`titan-safety promotion verify-audit`).
- [ ] No BLEEDING strategy is funded.
- [ ] Live record-matching (reconciliation) is on with 48 hours of zero mismatches.
- [ ] Capital deposited through the ledger; `capital verify-audit` is valid; the
      profit sweep is set up.

**Compliance**
- [ ] A lawyer and accountant have reviewed your setup and tax treatment.
- [ ] Forbidden manipulative strategies are disabled and stay disabled.
- [ ] Monitoring and off-machine log backups are running; 24/7 alerts reach you.

> When — and truly only when — every box is ticked: start at Phase 1 with small
> money, keep yourself in the loop for promotions and the daily risk envelope, and
> let TITAN trade inside the fence you built. Then scale up **slowly, by evidence,
> one careful step at a time.** That patience is the actual edge. Rushing is how
> beginners turn a good system into a bad story.
