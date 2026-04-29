# Stage 2 OpenEvolve Scaffold

This directory starts Stage 2 with one viable story:

- cache level: L2C
- expert pair: `MLOP + SPP+PPF`
- primary comparator: pair-best constituent single
- secondary comparators: no-prefetch, then weaker routee

The data-backed reason for this pair is complementarity on the train/search
screen: `MLOP` wins 3/10 traces, `SPP+PPF` wins 7/10, both routees beat
no-prefetch on 6/10, and the routee gap is at least 2% on 7/10.

After train-only OpenEvolve search and a small local knob grid, the active seed
is `MoP-V1.3` with `mop_total_budget = 9216`, `mop_sticky_margin_pct = 3`,
and `mop_score_weights = [1.0, 0.55, 1.0]`. See
`docs/decisions/stage2_policy_sweep.md`.

## Editable Surface

OpenEvolve edits only `candidate_policy()` in `initial_policy.py`. The evaluator
rejects unknown keys and keeps trace splits, parser code, metric definitions,
baselines, and simulator internals frozen.

Allowed knobs:

- `router`: `MoP-V1.1`, `MoP-V1.2`, or `MoP-V1.3`
- `mop_total_budget`
- `mop_one_shot_epochs`
- `mop_accuracy_floor`
- `mop_guarded_min_budget_share`
- `mop_sticky_margin_pct`
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

The evaluator hashes the validated policy dictionary plus frozen evaluator and
simulator inputs. Program text outside the literal policy is intentionally not
part of the behavior cache key, so comment-only changes cannot rerun the
simulator and appear better because of noise.

## Deterministic Sweep

Before spending more model budget, run the deterministic policy sweep:

```bash
python3 stage2/openevolve/sweep_policies.py \
  --stage stage1 \
  --preset tight \
  --workers 1 \
  --retries 1 \
  --out-dir results/stage2_openevolve/sweeps/stage1_tight_serial
```

Use `--workers 1` for Athena stability on this machine. Higher concurrency has
triggered transient `SIGBUS` failures in the simulator on some traces.

The latest cheap-model smoke that completed the loop was:

```bash
PYTHONPATH=external/openevolve STAGE2_EVAL_STAGE=stage1 \
  python3 external/openevolve/openevolve-run.py \
  stage2/openevolve/initial_policy.py \
  stage2/openevolve/evaluator.py \
  --config stage2/openevolve/config_smoke.yaml \
  --output results/stage2_openevolve/stage1_tuned_llama8b_iter5_builtinfeatures \
  --iterations 5
```

That run found one valid new policy, `[0.7, 0.3, 1.0]`. It improved the
10-trace stage2 search confirmation but was not promoted after the 13-trace
local-train confirmation.
