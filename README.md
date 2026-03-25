# Mixture-of-Prefetchers

Project workspace for evaluating L2 prefetcher coordination on top of upstream simulators.

## Submodules

- `external/athena`: upstream Athena simulator and scripts from CMU SAFARI
- `external/openevolve`: upstream OpenEvolve optimizer

Initialize or refresh submodules with:

```bash
git submodule update --init --recursive
```

## Single-Prefetcher Baselines

The smallest local workflow is the project-side runner below. It builds Athena once, downloads only the requested official Athena traces from Zenodo, runs a small baseline suite locally, and writes a flat summary.

```bash
python3 scripts/run_single_prefetcher_baselines.py
```

Defaults:

- Traces: `fluidanimate` and `streamcluster` Athena traces
- Experiments: `Baseline`, `Pythia`, `SPP+PPF`, `MLOP`, `SMS`
- Window: `20M` warmup + `50M` simulation instructions

Outputs:

- raw logs: `results/single_prefetcher_baselines/logs/`
- parsed CSV: `results/single_prefetcher_baselines/summary.csv`
- short Markdown report: `results/single_prefetcher_baselines/summary.md`

Use `--help` to override traces, experiments, or instruction counts.

## MoP-lite

Athena is vendored in-tree under `external/athena` because this project expects substantial local simulator edits.
The original upstream is documented in [UPSTREAM.md](/Users/barry/Library/Mobile Documents/com~apple~CloudDocs/Carnegie Mellon/15740/Proj/Mixture-of-Prefetchers/external/athena/UPSTREAM.md).

The pre-OpenEvolve path is wired through:

```bash
python3 scripts/run_mop_lite.py
```

Defaults:

- Experts: `Pythia` + `SPP+PPF`
- Routers: `FixedSplit`, `WinnerTakeAll`, `RandomRouter`, `OneShotFit`, `MoPLite`
- Traces: two small Athena PARSEC traces
- Window: `5M` warmup + `10M` simulation instructions

Outputs:

- raw logs: `results/mop_lite/logs/`
- parsed metrics: `results/mop_lite/metrics/`
- summary: `results/mop_lite/summary.csv`
- optional epoch traces: `results/mop_lite/epoch_logs/` with `--epoch-trace`

This stage intentionally stops before OpenEvolve. It only exercises the hand-written MoP-lite routers and the single-prefetcher baselines needed to compare against them.
