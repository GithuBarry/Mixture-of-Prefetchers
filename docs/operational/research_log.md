# Research log

Chronological, per-batch engineering log for MoP-lite Stage 1. Each entry
records the date, the batch goal, what was run, the observed signal, and the
concrete next action. Entries are append-only; mistakes are corrected by new
entries, not by rewriting history.

## 2026-04-17 — Stage 1 bring-up, pre-first-run

**Goal.** Stand up the full Stage 1 infrastructure (runner, manifest,
dataset, figures, docs, report scaffolding) before producing any numbers,
so that the first real run generates analysis-ready artifacts end-to-end.

**What was built / changed.**

- Patched `external/athena/src/oogway.cc`:
  - `initialize_mop_epoch` now explicitly disables OCP (`ocp_enable = false`)
    so the charter's OCP-disabled scope is enforced in code, not config.
  - Fixed MoP-lite fallback: when both expert scores were ≤ 0, the router
    previously fell through to "both experts active" (action 3). It now maps
    to "both off" (action 0), honoring the usefulness floor.
  - Extended the per-epoch CSV trace with `budget_share0/1`,
    `retired_insts`, `accuracy0/1`, `coverage0/1`.
- Added `external/athena/config/mop_lite_mab.ini` (Athena's built-in MAB
  coordinator) as a separate builtin baseline, labelled `AthenaMAB` in all
  results and figures.
- Added `builtin_coordinators: ["AthenaMAB"]` to every mode in
  `configs/run_modes.json` / `.yaml`.
- Rewrote `scripts/run_mop_lite.py`:
  - Added `--mode {smoke_mode,search_mode,final_mode}` that sources traces,
    routers, builtins, and instruction counts from `configs/run_modes.json`.
  - Emits a per-run record to `results/mop_lite/manifest.jsonl` with the full
    flag string, `git_revision`, host, seed, start/end UTC, and every
    primary metric we care about (MPKI, pf accuracy, pf useless, pf late,
    per-expert issued/useful/budget/selected_epochs).
  - Supports `AthenaMAB` via a separate `builtin_flags()` path.
- Added `scripts/build_dataset.py` that joins manifest + metrics + official
  split and writes `data/processed/runs.csv` + a summary markdown block.
- Added `scripts/make_figures.py` (matplotlib, Agg backend) producing:
  - `ipc_speedup_summary.png`
  - `single_expert_profiles.png`
  - `win_loss_mop_vs_best_single.png`
  - Tables for router ablation, expert-pair ablation, and hardware budget.
- Froze the split artifact `data/splits/official_v1.json` (copy of
  `configs/trace_suites.json`) with sha256 side-car
  `data/splits/official_v1.sha256`.
- Added `docs/operational/environment.md`, `docs/operational/dataset_schema.md`,
  `docs/operational/research_log.md`, `docs/operational/transparency_log.md`, `docs/operational/stage2_memo.md`,
  `report/outline.md`, `report/draft.md`.

**Verification.** `make -C external/athena -j$(nproc)` succeeded (exit 0).
Only pre-existing upstream warnings were produced; no new warnings from the
patched `oogway.cc`. No simulator runs have been executed yet.

**Next batch.** Run `scripts/run_mop_lite.py --mode smoke_mode --epoch-trace`
end-to-end on the 2 smoke traces × {Baseline, Pythia, SPP+PPF, MoPLite,
AthenaMAB} to:

1. Validate the pipeline produces non-empty manifest + figures + tables.
2. Confirm MoPLite's corrected fallback actually changes behaviour vs the
   previous "both on" default (expect different `pref{0,1}_budget_total`
   when both scores ≤ 0).

No results or figures will be reported before that run completes.

## 2026-04-17 — Smoke batch after pipeline hardening

**Goal.** Re-run the 2-trace smoke matrix after fixing the review findings that
affected evidence quality: persistent crash logs, fail-loud metric parsing,
manifest provenance stamps from active configs, split enforcement, stale figure
cleanup, and smoke-mode baseline consistency.

**What was run.**

```bash
python3 scripts/run_mop_lite.py --mode smoke_mode --skip-download --epoch-trace
python3 scripts/build_dataset.py
python3 scripts/make_figures.py
```

**Completed artifacts.**

- `results/mop_lite/manifest.jsonl` with 10 rows
- `results/mop_lite/logs/*.out,*.err` and `metrics/*.json` for all 10 runs
- `data/processed/runs.csv`
- `report/figures/*.png`
- `report/tables/*.md`

