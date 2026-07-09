# §PERF_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `PERF_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Performance / BIOS / GPU schedule pointers (hardware ops).
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## GPU schedule

```yaml
# TITAN GPU Schedule — market-hours priority reservation
# Deploy target: ~/.openclaw/infra/gpu_schedule.yaml
# TITANHOME: 2× RTX PRO 6000 Blackwell Max-Q (96GB each) via CUDA MPS

version: "1.1"
timezone: UTC
hardware_ref: ~/.openclaw/infra/hardware_bom.yaml

market_hours:
  trading_window: "00:00-23:59"
  maintenance_window: "06:00-10:00"

priorities:
  1:
    name: tier1_critical_inference
    services:
      - llama-server-qwen3-30b-fp8  # :30000 GPU 0
    gpu: 0
    mps_partition: inference-critical
    preemptible: false
    market_hours: always_on
    agents: [GUARDIAN, ORACLE, PREDATOR, AUGUR, WRAITH, NARRATIVE, TRENCH-OPS]
    note: "NEVER preempted — signals, risk, execution critical path"
  2:
    name: tier2_reasoning_inference
    services:
      - llama-server-qwen3-coder-80b  # :30001 GPU 1
    gpu: 1
    mps_partition: inference-high
    preemptible: false
    market_hours: always_on
    agents: [ARCHON, CORTEX, SENTINEL, LAMARCK, DARWIN_GODEL]
    note: "Orchestration + strategy — not on sub-second execution path"
  3:
    name: trading_aux
    services:
      - embedder  # :30004
      - revm_simulation  # :30020
    mps_partition: compute-medium
    preemptible: false
    market_hours: always_on
  4:
    name: tier3_offline_only
    services:
      - llama-server-deepseek-v4pro  # :30005 PRIMARY long-horizon R&D
      - llama-server-glm-5.2-offload  # :30003 SECONDARY R&D
    gpu: "0+1_expert_offload"
    mps_partition: compute-low
    preemptible: true
    allowed_windows:
      - maintenance_window
      - "22:00-06:00"
    market_hours: forbidden
    note: "Tier 3a DeepSeek V4 Pro (:30005) PRIMARY + Tier 3b GLM-5.2 (:30003) SECONDARY — R&D/evolution ONLY; NEVER on live trade path (TRENCH-OPS/GUARDIAN/EXECUTOR)"
  5:
    name: off_peak_compute
    services:
      - cuevm_fuzzing
      - monte_carlo_backtest
      - skill_evolution_training
    mps_partition: compute-low
    preemptible: true
    allowed_windows:
      - maintenance_window
      - "22:00-06:00"
    market_hours: forbidden

failover:
  gpu_0_failure:
    action: "Route Tier 1 to GPU 1 degraded Qwen3-30B; close-only until GPU 0 restored"
    cb: CB_GPU0_FAILOVER
  gpu_1_failure:
    action: "Tier 2 agents fallback to TITANSPARK :30002 utility model"
    cb: CB_GPU1_FAILOVER
  dual_gpu_failure:
    action: "HALT trading; emergency sweep to Trezor"
    cb: CB_DUAL_GPU_FAILURE

titanspark:
  role: utility_inference_failover
  hardware: ASUS GX10
  services:
    - qwen3-utility-30002
  note: "Utility tier failover — not primary critical-path inference"

enforcement:
  agent: FORGE
  heartbeat_check: HEARTBEAT.md
  on_violation:
    action: kill_off_peak_job
    alert: MEDIUM
```

## BIOS checklist (excerpt)

```markdown
# TITANHOME BIOS Checklist — WRX90E-SAGE SE + 9995WX

Use via **PiKVM** (192.168.10.5). Check each box in BIOS before Ubuntu install.

## Before first power-on

- [ ] Latest BIOS downloaded from ASUS WRX90E-SAGE SE support page
- [ ] USB Flashback done if recommended for 9995WX (see Level1Techs thread)
- [ ] Only Micron 7500 installed for first boot (optional — reduces variables)
- [ ] GPU0 in CPU-direct PCIe x16 slot, GPU1 in second x16
- [ ] TPM-SPI module installed
- [ ] XE360-TR5 pump connected to AIO_PUMP or CPU_FAN header

## BIOS navigation (ASUS workstation BIOS)

Press **Del** or **F2** at POST. Advanced Mode (F7) for most settings.

### EzFlash / BIOS version

- [ ] Note current BIOS version: _______________
- [ ] Update if not latest (Tool → ASUS EZ Flash)

### Ai Tweaker / Memory

| Setting | Target | Done |
|---------|--------|------|
| ECC Mode | Enabled | [ ] |
| EXPO / R-DIMM profile | EXPO I or DDR5-6000 CL36 | [ ] |
| Memory Context Restore | Enabled | [ ] |
| Power Down Enable | Disabled | [ ] |

If POST fails: clear CMOS, boot at JEDEC (4800), then enable EXPO.

### Advanced → AMD CBS / CPU

| Setting | Target | Done |
|---------|--------|------|
| SMT | Enabled | [ ] |
| Core Performance Boost | Auto (stock first) | [ ] |
| PBO | Disabled (tune later) | [ ] |

### Advanced → PCI Subsystem Settings

| Setting | Target | Done |
|---------|--------|------|
| Above 4G Decoding | **Enabled** | [ ] |
| Re-Size BAR Support | **Enabled** | [ ] |
| SR-IOV | Enabled | [ ] |
| PCIe Link Speed | Gen5 / Auto | [ ] |

### Advanced → NVMe / Storage

- [ ] Micron 7500 visible as boot device
- [ ] WD SN8100 drives visible (install OS on Micron only first)

### Boot

| Setting | Target | Done |
|---------|--------|------|
| Fast Boot | **Disabled** | [ ] |
| CSM | **Disabled** | [ ] |
| Secure Boot | **Disabled** (Ubuntu install) | [ ] |
| Boot Option #1 | Ubuntu USB (install) → then Micron NVMe | [ ] |

### Advanced → Trusted Computing

| Setting | Target | Done |
|---------|--------|------|
| TPM Device | Enabled | [ ] |
| TPM State | Enabled | [ ] |

### Advanced → CPU Configuration / SVM

| Setting | Target | Done |
|---------|--------|------|
| SVM Mode (AMD-V) | Enabled | [ ] |
| IOMMU | Enabled | [ ] |

### Advanced → Onboard Devices

- [ ] Primary display: PCIe slot with GPU0 (or auto)
- [ ] Serial / parallel: disabled if unused

### Power

| Setting | Target | Done |
|---------|--------|------|
| ErP Ready | Disabled | [ ] |
| Restore on AC Power Loss | Power Off | [ ] |

### Q-Fan / Monitor

- [ ] AIO pump: full speed or performance profile
- [ ] Chassis fans: performance curve (GPU load will be high)
- [ ] Set BIOS administrator password: [ ]

## POST verification screen (note in PiKVM screenshot)

- [ ] CPU: AMD Ryzen Threadripper PRO 9995WX
- [ ] RAM: ~512 GB (503–512 GiB usable is normal)
- [ ] GPU0 + GPU1 detected in PCIe info
- [ ] Storage: 3 NVMe drives
- [ ] No Q-code errors (consult manual if stuck on 00, 15, etc.)

## Save

- [ ] F10 → Save & Reset
- [ ] First boot after EXPO may take 5–8 minutes — do not power off
```

Full narrative PERF sections remain in `TITAN.reconciled.md` (§PERF).
