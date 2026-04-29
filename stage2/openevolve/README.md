# Stage 2 OpenEvolve Scaffold

This directory starts Stage 2 with one viable story:

- cache level: L2C
- expert pair: `MLOP + SPP+PPF`
- primary comparator: pair-best constituent single
- secondary comparators: no-prefetch, then weaker routee

The data-backed reason for this pair is complementarity on the train/search
screen: `MLOP` wins 3/10 traces, `SPP+PPF` wins 7/10, both routees beat
no-prefetch on 6/10, and the routee gap is at least 2% on 7/10.

## Editable Surface

OpenEvolve edits only `candidate_policy()` in `initial_policy.py`. The evaluator
rejects unknown keys and keeps trace splits, parser code, metric definitions,
baselines, and simulator internals frozen.

Allowed knobs:

- `router`: `MoP-V1.1` or `MoP-V1.2`
- `mop_total_budget`
- `mop_one_shot_epochs`
- `mop_accuracy_floor`
- `mop_guarded_min_budget_share`
- `mop_score_weights`

`WinnerTakeAll`, `OneShotFit`, and constituent singles remain comparators in
Stage 2 reports. They are not editable candidate policies for OpenEvolve.

## Local Smoke

Use the CMU AI Gateway key through an environment variable only. Do not write it
to this repo.

```bash
export CMU_AI_GATEWAY_API_KEY=...
PYTHONPATH=external/openevolve STAGE2_EVAL_STAGE=stage0 \
  python3 external/openevolve/openevolve-run.py \
  stage2/openevolve/initial_policy.py \
  stage2/openevolve/evaluator.py \
  --config stage2/openevolve/config_smoke.yaml \
  --output results/stage2_openevolve/smoke \
  --iterations 1
```

The evaluator writes `stage2/openevolve/candidate_ledger.jsonl` and raw
simulator artifacts under `results/stage2_openevolve/`.
