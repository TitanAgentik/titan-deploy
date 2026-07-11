# Memory System & Extractors — Rock-Solid Contract

> **Scope:** Deploy-time extractors (`scripts/`), runtime memory layout, decision log lifecycle, and the **shadow-only** boundary for DGM-H / Darwin-Godel evolution.  
> **Enforcement:** Code in `titan_safety/` + `promotion_gate.py` + `evolution_freeze.py` — prose alone does not authorize live evolution.

---

## 1. Shadow evolution boundary (never weaken)

DGM-H, GEPA, HyEvo, SIA LoRA, EurekAgent, and GRIS model swaps are **shadow-only** until an operator records explicit **YES** through the promotion gate **and** evolution is **unfrozen**.

| Layer | Mechanism | Live promotion? |
|-------|-----------|-----------------|
| `policy.yaml` | `promotion_gates.shadow_only_evolution` lists `dgm-h`, `gepa`, … | No auto-promote |
| `openclaw.json` | `shadow_evolution_outputs` auto-execute; `evolution_deploy_to_live` human-required | Shadow outputs only |
| `evolution_freeze.py` | `EVOLUTION_FROZEN` flag blocks `evolution_deploy`, `strategy_promotion`, `phase5_go_nogo`, `flash_loan_live` while frozen | Deny until unfreeze |
| `promotion_gate.py` | Requires literal `YES`, stats evidence for evolution categories, constitutional path blocks | Fail-closed |
| Agent routing | `DARWIN_GODEL` → Tier 3 (`:30005` / `:30003`) off-peak R&D only | Never Tier 1/2 live path |

**Invariants (tests:** `tests/test_evolution_shadow.py`, `tests/test_hardening_followups.py`):

1. Frozen + `YES` + strong stats → still **DENY** for `evolution_deploy`.
2. Unfrozen + non-`YES` response → **DENY** (no implicit approval).
3. Constitutional paths (`SOUL.md`, `risk_kernel/`, `kernel.py`, …) → **DENY** even with `YES`.
4. TIMEOUT on promotion prompts → HOLD/de-risk; **never** auto-promote.

CLI: `titan-safety evolution status|freeze|unfreeze` · `titan-safety promotion approve --response YES`

---

## 2. Extractor pipeline contract

Build order (`scripts/build.py`):

```text
normalize → reconcile → extract_bootstrap → extract_skills → extract_memory
  → templates → make_digest → sync_workspace_docs
```

### Input / output

| Script | Input | Output | Exit ≠ 0 when |
|--------|-------|--------|----------------|
| `extract_bootstrap.py` | `output/TITAN.reconciled.md` | `output/bootstrap/*.md` (9 files) | Missing/empty source; per-file or total bootstrap truncation; identifier policy violation; total > 150k bytes |
| `extract_skills.py` | reconciled | `output/workspace/skills/**/SKILL.md` | Missing §K; corrupt UTF-8; truncated `0x…` identifiers |
| `extract_memory.py` | reconciled | `output/memory/**/*.md` | Missing/empty source; identifier violations |
| `make_digest.py` | reconciled | `output/TITAN.digest.md` | Missing/empty reconciled file |

### Determinism & limits

- **Byte limits:** `bootstrapMaxChars` = 20,000 UTF-8 bytes per file; `bootstrapTotalMaxChars` = 150,000.
- **MEMORY.md:** ≤ 100 lines (`MEMORY_MAX_LINES`).
- **Truncation:** Fail-closed — extractors emit `ERROR:` on stderr and exit `1` if bootstrap char/line truncation would occur (no silent tail loss).
- **identifierPolicy=strict:** Output must not contain visibly truncated addresses or tx hashes (`0xabc…`, `0xabc...`). See `scripts/common.py:find_truncated_identifiers`.
- **Schema pointers:** Large JSON schemas in AGENTS are externalized to `refs/AGENTS_schemas.md` via `compact_agents_headroom()` so truncation does not cut enforceable policy.

### Shared helpers (`scripts/common.py`)

- `ExtractorError` — contract violations
- `read_source()` — missing / empty / non-UTF-8 → raise
- `truncate_to_chars()` / `truncate_lines()` — return `(content, was_truncated)`
- `fail_on_truncated_identifiers()` — strict compaction guard

