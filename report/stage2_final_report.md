# Stage 2 OpenEvolve Final Report

## Executive Read

We built a compact Mixture-of-Prefetchers coordinator on top of Athena's L2C prefetcher infrastructure, then used OpenEvolve to search a tiny policy surface. The selected story is `MLOP + SPP+PPF` at L2C, with `MoP-V1.3` as the evolved sticky-single router.

The strongest claim is train-window gap closing. On the 13-trace train-window confirmation surface, the pre-OpenEvolve `MoP-V1.2` reference reached `0.964637x` vs the pair-best single and `1.047685x` vs no-prefetch. The post-OpenEvolve `MoP-V1.3 sticky 3` seed reached `0.982884x` vs pair-best and `1.066243x` vs no-prefetch. It also beat the weaker expert on `11/13` traces, compared with `9/13` for `MoP-V1.2`, and reduced catastrophic traces from `3/13` to `2/13`.

The heldout result is a modest generalization result. On seven heldout traces, `MoP-V1.3` reached `0.979437x` vs pair-best and `1.003270x` vs no-prefetch. `MoP-V1.2` reached `0.975893x` vs pair-best and `0.998069x` vs no-prefetch. The selected router clears no-prefetch on heldout and remains below the best constituent single, which is a fair outcome for this project because the main comparator hierarchy kept pair-best first.

## What We Built On Athena

Athena provided the simulator, cache hierarchy, existing prefetchers, and the original `AthenaMAB` comparison point. Our contribution is the coordination layer and the evaluation harness around it.

We added router aliases and implementation paths for:

| Name | Meaning | Role |
| --- | --- | --- |
| `MoP-V0` | Original `MoPLite` | Stage 1 baseline router |
| `MoP-V1.1 Guarded` | Original `MoPLiteGuarded` | Stage 1 backup with guardrails |
| `MoP-V1.2 ProbeSingle` | Original `ProbeThenWinner` | Stage 1 finalist and pre-OpenEvolve reference |
| `MoP-V1.3 StickySingle` | OpenEvolve seed family | Stage 2 selected policy family |

The implementation surface for OpenEvolve was deliberately small. Candidates could edit only `candidate_policy()` and return a literal dictionary with router choice, total budget, one-shot epochs, guarded share, sticky margin, and three score weights. The evaluator rejected helper code, imports, file access, trace names, metric-key leakage, unknown policy keys, and malformed evolve blocks.

The important policy that survived confirmation is:

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

## Trace Protocol

Stage 1 selected L2C as the cache level and `MLOP + SPP+PPF` as the expert pair using train/search evidence. Heldout traces stayed reserved for final confirmation. The evidence set used the official split in `data/splits/official_v1.json`: 17 train traces and 7 heldout traces, with 10-trace and 13-trace train/search subsets for OpenEvolve confirmation.

The evaluation comparator hierarchy stayed fixed:

| Comparator | Purpose |
| --- | --- |
| Pair-best constituent single | Primary standard for router quality |
| No-prefetch | Secondary sanity baseline |
| Weaker constituent single | Practical minimum for routing value |
| WinnerTakeAll, OneShotFit, AthenaMAB | Simple coordination baselines |

The trace choice supports the story because `MLOP` and `SPP+PPF` have different strengths, while both can still produce useful speedups on parts of the split. On heldout, `SPP+PPF` is the stronger single overall at `1.023725x` vs no-prefetch, while `MLOP` sits at `0.974379x`. The router lands between the routees on several traces and clears no-prefetch in geomean, which is exactly the balanced-take behavior we wanted to test.

## Pre-OpenEvolve And Post-OpenEvolve Performance

| Surface | Pre-OpenEvolve `MoP-V1.2` | Post-OpenEvolve `MoP-V1.3` | Read |
| --- | ---: | ---: | --- |
| 13-trace train-window vs pair-best | `0.964637` | `0.982884` | large gap close |
| 13-trace train-window vs no-prefetch | `1.047685` | `1.066243` | stronger baseline speedup |
| 13-trace train-window vs weaker expert | `1.096428` | `1.117600` | stronger floor |
| Beats weaker expert | `9/13` | `11/13` | broader practical wins |
| Catastrophic traces vs pair-best | `3/13` | `2/13` | lower tail risk |
| 7-trace heldout vs pair-best | `0.975893` | `0.979437` | small heldout lift |
| 7-trace heldout vs no-prefetch | `0.998069` | `1.003270` | clears baseline |

The 13-trace train-window result also beats the simple coordination baselines:

| Method | Geomean vs pair-best | Geomean vs no-prefetch | Beats weaker | Catastrophic |
| --- | ---: | ---: | ---: | ---: |
| `MoP-V1.3 sticky 3` | `0.982884` | `1.066243` | `11/13` | `2/13` |
| `WinnerTakeAll` | `0.942771` | `1.024749` | `7/13` | `5/13` |
| `OneShotFit` | `0.943456` | `1.026820` | `6/13` | `5/13` |
| `AthenaMAB` | `0.942077` | `1.021295` | `6/13` | `5/13` |

Raw ledger excerpt for the selected train-window contrast:

