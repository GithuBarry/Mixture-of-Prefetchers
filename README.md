# Mixture-of-Prefetchers

This repository is a Stage 1 systems-research baseline for **two-expert L2
prefetcher coordination** on top of the Athena simulator.

The concrete question is:

> Can a small epoch-based controller coordinate two strong L2 prefetchers under
> explicit traffic and usefulness constraints, and beat fair baselines?

The current answer is:

- **yes, sometimes against no-prefetch**
- **not yet against the strongest single expert of the coordinated pair**

That negative result is still useful. The repo now contains the full baseline
package needed for Stage 2: working code, fixed splits, manifests, processed
data, figures, tables, and human-written logs.

## Current readout

Completed Stage 1 evidence currently covers:

- `10` train-side search traces
- `7` held-out traces
- `167` total completed runs in `data/processed/runs.csv`

Held-out-first summary:

- against **no-prefetch**, the strongest held-out coordinator is `AthenaMAB` at
  `1.0378x`
- against the **pair-best single expert** (`Pythia` / `SPP+PPF`), no coordinator
  reaches `1.0x`; the strongest is `AthenaMAB` at `0.9560x`
- `MoPLite` reaches `0.9974x` vs no-prefetch and `0.9188x` vs pair-best single
  on held-out

Train-side search subset summary:

- vs no-prefetch, `WinnerTakeAll` is strongest at `1.0111x`
- vs pair-best single, no coordinator reaches `1.0x`; `WinnerTakeAll` is
  strongest at `0.9750x`
- `MoPLite` reaches `1.0009x` vs no-prefetch and `0.9652x` vs pair-best single

So the current `MoPLite` rule is **not** the strongest coordinator in this repo,
and it does **not** beat the pair-best single expert in geomean on either split.

## What this means

Stage 1 succeeds as a **baseline and measurement foundation**, not as a
headline coordination win.

What is established:

- the simulator path is working and reproducible
- the two-expert control surface is implemented and logged
- the split protocol is frozen and respected
- coordinator baselines are compared under one fair protocol
- some coordinators deliver small `1+x` wins vs no-prefetch
- the current `Pythia + SPP+PPF` rules lose in geomean to the pair-best single

That is enough to justify Stage 2 optimization without overselling Stage 1.

## What to look at

Start here:

1. `docs/outsider_guide.md`
2. `report/draft.md`
3. `report/figures/ipc_speedup_summary.png`
5. `report/tables/router_ablation.md`

Key source-of-truth files:

- project guide: `docs/outsider_guide.md`
- operational index: `docs/README.md`
- split and run modes: `configs/trace_suites.json`, `configs/run_modes.json`
- environment and artifact flow: `docs/operational/environment.md`
- dataset schema: `docs/operational/dataset_schema.md`
- research log: `docs/operational/research_log.md`
- transparency log: `docs/operational/transparency_log.md`

## Repository structure

- `external/athena/`: vendored Athena / ChampSim simulator
- `scripts/run_mop_lite.py`: main experiment runner
- `scripts/build_dataset.py`: manifest + metrics -> `data/processed/runs.csv`
- `scripts/make_figures.py`: `runs.csv` -> report figures and tables
- `data/processed/`: merged Stage 1 dataset
- `report/`: draft report, figures, and tables

## Artifact flow

The evidence chain is simple and strict:

1. `scripts/run_mop_lite.py` writes raw artifacts and an append-only manifest
2. `scripts/build_dataset.py` turns manifests + metrics into `runs.csv`
3. `scripts/make_figures.py` rebuilds all report figures/tables from `runs.csv`

That separation is deliberate:

- `results/` = raw evidence
- `data/processed/` = analysis entry point
- `report/` = presentation layer

## Reproducing the completed Stage 1 dataset

```bash
git submodule update --init --recursive
make -C external/athena -j$(nproc)

# search-side batch
python3 scripts/run_mop_lite.py --mode search_mode --workers 15 --results-dir results/mop_lite_search

# held-out batch
python3 scripts/run_mop_lite.py --trace 437.leslie3d-134B --trace 459.GemsFDTD-1169B --trace 471.omnetpp-188B --trace parsec_2.1.canneal.simlarge.prebuilt.drop_4750M.length_250M --trace parsec_2.1.streamcluster.simlarge.prebuilt.drop_0M.length_250M --trace ligra_BC.com-lj.ungraph.gcc_6.3.0_O3.drop_500M.length_250M --trace secret_compute_fp_105 --warmup-instructions 20000000 --simulation-instructions 50000000 --expert-0 Pythia --expert-1 SPP+PPF --router FixedSplit --router WinnerTakeAll --router RandomRouter --router OneShotFit --router MoPLite --builtin AthenaMAB --single-baseline MLOP --single-baseline SMS --workers 15 --skip-download --results-dir results/mop_lite_final

# merged dataset + figures
python3 scripts/build_dataset.py --manifest results/mop_lite_search/manifest.jsonl --manifest results/mop_lite_final/manifest.jsonl
python3 scripts/make_figures.py
```

## Upstream vs local work

Upstream Athena provides:

- the simulator foundation
- single-expert prefetchers such as `Pythia`, `SPP+PPF`, `MLOP`, `SMS`
- Athena's builtin `AthenaMAB` coordinator

This repository adds:

- the scoped Stage 1 protocol
- local `oogway.cc` changes for the MoP-lite study
- simple router baselines (`FixedSplit`, `WinnerTakeAll`, `RandomRouter`, `OneShotFit`, `MoPLite`)
- manifests, dataset building, figure generation, and advisor-facing docs

## Bottom line

If you want the shortest honest summary:

- **the baseline is real and reproducible**
- **the current `MoPLite` rule is not yet better than the strongest single expert**
- **Stage 2 should optimize the control surface, not re-litigate the measurement setup**
