# Mixture-of-Prefetchers

This repository builds a small router on top of the Athena simulator to coordinate two L2-cache prefetchers. The current finished story uses `MLOP + SPP+PPF` at L2C and an OpenEvolve-selected router called `MoP-V2`.

Start with the final report:

1. `report/stage2_final_report.md`
2. `slides/mop_stage2_final/output/output.pptx`
3. `report/writing_logistics.md`

## Current Result

All headline performance is IPC speedup relative to disabled prefetching. The best expert is shown separately and computed as `max(MLOP, SPP+PPF)` on each trace.

| Evaluation set | Selected router | Speedup vs disabled prefetching | Best expert |
| --- | --- | ---: | ---: |
| 13-trace training-split validation | `MoP-V2` | `1.066x` | `1.085x` |
| 7-trace heldout | `MoP-V2` | `1.003x` | `1.024x` |

The manual reference router is `MoP-V1`. It reaches `1.048x` on the same 13-trace training-split validation set and `0.998x` on heldout.

## What We Added To Athena

Athena provides the simulator, cache hierarchy, prefetchers, and baseline machinery. This repo adds:

- an epoch-based L2C router for two constituent prefetchers
- MoP router variants `MoP-V1` and `MoP-V2`
- per-expert issued/useful counters and budget controls
- fixed train and heldout split handling
- an OpenEvolve policy-search sandbox
- candidate records, generated tables, generated figures, and a slide deck

## Trace Protocol

The official split has 24 traces:

- 17 training traces
- 7 heldout traces

OpenEvolve search used training traces. The quick evaluator used 3 training traces, wider validation used 10 training traces, and final training-split validation used the 13 locally available training traces with complete artifacts in this checkout. The four other training traces in the official split are `facesim`, `ligra_BFS`, `ligra_Triangle`, and `secret_compute_int_243`. Heldout evaluation used the 7 frozen heldout traces after policy selection.

Simulation windows:

- quick and training-split validation runs: `500K` warmup, `1M` simulation
- heldout runs: `20M` warmup, `50M` simulation
- router epoch length: `500K` retired instructions

## Router Names

| Name | Meaning |
| --- | --- |
| `MoP-V1` | one-epoch probe, then higher-scoring expert selection |
| `MoP-V2` | OpenEvolve-tuned `MoP-V1` with an evolved budget, score weights, and close-score tie margin |

The selected `MoP-V2` policy uses a `9216` per-epoch prefetch budget, about `18.4` prefetches per 1K retired instructions over a `500K`-instruction epoch. It also uses one initial dual-expert probe epoch, an accuracy floor of `30`, a `3%` close-score tie margin, and score weights `[1.0, 0.55, 1.0]` for accuracy, coverage, and traffic terms.

## OpenEvolve Runs

The candidate record contains 374 rows:

- 306 valid scored rows
- 68 fail-closed rows

The larger model sweeps requested:

- GPT-5 mini: 80 iterations
- GPT-5.4: 80 iterations
- Sonnet 4.6: 30 iterations

The repo records iterations, candidates, simulator outcomes, and generated artifacts. Gateway dollar billing should be read from the CMU AI Gateway dashboard.

## Rebuilding The Report Assets

```bash
python3 scripts/make_stage2_final_assets.py \
  --heldout-v12 results/stage2_openevolve/heldout/final_v12_reference_20260429 \
  --heldout-v13 results/stage2_openevolve/heldout/final_v13_20260429
```

Raw simulator outputs live under ignored `results/...` paths on the producing machine. The committed report, tables, figures, candidate records, and slide deck are the portable evidence package.

## Repository Map

- `external/athena/`: vendored Athena and ChampSim-derived simulator
- `scripts/run_mop_lite.py`: main experiment runner
- `scripts/make_stage2_final_assets.py`: final report table and figure builder
- `stage2/openevolve/evaluator.py`: OpenEvolve evaluator
- `stage2/openevolve/candidate_ledger.jsonl`: candidate record file
- `report/`: report, figures, tables, and writing logistics
- `slides/mop_stage2_final/`: presentation source, previews, and PowerPoint output
