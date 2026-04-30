# Project Guide

This document is for a reader who knows computer architecture in general but
does not know this repository.

## Current OpenEvolve Result

The current final writeup is `report/stage2_final_report.md`. That report supersedes the older baseline-centered sections below for the finished OpenEvolve story.

The selected setup is:

- cache level: L2C
- expert pair: `MLOP + SPP+PPF`
- selected router: `MoP-V1.3`
- performance baseline: disabled prefetching at `1.0x`
- oracle cap: per-trace `max(MLOP, SPP+PPF)`

The official split has 24 traces: 17 training traces and 7 heldout traces. OpenEvolve search used training traces, while the heldout traces were evaluated after policy selection. The selected router reaches `1.066243x` IPC speedup over disabled prefetching on 13 training-validation traces and `1.003270x` on 7 heldout traces.

Use `report/writing_logistics.md` for the mapping between public report names and raw artifact names such as `stage1`, `stage2`, `stage3`, `gm_vs_nopref`, and `gm_vs_pair_best`.

## What This Repository Is

This repository studies whether a small router can make a better L2 prefetching
policy out of **two existing L2 prefetchers**.

The simulator stack underneath the project is **Athena**, vendored in
`external/athena/`. Athena is a **trace-based simulator** built on ChampSim.
That means it does not run applications directly on real hardware. Instead, it
replays recorded execution traces and reports metrics such as IPC, cache misses,
and prefetch traffic for a chosen machine configuration.

The local method in this repository is **Mixture-of-Prefetchers Lite
(MoP-lite)**. MoP-lite is a small controller placed at the **L2 cache**. It does
not invent new prefetch candidates on its own. It only decides how two existing
L2 prefetchers should be enabled and budgeted from one epoch to the next.

The project question comes from `docs/operational/mop_stage1_instruction.md`:

> Can a small epoch-based manager combine two strong L2 prefetchers well enough
> to beat the strongest single-prefetcher baseline while staying within traffic
> and usefulness constraints?

That framing matters. The goal is not just "make something faster." The goal is
to test whether **coordination itself** adds value once two strong single
prefetchers already exist.

## Core Terms And Scale

- **Trace**: one recorded workload execution stream replayed by Athena.
- **Run**: one trace evaluated under one experiment setting, such as
  `Baseline`, `Pythia`, `SPP+PPF`, `AthenaMAB`, or `MoPLite`.
- **Warmup**: the initial part of a run that fills caches and predictor state.
  Warmup is not one epoch. It is a contiguous prefix of the run that may span
  many epochs.
- **Simulation window**: the measured part of the run after warmup. Final IPC
  and miss-rate statistics come from this part.
- **Epoch**: a fixed chunk of retired instructions. In this project,
  `og_instr_epoch_len=500000`, so one epoch is **500,000 retired instructions**.
  Retired instructions are instructions that complete at the simulated core.

The epoch size comes from:

- `external/athena/config/mop_lite.ini`
- `external/athena/config/mop_lite_mab.ini`

The run lengths come from `configs/run_modes.json`.

- `smoke_mode`: `5M` warmup + `10M` simulation = `15M` total instructions
  = `30` total epochs, of which `20` are measured simulation epochs.
- `search_mode`: same as `smoke_mode`, so again `30` total epochs and `20`
  measured simulation epochs.
- `final_mode`: `20M` warmup + `50M` simulation = `70M` total instructions
  = `140` total epochs, of which `100` are measured simulation epochs.

The official suite is:

- `24` traces total in `configs/trace_suites.json`
- `17` train traces and `7` held-out traces

The currently materialized Stage 1 evidence is:

- `17` train-side traces
- `7` held-out traces
- `230` completed runs in `data/processed/runs.csv`

So the finished Stage 1 snapshot now spans the full 24-trace suite: the
training side was covered by the official `search_mode` subset plus a matching
follow-on batch for the remaining training traces, and the held-out side was run
once as the final readout.

## The Two Experts And The Main Baselines

The default expert pair is fixed in `configs/trace_suites.json`:

- `expert_0 = Pythia`
- `expert_1 = SPP+PPF`

Why this pair?

- The project question is intentionally hard: can a router improve on **strong**
  single-expert baselines, not only on weak ones?
- Starting from a strong pair makes it harder to claim success by comparing to a
  weak strawman.
- It also means gains may be small or absent if one expert already dominates the
  relevant traces.

The key inherited components are:

