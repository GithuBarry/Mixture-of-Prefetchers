# Stage 2 OpenEvolve Start

Date: 2026-04-29

Status: Stage 2 scaffold is active after the Stage 1 train-only freeze commit.
Heldout traces remain unused for selection.

Update: the active seed was tightened by the train-only sweep in
`docs/decisions/stage2_policy_sweep.md`; it remains `MoP-V1.2` but uses
`mop_score_weights = [1.0, 0.5, 1.0]`.

Update: the OpenEvolve evaluator now hashes canonical policy behavior plus
frozen evaluator/simulator inputs, rejects non-literal evolved code, and returns
the full metric schema on failed candidates. This keeps the Stage 2 loop from
rewarding comment-only edits or crashing on invalid generated policies.

## Frozen Story

- cache level: L2C
- expert pair: `MLOP + SPP+PPF`
- main seed: `MoP-V1.2 ProbeSingle`
- backup seed: `MoP-V1.1 Guarded`
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

- router family: `MoP-V1.1` or `MoP-V1.2`
- total prefetch budget
- one-shot probe epochs
- accuracy floor
- guarded minimum budget share
- three score weights

Frozen:

- trace splits and heldout traces
- parser, dataset, and figure code
- no-prefetch and constituent single baselines
- metric definitions
- Athena simulator internals
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

## Artifact Paths

- Stage 2 scaffold: `stage2/openevolve/`
- candidate ledger: `stage2/openevolve/candidate_ledger.jsonl`
- smoke output: `results/stage2_openevolve/smoke_llama8b_iter1`
- stage1 full-program smoke: `results/stage2_openevolve/stage1_llama8b_full_iter3`

All paths above are repository-relative. Raw simulator outputs remain ignored
under `results/`.
