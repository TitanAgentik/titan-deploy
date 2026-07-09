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

- **Tier 1 (:30000, GPU 0):** Qwen3-30B FP8 — critical path; parallel 12, prewarm, p95 TTFT <300ms
- **Tier 2 (:30001, GPU 1):** Qwen3-Coder-80B — must NOT block Tier 1 (separate GPU + MPS partition)
- **Embedder (:30004):** ride-along GPU 0 — p95 <15ms; memory/rerank only
- **Tier 3a (:30005):** DeepSeek V4 Pro — PRIMARY R&D; kill if running during market hours
- **Tier 3 (:30003):** GLM-5.2 — secondary R&D; kill if running during market hours
- **CUDA MPS:** enforce partitions per `cuda-mps.conf`; run `forge_gpu_schedule_enforce.sh` each heartbeat
- **Latency budget:** `~/.openclaw/infra/latency_budget.yaml` — alert on breach
- **Edge RTT probes:** `~/.openclaw/infra/edge_rtt_probe.yaml` — log p50/p95 to `memory/infra/rtt.jsonl`
- REVM :30020, safety services :19001-19008
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

## Heartbeat Procedure (60s)

1. **Inference health:** curl `:30000/health`, `:30001/health`, `:30004/health` — TTFT probe if cold
2. **MPS enforce:** `bash ~/.openclaw/infra/forge_gpu_schedule_enforce.sh --dry-run` then apply if drift
3. **Edge RTT:** run probes from `edge_rtt_probe.yaml`; append JSONL to `memory/infra/rtt.jsonl`
4. **Latency budget:** compare live metrics vs `latency_budget.yaml`; CRITICAL if gate p95 >150ms or home→FRA p95 >100ms
5. **Chrony:** `chronyc tracking` — offset must be <500µs with GPSDO; warn if PPS lost >5min
6. **GPU schedule:** kill Tier 3/3a if market-hours window active per `gpu_schedule.yaml`

## Integration

- Heartbeat: HEARTBEAT.md → FORGE continuous heartbeat (60s)
- Edge mesh Phase 1: EDGE-FRA only