**Main findings from the smoke traces.**

- Both smoke traces still prefer the strongest single expert (`SPP+PPF`) over
  both coordinators.
- Geomean IPC vs best single expert on the smoke set:
  - `AthenaMAB`: `0.959924x`
  - `MoPLite`: `0.958711x`
- Per-trace MoP-lite results:
  - `429.mcf-192B`: `0.947542x` vs best single
  - `parsec_2.1.fluidanimate...`: `0.970011x` vs best single

**Important instrumentation note.**

`Core_0_L2C_prefetch_issued` remains zero on the MoPLite smoke runs while the
per-expert MoP counters are nonzero (`pref{0,1}_issued_total`). The current
dataset therefore preserves both the raw cache-level issued counter and the
downstream DRAM / queue-congestion proxies, and treats the per-expert MoP issue
counters as internal coordinator telemetry rather than ground-truth traffic.

**Interpretation.**

The codebase now produces a clean end-to-end smoke batch again. The current
MoP-lite rule is a valid baseline implementation, and the current smoke result
is a negative result: coordination is trailing the best single expert on both
smoke traces.

**Next action.**

Run a broader search-side batch on the training traces, keeping held-out traces
untouched, then decide whether the mainline MoP-lite rule needs a control-surface
adjustment before any final-mode evidence is generated.

## 2026-04-17 — Smoke-mode pipeline materialized

_Superseded by the hardened smoke rerun above; kept here only as historical context._

**Goal.** Validate the full Stage 1 evidence chain on the smoke subset and get a
first read on whether the current coordinator settings help on two quick traces.

**Materialized artifacts.** The workspace now contains outputs consistent with
the standard Stage 1 chain:

- raw run artifacts under `results/mop_lite/`
- analysis dataset `data/processed/runs.csv`
- dataset summary `data/processed/runs_summary.md`
- report tables under `report/tables/`

**Observed signal.** The current smoke snapshot says:

- `data/processed/runs_summary.md` reports **10 runs** over **2 traces**.
- Both smoke traces fall on the **train** side of the official split.
- `report/tables/router_ablation.md` reports geomean `speedup_vs_best_single`
  of **0.959924x** for `AthenaMAB` and **0.958711x** for `MoPLite` in the
  hardened smoke rerun.
- The best single expert on both smoke traces is `SPP+PPF`, according to the
  per-trace rows in `data/processed/runs.csv`.
- `MoPLite` lands close to baseline IPC on `fluidanimate` and slightly below
  baseline on `429.mcf-192B`, while staying below the best single expert on both
  smoke traces.

**Interpretation.** The strongest current result is infrastructure readiness.
The smoke batch proves the project can go from Athena runs to a dataset and then
to report tables. The current smoke traces favor the strongest single expert,
so the present evidence supports a careful negative performance statement on the
smoke subset.

**Next batch.** Run the documented `search_mode` matrix on the broader training
subset, rebuild `data/processed/runs.csv`, and inspect whether any traces show
the cross-expert complementarity the Stage 1 method is designed to capture.

## 2026-04-17 — Search-side batch on the training subset

**Goal.** Run the official `search_mode` matrix on the 10-trace training-side
search subset and get a first real router ablation beyond smoke.

**What was run.**

```bash
python3 scripts/run_mop_lite.py --mode search_mode --workers 15 \
  --results-dir results/mop_lite_search
python3 scripts/build_dataset.py \
  --manifest results/mop_lite_search/manifest.jsonl \
  --out-csv data/processed/search_runs.csv \
  --out-summary data/processed/search_runs_summary.md
```

**Completed artifacts.**

- `results/mop_lite_search/manifest.jsonl` with 90 rows
- 90 raw logs, 90 stderr files, and 90 metrics files
- `data/processed/search_runs.csv`

**Main findings.**

- Geomean IPC vs no-prefetch on the 10-trace training-side subset:
  - `WinnerTakeAll`: `1.011080x`
  - `AthenaMAB`: `1.004727x`
  - `FixedSplit`: `1.004193x`
  - `MoPLite`: `1.000874x`
- Geomean IPC vs the better of the coordinated pair (`Pythia`, `SPP+PPF`):
  - `WinnerTakeAll`: `0.975024x`
  - `AthenaMAB`: `0.968898x`
  - `FixedSplit`: `0.968383x`
  - `MoPLite`: `0.965182x`