- **`Pythia`**: an upstream Athena L2 prefetcher.
- **`SPP+PPF`**: another upstream Athena L2 prefetcher, exposed as
  `spp_ppf_dev` in `external/athena/scripts/config.py` and implemented under
  `external/athena/prefetcher/ppf_dev.cc`.
- **`AthenaMAB`**: this repo's name for Athena's built-in MAB-style
  coordinator. MAB means **multi-armed bandit**. It is not another prefetcher.
  It is another **epoch-based coordinator** for the same pair of experts.
  In Athena's L2-only mode it also acts once per epoch, but it learns by
  comparing rewards across actions instead of using the local MoP-lite score
  formula.

The important distinction is:

- `Pythia` and `SPP+PPF` are **prefetchers**.
- `AthenaMAB` and `MoPLite` are **coordinators** that sit above the pair.

## What We Inherited Versus What We Added

Inherited from Athena:

- the ChampSim-based simulator stack in `external/athena/`
- the existing single-prefetcher implementations such as `Pythia`, `SPP+PPF`,
  `MLOP`, and `SMS`
- Athena's built-in MAB coordinator, which this repo labels `AthenaMAB`
- Athena's trace metadata and download definitions in
  `external/athena/scripts/config.py`

Added in this repository:

- the scoped MoP-lite study and its frozen experiment protocol
- local edits to `external/athena/src/oogway.cc`
- local config files such as `external/athena/config/mop_lite.ini` and
  `external/athena/config/mop_lite_mab.ini`
- local simple router baselines: `FixedSplit`, `WinnerTakeAll`,
  `RandomRouter`, and `OneShotFit`
- the Python runners in `scripts/`
- the dataset pipeline and advisor-facing docs in `docs/`, `data/processed/`,
  and `report/`

So the right way to talk about ownership is:

- results for `Pythia` and `SPP+PPF` are upstream Athena prefetchers measured
  under this repo's protocol
- results for `AthenaMAB` are an upstream Athena coordinator measured under this
  repo's protocol
- results for `MoPLite` are the local coordinator path implemented and studied
  in this repository

## Why Python Runs The C++ Simulator

The microarchitectural behavior lives in Athena's C++ code and builds to the
compiled binary `external/athena/bin/champsim`.

Python is used around that binary because the project needs experiment
management, not a second simulator implementation. The Python layer in
`scripts/` handles:

- choosing traces and experiment settings
- building the exact simulator flags for each run
- downloading traces when needed
- launching many runs with controlled concurrency
- recording provenance such as git revision, host, seed, and timestamps in
  `results/mop_lite/manifest.jsonl`
- turning raw outputs into `data/processed/runs.csv` and report tables

That split is deliberate.

- C++ decides what the simulated machine does.
- Python decides which runs happen and how their outputs become evidence.

## What We Changed In The C++ Code

The local simulator edits are concentrated in `external/athena/src/oogway.cc`.
They are not a full rewrite of Athena. They are targeted changes for this study.

The main local changes are:

- **L2-only scope enforcement**: `initialize_mop_epoch()` calls
  `set_ocp_enabled(false)`, so the local study does not mix L2 coordination with
  Athena's off-chip predictor path.
- **Budgeted two-expert control**: the local path assigns a total per-epoch
  budget and tracks how much of that budget each expert can use.
- **Local router baselines**: `FixedSplit`, `WinnerTakeAll`, `RandomRouter`,
  `OneShotFit`, and `MoPLite` all live in the same `mop_decision()` /
  `configure_mop_epoch()` path.
- **Per-epoch telemetry**: the local path emits counters such as
  `pref_issued_total`, `pref_useful_total`, `pref_budget_total`, and
  `pref_selected_epochs`, plus optional epoch CSV traces.

That is why the repo can compare several router variants under one common
control surface.

## How The Router Actually Works

This is the most important local method detail.

At the end of each epoch, MoP-lite looks at the **previous epoch** and computes
one score for each expert.

For expert `i`, the code in `mop_score()` uses three signals:

1. **Accuracy**
   `accuracy_i = 100 * useful_i / issued_i`
2. **Coverage proxy**
   `coverage_i = useful_i / retired_insts_in_epoch`
3. **Traffic share**
   `traffic_i = issued_i / (issued_0 + issued_1 + 1)`

In those formulas:

- `issued_i` is the number of prefetches expert `i` issued in the previous epoch
- `useful_i` is the number of those prefetches that later proved useful
- `retired_insts_in_epoch` is the epoch length actually observed in that epoch

