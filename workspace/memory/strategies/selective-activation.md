# Selective activation — keep it simple

TITAN source and companions list many pipelines, skills, agents, and security modules.
That is a **catalog**, not a requirement to run everything.

## Rules

1. Enable only what current capital, phase, and operator intent need.
2. Allocator `max_active_pipelines` (default **4**) is the hard concentration cap.
3. Security: **Impenetrable always**; **Evasion + Stalking + Predatory armed by default** (`ghost_evasion` + `security_ops`). Live DEX only via shielded routes — public RPC forbidden.
4. New pipeline / skill / PoP = human YES (or promotion gate) — never auto-expand the set.
5. Prefer fewer HEALTHY lanes over many marginal ones.
6. **P22 Memecoin Trench** requires human YES + live profile + `memecoinTrench.enabled` — never auto-activate from catalog mention.

## See

- SOUL.md — Voice + Operational Doctrine
- iron-laws.md §14
- USER.md Preferences
- `risk_kernel/policy.yaml` allocator.selective_activation
- `openclaw.json` autonomy.selectiveActivation
- `memory/strategies/memecoin-trench.md`
