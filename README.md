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
