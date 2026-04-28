# Environment

This document records the Stage 1 and Stage 2 reproduction path. It answers four practical
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

- **Raw artifacts**: run-specific outputs under result roots such as
  `results/mop_lite_search/`, `results/mop_lite_final/`, or another explicit
  `--results-dir`, including logs, parsed metrics, and epoch traces.
- **Derived artifacts**: cross-run outputs built from raw artifacts, such as
  `data/processed/runs.csv` and `report/tables/*.md`.
- **Smoke mode**: the fastest end-to-end validation mode. It runs two traces
  with short instruction windows.
- **Search mode**: the wider train-side mode used for iteration.
- **Final mode**: the full-suite mode used for stronger evidence.
- **Open Evolve mode**: Stage 2 evaluation mode. Runs `OpenEvolve` (router
  type 5), `MoPLite`, and `WinnerTakeAll` on the `search_subset` traces at
  search-mode instruction windows. Produces manifests under
  `results/open_evolve_search/` intended for comparison against Stage 1
  MoPLite results.

## Canonical command order

**Stage 1 (baseline):**

```bash
make -C external/athena -j$(nproc)
python3 scripts/run_mop_lite.py --mode search_mode --workers 15 --results-dir results/mop_lite_search
python3 scripts/run_mop_lite.py <heldout trace list and flags> --workers 15 --results-dir results/mop_lite_final
python3 scripts/build_dataset.py --manifest results/mop_lite_search/manifest.jsonl --manifest results/mop_lite_final/manifest.jsonl
python3 scripts/make_figures.py
```

**Stage 2 / Open Evolve:**

```bash
make -C external/athena -j$(nproc)
python3 scripts/run_mop_lite.py --mode open_evolve_mode --workers 15 --results-dir results/open_evolve_search
# After reviewing search-side results, run held-out:
python3 scripts/run_mop_lite.py \
  --trace 437.leslie3d-134B --trace 459.GemsFDTD-1169B --trace 471.omnetpp-188B \
  --trace parsec_2.1.canneal.simlarge.prebuilt.drop_4750M.length_250M \
  --trace parsec_2.1.streamcluster.simlarge.prebuilt.drop_0M.length_250M \
  --trace ligra_BC.com-lj.ungraph.gcc_6.3.0_O3.drop_500M.length_250M \
  --trace secret_compute_fp_105 \
  --warmup-instructions 20000000 --simulation-instructions 50000000 \
  --expert-0 Pythia --expert-1 "SPP+PPF" \
  --router OpenEvolve --router MoPLite --builtin AthenaMAB \
  --workers 15 --skip-download --epoch-trace \
  --results-dir results/open_evolve_final
python3 scripts/build_dataset.py \
  --manifest results/mop_lite_search/manifest.jsonl \
  --manifest results/mop_lite_train_extra/manifest.jsonl \
  --manifest results/mop_lite_final/manifest.jsonl \
  --manifest results/open_evolve_search/manifest.jsonl \
  --manifest results/open_evolve_final/manifest.jsonl
python3 scripts/make_figures.py
```

## What each step produces

| Step | Producer | Main outputs |
| --- | --- | --- |
| Build | `make -C external/athena -j$(nproc)` | `external/athena/bin/champsim` |
| Raw runs | `scripts/run_mop_lite.py` | `<results-dir>/runs/<run_group_id>/`, `<results-dir>/manifest.jsonl` |
| Dataset | `scripts/build_dataset.py` | `data/processed/runs.csv`, `data/processed/runs_summary.md` |
| Figures/tables | `scripts/make_figures.py` | `report/figures/*.png`, `report/tables/*.md` |

## Provenance of the pipeline

The build step compiles the Athena simulator foundation under `external/athena/`.
That simulator comes from upstream Athena, documented in
`external/athena/UPSTREAM.md`, plus local project edits in files such as
`external/athena/src/oogway.cc`.

The run, dataset, and report steps are project-side workflow code in `scripts/`
and `docs/`. Those steps are the project-owned evidence pipeline built on top of
Athena.

## Current materialized snapshot

The current workspace contains the merged full-suite Stage 1 results.

- `data/processed/runs_summary.md` reports 230 runs over 24 traces.
- `report/tables/router_ablation.md` summarizes coordinator geomeans for the
  full 17-trace training split and the 7-trace held-out split.
- `report/tables/expert_pair_ablation.md` summarizes the committed
  `Pythia + SPP+PPF` pair across those runs.

Treat `data/processed/runs.csv` as the analysis entry point for the current
snapshot. Treat `results/mop_lite_search/runs/<run_group_id>/`,
`results/mop_lite_train_extra/runs/<run_group_id>/`, and
`results/mop_lite_final/runs/<run_group_id>/` as the places to inspect the
committed per-run evidence.

## Trace handling

Athena traces are fetched on demand from Zenodo record `17850673`
(`doi:10.5281/zenodo.17850673`) into `artifacts/athena_traces/`.

The runner resolves trace keys through Athena's `TRACE_DATA` in
`external/athena/scripts/config.py`. It downloads the archive file when the
local copy is missing.

The runner also creates a per-file symlink under `/tmp/mop_athena_traces/`
because ChampSim handles simpler local paths more reliably than long paths with
special characters.

Both project runners default to `--workers 8`, but the completed Stage 1 search
and held-out batches were run with `--workers 15` on this host to reduce wall-
clock time. Use `--workers 1` when a serial run is more appropriate for
debugging or constrained hosts.

## Artifact alignment rule

Keep the three artifact layers in sync.

1. Run one or more `scripts/run_mop_lite.py` batches, each with its own
   `--results-dir`, to refresh raw artifacts.
2. Run `scripts/build_dataset.py` with the manifests you want merged to refresh
   `data/processed/runs.csv`.
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
- `mop_winner_isolation_threshold` (OpenEvolve only; absent for other routers)
- full simulator `flags`
- `start_utc`, `end_utc`, and `duration_s`

`run_group_id` identifies one invocation of `run_mop_lite.py`. The dataset
builder computes speedups within each complete `run_group_id` and rejects
incomplete run groups instead of silently mixing partial reruns.

The frozen split artifact lives in `data/splits/official_v1.json`, with a sha256
stamp in `data/splits/official_v1.sha256`.

## Related documents

- `docs/operational/experiment_setup.md`: official trace suite, split, and run modes.
- `docs/operational/dataset_schema.md`: exact meaning of each dataset column.
- `docs/operational/research_log.md`: what has been run so far and what the results say.
