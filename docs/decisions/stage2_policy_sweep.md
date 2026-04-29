# Stage 2 Policy Sweep

Date: 2026-04-29

Status: train-only Stage 2 sweep first promoted a tuned `MoP-V1.2` seed. A
later GPT-5.4-mini OpenEvolve search promoted `MoP-V1.3 StickySingle`, and a
minimal GPT-5.4-nano run plus a tiny local grid tightened its sticky margin.
Heldout traces were not used.

## Selected Policy

The active Stage 2 seed is:

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

The backup/reference seed is:

```python
{
    "router": "MoP-V1.2",
    "mop_total_budget": 8192,
    "mop_one_shot_epochs": 1,
    "mop_accuracy_floor": 30,
    "mop_guarded_min_budget_share": 10,
    "mop_score_weights": [1.0, 0.5, 1.0],
}
```

The `MoP-V1.3` seed is a narrow extension of `MoP-V1.2`: it still uses only
single-expert actions after the one-epoch probe, but it keeps the prior single
expert when both scores are positive and within a 3% margin.

## Evidence

All runs used L2C `MLOP + SPP+PPF`, no heldout traces, and no downloads.

| Check | Traces | Candidate | vs pair-best | vs no-prefetch | vs weaker | beats weaker | both-on | single |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3-trace tight sweep | 3 | tuned `MoP-V1.2` | 0.936679 | 1.033235 | 1.018669 | 3/3 | 0.000 | 1.000 |
| 3-trace tight sweep | 3 | old seed | 0.935490 | 1.033502 | 1.019753 | 3/3 | 0.000 | 1.000 |
| 10-trace train/search | 10 | tuned `MoP-V1.2` | 0.958714 | 1.065858 | 1.105995 | 7/10 | 0.000 | 1.000 |
| 10-trace train/search | 10 | old seed | 0.957492 | 1.064016 | 1.103872 | 8/10 | 0.000 | 1.000 |
| 13-trace train-window | 13 | tuned `MoP-V1.2` | 0.965420 | 1.047570 | 1.096829 | 9/13 | 0.000 | 1.000 |
| 13-trace train-window | 13 | old seed | 0.963934 | 1.046549 | 1.095920 | 9/13 | 0.000 | 1.000 |

The tuned policy wins the combined metric and improves geomean versus pair-best,
no-prefetch, and weaker routee on both the 10-trace search confirmation and the
13-trace local-train confirmation. It does not solve the pair-best problem: it
is still below the best constituent single on geomean.

## OpenEvolve Smoke

A cheap CMU AI Gateway / Llama 8B OpenEvolve smoke was run after the deterministic
sweep. Two evaluator issues were fixed before treating the result as meaningful:

- failed candidates now return the full metric schema, so MAP-Elites feature
  dimensions do not crash on invalid edits;
- candidate cache keys now use the canonical validated policy plus frozen
  evaluator/simulator inputs, not surrounding program text, so docstring-only
  edits cannot earn a fresh noisy simulator score.

With that fix, the only valid new policy found in the 5-iteration smoke changed
`mop_score_weights` from `[1.0, 0.5, 1.0]` to `[1.0, 0.4, 1.0]`. It was not
promoted: on the 10-trace search confirmation it reached `0.958214x` vs
pair-best, `1.062867x` vs no-prefetch, and `1.106615x` vs weaker routee,
slightly below the active seed's `0.958273x`, `1.064585x`, and `1.108183x`.

After switching OpenEvolve MAP-Elites features from action-metric names to the
built-in `complexity` / `diversity` features, the cheap model produced a
stronger valid screen candidate with `mop_score_weights = [0.7, 0.3, 1.0]`.
That candidate improved the 10-trace search confirmation (`0.960233x` vs
pair-best and `1.066260x` vs no-prefetch), but it failed the 13-trace local-train
confirmation: `0.963380x` vs pair-best, `1.044298x` vs no-prefetch, and
`0.307692` catastrophic rate, compared with the active seed's `0.964299x`,
`1.047360x`, and `0.230769`. It is therefore not promoted.

OpenEvolve smoke artifacts:

- `results/stage2_openevolve/stage1_tuned_llama8b_iter5_behaviorhash`
- `results/stage2_openevolve/stage1_tuned_llama8b_iter5_builtinfeatures`
- `results/stage2_openevolve/stage2/047993d2d251398b`
- `results/stage2_openevolve/stage2/1662bd615d89c4e8`
- `results/stage2_openevolve/stage2/d1291eb1c25956db`
- `results/stage2_openevolve/stage2/38d624d27e711ce2`
- `results/stage2_openevolve/stage3/d1291eb1c25956db`
- `results/stage2_openevolve/stage3/38d624d27e711ce2`

