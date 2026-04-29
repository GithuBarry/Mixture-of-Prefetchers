# Stage 2 Heldout Protocol

Date: 2026-04-29

Status: predeclared before any Stage 2 heldout run. Heldout remains unused for
policy selection.

## Boundary

Heldout is reserved for final confirmation after the train-selected candidate is
frozen. The current frozen candidate is:

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

The reference policy is the current-checkout `MoP-V1.2` rerun recorded in
`stage2/openevolve/comparator_ledger.jsonl`.

## Metrics

Report the same metrics used for train-window selection:

- geomean versus pair-best single;
- geomean versus no-prefetch;
- geomean versus weaker routee;
- beats-weaker count;
- catastrophic count below `0.95x` versus pair-best;
- action mix where available.

Do not add, remove, or reweight metrics after seeing heldout results.

## Retry Rules

Simulator or machine failures are not performance results. A failed heldout job
may be rerun once if it fails before producing a complete manifest row for the
target experiment. Examples include `SIGBUS`, missing output files, truncated
JSON, or a nonzero simulator exit.

If the same trace and experiment fails twice:

- mark that trace and experiment invalid;
- do not substitute a partial manifest row;
- report the invalid count next to all heldout metrics;
- do not drop the trace silently from geomeans.

If a baseline or single expert fails twice on a heldout trace, the trace cannot
support fair pair-best/no-prefetch comparison and the whole heldout run is
invalid until the infrastructure issue is fixed.

If only the active router fails twice while all baselines and singles complete,
report the router failure as a failed heldout result rather than rerunning with
different knobs.

## Allowed Execution Changes

Allowed:

- rerun the exact same command after infrastructure failure;
- lower worker count for stability;
- rebuild Athena without source changes;
- record wall-clock/runtime diagnostics.

Not allowed:

- changing candidate policy knobs;
- changing expert pair, trace split, warmup, simulation length, metrics, or
  parser code;
- dropping traces because they hurt the result;
- using heldout results to pick between `MoP-V1.2`, `MoP-V1.3`, or comparator
  policies.

## Reporting

The heldout report must include:

- exact command;
- commit hash;
- result directory;
- manifest row count;
- invalid trace/experiment count;
- table comparing no-prefetch, pair-best, current-checkout `MoP-V1.2`, and
  active `MoP-V1.3`;
- explicit statement that heldout was not used for selection.
