# Environment

This document records the Stage 1 reproduction path. It answers four practical
questions:

1. Which toolchain produced the current artifacts?
2. Which scripts generate which files?
3. How are traces handled locally?
4. Which order keeps raw and derived artifacts aligned?

## Host toolchain

| Component | Version |
| --- | --- |
| OS | Linux (Ubuntu-family, glibc 2.35+) |
| Python | 3.12.12 |
| gcc / g++ | 11.4.0 |
| make | 4.3 |
| matplotlib | 3.10.8 |

## Main terms

- **Raw artifacts**: run-specific outputs under `results/mop_lite/`, such as
  logs, parsed metrics, and epoch traces.
- **Derived artifacts**: cross-run outputs built from raw artifacts, such as
  `data/processed/runs.csv` and `report/tables/*.md`.
- **Smoke mode**: the fastest end-to-end validation mode. It runs two traces
  with short instruction windows.
- **Search mode**: the wider train-side mode used for iteration.
- **Final mode**: the full-suite mode used for stronger evidence.

## Canonical command order

```bash
make -C external/athena -j$(nproc)
python3 scripts/run_mop_lite.py --mode smoke_mode --epoch-trace
python3 scripts/build_dataset.py
python3 scripts/make_figures.py
```

That order reflects the actual data flow.

## What each step produces

| Step | Producer | Main outputs |
| --- | --- | --- |
| Build | `make -C external/athena -j$(nproc)` | `external/athena/bin/champsim` |
| Raw runs | `scripts/run_mop_lite.py` | `results/mop_lite/runs/<run_group_id>/`, `results/mop_lite/manifest.jsonl` |
| Dataset | `scripts/build_dataset.py` | `data/processed/runs.csv`, `data/processed/runs_summary.md` |
| Figures/tables | `scripts/make_figures.py` | `report/figures/*.png`, `report/tables/*.md` |

## Current materialized snapshot

The current workspace already contains a smoke-mode analysis snapshot.

- `data/processed/runs_summary.md` reports 10 runs over 2 traces.
- `report/tables/router_ablation.md` and
  `report/tables/expert_pair_ablation.md` summarize that smoke batch.
- The official broader evaluation design still lives in
  `docs/experiment_setup.md` and `configs/*.json`.

Treat `data/processed/runs.csv` as the analysis entry point for the current
snapshot. Treat `results/mop_lite/runs/<run_group_id>/` as the place to inspect
per-run evidence.

## Trace handling

Athena traces are fetched on demand from Zenodo record `17850673`
(`doi:10.5281/zenodo.17850673`) into `artifacts/athena_traces/`.

The runner resolves trace keys through Athena's `TRACE_DATA` in
`external/athena/scripts/config.py`. It downloads the archive file when the
local copy is missing.

The runner also creates a per-file symlink under `/tmp/mop_athena_traces/`
because ChampSim handles simpler local paths more reliably than long paths with
special characters.

Both project runners default to `--workers 8`, so up to eight simulator
processes may execute concurrently. Use `--workers 1` when a serial run is more
appropriate for debugging or constrained hosts.

## Artifact alignment rule

Keep the three artifact layers in sync.

1. Run `scripts/run_mop_lite.py` to refresh raw artifacts.
2. Run `scripts/build_dataset.py` to refresh `data/processed/runs.csv`.
3. Run `scripts/make_figures.py` to refresh `report/`.

That sequence keeps advisor-facing tables and figures tied to the current raw
run set.

## Reproducibility stamps

Each run record written by `scripts/run_mop_lite.py` includes:

- `run_group_id`
- `git_revision`
- `host`
- `seed`
- `warmup_instructions`
- `simulation_instructions`
- `epoch_len_instructions`
- `mop_total_budget`
- `mop_accuracy_floor`
- `mop_fixed_split_ratio`
- `mop_score_weights`
- full simulator `flags`
- `start_utc`, `end_utc`, and `duration_s`

The frozen split artifact lives in `data/splits/official_v1.json`, with a sha256
stamp in `data/splits/official_v1.sha256`.

## Related documents

- `docs/experiment_setup.md`: official trace suite, split, and run modes.
- `docs/dataset_schema.md`: exact meaning of each dataset column.
- `docs/research_log.md`: what has been run so far and what the results say.
