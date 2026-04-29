# Stage 2 Policy Sweep

Date: 2026-04-29

Status: train-only Stage 2 sweep promoted a tuned `MoP-V1.2` seed. Heldout
traces were not used.

## Selected Policy

The active Stage 2 seed is:

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

This is the original `MoP-V1.2` seed with a higher accuracy weight. The router
still uses only single-expert actions after the one-epoch probe.

## Evidence

All runs used L2C `MLOP + SPP+PPF`, no heldout traces, and no downloads.

| Gate | Traces | Candidate | vs pair-best | vs no-prefetch | vs weaker | beats weaker | both-on | single |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| stage1 tight sweep | 3 | tuned `MoP-V1.2` | 0.936679 | 1.033235 | 1.018669 | 3/3 | 0.000 | 1.000 |
| stage1 tight sweep | 3 | old seed | 0.935490 | 1.033502 | 1.019753 | 3/3 | 0.000 | 1.000 |
| stage2 search confirm | 10 | tuned `MoP-V1.2` | 0.958714 | 1.065858 | 1.105995 | 7/10 | 0.000 | 1.000 |
| stage2 search confirm | 10 | old seed | 0.957492 | 1.064016 | 1.103872 | 8/10 | 0.000 | 1.000 |
| stage3 local-train confirm | 13 | tuned `MoP-V1.2` | 0.965420 | 1.047570 | 1.096829 | 9/13 | 0.000 | 1.000 |
| stage3 local-train confirm | 13 | old seed | 0.963934 | 1.046549 | 1.095920 | 9/13 | 0.000 | 1.000 |

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

## Trace Availability

Full 17-trace train confirmation was attempted with `--skip-download` and
failed loudly because four train traces are not available locally:

- `parsec_2.1.facesim.simlarge.prebuilt.drop_1500M.length_250M`
- `ligra_BFS.com-lj.ungraph.gcc_6.3.0_O3.drop_500M.length_250M`
- `ligra_Triangle.com-lj.ungraph.gcc_6.3.0_O3.drop_750M.length_250M`
- `secret_compute_int_243`

Because downloading more traces was too slow, Stage 3 was made explicit as the
13 locally available train traces. Stage 4 remains the full 17-trace train
confirmation once those traces are available.

## Artifacts

- `results/stage2_openevolve/sweeps/stage1_tight_serial_20260429`
- `results/stage2_openevolve/sweeps/stage2_confirm_top3_20260429`
- `results/stage2_openevolve/sweeps/stage3_local_train_confirm_top2_20260429`
- `results/stage2_openevolve/sweeps/stage3_train_confirm_top2_20260429`
- `stage2/openevolve/selection_ledger.jsonl`

Raw simulator outputs remain under ignored `results/`; the selection ledger is
the committed summary artifact.