- `MoPLite` beats the pair-best single expert on 4 of the 10 search traces:
  `450.soplex`, `605.mcf_s`, `ligra_CF`, and `secret_compute_int_568`.

**Interpretation.**

The search-side result shows real complementarity pockets, but not enough to
overcome the best single expert in geomean. This is a scientifically useful
negative result: coordination can help on selected traces, yet the current
default MoP-lite rule is not the best policy over the search subset.

**Next action.**

Run the held-out batch without touching the held-out traces during tuning, then
rebuild the merged dataset and figures.

## 2026-04-17 — Held-out final batch and final Stage 1 readout

**Goal.** Run the untouched held-out split once, merge the search + held-out
manifests, and produce the final Stage 1 analysis artifacts.

**What was run.**

```bash
python3 scripts/run_mop_lite.py \
  --trace 437.leslie3d-134B \
  --trace 459.GemsFDTD-1169B \
  --trace 471.omnetpp-188B \
  --trace parsec_2.1.canneal.simlarge.prebuilt.drop_4750M.length_250M \
  --trace parsec_2.1.streamcluster.simlarge.prebuilt.drop_0M.length_250M \
  --trace ligra_BC.com-lj.ungraph.gcc_6.3.0_O3.drop_500M.length_250M \
  --trace secret_compute_fp_105 \
  --warmup-instructions 20000000 \
  --simulation-instructions 50000000 \
  --expert-0 Pythia --expert-1 SPP+PPF \
  --router FixedSplit --router WinnerTakeAll --router RandomRouter \
  --router OneShotFit --router MoPLite \
  --builtin AthenaMAB \
  --single-baseline MLOP --single-baseline SMS \
  --workers 15 --skip-download \
  --results-dir results/mop_lite_final

python3 scripts/build_dataset.py \
  --manifest results/mop_lite_search/manifest.jsonl \
  --manifest results/mop_lite_final/manifest.jsonl \
  --out-csv data/processed/runs.csv \
  --out-summary data/processed/runs_summary.md

python3 scripts/make_figures.py
```

**Completed artifacts.**

- `results/mop_lite_final/manifest.jsonl` with 77 rows
- merged `data/processed/runs.csv` with 230 rows across the full 24-trace suite
- regenerated `report/figures/*.png` and `report/tables/*.md`

**Main findings.**

- Held-out geomean IPC vs no-prefetch:
  - `AthenaMAB`: `1.037783x`
  - `OneShotFit`: `1.003241x`
  - `WinnerTakeAll`: `0.999658x`
  - `MoPLite`: `0.997413x`
  - `RandomRouter`: `0.998269x`
  - `FixedSplit`: `0.995448x`
- Held-out geomean IPC vs pair-best single (`Pythia` / `SPP+PPF`):
  - `AthenaMAB`: `0.956029x`
  - `OneShotFit`: `0.924208x`
  - `WinnerTakeAll`: `0.920907x`
  - `RandomRouter`: `0.919627x`
  - `MoPLite`: `0.918839x`
  - `FixedSplit`: `0.917028x`
- `MoPLite` beats the pair-best single expert on only 1 of 7 held-out traces
  (`459.GemsFDTD`) and is effectively tied on `ligra_BC` and `streamcluster`.
- `MoPLite` beats no-prefetch on 3 of 7 held-out traces and loses on the rest.

**Important caveat.**

For coordinator rows, Athena's raw `Core_0_L2C_prefetch_issued` counter can stay
at zero while the per-expert MoP issue counters move. The final Stage 1 dataset
therefore uses a documented fallback traffic proxy for coordinator rows:
`pref0_issued_total + pref1_issued_total` when the raw cache-issued counter is
zero. This keeps the traffic and accuracy analyses from collapsing to hidden
zeros, but it also means coordinator traffic is measured by a different, more
conservative proxy than single-expert traffic.

**Interpretation.**

Stage 1 is scientifically complete as a baseline. The code, split, manifest,
dataset, figures, and report foundation are all real and reproducible. The
performance story is negative but clear: the current `Pythia + SPP+PPF`
MoP-lite rule does not beat the strongest single expert in geomean on either the
full 17-trace training split or the held-out split. Against no-prefetch, some
coordinators do deliver `1+x` gains, but the pair-best single expert remains
the stronger reference. That means Stage 2 should search the control surface
rather than restate Stage 1 as a success claim.

