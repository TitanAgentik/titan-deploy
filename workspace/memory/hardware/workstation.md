# TITANHOME Workstation

**Role:** Primary compute + Tier 1/2 inference + safety services

- CPU: AMD Ryzen Threadripper PRO 9995WX (96C/192T)
- Board: ASUS Pro WS WRX90E-SAGE SE (128 PCIe 5.0 lanes)
- RAM: 512GB DDR5-6000 ECC R-DIMM (8×64GB)
- GPU: 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96GB each, 192GB total)
- Storage: Micron 7500 Pro 3.8TB (boot) + 2× WD Black SN8100 4TB
- PSU: Super Flower Leadex Titanium 2200W
- Cooling: Silverstone XE360-TR5 360mm AIO + Noctua iPPC fans
- Timing: LBE-1425 GPSDO → E810-XXVDA4T | UPS: Eaton 9SX 3000VA | OOB: AST2600 BMC (no PiKVM) | TPM: ASUS TPM-SPI
- NIC: Intel E810-XXVDA4T (4×25GbE PTP/SyncE)
- Chassis: Phanteks Enthoo Pro 2 Server Edition

## Inference Services

- Tier 1 :30000 (GPU 0): Qwen3-30B-A3B FP8 — critical path
- Tier 2 :30001 (GPU 1): Qwen3-Coder-Next-80B — reasoning
- Tier 3a :30005 (off-peak): DeepSeek V4 Pro — PRIMARY R&D/evolution
- Tier 3b :30003 (off-peak): GLM-5.2 — SECONDARY R&D only
- REVM :30020 | Embedder :30004
- Safety: risk kernel + reconciliation + dead-man's switch (:19001-19005)

## Power

- 240V dedicated circuit + **UPS REQUIRED for live capital** (≥15 min runtime)
- On power-loss: HALT trading per `risk_kernel/policy.yaml`

BOM: `~/.openclaw/infra/hardware_bom.yaml` | Schedule: `gpu_schedule.yaml`