The current default score in `external/athena/config/mop_lite.ini` is:

```text
score_i = 1.0 * (accuracy_i / 100)
        + 0.25 * coverage_i
        - 1.0 * traffic_i
```

with one hard rule in front of it:

- if `issued_i > 0` and `accuracy_i < mop_accuracy_floor`, then `score_i = 0`

The current floor is `mop_accuracy_floor = 30`, so any expert that issued
prefetches but fell below `30%` accuracy in the previous epoch is treated as
unacceptable for the next epoch.

Two clarifications matter here.

1. The current MoP-lite score uses **accuracy, usefulness-derived coverage, and
   traffic share**. It does **not** directly use the logged epoch fields
   `overall_bw`, `pref_bw`, or `pref_pollution`, even though those are emitted to
   the epoch CSV for later analysis.
2. The decision is **epoch-based**, not per-access. The router only changes the
   enable state and budget allocation once per epoch.

### The Action Space

`mop_decision()` chooses among four coarse actions:

- `0`: both experts off
- `1`: only expert 1 on
- `2`: only expert 0 on
- `3`: both experts on

The router variants differ in how they choose that action and how they split the
budget.

- **`FixedSplit`**: always action `3`, always both experts on, always split the
  budget by `mop_fixed_split_ratio`.
- **`WinnerTakeAll`**: choose the higher-scoring expert and give it the full
  budget.
- **`RandomRouter`**: randomly choose one expert and give it the full budget.
- **`OneShotFit`**: act like `WinnerTakeAll` for the first
  `mop_one_shot_epochs` epochs, then freeze the better average-scoring expert for
  the rest of the run.
- **`MoPLite`**: use the score signs directly.
  - if both scores are `<= 0`, choose action `0`
  - if only one score is positive, choose that expert only
  - if both scores are positive, choose action `3` and split the total budget in
    proportion to the two scores

So the local MoP-lite rule is not "always mix both experts." It is closer to
"turn off weak epochs, choose a winner when only one looks acceptable, and share
budget only when both look useful."

### What The Budget Means

The local total budget is `mop_total_budget = 2048` per epoch.

In the current implementation, that budget is enforced by `allow_prefetch()` in
`oogway.cc`. Once an expert has issued as many prefetches as its current epoch
budget allows, further prefetches from that expert are blocked until the next
epoch starts.

## Why These Settings Exist

The key fixed choices are motivated by clarity more than by cleverness.

- **Two experts only**: keeps the causal story readable and the action space
  small.
- **Epoch-based control**: keeps the controller simple enough to analyze and
  realistic enough to instrument in Athena.
- **Instruction-counted epochs**: makes the decision cadence independent of host
  machine speed.
- **OCP disabled**: isolates the question to L2-prefetcher coordination instead
  of mixing it with off-chip prediction. OCP stands for **off-chip predictor**.
- **Strong default pair**: makes the question harder but scientifically cleaner.
  If a router cannot beat strong singles, that is still useful evidence.

There is an important implication of that last choice.

If the two experts are already strong and have very similar win regions, then a
router may have little room to help. In that case, gating and budget sharing can
easily make things worse by suppressing the stronger expert or by spending time
with both experts off.

The opposite intuition is also possible: two weaker or more specialized experts
could be more complementary and might benefit more from routing. That is a
reasonable hypothesis, but **this repository does not yet contain committed
evidence that validates it**. The only committed pair-level evidence is for
`Pythia + SPP+PPF`, so any stronger claim about weak or specialized pairs would
be speculation at this point.

## What The Current Evidence Shows

The committed evidence now includes:

- the 10-trace training-side `search_mode` batch under `results/mop_lite_search/`
- the 7-trace follow-on training batch under `results/mop_lite_train_extra/`
- the 7-trace held-out batch under `results/mop_lite_final/`
- the merged processed dataset `data/processed/runs.csv`
- the regenerated figures and tables under `report/`

Taken together, those two training-side batches cover the full 17-trace training split.

The main Stage 1 conclusion is simple: some coordinators beat no-prefetch, but
no tested coordinator beats the pair-best single expert in geomean on either
split.

That result is easiest to read through two comparisons.

### Against no-prefetch

- On the 17-trace training side:
  - `AthenaMAB = 1.0095x`
  - `WinnerTakeAll = 1.0037x`
  - `FixedSplit = 1.0017x`
  - `MoPLite = 0.9986x`