## 2026-04-17 — Focused epoch-trace diagnostic for routing behavior

**Goal.** Answer the obvious follow-up question the merged batch cannot answer
by itself: how often does `MoPLite` route to the offline-better expert at the
epoch level on a few representative traces?

**What was run.**

```bash
python3 scripts/run_mop_lite.py \
  --trace 450.soplex-92B \
  --trace 605.mcf_s-472B \
  --trace 459.GemsFDTD-1169B \
  --trace 437.leslie3d-134B \
  --expert-0 Pythia --expert-1 SPP+PPF \
  --router MoPLite \
  --workers 4 --epoch-trace --skip-download \
  --warmup-instructions 5000000 --simulation-instructions 10000000 \
  --results-dir results/mop_lite_epoch_diag
```

**Working definition.** The offline oracle for an epoch is the expert with the
higher realized `useful` count in that same epoch. When both experts have zero
useful prefetches, the oracle action is "both off". Two match metrics are
useful:

- **exact oracle match**: chosen action equals the oracle action
- **oracle included**: the chosen action contains the oracle expert, so `both on`
  counts as including the better expert even when it is not exact

**Observed signal.**

- `450.soplex-92B`
  - exact oracle match: `0.633`
  - oracle included: `0.967`
- `605.mcf_s-472B`
  - exact oracle match: `0.900`
  - oracle included: `0.933`
- `459.GemsFDTD-1169B`
  - exact oracle match: `0.000`
  - oracle included: `1.000`
- `437.leslie3d-134B`
  - exact oracle match: `0.000`
  - oracle included: `1.000`

**Interpretation.** The current `MoPLite` rule often **includes** the better
expert, but does not necessarily isolate it. On `GemsFDTD` and `leslie3d` it
includes the better expert every epoch in this diagnostic, yet still fails to be
the best overall coordinator on the merged Stage 1 result. That is strong
evidence that the current weakness is not only "choosing the wrong expert"; it
also involves how aggressively the router shares budget or keeps both experts
enabled.

## 2026-04-17 — Failure-case epoch diagnostics

**Goal.** Test whether the strongest MoPLite losses are primarily caused by
choosing the wrong expert, or by other control decisions such as overuse of the
`both off` action or weak isolation of the winning expert.

**What was run.**

```bash
python3 scripts/run_mop_lite.py --trace 602.gcc_s-734B \
  --expert-0 Pythia --expert-1 SPP+PPF \
  --router MoPLite --workers 2 --epoch-trace --skip-download \
  --warmup-instructions 5000000 --simulation-instructions 10000000 \
  --results-dir results/mop_lite_epoch_diag_602

python3 scripts/run_mop_lite.py --trace secret_compute_fp_105 \
  --expert-0 Pythia --expert-1 SPP+PPF \
  --router MoPLite --workers 2 --epoch-trace --skip-download \
  --warmup-instructions 20000000 --simulation-instructions 50000000 \
  --results-dir results/mop_lite_epoch_diag_fp105
```

**Observed signal.**

- `602.gcc_s-734B`
  - oracle-better expert included: `1.000`
  - exact oracle action match: `0.000`
- `secret_compute_fp_105`
  - oracle-better expert included: `0.993` overall / `0.985` on nonzero-useful epochs
  - exact oracle action match: `0.536`
  - `both off` action rate: `0.543`

**Interpretation.** These failure diagnostics sharpen the mechanism claim. The
current MoPLite losses are not mainly caused by choosing the wrong expert.
Instead, the rule often includes the right expert but still loses because it
fails to isolate that expert, turns both experts off too often, or shares budget
in a way that gives up too much IPC.

## 2026-04-17 — Fair routing criterion on complementary Pythia/SPP traces

**Criterion.** Evaluate routing only on traces where both `Pythia` and
`SPP+PPF` are individually above no-prefetch, and one of them is clearly better.
Do not report only the traces that make the router look good.

**Criterion-matching diagnostics run.**

- `429.mcf-192B` (SPP+PPF better)
- `619.lbm_s-2676B` (SPP+PPF better)
- `602.gcc_s-734B` (Pythia better)
- `secret_compute_int_243` (Pythia better)
- `secret_compute_fp_105` (Pythia better)
- `437.leslie3d-134B` (Pythia slightly better)
- `parsec_2.1.canneal...` (Pythia better)

