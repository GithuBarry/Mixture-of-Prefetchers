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
| `gpt-5.4-mini` | `stage2/openevolve/config_modelcmp_gpt54mini.yaml` |
| `gpt-5.4-nano` | `stage2/openevolve/config_modelcmp_gpt54nano.yaml` |
| `claude-haiku-4-5-20251001-v1:0` | `stage2/openevolve/config_modelcmp_claude_haiku45.yaml` |

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
