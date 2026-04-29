# Stage 1 to Stage 2 Freeze

Date: 2026-04-29

Status: Stage 1 frozen as a high-risk / negative result. The train-only finish
screen improves over no-prefetch, but no tested MoP variant reaches the
promotion threshold versus the pair-best single expert.

## Frozen Boundary

- Cache level: L2C.
- Held-out use: no held-out traces were used for the Stage 1 finish selection.
- Primary comparator: pair-best constituent single prefetcher on the same trace.
- Secondary comparator: no-prefetch.
- Stage 2 should treat `data/processed/runs.csv` as the preserved historical
  Stage 1 full-suite table and `data/processed/stage1_finish_pair_screen_1m.csv`
  as the train-only finish screen table.

## Router Names

| Name | Legacy alias | Router type | Why it exists |
| --- | --- | ---: | --- |
| `MoP-V0` | `MoPLite` | 4 | Original score-sign router baseline. |
| `MoP-V1.1` | `MoPLiteGuarded` | 5 | Removes both-off fallback when both scores are nonpositive and guards budget split. |
| `MoP-V1.2` | `ProbeThenWinner` | 6 | ProbeSingle family; Stage 1 finish modes force `mop_one_shot_epochs=1`. |

## AMPM Qualification

Result dir: `results/_dev_stage1_l2c_ampm_search_1m`

| Single | Geomean vs no-prefetch | Wins vs no-prefetch |
| --- | ---: | ---: |
| `AMPM` | 1.062585 | 7/10 |
| `Pythia` | 1.080441 | 8/10 |
| `SPP+PPF` | 1.085337 | 8/10 |
| `MLOP` | 0.976004 | 7/10 |
| `SMS` | 0.991905 | 4/10 |

Decision: do not promote AMPM into Stage 2 pair search. It beats no-prefetch on
7/10 search traces, but it never beats the best existing single expert by the
required `>=2%` trace-level margin.

## Pair Screen

Corrected screen knobs:

- `stage1_pair_screen_1m`
- `500K` warmup, `1M` simulation
- `mop_one_shot_epochs=1`
- explicit `mop_total_budget=8192`
- train/search traces only

Completed result dirs:

- `results/stage1_pair_screen_1m_probe1_budget8192_Pythia_SPPplusPPF`
- `results/stage1_pair_screen_1m_probe1_budget8192_MLOP_SPPplusPPF`

| Pair | Best MoP variant | Geomean vs no-prefetch | Geomean vs pair-best | Catastrophic traces vs pair-best | Action note |
| --- | --- | ---: | ---: | ---: | --- |
| `Pythia + SPP+PPF` | `MoP-V1.1` | 1.065671 | 0.957672 | 4/10 | Guarded removes off but still uses both-on 76.7%. |
| `MLOP + SPP+PPF` | `MoP-V0` | 1.065933 | 0.961801 | 3/10 | Original router remains slightly ahead of V1.2 on geomean. |
| `MLOP + SPP+PPF` | `MoP-V1.2` | 1.064329 | 0.960353 | 3/10 | Single-action rate is 100%, but still trails pair-best. |

Best non-MoP coordinator in the completed finish screen:

| Pair | Coordinator | Geomean vs no-prefetch | Geomean vs pair-best |
| --- | --- | ---: | ---: |
| `MLOP + SPP+PPF` | `OneShotFit` | 1.084763 | 0.978791 |

Failed corrected screens:

- `results/stage1_pair_screen_1m_probe1_budget8192_MLOP_Pythia`
- `results/stage1_pair_screen_1m_probe1_budget8192_MLOP_SMS`
- `results/stage1_pair_screen_1m_probe1_budget8192_MLOP_SMS_serial`

These are not used as completed evidence. The corrected `MoP-V1.2` path hit
`SIGBUS` on `secret_compute_int_568` for MLOP-containing pairs that did not use
`SPP+PPF`. `MLOP + SMS` also failed when rerun alone, so this is recorded as a
real Stage 1 compatibility risk rather than a promotion candidate.

## Decision

No pair/family satisfies the promotion rule:

- no MoP variant reaches `>=0.98x` geomean versus pair-best on the completed
  train/search screen;
- the best MoP candidates do beat no-prefetch, but have 3-4 catastrophic traces
  below `0.95x` versus pair-best;
- `MoP-V1.2` fixes action indecision mechanically, but does not improve over
  `MoP-V0` on the best completed pair.

Frozen Stage 2 shortlist, if the project proceeds despite the high-risk signal:

- primary expert pair: `MLOP + SPP+PPF`, because it gives the closest completed
  train/search result to pair-best through `OneShotFit` and leaves a clear
  single-action policy target;
- backup expert pair: `Pythia + SPP+PPF`, because both routees beat no-prefetch
  on more search traces and it is the most stable existing pair;
- main seed: `MoP-V1.2 ProbeSingle`, only as a policy-search seed, not as a
  Stage 1 win;
- backup seed: `MoP-V1.1 Guarded`.

Stage 2 launch is allowed only under a high-risk label: the mechanism failure is
policy/action related, but Stage 1 did not produce a train-confirmed win over
pair-best. The comparator hierarchy must remain pair-best single first,
no-prefetch second.

## Rebuilt Artifacts

- `data/processed/stage1_finish_pair_screen_1m.csv`
- `data/processed/stage1_finish_pair_screen_1m_summary.md`
- report figures and tables rebuilt with `python3 scripts/make_figures.py`

The full historical Stage 1 dataset remains:

- `data/processed/runs.csv`
- `data/processed/runs_summary.md`

Some historical raw roots referenced by `data/processed/runs.csv` are not
present in this local checkout. This memo therefore uses the new train-only raw
directories above for the finish decision and keeps the historical processed
dataset as preserved context, not as a new selection source.