**Observed signal.**

- Clear successes:
  - `602.gcc_s`: oracle-better expert included in `100%` of epochs
  - `619.lbm_s`: `100%`
  - `secret_compute_int_243`: `100%`
  - `437.leslie3d`: `100%`
- Mixed or failing criterion cases:
  - `429.mcf`: exact oracle match `0.900`, but `both off` in `93.3%` of epochs
  - `secret_compute_fp_105`: oracle included in `98.5%` of nonzero-useful epochs,
    but exact match only `0.536` and `both off` rate `0.543`
  - `parsec canneal`: exact oracle match `0.967`, but `both off` in `100%` of
    epochs under the short-window diagnostic

**Interpretation.** Under a fair predeclared criterion, the router does show
real routing skill on some complementary traces. But the same criterion set also
contains clear failures. So the right conclusion is not "the router can never
pick the right expert" and not "the router works when evaluated fairly". The
right conclusion is narrower: the current score often identifies the better
expert, but the action policy still overuses `both off` or fails to translate
that ranking into a consistently good epoch action.

## 2026-04-17 — Alternate-pair exploratory baselines on held-out traces

**Goal.** Check whether the negative `MoPLite` result is mostly a bad pair
choice rather than a bad router, using small held-out exploratory batches with
alternate expert pairs.

**What was run.** Three held-out exploratory batches with the same light
coordinator set (`MoPLite`, `FixedSplit`, `WinnerTakeAll`, `AthenaMAB`) and
shorter windows (`5M` warmup + `10M` simulation):

- `MLOP + SMS`
- `Pythia + SMS`
- `MLOP + Pythia`

**Observed signal.** `MoPLite` geomean on held-out traces:

- `MLOP + SMS`: `0.999778x` vs no-prefetch, `0.984551x` vs pair-best single
- `Pythia + SMS`: `0.998842x` vs no-prefetch, `0.913791x` vs pair-best single
- `MLOP + Pythia`: `1.000381x` vs no-prefetch, `0.923328x` vs pair-best single

**Interpretation.** Pair choice clearly matters: alternate pairs can improve the
no-prefetch result and move `MoPLite` closer to parity with the pair-best single
expert. But no tested alternate pair turns `MoPLite` into a winner against its
own pair-best single. That means the current Stage 1 weakness is not only pair
selection; the router policy itself still leaves substantial value unrealized.

## 2026-04-28 — LLC-prefetcher experiment surface

**Goal.** Explore the user's suggested "last-level cache" angle without
weakening the prefetch-off baseline or relabeling the current MoPLite router as
a win.

**What changed.** Added an explicit `llc` experiment kind to
`scripts/run_mop_lite.py`. These runs use the same baseline flags and same trace
protocol, but add `--llc_prefetcher_types=<candidate>` without enabling any L2
prefetcher. The dataset builder now records `llc_prefetch_issued`,
`llc_prefetch_useful`, `downstream_prefetch_issued`, and
`downstream_prefetch_useful`, so LLC-only traffic is not hidden behind L2C
counters.

**Exploratory screen.** A local, short-window screen was run on the 13 traces
already present under `artifacts/athena_traces` using `0.5M` warmup and `1M`
simulation instructions. This was a candidate search, not final evidence.

- `LLC-AMPM`: `1.0083x` geomean vs no-prefetch, `7/13` per-trace wins.
- `SPP+PPF`: `1.0453x` geomean vs no-prefetch, `9/13` per-trace wins in the
  same screen.
- `SPP+PPF + LLC-AMPM`: `0.9994x` geomean vs no-prefetch, showing that naive
  L2+LLC stacking can interfere rather than help.

**End-to-end smoke check.** `python3 scripts/run_mop_lite.py --mode smoke_mode
--workers 6 --skip-download --results-dir results/_dev_llc_smoke` completed
with 12 runs. `LLC-AMPM` beat no-prefetch on both smoke traces (`1.0215x` on
`fluidanimate`, `1.0001x` on `429.mcf`) but did not beat the stronger L2 single
expert on those traces.

**Longer local check.** A second local run used all 13 currently downloaded
traces and the search-window length (`5M` warmup + `10M` simulation):
`python3 scripts/run_mop_lite.py --warmup-instructions 5000000
--simulation-instructions 10000000 --workers 8 --skip-download --results-dir
results/_dev_llc_local_10m --llc-prefetcher LLC-AMPM ...`. Because one local
PARSEC canneal trace is a short dev trace not in `official_v1`, this remains a
local stress check rather than an official dataset row.