Tests: `tests/test_extractors.py`

---

## 3. Memory layout

### Bootstrap vs runtime vs Honcho

| Store | Path | Loaded when | Writable by agents |
|-------|------|-------------|-------------------|
| Bootstrap pointers | `workspace/MEMORY.md` | Main session only | Operator / extractors |
| Sidecar detail | `workspace/memory/**` | On-demand via pointers | GUARDIAN-gated paths for `memory/risk/` |
| Session scratch | `~/.openclaw/memory/` | Per-session | Session scope |
| Persistent runtime | `/data/openclaw/memory/` | Cross-session | JSONL + DB with audit chain |
| Honcho dialectic | `~/.hermes/` + `honcho.json` | HERALD / HYPERION modeling | **Advisory only** — no trade authority |

**Boundary:** Honcho models operator preferences for messaging; it does **not** replace local decision logs, promotion audit, or risk kernel state.

### Decision log (`decision_log.jsonl`)

- **Path:** `/data/openclaw/memory/decision_log.jsonl` (deploy bundle uses same schema via `titan_safety.audit_chain`)
- **Format:** Append-only JSONL with `content_hash` + `chain_hash` per row
- **Required fields on memory writes:** `ts`, `agent_id`, `rationale` (`decision_log.validate_memory_write`)
- **Rotation:** Max **500 resolved** entries; pending/ambiguous rows never pruned (`decision_log.rotate_decision_log`)
- **Corruption:** `CB_DECISION_LOG_CORRUPT` → restore from `.bak` sibling if backup verifies (`decision_log.repair_decision_log`)

CLI:

```bash
titan-safety audit verify --log /data/openclaw/memory/decision_log.jsonl
titan-safety audit rotate --log /data/openclaw/memory/decision_log.jsonl
titan-safety audit repair --log /data/openclaw/memory/decision_log.jsonl
titan-safety audit ensure --log /data/openclaw/memory/decision_log.jsonl
```

Tests: `tests/test_audit_chain.py`, `tests/test_decision_log.py`

### Checkpoints

```yaml
checkpoint_enabled: true
checkpoint_db: /data/openclaw/memory/decision_checkpoints.db
checkpoint_resume_on_restart: true
checkpoint_clear_on_success: true
```

`CB_CHECKPOINT_STALE` — abandon checkpoint >1h with no progress (see `AGENTS.md`).

---

## 4. Circuit breakers (memory family)

| CB | Trigger | Action |
|----|---------|--------|
| `CB_DECISION_LOG_CORRUPT` | JSONL parse or chain verify fail | Repair from `.bak`, alert |
| `CB_DECISION_LOG_FULL` | >500 resolved without rotation | `audit rotate` / `audit ensure` |
| `CB_REFLECTION_DRIFT` | >5 same-asset systematic errors | Disable pipeline for asset |
| `CB_CHECKPOINT_STALE` | Checkpoint >1h idle | Abandon, restart fresh |

---

## 5. Operator checklist

1. Run `python3 scripts/build.py` after `source/TITAN.md` changes — extractors must exit 0.
2. Run `pytest tests/test_extractors.py tests/test_decision_log.py tests/test_evolution_shadow.py -q`.
3. Before live capital: `titan-safety evolution status` (expect frozen when `capital_profile: live`).
4. Periodically: `titan-safety audit ensure --log /data/openclaw/memory/decision_log.jsonl`.

---

## 6. Related files

| File | Role |
|------|------|
| `templates/safety/titan_safety/evolution_freeze.py` | Live-capital evolution freeze |
| `templates/safety/titan_safety/promotion_gate.py` | Human YES + stats + constitutional blocks |
| `templates/safety/titan_safety/audit_chain.py` | Hash-chained decision log writer |
| `templates/safety/titan_safety/decision_log.py` | Rotation, repair, write validation |
| `templates/risk_kernel/policy.yaml` | `shadow_only_evolution`, `evolution.freeze_during_live` |
| `refs/AGENTS_schemas.md` | Full decision-log JSON schemas |
