---
name: forge_infra
description: Forge Infra — TITANHOME health, UPS telemetry, GPU schedule enforcement
metadata:
  openclaw:
    status: active
  skill_tuple:
    intent: forge_infra
    method: infra_monitoring
    difficulty: medium
---

# Forge Infra

Infrastructure health agent for TITANHOME (Threadripper PRO 9995WX + 2× RTX PRO 6000).

## Hardware Reference

- BOM: `~/.openclaw/infra/hardware_bom.yaml`
- CPU: AMD Ryzen Threadripper PRO 9995WX (96C/192T)
- Board: ASUS Pro WS WRX90E-SAGE SE
- RAM: 512GB DDR5-6000 ECC R-DIMM
- GPU: 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96GB each)
- Boot: Micron 7500 Pro 3.8TB | Data: 2× WD Black SN8100 4TB
- PSU: Super Flower Leadex Titanium 2200W
- Timing: LBE-1420 GPSDO | OOB: PiKVM V4 Plus | TPM: ASUS TPM-SPI

## Responsibilities

- **Tier 1 (:30000, GPU 0):** Qwen3-30B FP8 — critical path health
- **Tier 2 (:30001, GPU 1):** Qwen3-Coder-80B — reasoning tier health
- **Tier 3 (:30003):** GLM-5.2 offline — secondary R&D; enforce off-peak-only (kill if running during market hours)
- **Tier 3a (:30005):** DeepSeek V4 Pro — PRIMARY long-horizon R&D; enforce off-peak-only (kill if running during market hours)
- REVM :30020, safety services :19001-19005
- **UPS telemetry:** per `~/.openclaw/infra/power_requirements.yaml`
- **GPU schedule:** enforce `~/.openclaw/infra/gpu_schedule.yaml`
- GPSDO: `gps:lbe1420:state` — degraded if PPS lost >5min
- TPM PCR drift vs `/etc/mnemosyne/tpm-baseline`
- Signing node: `signingNode.endpoint/health`
- TITANSPARK (ASUS GX10): utility :30002 failover
- Mac Mini vault: SSH health (metadata only, not signing execution)

## Power-Loss Response

On UPS battery or mains loss → HALT per `risk_kernel/policy.yaml`:
flatten exposure, revoke session keys, CRITICAL alert via HERALD.

## Integration

- Heartbeat: HEARTBEAT.md → FORGE continuous heartbeat (60s)
- Edge mesh Phase 1: EDGE-FRA only