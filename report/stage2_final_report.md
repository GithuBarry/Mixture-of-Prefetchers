# Mixture-of-Prefetchers OpenEvolve Report

## Executive Read

We used OpenEvolve, a large-language-model program search framework, to tune a compact router that chooses between two Athena L2-cache prefetchers. The expert pair is `MLOP + SPP+PPF` at L2C. The final router is `MoP-V1.3`, a sticky single-expert router selected by OpenEvolve.

All performance numbers in this report use disabled prefetching as `1.0x`. The per-trace oracle best prefetcher is shown as a cap: for each trace, it is `max(MLOP, SPP+PPF)`, then geomeaned across the trace set. The router is judged by how close it gets to that cap while staying above disabled prefetching.

The main result is a stronger 13-trace training-validation router. The manual `MoP-V1.2` router reaches `1.047685x` IPC speedup over disabled prefetching. The OpenEvolve-selected `MoP-V1.3` router reaches `1.066243x`. The oracle cap on the same traces is `1.084810x`, so `MoP-V1.3` reaches `0.982884x` of the cap. It also beats the worse constituent prefetcher on `11/13` traces and has `2/13` traces below `0.95x` of the cap.

The heldout result is smaller and still positive by the disabled-prefetching baseline. On seven heldout traces, `MoP-V1.3` reaches `1.003270x` over disabled prefetching. The oracle cap is `1.024333x`, and `MoP-V1.3` reaches `0.979437x` of that cap. This is a modest generalization result, and it is the right claim size for the data.

The IPC result comes from cycle reduction under a fixed instruction window. On the 13-trace training-validation run, `MoP-V1.3` has instruction-count ratio `0.999999462x` and cycle-count ratio `0.937877x` relative to disabled prefetching. On heldout, the instruction-count ratio is `1.000000009x` and the cycle-count ratio is `0.996737x`. The advisor-facing answer is: the simulator holds the retired-instruction window fixed, so IPC movement is effectively cycle movement.

![Router geomean with disabled prefetching as 1x](figures/stage2_pre_post_geomean.png)

## What We Built On Athena

Athena provides the simulator, cache hierarchy, L2C prefetchers, and existing comparison baselines. Our work sits above that substrate:

- a two-prefetcher routing layer for Athena L2C
- epoch-level counters for each expert, including issued and useful prefetches
- router variants that select one expert, preserve a guarded budget share, or add sticky single-expert behavior
- a fixed train and heldout trace protocol
- an OpenEvolve evaluator that accepts a small literal policy dictionary
- ledgers and plots that rebuild from simulator summaries

The router names in the code mean:

| Name | Behavior | Role in this report |
| --- | --- | --- |
| `MoP-V1.1` | guarded router with budget-share protection | backup manual family |
| `MoP-V1.2` | probes both experts for one epoch, then selects the higher-scoring expert | manual before-OpenEvolve reference |
| `MoP-V1.3` | `MoP-V1.2` plus a sticky margin that keeps the previous single-expert action when scores are close | final OpenEvolve-selected router |

The selected policy is:

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

`mop_total_budget` is the per-epoch prefetch budget. `mop_one_shot_epochs` is the initial dual-expert probe window. `mop_guarded_min_budget_share` is each expert's minimum share when the guarded family is active. `mop_sticky_margin_pct` is the score tie band for `MoP-V1.3`. `mop_score_weights` weight the accuracy, coverage, and traffic terms used by the router score.

At runtime, the router reads previous-epoch per-expert issued and useful counters, the retired-instruction epoch boundary, and its own previous action. It can choose `MLOP`, `SPP+PPF`, both, or the prefetcher-off action, and it can split the per-epoch budget. OpenEvolve could change the literal `candidate_policy()` dictionary: router family, total budget, one-shot epochs, accuracy floor, guarded minimum share, sticky margin, and score weights. The trace split, heldout traces, parser, metric definitions, baseline runs, expert pair, cache level, and simulator internals stayed fixed.

## Trace Protocol

The official split has 24 traces: 17 training traces and 7 heldout traces. OpenEvolve search used training traces. The quick evaluator used 3 training traces. Wider validation used 10 training traces. Final training validation used the 13 training traces available in this checkout. Heldout evaluation used the 7 frozen heldout traces after policy selection.

The fixed final setup is:

| Item | Value |
| --- | --- |
| Cache level | L2C |
| Expert pair | Athena `MLOP + SPP+PPF` L2-cache prefetchers |
| Training traces in official split | 17 |
| Quick OpenEvolve evaluator | 3 training traces, `500K` warmup, `1M` simulation |
| Wider OpenEvolve validation | 10 training traces, `500K` warmup, `1M` simulation |
| Final training validation | 13 training traces, `500K` warmup, `1M` simulation |
| Heldout evaluation | 7 heldout traces, `5M` warmup, `10M` simulation |
| Router epoch length | `500K` retired instructions |
| Selected per-epoch prefetch budget | `9216` |

The comparator hierarchy is:

| Comparator | Purpose |
| --- | --- |
| Disabled prefetching | universal `1.0x` baseline for performance |
| Per-trace oracle best prefetcher | cap from `max(MLOP, SPP+PPF)` on each trace |
| Worse constituent prefetcher | minimum practical routing check |
| Simple router baselines | `WinnerTakeAll`, `OneShotFit`, and Athena MAB |

