# §MODELS_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `MODELS_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Reconciled model tier architecture (critical path unchanged).
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Tiers (reconciled)

| Tier | Port | Model | Role |
|------|------|-------|------|
| 1 | `:30000` | Qwen3-30B-A3B FP8 | Signals, risk, execution (critical) |
| 2 | `:30001` | Qwen3-Coder-Next-80B | Orchestration, strategy, code |
| 3a | `:30005` | DeepSeek V4 Pro | Primary R&D / long-horizon |
| 3b | `:30003` | GLM-5.2 | Secondary R&D |
| Embed | `:30004` | Qwen3-Embedding | Memory search / embedder |

**Never** put GLM/DeepSeek on TRENCH-OPS / GUARDIAN / EXECUTOR live path.

Heterogeneous BFT: GUARDIAN→Qwen30B, ARCHON→Qwen-Coder, CORTEX→DeepSeek.