```json
"candidate": "current-checkout MoP-V1.2 reference", "metrics": {"beats_weaker_rate": 0.6923076923076923, "catastrophic_rate": 0.23076923076923078, "combined_score": -0.03363851952364746, "gm_vs_nopref": 1.0476848980087445, "gm_vs_pair_best": 0.9646368735247647, "gm_vs_weaker": 1.096428499605789, "n_traces": 13.0}
```

```json
"candidate": "post-OpenEvolve MoP-V1.3 sticky 3", "metrics": {"beats_weaker_rate": 0.8461538461538461, "catastrophic_rate": 0.15384615384615385, "combined_score": 0.0025467018402465964, "gm_vs_nopref": 1.0662425357579794, "gm_vs_pair_best": 0.9828844587135206, "gm_vs_weaker": 1.1176001948856458, "n_traces": 13.0}
```

## OpenEvolve Model Scaling

We used small smoke runs first, then scaled with `gpt-5-mini`, `gpt-5.4`, and Claude Sonnet 4.6. Kimi models were absent from the gateway model list for this key, so the expanded comparison used the strongest available gateway models. The largest sweep was the 80-iteration GPT-5 mini run, with 30-iteration sweeps for GPT-5.4 and Sonnet 4.6.

| Model | Best cheap-screen result | 10-trace confirmation |
| --- | ---: | ---: |
| `gpt-5-mini` | `0.940345x` vs pair-best, combined `-0.088985` | `0.979050x`, combined `0.000477` |
| `gpt-5.4` | `0.939387x` vs pair-best, combined `-0.089064` | Screen result trailed promoted hits |
| Claude Sonnet 4.6 | `0.940183x` vs pair-best, combined `-0.088685` | `0.979135x`, combined `0.000481` |

The scaled model search found nearby policies with slightly stronger cheap-screen scores, especially Sonnet 4.6. Wider confirmation kept the frozen `MoP-V1.3 sticky 3` seed because its 10-trace result remained stronger at `0.980137x` vs pair-best and combined `0.001776`.

The malformed and failed candidates are useful evidence about evaluator rigor. The ledger includes command failures from simulator `SIGBUS`, rejected helper/import code, unknown policy keys such as `both_on_rate`, `single_action_rate`, `mop_budget_ratio`, and `mop_budget_multiplier`, and missing evolve markers. These candidates were scored as failed and kept in the ledger.

## Heldout Handling

The `MoP-V1.3` heldout run completed normally in `results/stage2_openevolve/heldout/final_v13_20260429`. The matching `MoP-V1.2` reference completed all 28 raw metric files in `results/stage2_openevolve/heldout/final_v12_reference_20260429`, while the runner exited before writing the full roll-up. I rebuilt its `summary.csv` from the 28 raw metric JSON files using `scripts/rebuild_mop_summary_from_metrics.py`, which calls the same parser and summary writer used by the normal runner. The provenance file is `results/stage2_openevolve/heldout/final_v12_reference_20260429/summary_rebuild_provenance.json`.

That reconstruction changes no metrics. It supplies the missing table layer from complete raw simulator outputs.

## Claims We Can Defend

1. Stage 1 established a clean and conservative expert-pair story at L2C: `MLOP + SPP+PPF` creates a routing problem with meaningful expert spread.
2. Stage 2 OpenEvolve improved the router family on train-window evidence by moving from `MoP-V1.2` to `MoP-V1.3 sticky 3`.
3. The selected router beats no-prefetch in train-window and heldout geomean.
4. The selected router stays below pair-best single in geomean, which keeps the scientific claim honest.
5. The selected router beats simple coordination baselines on the 13-trace train-window surface.
6. Larger OpenEvolve sweeps found stronger cheap-screen hits, and the confirmation path preserved the frozen seed.

The most likely reviewer concern is selection leakage. The trace protocol answers it directly: Stage 1 selected the cache level and pair on train/search evidence, Stage 2 searched only train/search surfaces, and heldout was used after the seed was fixed. The next concern is whether OpenEvolve merely found a fragile number tweak. The evaluator answers that by constraining candidates to a small literal policy dictionary, logging every candidate, and scoring malformed or simulator-failed candidates as failures. The final concern is whether the router beats the best possible routee. Our claim is deliberately narrower: the evolved router closes much of the train-window pair-best gap, clears no-prefetch on heldout, and gives a balanced combined behavior for two routees with different strengths.

## Artifacts

| Artifact | Path |
| --- | --- |
| Final metrics table | `report/tables/stage2_final_metrics.md` |
| Scaled model table | `report/tables/stage2_scale_model_summary.md` |
| Pre/post geomean figure | `report/figures/stage2_pre_post_geomean.png` |
| Heldout trace profile figure | `report/figures/stage2_heldout_trace_profile.png` |
| Model comparison figure | `report/figures/stage2_model_comparison.png` |
| Scaled model figure | `report/figures/stage2_scale_model_comparison.png` |
| Stage 2 evaluator | `stage2/openevolve/evaluator.py` |
| Candidate ledger | `stage2/openevolve/candidate_ledger.jsonl` |
| Frozen policy seed | `stage2/openevolve/initial_policy.py` |
| Slide deck | `slides/mop_stage2_final/output/output.pptx` |
| Slide deck previews | `slides/mop_stage2_final/scratch/slide-01.png` through `slide-08.png` |
| Slide deck quality report | `slides/mop_stage2_final/scratch/quality-report.json` |
