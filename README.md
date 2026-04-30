# Mixture-of-Prefetchers

This repository builds a small router on top of the Athena simulator to coordinate two L2-cache prefetchers. The current finished story uses `MLOP + SPP+PPF` at L2C and an OpenEvolve-selected router called `MoP-V1.3`.

Start with the final report:

1. `report/stage2_final_report.md`
2. `slides/mop_stage2_final/output/output.pptx`
3. `report/writing_logistics.md`

## Current Result

All headline performance is IPC speedup relative to disabled prefetching. The oracle best prefetcher is shown separately as a cap, computed as `max(MLOP, SPP+PPF)` on each trace.

| Surface | Selected router | Speedup vs disabled prefetching | Oracle best cap |
| --- | --- | ---: | ---: |
| 13-trace training validation | `MoP-V1.3` | `1.066243x` | `1.084810x` |
| 7-trace heldout | `MoP-V1.3` | `1.003270x` | `1.024333x` |

The manual reference router is `MoP-V1.2`. It reaches `1.047685x` on the same 13-trace training-validation surface and `0.998069x` on heldout.

## What We Added To Athena

Athena provides the simulator, cache hierarchy, prefetchers, and baseline machinery. This repo adds:

- an epoch-based L2C router for two constituent prefetchers
- MoP router variants `MoP-V1.1`, `MoP-V1.2`, and `MoP-V1.3`
- per-expert issued/useful counters and budget controls
- fixed train and heldout split handling
- an OpenEvolve policy-search sandbox
- candidate ledgers, generated tables, generated figures, and a slide deck

## Trace Protocol

The official split has 24 traces:

- 17 training traces
- 7 heldout traces

OpenEvolve search used training traces. The quick evaluator used 3 training traces, wider validation used 10 training traces, and final training validation used the 13 training traces available in this checkout. Heldout evaluation used the 7 frozen heldout traces after policy selection.

Simulation windows:

- quick and training-validation runs: `500K` warmup, `1M` simulation
- heldout runs: `5M` warmup, `10M` simulation
- router epoch length: `500K` retired instructions

## Router Names

| Name | Meaning |
| --- | --- |
| `MoP-V1.1` | guarded router with budget-share protection |
| `MoP-V1.2` | one-epoch probe, then higher-scoring expert selection |
| `MoP-V1.3` | `MoP-V1.2` plus a sticky margin for close expert scores |

The selected `MoP-V1.3` policy is:

```python
{
    "router": "MoP-V1.3",
    "mop_total_budget": 9216,
    "mop_one_shot_epochs": 1,
    "mop_accuracy_floor": 30,
    "mop_guarded_min_budget_share": 10,
    "mop_sticky_margin_pct": 3,
    "mop_score_weights": [1.0, 0.55, 1.0],
}
```

## OpenEvolve Runs

The candidate ledger contains 290 rows:

- 225 valid scored rows
- 65 fail-closed rows

The larger model sweeps requested:

- GPT-5 mini: 80 iterations
- GPT-5.4: 30 iterations
- Sonnet 4.6: 30 iterations

The repo records iterations, candidates, simulator outcomes, and generated artifacts. Gateway dollar billing should be read from the CMU AI Gateway dashboard.

## Rebuilding The Report Assets

```bash
python3 scripts/make_stage2_final_assets.py \
  --heldout-v12 results/stage2_openevolve/heldout/final_v12_reference_20260429 \
  --heldout-v13 results/stage2_openevolve/heldout/final_v13_20260429
```

Raw simulator outputs live under ignored `results/...` paths on the producing machine. The committed report, tables, figures, ledgers, and slide deck are the portable evidence layer.

## Repository Map

- `external/athena/`: vendored Athena and ChampSim-derived simulator
- `scripts/run_mop_lite.py`: main experiment runner
- `scripts/make_stage2_final_assets.py`: final report table and figure builder
- `stage2/openevolve/evaluator.py`: OpenEvolve evaluator
- `stage2/openevolve/candidate_ledger.jsonl`: candidate audit ledger
- `report/`: report, figures, tables, and writing logistics
- `slides/mop_stage2_final/`: presentation source, previews, and PowerPoint output