The expert pair supports the routing story because the two prefetchers have different strengths. On heldout, `SPP+PPF` is stronger overall at `1.023725x` over disabled prefetching, while `MLOP` reaches `0.974379x`. The router lands between disabled prefetching and the oracle cap in geomean.

## Before And After OpenEvolve

![Heldout trace profile](figures/stage2_heldout_trace_profile.png)

| Surface | Manual `MoP-V1.2` | OpenEvolve `MoP-V1.3` | Oracle cap |
| --- | ---: | ---: | ---: |
| 13-trace training validation, speedup vs disabled prefetching | `1.047685` | `1.066243` | `1.084810` |
| 13-trace training validation, ratio to oracle cap | `0.964637` | `0.982884` | `1.000000` |
| 13-trace training validation, beats worse prefetcher | `9/13` | `11/13` |  |
| 13-trace training validation, below `0.95x` oracle cap | `3/13` | `2/13` |  |
| 7-trace heldout, speedup vs disabled prefetching | `0.998069` | `1.003270` | `1.024333` |
| 7-trace heldout, ratio to oracle cap | `0.975893` | `0.979437` | `1.000000` |

The 13-trace training-validation result also beats the simple router baselines on the same surface:

| Method | Speedup vs disabled prefetching | Ratio to oracle cap | Beats worse prefetcher | Below `0.95x` oracle cap |
| --- | ---: | ---: | ---: | ---: |
| OpenEvolve `MoP-V1.3` | `1.066243` | `0.982884` | `11/13` | `2/13` |
| winner-take-all router | `1.024749` | `0.942771` | `7/13` | `5/13` |
| one-shot fit router | `1.026820` | `0.943456` | `6/13` | `5/13` |
| Athena MAB router baseline | `1.021295` | `0.942077` | `6/13` | `5/13` |

The heldout trace profile shows the remaining risk. On `secret_compute_fp_105`, `MoP-V1.3` improves the tail loss from the manual router, yet it remains the largest heldout loss relative to the oracle cap.

## OpenEvolve Search

![OpenEvolve model search trajectory](figures/stage2_scale_model_comparison.png)

OpenEvolve searched a tiny policy surface. The first small model-comparison pass requested 6 iterations per model. The larger sweeps requested 80 GPT-5 mini iterations, 30 GPT-5.4 iterations, and 30 Sonnet 4.6 iterations. The captured logs show approximate wall-clock times of `97.3` minutes for GPT-5 mini, `40.2` minutes for GPT-5.4, and `43.9` minutes for Sonnet 4.6 on the local setup used here.

Search cost is reported as model iterations, generated candidates, and simulator evaluations. The candidate ledger contains 290 rows: 225 valid scored rows and 65 fail-closed rows. Valid rows break down into 7 one-trace smoke rows, 163 quick-evaluation rows, 45 wider-validation rows, and 10 final training-validation rows. Failed rows include malformed policy dictionaries, disallowed helper code, unknown policy keys, and simulator command failures.

The scale-run summary is:

| Model | Iterations requested | Best quick-evaluation speedup vs disabled prefetching | Wider-validation speedup vs disabled prefetching |
| --- | ---: | ---: | ---: |
| GPT-5 mini | 80 | `1.034404` | `1.087110` |
| GPT-5.4 | 30 | `1.036363` | quick evaluation pass |
| Sonnet 4.6 | 30 | `1.035037` | `1.087326` |

The quick-evaluation winners were close. Wider validation kept the selected `MoP-V1.3` policy because it reached `1.089214x` over disabled prefetching on the 10-trace validation surface and then `1.066243x` on the 13-trace training-validation surface. A higher 10-trace hit reached `1.089827x`, then failed the 13-trace confirmation path through simulator failures, which the ledger preserved as failed candidate rows.

The repository artifacts record iteration and candidate counts. A CMU AI Gateway billing export is absent from the committed evidence, so dollar cost should be read from the gateway dashboard rather than inferred from the repo.

## What The Evidence Supports

The strongest defensible claim is:

> A small OpenEvolve-searched router on top of Athena L2C improves the manual router for `MLOP + SPP+PPF`, reaches `1.066243x` IPC speedup over disabled prefetching on 13 training-validation traces, and reaches `1.003270x` on 7 heldout traces while remaining below the per-trace oracle best prefetcher cap.

The scientific boundaries are clean:

- heldout traces are used after policy selection
- performance plots use disabled prefetching as the `1.0x` baseline
- the oracle best prefetcher is a separate cap
- instruction count stays fixed within tiny simulator-rounding error
- the final method stays inside a compact router policy surface
- malformed or out-of-contract OpenEvolve candidates receive failure scores and stay in the ledger

The main limitation is the heldout size. Seven traces can show a useful sanity check, yet the training-validation signal carries most of the quantitative weight. The heldout result supports a modest generalization claim, and the trace-level plot shows where the policy still needs work.

## Reproduction Notes

The detailed path ledger, naming map, generated-file list, and code/report naming discrepancies live in [writing_logistics.md](writing_logistics.md). That file is intentionally separate from the main report so this document can read like a result summary.

The generated tables use public column names, and the logistics note maps those names back to raw ledger keys such as `gm_vs_nopref` and `gm_vs_pair_best`.