- `LLC-AMPM`: `0.9654x` geomean vs no-prefetch, `5/13` per-trace wins.
- `Pythia`: `0.9825x` geomean vs no-prefetch, `7/13` per-trace wins.
- `SPP+PPF`: `0.9991x` geomean vs no-prefetch, `6/13` per-trace wins.

**Interpretation.** The defensible angle is now a broader cache-level portfolio
measurement: LLC-only prefetching can be evaluated fairly and sometimes helps,
but the longer local check does not justify claiming that LLC assistance fixes
the current routing weakness. The stronger evidence remains the existing
official Stage 1 result: some coordinators and L2 single experts beat
no-prefetch in split geomean, while the current MoPLite routing rule does not
beat the pair-best single. The next evidence-producing run should include the
full official suite, matched L2 singles, matched LLC-only candidates, and the
existing coordinators.

## 2026-04-28 — Stage 2 guarded router seed

**Goal.** Prepare a Stage 2 implementation seed that directly targets the
documented Stage 1 failure mode: `MoPLite` often has useful ranking signal but
overuses `both off` or starves one expert through score-proportional budget
splitting.

**Implementation.** Added explicit router `MoPLiteGuarded`
(`mop_router_type=5`) without changing old `MoPLite` (`mop_router_type=4`).
The guarded variant:

- maps both nonpositive scores to `both on` instead of `both off`
- applies a configurable per-expert budget floor,
  `mop_guarded_min_budget_share`, when both experts are enabled
- is available only through explicit `--router MoPLiteGuarded`; it is not in
  default or recommended run modes yet

**Development evidence.**

- two-trace smoke: `MoPLiteGuarded` `1.0205x` vs no-prefetch, old `MoPLite`
  approximately neutral
- 13-local-trace 1M scout: `MoPLiteGuarded` `1.0115x` vs no-prefetch and
  `1.0018x` vs old `MoPLite`
- official 10-trace search subset, `5M` warmup + `10M` simulation:
  - `MoPLiteGuarded`: `1.004932x` vs no-prefetch
  - old `MoPLite`: `1.002077x` vs no-prefetch
  - `MoPLiteGuarded / MoPLite`: `1.002849x`
  - `MoPLiteGuarded` vs pair-best single: `0.970158x`

**Interpretation.** The guarded policy is a modest but real train-side
improvement over old `MoPLite`. It does not solve the pair-best-single problem.
Treat it as a Stage 2 seed family for train-side structural search, not as the
final result.

## 2026-04-28 — Forced-single probe after initial epoch

**Goal.** Test whether `MoPLite` is losing because it is too indecisive:
overusing `both off` on some traces and `both on` / budget sharing on others.

**Implementation.** Added explicit router `ProbeThenWinner`
(`mop_router_type=6`). It uses the initial both-on epoch to collect signal, then
chooses exactly one expert by score after the configured probe window. The
runner also gained explicit MoP knob overrides for dev sweeps, with structured
capture of `mop_one_shot_epochs`.

**What was run.** Dev-only 1M filtered sweeps on five local traces where both
`Pythia` and `SPP+PPF` beat no-prefetch and separate by about 1% or more:

- `results/_dev_forced_single_probe`
- `results/_dev_forced_single_budget1024`
- `results/_dev_forced_single_budget4096`
- `results/_dev_forced_single_budget8192`

**Observed signal.**

- At budget 2048, forced-single routers improved over old `MoPLite` and
  `MoPLiteGuarded` on the filtered five-trace geomean, but stayed below the
  worse single routee on four of five traces.
- At budget 8192, `WinnerTakeAll` reached `1.035682x` vs no-prefetch and
  `0.991810x` vs pair-best on the filtered set; `ProbeThenWinner` reached
  `1.035570x` and `0.991703x`.
- The desired "between the two routees and closer to the better one" shape held
  for only two of five traces at budget 8192.

**Interpretation.** The indecision hypothesis is partly right: removing both
mixed actions after an initial probe and raising the budget improves the filtered
dev result. It is not a complete fix. Some traces still fall below the worse
single, while others overshoot the better single. Treat forced-single routing as
a Stage 2 candidate family, not as final evidence.