## GPT-5.4-mini OpenEvolve Confirmation

Kimi/Moonshot model IDs were probed through the CMU AI Gateway, but this team
was not allowed to access them. `gpt-5.4-mini` was available and produced a
valid `MoP-V1.3` candidate when run directly on the 10-trace train/search
subset.

| Window | Traces | Candidate | vs pair-best | vs no-prefetch | vs weaker | beats weaker | catastrophic | both-on | single |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10-trace train/search | 10 | `MoP-V1.3`, budget 9216, sticky 5 | 0.977466 | 1.087038 | 1.130068 | 8/10 | 2/10 | 0.000 | 1.000 |
| 10-trace train/search | 10 | `MoP-V1.2` reference | 0.959129 | 1.062249 | 1.106171 | 7/10 | 3/10 | 0.000 | 1.000 |
| local train-window | 13 | `MoP-V1.3`, budget 9216, sticky 5 | 0.982234 | 1.067489 | 1.116795 | 10/13 | 3/13 | 0.000 | 1.000 |
| local train-window | 13 | `MoP-V1.2` reference | 0.965888 | 1.049788 | 1.096860 | 10/13 | 3/13 | 0.000 | 1.000 |

This is the first Stage 2 candidate in this run sequence that improves the
active reference on the 10-trace train/search subset and preserves the gain on
the 13 locally available train traces. It still does not beat pair-best single
overall, but it materially closes the gap while improving over no-prefetch and
the weaker routee.

GPT-5.4-mini artifacts:

- `results/stage2_openevolve/stage2_gpt54mini_iter4`
- `results/stage2_openevolve/stage2/48b15535009fa381`
- `results/stage2_openevolve/stage3/48b15535009fa381`
- `results/stage2_openevolve/stage2/696ab41d0e1b93bf`
- `results/stage2_openevolve/stage3/696ab41d0e1b93bf`

## Post-Promotion Continuation

Two short GPT-5.4-mini continuation runs were made after promoting the
`MoP-V1.3`, budget 9216, sticky 5 seed. They did not justify another
promotion.

| Window | Traces | Candidate | vs pair-best | vs no-prefetch | vs weaker | beats weaker | catastrophic | Outcome |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 10-trace train/search | 10 | `MoP-V1.3`, budget 10240, sticky 10, weights `[1.0, 0.5, 1.0]` | 0.982001 | 1.089827 | 1.133480 | 8/10 | 2/10 | rejected: failed 13-trace train-window confirmation twice with simulator `SIGBUS` |
| 10-trace train/search | 10 | `MoP-V1.3`, budget 8960, sticky 5, weights `[1.0, 0.56, 1.0]` | 0.977240 | 1.087744 | 1.131943 | 8/10 | 2/10 | rejected: tiny composite gain, lower pair-best geomean, and failed 13-trace train-window confirmation |

The first rejected candidate looked better than the promoted seed on the
10-trace train/search window, but it was not reproducible enough for the
train-window check. The second rejected candidate improved the combined score
only from `-0.001472` to `-0.001210`, while lowering pair-best geomean from
`0.977466` to `0.977240`. These results were useful negative evidence before
the later sticky-margin grid.

Continuation artifacts:

- `results/stage2_openevolve/stage2_gpt54mini_postpromote_iter4`
- `results/stage2_openevolve/stage2_gpt54mini_postfail_iter4`
- `results/stage2_openevolve/stage2/53e5b8b728c0a657`
- `results/stage2_openevolve/stage2/bf4d587210a19f36`
- `results/stage2_openevolve/stage3/53e5b8b728c0a657`
- `results/stage2_openevolve/stage3/bf4d587210a19f36`

## Minimal Nano And Local Sticky Grid

The full GPT-5.4-mini continuation prompt began triggering CMU AI Gateway prompt
filtering before candidate generation. A shorter GPT-5.4-nano config was added
only as a generator; all candidates still used the same frozen evaluator and
simulator path.

| Window | Traces | Candidate | vs pair-best | vs no-prefetch | vs weaker | beats weaker | catastrophic | Outcome |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 10-trace train/search | 10 | sticky 5, weights `[1.0, 0.57, 1.0]` | 0.978647 | 1.084972 | 1.128668 | 8/10 | 2/10 | rejected: 13-trace geomeans below sticky 5 seed despite better robustness counts |
| 13-trace train-window | 13 | sticky 5, weights `[1.0, 0.57, 1.0]` | 0.982187 | 1.066777 | 1.116029 | 11/13 | 2/13 | rejected |
| 10-trace train/search | 10 | sticky 3, weights `[1.0, 0.55, 1.0]` | 0.980137 | 1.089214 | 1.130177 | 7/10 | 2/10 | promoted after train-window confirmation |
| 13-trace train-window | 13 | sticky 3, weights `[1.0, 0.55, 1.0]` | 0.982884 | 1.066243 | 1.117600 | 11/13 | 2/13 | active seed |

