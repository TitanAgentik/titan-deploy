# Titan Agentik — Complete Setup Guide (Beginner Edition)

**From TITANHOME BIOS to your first paper trade, then carefully to live capital.**

This document is a single, start-to-finish walkthrough for standing up **Titan Agentik** — the crypto control plane and autonomous trading stack in this repository. It assumes you can use a terminal and follow instructions, but **does not** assume you already know systemd, MEV, or exchange APIs.

If you want a shorter technical checklist, see `DEPLOYMENT_GUIDE.md`. If you want philosophy and “why each rule exists,” see `DEPLOYMENT_GUIDE_BEGINNER.md`. **This guide is the chronological recipe:** do step 1, then step 2, all the way through verification and optional live capital.

---

## Table of contents

1. [What you are building](#1-what-you-are-building)
2. [Hardware you need](#2-hardware-you-need)
3. [Before first power-on — physical assembly](#3-before-first-power-on--physical-assembly)
4. [PiKVM — control the machine without a monitor](#4-pikvm--control-the-machine-without-a-monitor)
5. [TITANHOME BIOS — complete checklist](#5-titanhome-bios--complete-checklist)
6. [Install Ubuntu on TITANHOME](#6-install-ubuntu-on-titanhome)
7. [Wire your home network (LAN)](#7-wire-your-home-network-lan)
8. [GPU drivers and post-install](#8-gpu-drivers-and-post-install)
9. [Bring up the other machines](#9-bring-up-the-other-machines)
10. [UPS and power-loss drill](#10-ups-and-power-loss-drill)
11. [Time sync (GPSDO + chrony)](#11-time-sync-gpsdo--chrony)
12. [Build and deploy the software](#12-build-and-deploy-the-software)
13. [Secrets file — every variable explained](#13-secrets-file--every-variable-explained)
14. [Data providers — everything you need to subscribe to](#14-data-providers--everything-you-need-to-subscribe-to)
15. [Download AI models and start inference](#15-download-ai-models-and-start-inference)
16. [Start safety services (the non-negotiable core)](#16-start-safety-services-the-non-negotiable-core)
17. [Message bus, chain nodes, and edge servers](#17-message-bus-chain-nodes-and-edge-servers)
18. [Telegram and operator notifications](#18-telegram-and-operator-notifications)
19. [Titan Agentik web UI (Crypto Dashboard)](#19-titan-agentik-web-ui-crypto-dashboard)
20. [Paper trading — prove it works with fake money](#20-paper-trading--prove-it-works-with-fake-money)
21. [Promotion and going live (human gates)](#21-promotion-and-going-live-human-gates)
22. [Phased capital plan](#22-phased-capital-plan)
23. [Daily operator routine](#23-daily-operator-routine)
24. [Troubleshooting common failures](#24-troubleshooting-common-failures)
25. [Master checklists](#25-master-checklists)

---

## 1. What you are building

**Titan Agentik** is not one program — it is a **stack**:

| Layer | What it does | Plain English |
|-------|----------------|---------------|
| **Agents** | 23 specialized AI workers | Each has a job: scan markets, size risk, execute trades, send alerts |
| **Safety kernel** | Hard-coded limits on `:19001` | A robot lawyer that says YES or NO before money moves |
| **Signing node** | Isolated signer on `:19010` | A vault that signs transactions; the AI never holds withdrawal keys |
| **Edge mesh** | 5 small servers worldwide | Places your orders close to exchanges so delay is low |
| **Inference** | Local AI on GPUs `:30000–30002` | The “brains” — must stay on your hardware for live path |
| **Crypto Dashboard** | Web UI at `:5173` | Titan Agentik operator interface — equity, risk, pipelines, promotions |

**Three modes of money:**

- **Paper** — simulated trades, no real capital. Start here.
- **Shadow** — real market data, still no capital committed.
- **Live** — real money. Only after verify passes, paper minimums, and your explicit **YES**.

**Golden rule:** If something breaks, the system **fails closed** (denies trades). That is intentional.

---

## 2. Hardware you need

Authoritative spec: `templates/infra/hardware_bom.yaml`

### Required for a full spec build

| Machine | Role | Why you need it |
|---------|------|-----------------|
| **TITANHOME** | Brain | Runs AI models, safety services, OpenClaw gateway |
| **Signing node** | Key vault | Signs txs; co-located on TITANHOME at first (`127.0.0.1:19010`), separate machine later |
| **UPS** | Battery backup | **Required before live capital** — power loss mid-trade = real losses |
| **PiKVM** | Remote BIOS/OS | Configure BIOS and install Ubuntu without a physical keyboard/monitor |

### Strongly recommended

| Machine | Role | Why |
|---------|------|-----|
| **TITANSPARK** (ASUS GX10) | Utility AI `:30002` | Runs lighter agents (HERALD, NEXUS, ATLAS, …) so TITANHOME GPUs stay free for critical path |
| **Mac Mini vault** | Trezor ceremonies | Hardware wallet metadata; weekly profit sweeps to cold storage |

### TITANHOME reference build (operator-locked BOM)

- **CPU:** AMD Threadripper PRO 9995WX (96 cores / 192 threads)
- **Board:** ASUS Pro WS WRX90E-SAGE SE
- **RAM:** 512 GB DDR5-6000 ECC RDIMM
- **GPUs:** 2× NVIDIA RTX PRO 6000 Blackwell (96 GB VRAM each)
- **Boot disk:** Micron 7500 Pro 3.8 TB NVMe
- **Data disks:** 2× WD Black SN8100 4 TB
- **PSU:** Super Flower Leadex Titanium 2200 W
- **Timing:** LBE-1420 GPSDO (optional but recommended for latency-sensitive live trading)
- **Security:** TPM-SPI module

### Realistic minimum (if you are not on full BOM yet)

You can **develop and paper-trade** on less:

- 128 GB system RAM minimum (256 GB+ preferred)
- **48–96 GB total GPU VRAM** to run one serious local model + simulations
- One good NVMe for OS + models

You cannot run the full 23-agent, dual-80B spec on a gaming PC and expect production results — but you *can* learn the stack and run paper mode while you upgrade.

### Edge PoPs (cloud — not in your home rack)

Five **stateless** workers (no LLM on edge):

| PoP | Region | Targets |
|-----|--------|---------|
| EDGE-FRA | Frankfurt | Erigon, Jito, ETH builders, Solana EU |
| EDGE-TKY | Tokyo | Binance, OKX, Hyperliquid |
| EDGE-SIN | Singapore | Bybit, BSC, Sui |
| EDGE-USE | N. Virginia | Coinbase, L2 sequencers, Flashbots US |
| EDGE-AMS | Amsterdam | Solana gRPC backup, Nostr |

Config: `templates/infra/edge_mesh.yaml`. Bootstrap **EDGE-FRA first** if you are overwhelmed; the repo’s `verify.sh` expects all five configured for full mesh.

---

## 3. Before first power-on — physical assembly

Follow `templates/infra/network_topology.yaml` → `connection_order`.

**Do this in order:**

1. **Bench-build TITANHOME** — CPU, RAM, both GPUs, AIO cooler, storage. **Do not plug in power yet.**
2. **GPU placement** — GPU0 in the **CPU-direct** PCIe x16 slot (check WRX90E manual). GPU1 in second x16 slot.
3. **Install TPM-SPI** on the motherboard header.
4. **Storage** — For first install, only the **Micron 7500** boot drive is required. Leave WD SN8100 drives unformatted until after Ubuntu works.
5. **PiKVM cabling** — HDMI capture from TITANHOME → PiKVM; USB-ATX power control; PiKVM Ethernet → switch.
6. **First power-on via PiKVM** — You should see POST. If memory training hangs 5–8 minutes after EXPO, that is normal; do not power off.

**Do not skip:** adequate cooling. Two 300 W-class GPUs under sustained inference need aggressive fan curves.

---

## 4. PiKVM — control the machine without a monitor

PiKVM lives at **`192.168.10.5`** on the recommended LAN plan.

1. Connect PiKVM to your switch and find its IP (or use `.5` if you configured static).
2. Open `https://<pikvm-ip>/` in a browser.
3. You will use PiKVM for:
   - Entering BIOS (Del / F2 at POST)
   - Selecting USB boot for Ubuntu installer
   - Watching POST error codes if boot fails

**Why it matters:** Server/workstation builds often fail first POST (memory training, PCIe detection). PiKVM lets you fix BIOS without dragging a monitor to the rack.

---

## 5. TITANHOME BIOS — complete checklist

Full printable checklist: `templates/infra/titanhome_bios_checklist.md`

Access BIOS: **Del** or **F2** at POST → **Advanced Mode (F7)**.

### 5.1 Before you change settings

- [ ] Download latest BIOS for **WRX90E-SAGE SE** from ASUS
- [ ] Use USB BIOS Flashback if recommended for 9995WX (see Level1Techs thread)
- [ ] Note current BIOS version: _______________

### 5.2 Memory (Ai Tweaker)

| Setting | Set to | Why |
|---------|--------|-----|
| ECC Mode | **Enabled** | Catches RAM errors before silent corruption |
| EXPO / R-DIMM profile | **DDR5-6000 CL36** (EXPO I) | Matches your 512 GB kit |
| Memory Context Restore | Enabled | Faster reboot |
| Power Down Enable | **Disabled** | Keeps DIMMs ready — reduces wake latency |

If POST fails: clear CMOS, boot JEDEC (4800 MHz), then re-enable EXPO.

### 5.3 CPU (AMD CBS)

| Setting | Set to |
|---------|--------|
| SMT | Enabled (192 threads) |
| Core Performance Boost | Auto (stock first) |
| PBO | **Disabled** until you are stable |

### 5.4 PCIe (critical for dual GPUs + large models)

| Setting | Set to | Why |
|---------|--------|-----|
| Above 4G Decoding | **Enabled** | Required for large GPU BAR |
| Re-Size BAR Support | **Enabled** | Maps full 96 GB VRAM to OS |
| SR-IOV | Enabled | Future VF passthrough |
| PCIe Link Speed | Gen5 / Auto | |

### 5.5 Boot

| Setting | Set to |
|---------|--------|
| Fast Boot | **Disabled** |
| CSM | **Disabled** |
| Secure Boot | **Disabled** (for Ubuntu install) |
| Boot Option #1 | Ubuntu USB → then Micron NVMe |

### 5.6 Security / virtualization

| Setting | Set to |
|---------|--------|
| TPM Device | Enabled |
| TPM State | Enabled |
| SVM Mode (AMD-V) | Enabled |
| IOMMU | Enabled |

### 5.7 Trading latency profile (enable before **live** capital)

These increase idle power ~50–80 W but remove 50–200 µs wake latency:

| Setting | Set to |
|---------|--------|
| Global C-state Control | **Disabled** |
| CPU C-States | **Disabled** |
| CPPC Preferred Cores | Enabled |

Re-enable C-states during maintenance windows when not trading.

### 5.8 Power and fans

| Setting | Set to |
|---------|--------|
| ErP Ready | Disabled |
| Restore on AC Power Loss | **Power Off** |
| AIO pump | Performance / full speed |
| Chassis fans | Aggressive curve |
| BIOS administrator password | **Set one** |

### 5.9 POST verification (screenshot via PiKVM)

Confirm you see:

- [ ] CPU: AMD Ryzen Threadripper PRO 9995WX
- [ ] RAM: ~512 GB (503–512 GiB usable is normal)
- [ ] GPU0 + GPU1 in PCIe info
- [ ] 3 NVMe drives visible
- [ ] No Q-code hang (consult manual if stuck)

Press **F10 → Save & Reset**.

---

## 6. Install Ubuntu on TITANHOME

Detailed steps: `templates/infra/titanhome_ubuntu_install.md`

### 6.1 Create boot USB

1. Download **Ubuntu 24.04 LTS** (Desktop for easier first setup, or Server for headless).
2. Write to USB with balenaEtcher, or:

```bash
sudo dd if=ubuntu-24.04.4-desktop-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

### 6.2 Install

1. Insert USB, power on, **F8** boot menu → select USB.
2. Installer choices:

| Screen | Choice |
|--------|--------|
| Hostname | `titanhome` |
| Username | e.g. `hyperion` |
| Password | Strong; **disable auto-login** for production |
| Disk | **Micron 7500 only** — manual partitions below |

**Recommended partitions (Micron 7500):**

| Partition | Size | Mount |
|-----------|------|-------|
| EFI | 512 MB | `/boot/efi` |
| root | 200 GB | `/` |
| swap | 64 GB | swap |
| data | remainder | `/data` |

3. Complete install, remove USB, set BIOS boot to Micron NVMe, reboot.

### 6.3 First login sanity checks

```bash
uname -m                    # x86_64
lscpu | head -20
free -h                     # expect ~512 Gi on full BOM
lsblk
ip link                     # note Ethernet interface name (e.g. eno1)
```

---

## 7. Wire your home network (LAN)

Plan: `templates/infra/network_topology.yaml`

**Recommended static IPs (flat LAN `192.168.10.0/24`):**

| Host | IP | Role |
|------|-----|------|
| PiKVM | 192.168.10.5 | Out-of-band |
| TITANHOME | 192.168.10.10 | Primary |
| Signing (phase 2) | 192.168.10.11 | Optional dedicated NUC |
| TITANSPARK | 192.168.10.20 | Utility AI |
| Mac Mini vault | 192.168.10.30 | Trezor / metadata |
| Router | 192.168.10.1 | Gateway |

### 7.1 Static IP on TITANHOME

Replace `eno1` with your interface from `ip link`:

```bash
sudo nano /etc/netplan/01-titanhome.yaml
```

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1:
      addresses:
        - 192.168.10.10/24
      routes:
        - to: default
          via: 192.168.10.1
      nameservers:
        addresses:
          - 192.168.10.1
          - 1.1.1.1
```

```bash
sudo chmod 600 /etc/netplan/01-titanhome.yaml
sudo netplan apply
hostnamectl set-hostname titanhome
```

### 7.2 Verify LAN before software

From TITANHOME:

```bash
ping -c3 192.168.10.20    # TITANSPARK (after it is up)
ping -c3 192.168.10.30    # vault
```

**Production rule:** Ethernet only on trading nodes — no WiFi for TITANHOME or TITANSPARK.

---

## 8. GPU drivers and post-install

### 8.1 NVIDIA drivers

```bash
sudo apt update && sudo apt upgrade -y
sudo ubuntu-drivers list
sudo ubuntu-drivers install    # or: sudo apt install nvidia-driver-580
sudo reboot
```

After reboot — **both GPUs must appear:**

```bash
nvidia-smi -L
nvidia-smi
```

You should see **2× RTX PRO 6000** (or your installed models) with no errors.

### 8.2 Titan post-install script

Clone the repo (if not already), then:

```bash
bash /path/to/titan-deploy/scripts/titanhome-postinstall.sh
```

This script installs base dependencies (Python, build tools, chrony hooks, etc.). Read the script if you want to know exactly what it changes.

### 8.3 Optional: latency tuning (before live)

```bash
cd /path/to/titan-deploy
./deploy.sh --latency-tune
```

Applies sysctl, chrony, and fast-path settings from `templates/infra/latency_fast_path.yaml`.

---

## 9. Bring up the other machines

### 9.1 TITANSPARK (ASUS GX10)

- Connect **wired Ethernet** to switch — target IP `192.168.10.20`
- Disable sleep/hibernate
- Install Ubuntu if not pre-installed
- Later: run utility inference (SGLang) on **`:30002`**

TITANHOME will call utility agents at `http://192.168.10.20:30002/v1` (LAN) or via WireGuard `http://10.0.10.3:30002/v1`.

### 9.2 Mac Mini vault

- Enable **FileVault**, firewall, no sleep on AC power
- Static IP `192.168.10.30`
- Install Trezor Suite; bridge reachable from TITANHOME only
- **Does not execute signing** — signing stays on signing node `:19010`

### 9.3 Signing node (phase 1)

Initially co-located on TITANHOME:

- Endpoint: `http://127.0.0.1:19010`
- Separate cgroups/VM in phase 2 (`signing.lan` at `.11`)
- Spec: `templates/infra/signing_node.yaml`

---

## 10. UPS and power-loss drill

Spec: `templates/infra/power_requirements.yaml`

**Before live capital:**

- UPS ≥ **3000 VA**, ≥ **15 minutes** runtime
- Protect: TITANHOME, signing node, TITANSPARK, vault, core switch
- USB to TITANHOME for **NUT** monitoring (optional but recommended)

**Policy behavior on power loss:** halt trading, flatten positions, revoke session keys.

**Drill:**

1. System running in paper mode with services healthy
2. Pull UPS mains plug (simulated outage)
3. Confirm: trading halts, CRITICAL alert fires (Telegram when wired)
4. Document runtime minutes achieved

`verify.sh` checks `live_capital_requires_ups: true` in power requirements.

---

## 11. Time sync (GPSDO + chrony)

The LBE-1420 GPSDO provides **PPS** (pulse-per-second) for sub-millisecond clock discipline.

After OS install:

1. Connect GPSDO per manufacturer wiring to TITANHOME
2. Configure **chrony** to prefer PPS source
3. Verify:

```bash
chronyc sources -v
chronyc tracking
```

You want `Leap status: Normal` and a selected source with low offset. Fallback: NTP pool if GPS lost > 5 minutes.

Accurate time matters for log correlation, exchange API signatures, and latency measurement — not for “winning HFT races” alone.

---

## 12. Build and deploy the software

All commands from the **titan-deploy** repo root.

### 12.1 One-time developer setup

```bash
cd ~/path/to/titan-deploy

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
```

Expect **dozens of passing tests**. If tests fail, stop — fix before deploy.

### 12.2 Install runtimes (OpenClaw + Hermes)

```bash
./deploy.sh --install-packages
```

Installs global `openclaw` (Node) and `hermes-agent` (Python) if not present.

### 12.3 Deploy bundle to home directory

```bash
./deploy.sh --dry-run    # read the plan
./deploy.sh              # build + install to ~/.openclaw and ~/.hermes
```

**Where files go:**

| Path | Contents |
|------|----------|
| `~/.openclaw/` | openclaw.json, policy, safety code, infra, playbooks |
| `~/.openclaw/.env` | **Your secrets** (create from template) |
| `~/.hermes/` | Hermes config + skills symlink |

**Edit rule:** Change **`templates/`** in the git repo, then redeploy. Never hand-edit `output/` or installed copies long-term.

### 12.4 Install systemd services

```bash
./deploy.sh --systemd
```

This copies unit files for risk kernel, reconciliation, inference servers, etc.

### 12.5 Create secrets file

```bash
cp ~/.openclaw/infra/live.env.example ~/.openclaw/.env
chmod 600 ~/.openclaw/.env
nano ~/.openclaw/.env
```

Fill values — Section 13 and 14 explain every provider.

### 12.6 Verify (must pass)

```bash
./deploy.sh --verify
```

Ends with **`Verification PASSED`**. If not, read the failure, fix, redeploy, retry.

### 12.7 First-run ritual

Work through `BOOTSTRAP.md` checkbox by checkbox. Delete `BOOTSTRAP.md` when complete.

---

## 13. Secrets file — every variable explained

Template: `templates/infra/live.env.example` → installed at `~/.openclaw/infra/live.env.example`

Copy to `~/.openclaw/.env`. **Never commit this file.**

### Control plane

| Variable | Required when | Meaning |
|----------|---------------|---------|
| `TELEGRAM_BOT_TOKEN` | Operator alerts | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_USER_ID` | Operator alerts | Your numeric Telegram user ID |
| `NATS_URL` | Multi-agent messaging | Default `nats://127.0.0.1:4222` |

### Live arm switches (fail-closed)

| Variable | Meaning |
|----------|---------|
| `TITAN_LIVE_SIGNING_READY=0` | Keep **0** until Trezor bridge + `:19010` health OK |
| Set to `1` | Arms live signing path |

### Reconciliation (positions vs exchange)

| Variable | Meaning |
|----------|---------|
| `TITAN_RECON_FETCHER_URL` | HTTP endpoint returning JSON positions (preferred aggregator) |
| `BINANCE_API_KEY` / `SECRET` | Binance read + trade keys |
| `OKX_API_KEY` / `SECRET` / `PASSPHRASE` | OKX |
| `BYBIT_API_KEY` / `SECRET` | Bybit |
| `HYPERLIQUID_PRIVATE_KEY` / `WALLET_ADDRESS` | Hyperliquid |

**Exchange key hygiene:**

- **Trade only** — withdrawals disabled
- IP allowlist to your edge/home egress
- Separate subaccount per strategy if exchange supports it

### Chain RPC

| Variable | Meaning |
|----------|---------|
| `ETH_RPC_URL` | Fallback/public EVM RPC |
| `ERIGON_HTTP_URL` | Local Erigon on EDGE-FRA (default `http://127.0.0.1:8545` if tunneled) |
| `SOLANA_RPC_URL` | Solana HTTP RPC (Helius, QuickNode, etc.) |
| `GEYSER_GRPC_URL` | Yellowstone gRPC for low-latency Solana streams |
| `JITO_BLOCK_ENGINE_URL` | Jito bundle submission (Frankfurt for EU) |

### Signing

| Variable | Meaning |
|----------|---------|
| `TREZOR_BRIDGE_SOCKET` | Local Trezor bridge socket |
| `OPENCLAW_TREZOR_BRIDGE` | Optional bridge override |

### Edge / Coinbase

| Variable | Meaning |
|----------|---------|
| `TITAN_EDGE_MESH` | Path to edge mesh YAML |
| `EDGE_FRA_RPC` | EDGE-FRA chain RPC if not local |
| `COINBASE_API_KEY` / `SECRET` | Coinbase Advanced Trade |

### Web UI (optional)

| Variable | Meaning |
|----------|---------|
| `VITE_TITAN_STATUS_URL` | Proxy target for dashboard health |
| `VITE_TITAN_KERNEL_URL` | Risk kernel health |

---

## 14. Data providers — everything you need to subscribe to

This is the **complete provider map** for Titan Agentik. You do not need every provider on day one — but each **live pipeline** needs its feeds wired or the kernel **denies** trades (fail-closed).

### 14.1 How data flows (big picture)

```
External APIs / nodes          Agents                 Safety
─────────────────────         ───────                ──────
Exchanges (CEX WS/REST)  →    NEXUS, PREDATOR   →    ORACLE signals
Erigon (EVM archive)     →    WRAITH, ORACLE    →    Risk kernel :19001
Geyser (Solana stream)   →    PREDATOR, P22     →    Portfolio :19004
Sentiment (LunarCrush…)  →    ORACLE            →    GUARDIAN sizing
Jito / Flashbots         →    TRENCH-OPS        →    Signing :19010
```

**NEXUS** (utility agent on TITANSPARK `:30002`) aggregates feeds: funding rates, oracle consensus, AVS registry.

**ORACLE** (Tier 1 `:30000`) runs four analyst roles: fundamentals, sentiment, news, technical — see `AGENTS.md`.

### 14.2 Tier 0 — Infrastructure (you run or rent)

| Provider | What it gives you | Used by | Setup |
|----------|-------------------|---------|-------|
| **NATS JetStream** | Internal agent bus | All agents | `nats-server -js` on TITANHOME |
| **Erigon archive node** | Ethereum history + txpool | WRAITH, ORACLE, DeFi strategies | Run on **EDGE-FRA**; set `ERIGON_HTTP_URL` |
| **Solana RPC** | HTTP JSON-RPC | General Solana reads | Helius, QuickNode, Triton |
| **Yellowstone Geyser gRPC** | Sub-second Solana account/tx streams | P22 memecoin, PREDATOR | `GEYSER_GRPC_URL` + `HELIUS_API_KEY` |
| **Jito Block Engine** | Private bundle submission | P22, MEV strategies | `JITO_BLOCK_ENGINE_URL` |
| **WireGuard mesh** | Encrypted path to edge PoPs | TRENCH-OPS dispatch | `edge_mesh_wg_setup.sh` |

Erigon is heavy (multi-TB sync). Plan **days** for initial sync. Until Erigon is healthy, EVM-heavy lanes stay paper-only.

Geyser config reference: `templates/infra/solana_memecoin.yaml`

```yaml
geyser:
  endpoint: "${GEYSER_GRPC_URL}"
  api_key_env: HELIUS_API_KEY
  programs:
    pump_fun: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
jito:
  block_engine_url: "https://frankfurt.mainnet.block-engine.jito.wtf"
  bundle_only: true
```

### 14.3 Tier 1 — Centralized exchanges (CEX)

| Exchange | PoP | Env vars | Data you get |
|----------|-----|----------|--------------|
| **Binance** | EDGE-TKY | `BINANCE_API_KEY`, `BINANCE_API_SECRET` | Order book, fills, funding, positions |
| **OKX** | EDGE-TKY | `OKX_*` | Same |
| **Hyperliquid** | EDGE-TKY | `HYPERLIQUID_*` | Perps, L1 snapshots |
| **Bybit** | EDGE-SIN | `BYBIT_*` | Perps, spot |
| **Coinbase** | EDGE-USE | `COINBASE_*` | Spot, Advanced Trade |

**Minimum for reconciliation:** read access to every venue where you have open positions.

**Minimum for live execution:** trade-enabled keys + IP allowlist + subaccount isolation.

### 14.4 Tier 2 — On-chain / DeFi indexers

| Provider | Data | Used for | Notes |
|----------|------|----------|-------|
| **DefiLlama** | TVL, yields, protocol stats | ORACLE fundamentals | Public API; rate-limit politely |
| **The Graph** | Subgraph queries | Protocol-specific metrics | Needs API key for production volume |
| **Dune Analytics** | SQL on-chain data | Research, ORACLE | API key |
| **Nansen** (optional) | Smart money labels | WRAITH, PREDATOR | Paid; `CB_NANSEN_RATE_LIMIT` if stale |
| **CoinGecko / CoinMarketCap** | Prices, market cap | Cross-check oracle median | NEXUS requires **3+ sources** for prices |

### 14.5 Tier 3 — Sentiment and news (ORACLE analysts)

Documented in `AGENTS.md` TradingAgents integration:

| Source | Data | Agent role |
|--------|------|------------|
| **LunarCrush** | Social volume, galaxy score | Sentiment analyst |
| **Santiment** | On-chain + social metrics | Sentiment analyst |
| **Reddit** | r/cryptocurrency, r/ethtrader, protocol subs | Sentiment analyst |
| **Twitter/X** | Influencer feeds | Sentiment analyst |
| **Telegram** | Group velocity | Sentiment analyst |
| **News APIs / RSS** | Macro, regulatory, protocol news | News analyst |

**Rule:** Sentiment claims must cite a **specific post with timestamp** — no vibe-based trading.

For beginners: start with **free tiers** (LunarCrush limited, Reddit API, RSS). Add paid Santiment/Nansen when a lane is promoted toward live.

### 14.6 Tier 4 — MEV-private submission (required for DEX/MEV lanes)

| Provider | Region | Used when |
|----------|--------|-----------|
| **Flashbots Protect** | US/EU | EVM swaps, flash loans on Ethereum/L2 |
| **Jito bundles** | FRA/TKY | Solana, memecoin P22 |
| **UniswapX / intent solvers** | varies | Declarative intents (advanced) |

Public mempool submission for size trades is **forbidden** by policy — expect `CB_MEV_LEAK` halt if detected.

Flash-loan providers (on-chain, not API keys): Balancer, Morpho, Aave V3, Uniswap V4 — see `templates/infra/flash_loan.yaml`.

### 14.7 Tier 5 — Macro / regime (AUGUR)

| Source | Status | Env / file |
|--------|--------|------------|
| **AUGUR regime feed** | Stub by default | `~/.openclaw/safety/augur_regime.json` until live wire |

Wire live macro data before trusting regime-dependent sizing.

### 14.8 Provider checklist by pipeline (common lanes)

| Pipeline | Minimum providers |
|----------|-------------------|
| **P5 Funding carry** | Binance or OKX funding + HL/Drift perps, NEXUS funding monitor |
| **P6 Liquidations** | Erigon + Aave/Morpho subgraph + mempool (EDGE-FRA) |
| **P22 Memecoin** | Geyser + Jito + SOL RPC + PREDATOR filter; promotion YES |
| **P29/P30 MEV** | Erigon txpool, Flashbots/Jito, EDGE-TKY RTT < 1 ms |
| **Flash loans** | EVM RPC + simulation + Flashbots; `flash_loan_live` YES |
| **CEX arb** | 2+ exchange WS feeds + reconciliation |

### 14.9 What happens if a feed is missing?

Fail-closed behavior:

- Reconciliation without keys → **DENY** live trades
- Stale price (>60s) → circuit breaker, lane halt
- Geyser down → P22 paper only
- Signing not ready (`TITAN_LIVE_SIGNING_READY=0`) → **DENY** all live signing

This is safety working, not a bug.

---

## 15. Download AI models and start inference

Model paths are in systemd units under `templates/systemd/`.

### 15.1 Models to download (full spec)

| Tier | Port | GPU | Model | Role |
|------|------|-----|-------|------|
| 1 | `:30000` | 0 | Qwen3-30B-A3B FP8 | Signals, risk, execution |
| 2 | `:30001` | 1 | Qwen3-Coder-Next-80B | Orchestration, ARCHON |
| U | `:30002` | TITANSPARK | Qwen3-30B FP4 | HERALD, NEXUS, ATLAS, … |
| Embedder | `:30004` | 0 ride-along | Qwen3-Embedding-8B | Memory search |
| 3a/3b | `:30005`/`:30003` | off-peak | DeepSeek V4 / GLM-5.2 | R&D only — **never live critical path** |

Store under `/data/models/` (or your `/data` mount).

### 15.2 Start inference on TITANHOME

```bash
./deploy.sh --start-inference
```

Health checks:

```bash
curl -s localhost:30000/health
curl -s localhost:30001/health
```

### 15.3 GPU schedule

`templates/infra/gpu_schedule.yaml` — Tier 1 is **never preempted**. Tier 3 runs off-peak only (22:00–06:00). FORGE enforces via `forge_gpu_schedule_enforce.sh`.

---

## 16. Start safety services (the non-negotiable core)

```bash
./deploy.sh --start-services
```

### Port map (memorize these)

| Port | Service | Purpose |
|------|---------|---------|
| **19001** | Risk kernel | Pre-trade YES/NO |
| **19002** | Reconciliation | Positions vs exchange |
| **19003** | Status aggregator | `/health` for whole stack |
| **19004** | Portfolio risk | Drawdown, concentration |
| **19005** | Dead-man's switch | Heartbeat / flatten |
| **19006** | Allocator | Kelly sizing |
| **19007** | TCA | Execution quality |
| **19008** | Security Ops | Lockdown, pillars |
| **19010** | Signing node | Transaction signatures |
| **18789** | OpenClaw gateway | Agent orchestration |
| **4222** | NATS | Message bus |

**Single health check:**

```bash
curl -s http://127.0.0.1:19003/health | jq
```

Expect `"status":"ok"`.

### Kill switch drill

```bash
~/.openclaw/safety/bin/titan-safety kill activate --operator YOU --reason drill
~/.openclaw/safety/bin/titan-safety kill status
~/.openclaw/safety/bin/titan-safety kill deactivate --operator YOU --signed "$(~/.openclaw/safety/bin/titan-safety kill sign --command RESUME --operator YOU)"
```

### Fail-closed drill

```bash
sudo systemctl stop titan-risk-kernel
# Attempt paper trade — must DENY
sudo systemctl start titan-risk-kernel
```

---

## 17. Message bus, chain nodes, and edge servers

### 17.1 NATS

```bash
nats-server -js
# Or enable nats systemd unit if installed
```

### 17.2 Erigon (EDGE-FRA)

Run on Frankfurt edge server — not on TITANHOME. Requires large NVMe. Point `ERIGON_HTTP_URL` at it (WireGuard tunnel or public endpoint with auth).

### 17.3 Solana Geyser

Sign up for **Helius** (or Triton), enable Yellowstone gRPC, set:

```bash
GEYSER_GRPC_URL=https://grpc.mainnet.helius-rpc.com
HELIUS_API_KEY=your_key
```

Test with:

```bash
~/.openclaw/safety/bin/titan-safety memecoin status
```

### 17.4 Edge mesh bootstrap

```bash
# WireGuard hub on TITANHOME first
bash ~/.openclaw/infra/edge_mesh_wg_setup.sh

# Per PoP (example Frankfurt)
POP=EDGE-FRA bash ~/.openclaw/infra/edge_pop_bootstrap.sh
POP=EDGE-TKY bash ~/.openclaw/infra/edge_pop_bootstrap.sh
# ... SIN, USE, AMS

# Verify routing
~/.openclaw/safety/bin/titan-safety edge route --venue jito --strategy P22
~/.openclaw/safety/bin/titan-safety edge mesh verify
```

Edge workers listen on **`:19100`** per PoP.

---

## 18. Telegram and operator notifications

1. Create bot via [@BotFather](https://t.me/BotFather) → `TELEGRAM_BOT_TOKEN`
2. Get your user ID (message [@userinfobot](https://t.me/userinfobot)) → `TELEGRAM_USER_ID`
3. Add both to `~/.openclaw/.env`
4. Restart gateway:

```bash
systemctl --user restart openclaw-gateway
openclaw gateway status
```

5. Test HERALD template:

```bash
python3 ~/.openclaw/workspace/skills/herald_notify/notify.py
```

HERALD sends: trade fills, hourly digest (`:00 UTC`), CRITICAL alerts, promotion prompts.

**Rule:** Promotion timeout → **HOLD**, never auto-promote.

---

## 19. Titan Agentik web UI (Crypto Dashboard)

```bash
cd /path/to/titan-deploy/web
npm install
npm run dev
```

Open **http://127.0.0.1:5173**

**Do not expose port 5173 to the public internet.** Use:

- SSH tunnel: `ssh -L 5173:127.0.0.1:5173 user@192.168.10.10`
- Tailscale Serve
- Cloudflare Tunnel + SSO

Sections: Dashboard, Capital, Risk, Security Ops, Pipelines, Promotions, Memecoin Trench, Edge Mesh, Flash Loans, Signing Node, Settings.

Live mutating actions require HMAC in Settings (`X-Titan-Auth`).

---

## 20. Paper trading — prove it works with fake money

**Do not add live keys until:**

- [ ] `./deploy.sh --verify` passes
- [ ] All safety services healthy
- [ ] Kill switch + fail-closed drills done
- [ ] At least **3 days paper** per lane (`promotion.paperMinimumDays`)

### Paper commands

```bash
# Memecoin filter sim
~/.openclaw/safety/bin/titan-safety memecoin sim --count 100

# Flash loan sim
~/.openclaw/safety/bin/titan-safety flashloan sim --count 100

# Edge route check
~/.openclaw/safety/bin/titan-safety edge route --venue binance --strategy P5

# Capital ledger (paper deposit — not trading PnL)
~/.openclaw/safety/bin/titan-safety capital deposit --amount 2500 --asset USDC --operator YOU
~/.openclaw/safety/bin/titan-safety capital balance
```

Watch Titan Agentik **Crypto Dashboard** for lane status, equity curve (demo until live), and promotion queue.

---

## 21. Promotion and going live (human gates)

Every strategy lane follows:

1. **Backtest** (realistic costs)
2. **Paper** ≥ 3 days
3. **Shadow** (private mempool, no capital)
4. **Micro-live** ≤ 0.1% equity
5. **Statistical gate** — min 200 trades, DSR ≥ 0.90, PSR ≥ 0.90
6. **Phase 5 operator YES**

```bash
~/.openclaw/safety/bin/titan-safety promotion approve \
  --category strategy \
  --subject P5 \
  --response YES \
  --operator YOU
```

### Special activations

| Feature | Extra gate |
|---------|------------|
| **P22 Memecoin live** | Geyser + Jito + `memecoinTrench.enabled: true` in openclaw.json |
| **Flash loans live** | `flash_loan_live` YES + `flashLoanRouter.enabled: true` |
| **Leverage change** | Human YES always |
| **Withdrawal > 20% equity** | Human confirm |

Playbook: `templates/playbooks/promotion.yaml`

---

## 22. Phased capital plan

From `PRODUCTION_READINESS.md`:

| Phase | Capital | Focus |
|-------|---------|-------|
| **0** | $0 | Infra + paper only |
| **1** | $2.5K–10K | Micro-live, allocator advisory |
| **2** | $10K–50K | Allocator enforced, live recon 48h zero divergence |
| **3** | $50K+ | Proven lanes only; weekly profit sweeps to Trezor at ≥ $35K equity |

**Weekly sweep rule (R23):** Below $35K → 100% reinvest. At/above $35K → sweep 20% of weekly profit every 7 days to Trezor Safe 7.

Set live signing only when ready:

```bash
# In ~/.openclaw/.env after Trezor + :19010 healthy
TITAN_LIVE_SIGNING_READY=1
```

---

## 23. Daily operator routine

1. **Health:** `curl :19003/health` — all green
2. **Heartbeat:** `titan-safety heartbeat` (dead-man's switch)
3. **Reconciliation:** check divergence in Crypto Dashboard or `titan-safety recon status`
4. **Drawdown:** review tiers (2% alert → 12% halt); velocity breakers still hard-stop
5. **Promotions:** clear PENDING items — YES or NO, never ignore (timeout = de-risk)
6. **Telegram hourly digest** at `:00 UTC`
7. **Weekly:** `titan-safety capital verify-audit`, review TCA scorecards

---

## 24. Troubleshooting common failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `verify.sh` fails on edge mesh | PoP not bootstrapped | Run `edge_pop_bootstrap.sh` per PoP |
| `:30000/health` down | Model path wrong or OOM | Check `journalctl -u llama-server-tier1`; verify `/data/models` |
| All trades DENY | Kill switch active or kernel stopped | `kill status`; `systemctl status titan-risk-kernel` |
| Reconciliation DENY | Missing exchange keys | Fill `.env`; check IP allowlist |
| P22 always paper | Geyser not set | `GEYSER_GRPC_URL`, `HELIUS_API_KEY` |
| Signing DENY | `TITAN_LIVE_SIGNING_READY=0` | Complete Trezor bridge setup first |
| `nvidia-smi` one GPU | Wrong slot or power | Reseat GPU0 in CPU-direct slot; check PCIe power cables |
| POST memory hang | EXPO unstable | Clear CMOS; JEDEC first; update BIOS |

---

## 25. Master checklists

### Phase A — Hardware (no software)

- [ ] TITANHOME assembled, TPM installed, PiKVM working
- [ ] BIOS checklist complete (`titanhome_bios_checklist.md`)
- [ ] POST shows 9995WX + 512 GB + 2 GPUs
- [ ] Ubuntu 24.04 on Micron 7500, hostname `titanhome`
- [ ] Static IP `.10`, `nvidia-smi` shows 2 GPUs
- [ ] TITANSPARK `.20`, vault `.30` on Ethernet
- [ ] UPS installed

### Phase B — Software deploy

- [ ] `pytest` passes in repo
- [ ] `./deploy.sh --verify` → **Verification PASSED**
- [ ] `~/.openclaw/.env` filled (Section 13)
- [ ] `:19003/health` ok
- [ ] `:30000` and `:30001` health ok
- [ ] Kill switch + fail-closed drills done
- [ ] `BOOTSTRAP.md` complete

### Phase C — Data providers

- [ ] NATS running
- [ ] Exchange keys (read) for reconciliation
- [ ] Erigon syncing on EDGE-FRA
- [ ] Solana RPC + Geyser (if P22)
- [ ] Jito / Flashbots endpoints configured
- [ ] Telegram bot live

### Phase D — Paper validation

- [ ] 3+ days paper per lane
- [ ] Adversarial + chaos harnesses green
- [ ] Memecoin sim / flashloan sim if using those lanes
- [ ] Edge mesh verify passes

### Phase E — Live (human YES each)

- [ ] `PRODUCTION_READINESS.md` gates satisfied
- [ ] Phase 5 YES per lane
- [ ] `TITAN_LIVE_SIGNING_READY=1`
- [ ] Micro-live ≤ 0.1% equity
- [ ] 48h reconciliation zero divergence
- [ ] UPS drill documented

---

## Related files (quick index)

| Topic | File |
|-------|------|
| BIOS | `templates/infra/titanhome_bios_checklist.md` |
| Ubuntu install | `templates/infra/titanhome_ubuntu_install.md` |
| Network | `templates/infra/network_topology.yaml` |
| Hardware BOM | `templates/infra/hardware_bom.yaml` |
| Power / UPS | `templates/infra/power_requirements.yaml` |
| GPU schedule | `templates/infra/gpu_schedule.yaml` |
| Edge mesh | `templates/infra/edge_mesh.yaml` |
| Solana memecoin | `templates/infra/solana_memecoin.yaml` |
| Flash loans | `templates/infra/flash_loan.yaml` |
| Secrets template | `templates/infra/live.env.example` |
| Risk policy | `templates/risk_kernel/policy.yaml` |
| Main config | `templates/openclaw.json` |
| First-run ritual | `BOOTSTRAP.md` |
| Production gates | `PRODUCTION_READINESS.md` |
| Web UI | `web/README.md` |
| Agent roles | `AGENTS.md` |

---

## Final word for beginners

Titan Agentik is **dangerous software** if rushed. The stack is designed so that skipping steps produces **DENY**, not silent failures — learn to appreciate that.

Your order of operations is always:

1. **Hardware + BIOS + OS**
2. **Deploy + verify**
3. **Wire data providers**
4. **Paper trade until bored**
5. **Promote one lane at a time**
6. **Add capital slowly**

When in doubt, run `./deploy.sh --verify` and read `PRODUCTION_READINESS.md` before funding the next phase.

Good luck — and keep the kill switch command on a sticky note until live capital is boring.
