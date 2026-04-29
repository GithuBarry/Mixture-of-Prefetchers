# Stage 2 OpenEvolve Start

Date: 2026-04-29

Status: Stage 2 scaffold is active after the Stage 1 train-only freeze commit.
Heldout traces remain unused for selection.

Update: the active seed was first tightened by the train-only sweep in
`docs/decisions/stage2_policy_sweep.md`; it remained `MoP-V1.2` with
`mop_score_weights = [1.0, 0.5, 1.0]`.

Update: after GPT-5.4-mini search on the 10-trace train/search subset, the
active seed is promoted to `MoP-V1.3`, a narrow sticky-single extension of
`MoP-V1.2`. The confirmed policy is:

```python
{
    "router": "MoP-V1.3",
    "mop_total_budget": 9216,
    "mop_one_shot_epochs": 1,
    "mop_accuracy_floor": 30,
    "mop_guarded_min_budget_share": 10,
    "mop_sticky_margin_pct": 5,
    "mop_score_weights": [1.0, 0.55, 1.0],
}
```

Update: a later minimal-prompt GPT-5.4-nano run and a tiny local knob grid
promoted the sticky margin from `5` to `3`. The active confirmed policy is now:

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

Update: the OpenEvolve evaluator now hashes canonical policy behavior plus
frozen evaluator/simulator inputs, rejects non-literal evolved code, and returns
the full metric schema on failed candidates. This keeps the Stage 2 loop from
rewarding comment-only edits or crashing on invalid generated policies.

## Frozen Story

- cache level: L2C
- expert pair: `MLOP + SPP+PPF`
- main seed: `MoP-V1.3 StickySingle`
- backup seed: `MoP-V1.2 ProbeSingle`
- primary comparator: pair-best constituent single expert
- secondary comparators: no-prefetch, then weaker routee

The reason for choosing `MLOP + SPP+PPF` is complementarity, not a Stage 1 win
over pair-best. On the train/search pair screen, `MLOP` wins 3/10 traces,
`SPP+PPF` wins 7/10 traces, both routees beat no-prefetch on 6/10 traces, and
the routee gap is at least 2% on 7/10 traces. This gives Stage 2 a focused
policy-search target: beat no-prefetch and the weaker routee while closing the
gap to pair-best.

## OpenEvolve Surface

OpenEvolve may edit only `candidate_policy()` in
`stage2/openevolve/initial_policy.py`.

Allowed outputs:

- router family: `MoP-V1.1`, `MoP-V1.2`, or `MoP-V1.3`
- total prefetch budget
- one-shot probe epochs
- accuracy floor
- guarded minimum budget share
- sticky margin percentage for `MoP-V1.3`
- three score weights

Frozen:

- trace splits and heldout traces
- parser, dataset, and figure code
- no-prefetch and constituent single baselines
- metric definitions
- Athena simulator internals, except the already-implemented `MoP-V1.3`
  sticky-single router branch and its one exposed margin knob
- expert pair

`WinnerTakeAll`, `OneShotFit`, and single experts remain comparators. They are
not editable candidate policies for Stage 2 search.

The evaluator parses the evolve block as a literal policy function. Imports,
file reads, helper code, and arbitrary Python execution inside the candidate are
rejected before simulator execution.

## Smoke Evidence

The CMU AI Gateway endpoint was verified with the key provided through the
environment only. No key is stored in the repository.

Cheap model used for smoke:

- `meta.llama3-1-8b-instruct-v1:0`

Real simulator smoke:

- stage0, one trace, `MoP-V1.2`: `1.006177x` vs pair-best, `1.007034x` vs
  no-prefetch, `1.006678x` vs weaker routee, `single_action_rate = 1.0`
- stage1, three traces, seed `MoP-V1.2`: `0.931329x` vs pair-best,
  `1.028310x` vs no-prefetch, `1.012950x` vs weaker routee,
  `beats_weaker_rate = 2/3`

Before evaluator hardening, the first three cheap OpenEvolve mutations were
worse than the seed. They increased both-on usage and reduced weaker-routee
performance, so the objective direction looked reasonable. The committed
candidate ledger keeps only the post-hardening seed reruns.

## GPT-5.4-mini Search Evidence

Kimi/Moonshot model IDs were probed through the CMU AI Gateway and were not
available to this team. The gateway did allow `gpt-5.4-mini`, which was used
for the successful train/search run.

The successful candidate came from
`results/stage2_openevolve/stage2_gpt54mini_iter4`. On the 10-trace
train/search subset, it reached:

- `0.977466x` vs pair-best
- `1.087038x` vs no-prefetch
- `1.130068x` vs weaker routee
- `0.800000` beats-weaker rate
- `0.200000` catastrophic rate

The `MoP-V1.2` reference under the same rebuilt binary reached:

- `0.959129x` vs pair-best
- `1.062249x` vs no-prefetch
- `1.106171x` vs weaker routee
- `0.700000` beats-weaker rate
- `0.300000` catastrophic rate

On the 13-trace local train-window confirmation, the candidate reached:

- `0.982234x` vs pair-best
- `1.067489x` vs no-prefetch
- `1.116795x` vs weaker routee
- `0.769231` beats-weaker rate
- `0.230769` catastrophic rate

A later sticky-margin-only local grid found `MoP-V1.3`, budget `9216`,
sticky `3`, weights `[1.0, 0.55, 1.0]`. On the 10-trace train/search subset it
reached:

- `0.980137x` vs pair-best
- `1.089214x` vs no-prefetch
- `1.130177x` vs weaker routee
- `0.700000` beats-weaker rate
- `0.200000` catastrophic rate

On the 13-trace local train-window confirmation, it reached:

- `0.982884x` vs pair-best
- `1.066243x` vs no-prefetch
- `1.117600x` vs weaker routee
- `0.846154` beats-weaker rate
- `0.153846` catastrophic rate

This supersedes sticky `5` as the active Stage 2 seed because it improves the
primary pair-best comparator and robustness counts on the 13 locally available
train traces, while preserving a clear gain over no-prefetch. It does slightly
lower the no-prefetch geomean versus sticky `5` on the 13-trace train-window
confirmation (`1.066243x` vs `1.067489x`), so that tradeoff must be reported.

The `MoP-V1.2` reference under the same rebuilt binary reached:

- `0.965888x` vs pair-best
- `1.049788x` vs no-prefetch
- `1.096860x` vs weaker routee
- `0.769231` beats-weaker rate
- `0.230769` catastrophic rate

## Artifact Paths

- Stage 2 scaffold: `stage2/openevolve/`
- candidate ledger: `stage2/openevolve/candidate_ledger.jsonl`
- smoke output: `results/stage2_openevolve/smoke_llama8b_iter1`
- stage1 full-program smoke: `results/stage2_openevolve/stage1_llama8b_full_iter3`
- GPT-5.4-mini search output: `results/stage2_openevolve/stage2_gpt54mini_iter4`
- confirmed candidate search-window artifacts: `results/stage2_openevolve/stage2/48b15535009fa381`
- confirmed candidate train-window artifacts: `results/stage2_openevolve/stage3/48b15535009fa381`
- minimal nano output: `results/stage2_openevolve/stage2_gpt54nano_minimal_iter8_20260429`
- sticky-margin grid: `results/stage2_openevolve/sweeps/stage2_v13_local_grid_20260429`
- active sticky-3 search-window artifacts: `results/stage2_openevolve/stage2/a52ed8a4151ad6cc`
- active sticky-3 train-window artifacts: `results/stage2_openevolve/stage3/a52ed8a4151ad6cc`

All paths above are repository-relative. Raw simulator outputs remain ignored
under `results/`.
