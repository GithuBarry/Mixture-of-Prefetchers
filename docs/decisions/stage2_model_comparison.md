# Stage 2 Model Comparison

Date: 2026-04-29

Status: train-only OpenEvolve model comparison protocol. Heldout remains unused
for model choice.

## Purpose

Compare which accessible CMU AI Gateway model produces the best valid
OpenEvolve candidate on the same frozen Stage 2 policy surface.

## Fixed Surface

- Cache level: L2C.
- Expert pair: `MLOP + SPP+PPF`.
- Editable file: `stage2/openevolve/initial_policy.py` through OpenEvolve's
  evolve block.
- Evaluator: `stage2/openevolve/evaluator.py`.
- Evaluation window: `STAGE2_EVAL_STAGE=stage2`, the 10-trace train/search
  subset.
- Candidate surface: literal `candidate_policy()` dictionary only.
- Heldout: not used.

The literal-policy restriction is deliberate. It keeps Stage 2 comparable with
the existing freeze and prevents model-specific code edits from changing parser,
metric, split, or simulator behavior.

## Models

The gateway model probe found no Kimi/Moonshot IDs. The comparison uses three
accessible models:

| Model | Config |
| --- | --- |
| `gpt-5.4-mini` | `stage2/openevolve/config_modelcmp_short_gpt54mini.yaml` |
| `gpt-5.4-nano` | `stage2/openevolve/config_modelcmp_short_gpt54nano.yaml` |
| `gpt-5-mini` | `stage2/openevolve/config_modelcmp_short_gpt5mini.yaml` |
| `claude-haiku-4-5-20251001-v1:0` | `stage2/openevolve/config_modelcmp_short_claude_haiku45.yaml` |

The first, more verbose `gpt-5.4-mini` comparison config was rejected by the
gateway prompt filter before producing a candidate. The actual comparison uses
the shorter matched configs above. `gpt-5-mini` was added after `gpt-5.4-mini`
also hit the prompt filter with the shorter config.

## Planned Command Shape

Run each model with the same iteration count and output root:

```bash
PYTHONPATH=external/openevolve STAGE2_EVAL_STAGE=stage2 \
  python3 external/openevolve/openevolve-run.py \
  stage2/openevolve/initial_policy.py \
  stage2/openevolve/evaluator.py \
  --config <config> \
  --output results/stage2_openevolve/modelcmp/<model>_iter6_20260429 \
  --iterations 6
```

The API key must be provided only through `CMU_AI_GATEWAY_API_KEY`; do not write
it to the repository.

## Decision Rule

For each model, record:

- best valid policy;
- best 10-trace train/search metrics;
- invalid candidate count;
- whether the best policy is new or repeats an existing cached policy;
- confirmation status on the 13-trace train-window only if it beats the active
  seed's 10-trace combined score.

Do not use heldout for model comparison.

## Observed Results

All runs used `STAGE2_EVAL_STAGE=stage2`, L2C `MLOP + SPP+PPF`, and the same
literal-policy evaluator. OpenEvolve was allowed to edit only the dictionary
returned by `candidate_policy()`. Generated imports, helper functions, IO, and
other code changes were rejected before simulator execution.

| Model | Result | Best new candidate | Best retained policy | Notes |
| --- | --- | --- | --- | --- |
| `gpt-5.4-mini` verbose | gateway prompt filter | none | active sticky `3` seed | stopped after two gateway rejections |
| `gpt-5.4-mini` short | gateway prompt filter | none | active sticky `3` seed | stopped after one gateway rejection |
| `gpt-5.4-nano` short | completed, no valid generated candidate | none | active sticky `3` seed | six generated candidates rejected by literal-policy guard |
| `claude-haiku-4-5-20251001-v1:0` short | completed, valid but worse | `ed7382b42711ea0d` | active sticky `3` seed | two valid nearby policies, two simulator failures, two active-seed repeats |
| `gpt-5-mini` short | completed, valid but worse | `73e28a5ce395155f` | active sticky `3` seed | three valid nearby policies, one malformed response, two active-seed repeats |

The active sticky `3` seed remains the best 10-trace train/search policy in
this comparison:

```text
MoP-V1.3 sticky 3:
  vs pair-best:    0.980137
  vs no-prefetch:  1.089214
  vs weaker:       1.130177
  beats weaker:    7/10
  catastrophic:    2/10
  combined score:  0.001776
```

The strongest generated non-seed policies were close but did not beat it:

| Model | Code hash | Policy delta | vs pair-best | vs no-prefetch | vs weaker | beats weaker | catastrophic | combined |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Claude Haiku 4.5 | `ed7382b42711ea0d` | budget `9280`, weight `0.54` | 0.978245 | 1.085771 | 1.129355 | 8/10 | 2/10 | -0.001094 |
| `gpt-5-mini` | `73e28a5ce395155f` | weight `0.545` | 0.979503 | 1.088507 | 1.130048 | 7/10 | 2/10 | 0.000944 |

## Interpretation

OpenEvolve is being called correctly: the logs show model initialization,
process-based evolution, checkpointing, generated candidate evaluation, and
`best_program` artifacts for the completed runs. The comparison did not improve
over the active seed, but it does identify the currently useful generators:
`gpt-5-mini` and Claude Haiku 4.5 can produce valid nearby numeric policies;
`gpt-5.4-nano` is too weak for this literal-policy surface; `gpt-5.4-mini` is
blocked by the gateway filter under both prompt variants.

The next train-only OpenEvolve pass should spend on `gpt-5-mini` first, with
Claude Haiku 4.5 as a backup/diversity generator. It should keep the current
literal-policy boundary until a separate, predeclared code-edit protocol exists.
Allowing arbitrary code edits now would confound the policy claim by letting
OpenEvolve change parser, metric, split, or simulator behavior.

## Artifacts

- `stage2/openevolve/model_comparison_ledger.jsonl`
- `stage2/openevolve/candidate_ledger.jsonl`
- `results/stage2_openevolve/modelcmp/gpt54mini_iter6_20260429`
- `results/stage2_openevolve/modelcmp/gpt54mini_short_iter6_20260429`
- `results/stage2_openevolve/modelcmp/gpt54nano_short_iter6_20260429`
- `results/stage2_openevolve/modelcmp/claude_haiku45_short_iter6_20260429`
- `results/stage2_openevolve/modelcmp/gpt5mini_short_iter6_20260429`

Heldout traces were not used.
