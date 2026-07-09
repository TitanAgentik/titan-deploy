# Quantum-Inspired Lane Selection (Offline)

**Status:** advisory only — `live_path: false`, `backend: classical_sa`

Classical QUBO + simulated annealing for pipeline/lane subset selection.
Compares against fractional-Kelly `CapitalAllocator` for R&D; **not wired to live gates**.

## Constraints

- No cloud QPU, no `quantum.enabled` policy changes
- Stdlib-only module: `titan_safety/quantum_inspired.py`
- Dormant quantum agents (QCC/QSA/QRP) remain unused

## CLI

```bash
titan-safety qi demo --seed 42 --k 4
titan-safety qi optimize --lanes-json '[{...}]' --k 4 --compare-kelly
```

## QUBO objective

- Reward: normalized edge/variance per lane (Kelly-like signal)
- Penalty: variance (`risk_lambda`), same-cluster pairs (`cluster_penalty`)
- Cardinality: soft constraint toward `k` active lanes

See: `refs/RESEARCH_detail.md`, `titan-safety allocator plan`
