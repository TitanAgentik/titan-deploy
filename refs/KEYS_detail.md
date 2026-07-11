# §KEYS_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `KEYS_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Key custody / signing isolation — no secrets. Points at infra specs.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Principles

1. Never store session keys or seeds in agent memory / workspace markdown.
2. Signing only via in-process `titan_safety.SigningNode` with fresh `X-Titan-Gate-Receipt`.
3. Mac Mini vault = metadata + Trezor ceremonies; not the live signer.
4. Live capital: `withdrawal_adapter: trezor_signing` (not mock).
5. Control-plane HMAC secret: `~/.openclaw/safety/control_plane.secret` mode 0600.

## Specs

- `templates/infra/signing_node.yaml`
- `templates/infra/power_requirements.yaml` (UPS on signing path)
- `templates/openclaw.json` → `signingNode`

## Operator checklist

- [ ] Trezor / hardware wallet provisioned
- [ ] In-process signing OK (`signingNode.mode: in_process`; do not require `:19010`)
- [ ] Gate receipt required (`requireGateReceipt: true`)
- [ ] Exchange API keys: trade-only, withdrawal disabled where possible