Sticky `3` supersedes sticky `5` because it improves the primary pair-best
comparator and robustness counts on the 13 locally available train traces, and
it improves the weaker-routee geomean. It does slightly lower no-prefetch
geomean on the 13-trace train-window confirmation (`1.066243x` vs
`1.067489x`), so the final story should report that tradeoff rather than claim
uniform improvement over the previous sticky `5` seed.

Two nearby weight-only points, `[1.0, 0.56, 1.0]` and `[1.0, 0.58, 1.0]`, failed
during 10-trace train/search measurement on the MLOP single baseline for
`secret_compute_int_568`. They were not interpreted from partial manifests.

A final 4-iteration minimal-nano pass centered on sticky `3` did not find a
valid improvement. All generated mutations were rejected by the literal-policy
guard before simulator execution, and the tracked best remained sticky `3`.

Minimal nano and sticky-grid artifacts:

- `results/stage2_openevolve/stage2_gpt54nano_minimal_iter8_20260429`
- `results/stage2_openevolve/sweeps/stage2_v13_local_grid_20260429`
- `results/stage2_openevolve/stage2/7883aa5c4c1a14dc`
- `results/stage2_openevolve/stage3/7883aa5c4c1a14dc`
- `results/stage2_openevolve/stage2/a52ed8a4151ad6cc`
- `results/stage2_openevolve/stage3/a52ed8a4151ad6cc`
- `results/stage2_openevolve/stage2_gpt54nano_after_sticky3_iter4_20260429`

## Comparator Check

`WinnerTakeAll`, `OneShotFit`, and `AthenaMAB` were run on the same 13-trace
train-window as the active `MoP-V1.3` seed. This checks whether the result is
just a trivial single-expert chooser or an older built-in coordinator effect.
It is not: all three comparators stay above no-prefetch but are substantially
worse than the sticky-margin policy.

| Candidate | vs pair-best | vs no-prefetch | vs weaker | beats weaker | catastrophic | combined score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pre-OpenEvolve `MoP-V1.2` reference | 0.965888 | 1.049788 | 1.096860 | 10/13 | 3/13 | -0.031762 |
| post-OpenEvolve `MoP-V1.3` sticky 3 | 0.982884 | 1.066243 | 1.117600 | 11/13 | 2/13 | 0.002547 |
| `WinnerTakeAll` | 0.942771 | 1.024749 | 1.071244 | 7/13 | 5/13 | -0.085210 |
| `OneShotFit` | 0.943456 | 1.026820 | 1.072286 | 6/13 | 5/13 | -0.083784 |
| `AthenaMAB` | 0.942077 | 1.021295 | 1.069394 | 6/13 | 5/13 | -0.097136 |

Comparator artifacts:

- `results/stage2_openevolve/comparators/stage3_winnertakeall_20260429`
- `results/stage2_openevolve/comparators/stage3_oneshotfit_20260429`
- `results/stage2_openevolve/comparators/stage3_athenamab_20260429`

## Trace Availability

Full 17-trace train confirmation was attempted with `--skip-download` and
failed loudly because four train traces are not available locally:

- `parsec_2.1.facesim.simlarge.prebuilt.drop_1500M.length_250M`
- `ligra_BFS.com-lj.ungraph.gcc_6.3.0_O3.drop_500M.length_250M`
- `ligra_Triangle.com-lj.ungraph.gcc_6.3.0_O3.drop_750M.length_250M`
- `secret_compute_int_243`

Because downloading more traces was too slow, the current train-window evidence
uses the 13 locally available train traces. The full 17-trace train confirmation
remains pending until those traces are available.

## Artifacts

- `results/stage2_openevolve/sweeps/stage1_tight_serial_20260429`
- `results/stage2_openevolve/sweeps/stage2_confirm_top3_20260429`
- `results/stage2_openevolve/sweeps/stage3_local_train_confirm_top2_20260429`
- `results/stage2_openevolve/sweeps/stage3_train_confirm_top2_20260429`
- `results/stage2_openevolve/sweeps/stage2_v13_local_grid_20260429`
- `stage2/openevolve/selection_ledger.jsonl`

Raw simulator outputs remain under ignored `results/`; the selection ledger is
the committed summary artifact.
