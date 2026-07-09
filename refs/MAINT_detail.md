# §MAINT_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `MAINT_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Maintenance / update / ZFS rollback narrative.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Status

The original companion body was **not included** in the TITAN.md dump shipped to
this machine. Narrative / research content remains in `output/TITAN.reconciled.md`
under related sections.

## See also

- `templates/infra/titanhome_ubuntu_install.md`
- Health: `curl :19003/health`

## Operator note

Do not block OpenClaw/Hermes startup on this file. Bootstrap context is the
`workspace/*.md` set; this companion is reference-only.