- On the 7-trace held-out split:
  - `AthenaMAB = 1.0378x`
  - `OneShotFit = 1.0032x`
  - `WinnerTakeAll = 0.9997x`
  - `MoPLite = 0.9974x`

### Against the best of the coordinated pair (`Pythia`, `SPP+PPF`)

- On the 17-trace training side:
  - `AthenaMAB = 0.9619x`
  - `WinnerTakeAll = 0.9564x`
  - `FixedSplit = 0.9545x`
  - `MoPLite = 0.9515x`
- On the held-out split:
  - `AthenaMAB = 0.9560x`
  - `OneShotFit = 0.9242x`
  - `WinnerTakeAll = 0.9209x`
  - `MoPLite = 0.9188x`

The epoch traces still answer one useful review question directly: **yes, the
controller really does use the "both experts off" action, and the current
weakness is not only choosing the wrong expert**.

- Historical smoke epoch traces show repeated action `0` rows.
- The focused epoch diagnostic under `results/mop_lite_epoch_diag/` shows that
  `MoPLite` often includes the offline-better expert for the epoch even when it
  still loses overall. For example, on `459.GemsFDTD` and `437.leslie3d` the
  chosen action includes the offline-better expert in every epoch of that
  diagnostic, yet `MoPLite` is not the best overall coordinator in the merged
  Stage 1 result.

Even under a stricter fair-routing criterion, the current router does not beat a
blind fixed expert. On the 8 traces where both `Pythia` and `SPP+PPF` are
individually above no-prefetch and one clearly wins, `MoPLite` reaches only
`1.008597x` vs no-prefetch, while always choosing `Pythia` reaches `1.224603x`
and always choosing `SPP+PPF` reaches `1.172079x`. That is an important result:
the problem is not just picking the wrong expert on obviously complementary
traces. The current action policy still leaves too much value on the table.

So the current local result is not "the router made two experts stronger." The
current local result is closer to this:

- the pipeline works end to end
- the router logic is implemented and observable
- some coordinators achieve small `1+x` gains over no-prefetch
- the current `Pythia + SPP+PPF` coordination rules still lose in geomean to the
  better single expert from that pair on both the full training side and the
  held-out evidence
- under a fair predeclared routing criterion, the router has real ranking skill
  on some complementary traces, but still fails because its action policy is not
  reliable across the whole criterion set

The report figures now separate those questions cleanly:

- `ipc_speedup_summary.png` is only about beating prefetch-off
- `single_expert_profiles.png` is about whether the experts genuinely differ
- `win_loss_mop_vs_best_single.png` is about per-trace losses to the pair-best single
- `router_compare_criterion.png` is about what the routers actually predicted and whether those actions included the better expert

That does **not** invalidate the method. It does mean the current tracked result
is a negative performance result against the pair-best single baseline, not a
success claim.

## What Is Still Open

The current repo now has a complete Stage 1 baseline, but several scientific
questions remain open:

- whether Stage 2 tuning over the frozen control surface can turn the current
  negative-vs-best-single result into a positive held-out result
- whether a different expert pair is more complementary than `Pythia + SPP+PPF`
- whether the current floor and score weights are too aggressive
- whether the coordinator traffic proxy should be replaced by a simulator-side
  issued-traffic counter in a future measurement-only patch

## Where To Verify Claims

- Project charter: `docs/operational/mop_stage1_instruction.md`
- Official trace suite and run lengths: `docs/operational/experiment_setup.md`
- Local router implementation: `external/athena/src/oogway.cc`
- Local MoP-lite config: `external/athena/config/mop_lite.ini`
- Current processed dataset: `data/processed/runs.csv`
- Current merged summary: `data/processed/runs_summary.md`
- Current coordinator table: `report/tables/router_ablation.md`
- Fair routing criterion table: `report/tables/routing_criterion.md`
- Alternate-pair exploratory table: `report/tables/alternate_pair_exploration.md`
- Raw epoch traces: `results/mop_lite_search/runs/*/epoch_logs/*.csv` and
  `results/mop_lite_final/runs/*/epoch_logs/*.csv`

## Bottom Line

The repository already has a reproducible Stage 1 baseline: a two-expert L2
router, per-epoch telemetry, a fixed split, append-only manifests, a processed
dataset, and regenerated report artifacts. The committed evidence shows that the
current rules can deliver small wins over no-prefetch, but no tested
coordinator beats the strongest single expert from the committed pair in
geomean on either the full training side or the held-out split.
