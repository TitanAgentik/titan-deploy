# §FORTRESS_detail.md — Perimeter Hardening

> Companion for host / edge / vault perimeter. Complements AEGIS (in-process DENY).

## Pillar: Impenetrable (perimeter)

Complements AEGIS L1–L6 with host / edge / vault hardening.

## Scope

- Protectli / OPNsense / Suricata perimeter (ops-installed)
- Headscale mesh for operator + edge PoPs
- UPS-protected signing path (power_requirements.yaml)
- Air-gapped staging for promotions (`airGappedStaging: true`)
- Mac Mini vault metadata only — never live signing

## Hardening checklist

1. Signing node: minimal OS, no evolution workloads, UPS, TPM-SPI PCR baseline
2. Agent FS cannot write `control_plane.secret` or `kill_switch.secret`
3. Staging dir isolated from live skills/
4. Edge workers: stateless, no LLM, same-AZ as exchange matching engines
5. Cockpit: Tailscale / SSH tunnel only — never raw public admin UI

## See also

- `refs/AEGIS_detail.md`
- `infra/signing_node.yaml`, `infra/network_topology.yaml`, `infra/power_requirements.yaml`
