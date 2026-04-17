# Candidate trace inventory

This document records **where candidate traces come from** in this repository and how they relate to the runners.

## Sources

| Source | What it defines |
| --- | --- |
| `external/athena/scripts/config.py` | `TRACE_DATA`: authoritative map of trace **keys** → file paths, workload type (`SPEC`, `PARSEC`, `LIGRA`, `CVP`), and `adverse` flag |
| `scripts/run_single_prefetcher_baselines.py` | Default traces (`DEFAULT_TRACES`), Zenodo record `17850673`, `--trace` repeated for selection |
| `scripts/run_mop_lite.py` | Same `--trace` mechanism; defaults to `DEFAULT_TRACES` from baselines script |
| Athena README (`external/athena/README.md`) | States the Zenodo bundle contains **100** traces matching the four suites in `TRACE_DATA` |

## Candidate pool size

- **100 trace keys** in `TRACE_DATA` (49 SPEC, 13 PARSEC, 13 LIGRA, 25 CVP as counted from `config.py`).
- The Zenodo API for record `17850673` reports **100 files**, consistent with “one archive file per config entry” for project download URLs (`scripts/run_single_prefetcher_baselines.py` builds URLs from the filename under `traces/`).

## Trace selection mechanism

1. Pass Athena trace keys (not filesystem paths) with repeated `--trace` flags.
2. Runners resolve keys via `TRACE_DATA`, download from Zenodo if missing (unless `--skip-download`), and place files under `artifacts/athena_traces/`.
3. Instruction windows are set by `--warmup-instructions` and `--simulation-instructions` on the project runners (they replace the `BASE` flags in `EXP_VARIABLES`); per-trace `knobs` in `TRACE_DATA` are not applied by these project scripts in the same way Athena’s Slurm pipeline might.

## Full candidate list (keys)

All keys are the string keys of `TRACE_DATA` in `external/athena/scripts/config.py`. For a machine-readable list:

```bash
python3 -c "import importlib.util; from pathlib import Path; p=Path('external/athena/scripts/config.py'); s=importlib.util.spec_from_file_location('c',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('\n'.join(sorted(m.TRACE_DATA.keys())))"
```

(Run from the repository root.)

## Notes on support and uncertainty

| Topic | Note |
| --- | --- |
| **Zenodo vs local** | If a trace is in `TRACE_DATA`, the project assumes it can be fetched from Zenodo `17850673` using the basename of `path` under `traces/`. This matches Athena’s published bundle. |
| **CVP “secret” names** | Keys like `secret_compute_int_12` map to `compute_int_12.champsim.gz` on disk; the “secret” prefix is naming in `TRACE_DATA`, not a separate download location. |
| **Per-trace knobs** | PARSEC/LIGRA/CVP entries often include `knobs` with 100M/150M-style defaults in Athena’s config; the project runners **override** warmup/sim via CLI. Documented in `docs/operational/experiment_setup.md`. |
| **Benchmark family** | Families (e.g. multiple `streamcluster` drops) are **inferred** from name prefixes unless otherwise stated; use exact `TRACE_DATA` keys in configs. |

## Relation to the official suite

The **official** MoP-lite suite (24 traces), train/held-out split, and search subset are **not** the full 100-trace pool; they are a deliberate subset recorded in `configs/trace_suites.json`. See `docs/operational/experiment_setup.md`.
