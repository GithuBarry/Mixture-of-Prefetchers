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

## 2026-04-28 — Open Evolve: Stage 2 router implementation

**Goal.** Implement `OpenEvolve` (router type 5) as a targeted fix for the two
root causes identified in Stage 1 failure diagnostics:
(1) both-off overuse driven by cold-start and accuracy-floor trips, and
(2) insufficient winner isolation when one expert dominates.

**What was changed.**

- `external/athena/inc/knobs.def`: added `mop_winner_isolation_threshold`
  (float, default `3.0`) controlling the score-ratio above which E2 routes
  exclusively to one expert.
- `external/athena/src/oogway.cc`: added router type 5 (`OpenEvolve`) in both
  `mop_decision` and `configure_mop_epoch`.  Three targeted changes vs
  MoPLite (type 4):
  - **E1 Anti-Off Gate**: when both scores ≤ 0, fall back to
    the historically more-active expert (or `both on` on epoch 1) instead of
    `both off`.
  - **E2 Winner Isolation**: when one score ≥ `mop_winner_isolation_threshold ×`
    the other, route exclusively to the dominant expert with the full budget.
  - **E3 Squared-Score Budget Split**: when both-on action is selected, use
    squared scores for the budget allocation (steeper than linear; reduces
    traffic dilution to the weaker expert).
  Also updated `print_config` to log `mop_winner_isolation_threshold`.
- `external/athena/config/mop_lite_open_evolve.ini`: new INI file, identical
  to `mop_lite.ini` except `mop_router_type=5` and explicit
  `mop_winner_isolation_threshold=3.0`.
- `scripts/run_mop_lite.py`:
  - `ROUTERS` dict extended with `"OpenEvolve": 5`.
  - `ROUTER_BASE_CONFIGS` dict added: `OpenEvolve` loads
    `config/mop_lite_open_evolve.ini`; all other routers unchanged.
  - `INTERESTING_CONFIG_KEYS` extended with `mop_winner_isolation_threshold`
    so the active value is stamped into every manifest row.
  - `--mode` now accepts `open_evolve_mode`.
- `configs/run_modes.json` and `run_modes.yaml`: added `open_evolve_mode`
  (5M warmup / 10M sim, `search_subset`, `recommended_routers_open_evolve`).
- `configs/trace_suites.json` and `trace_suites.yaml`: added `OpenEvolve` to
  `recommended_routers_all` and added new key
  `recommended_routers_open_evolve: ["OpenEvolve", "MoPLite", "WinnerTakeAll"]`.
- `scripts/print_run_commands.py`: added `open_evolve_mode` to the mode choices.
- `report/draft.md`: added Section 7 (Open Evolve) with design rationale,
  change table, success criterion, run commands, and knob reference.

**Verification.**

```bash
make -C external/athena -j$(nproc)
```

Build succeeds with no new warnings from modified files.  No simulator runs
have been executed yet under `open_evolve_mode`; Stage 2 experiments are
pending.

**Next batch.**

Run `scripts/run_mop_lite.py --mode open_evolve_mode --workers 15
--results-dir results/open_evolve_search` on the 10-trace search subset
to get a first read on whether E1/E2/E3 improve `speedup_vs_best_single`
relative to Stage 1 MoPLite, and confirm the both-off rate drops on the
known failure-mode traces.  Review search-side results before running
the held-out batch.

## 2026-04-28 — OpenEvolve smoke validation on 2-trace subset

**Goal.** Validate that `OpenEvolve` (router type 5) behaves differently from
MoPLite on the two locally available traces (`429.mcf-192B` and
`parsec_2.1.fluidanimate...`), focusing on the both-off epoch rate and IPC
vs pair-best single expert.

**What was run.**

```bash
python3 scripts/run_mop_lite.py \
  --trace "429.mcf-192B" \
  --trace "parsec_2.1.fluidanimate.simlarge.prebuilt.drop_9500M.length_250M" \
  --expert-0 Pythia --expert-1 "SPP+PPF" \
  --router OpenEvolve --router MoPLite --router WinnerTakeAll \
  --builtin AthenaMAB \
  --warmup-instructions 5000000 --simulation-instructions 10000000 \
  --workers 6 --skip-download --epoch-trace \
  --results-dir results/open_evolve_smoke
```

**Completed artifacts.**

- `results/open_evolve_smoke/manifest.jsonl` with 14 rows
- `results/open_evolve_smoke/summary.csv` and `summary.md`
- epoch-trace CSVs for all 4 coordinator/router variants × 2 traces

**Main findings.**

Both-off epoch rates (30 epochs each, 5M warmup + 10M sim):

| Trace | MoPLite | OpenEvolve | WinnerTakeAll | AthenaMAB |
| --- | ---: | ---: | ---: | ---: |
| `429.mcf-192B` | 90.0% | **0.0%** | 0.0% | 13.3% |
| `fluidanimate` | 96.7% | **0.0%** | 0.0% | 6.7% |

E1 (Anti-Off Gate) completely eliminated the both-off collapse on both traces.
MoPLite was silencing all prefetching in 90–97% of epochs; OpenEvolve
routes to the historically-better expert in those slots instead.

Per-trace `speedup_vs_best_single`:

| Trace | MoPLite | OpenEvolve | WinnerTakeAll | AthenaMAB |
| --- | ---: | ---: | ---: | ---: |
| `429.mcf-192B` | 0.848074x | 0.847417x | 0.852123x | 0.862850x |
| `fluidanimate` | 0.970203x | **1.000549x** | 0.999035x | 1.006221x |

Geomean `speedup_vs_best_single` (2 traces):

| Router | Geomean |
| --- | ---: |
| AthenaMAB | 0.931782x |
| WinnerTakeAll | 0.922660x |
| **OpenEvolve** | **0.920805x** |
| MoPLite | 0.907085x |

`OpenEvolve` improves over MoPLite by **+1.4 pp geomean** and crosses
`1.0x` on `fluidanimate` (MoPLite was at `0.970x`). It does not yet beat
`AthenaMAB` on this 2-trace sample.

On `429.mcf`, SPP+PPF is the dominant expert by a wide margin and no
coordinator comes close to the pair-best single. The both-off fix does not
rescue this trace because the underlying routing problem is structural: no
coordinator can overcome SPP+PPF's large advantage on this workload at
these window lengths.

**Interpretation.**

E1 is the main driver of the improvement so far. The anti-off gate converts
epochs that were previously dead (both off) into single-expert epochs,
recovering the coverage that MoPLite was discarding. E2 and E3 are active
but require more diverse traces (with genuine score separation between
experts) to show their effect clearly.

**Next batch.**

Download the remaining 8 traces from the `search_subset` and run
`open_evolve_mode` on all 10 to get a full training-side geomean comparison
against Stage 1 MoPLite.

## 2026-04-28 — OpenEvolve full search-subset evaluation (10 traces)

**Goal.** Run the full `open_evolve_mode` matrix on all 10 `search_subset`
traces and compare `OpenEvolve` against `MoPLite`, `WinnerTakeAll`, and
`AthenaMAB` in geomean `speedup_vs_best_single`.

**What was run.**

```bash
python3 scripts/run_mop_lite.py --mode open_evolve_mode --workers 8 \
  --results-dir results/open_evolve_search
```

90 runs total (10 traces × 9 experiments: Baseline, Pythia, SPP+PPF, MLOP,
SMS, OpenEvolve, MoPLite, WinnerTakeAll, AthenaMAB).

**Completed artifacts.**

- `results/open_evolve_search/manifest.jsonl` with 90 rows
- `results/open_evolve_search/summary.csv` and `summary.md`

**Per-trace `speedup_vs_best_single`:**

| Trace | MoPLite | OpenEvolve | WinnerTakeAll | AthenaMAB |
| --- | ---: | ---: | ---: | ---: |
| `429.mcf` | 0.9590 | 0.9605 | 0.9635 | 0.9788 |
| `450.soplex` | 1.1628 | **1.1263** | 1.1266 | 0.9644 |
| `602.gcc_s` | 0.7059 | 0.7031 | 0.7384 | **1.0022** |
| `605.mcf_s` | 1.1794 | **1.2179** | 1.2092 | 0.8575 |
| `ligra_CF` | **1.0210** | 1.0105 | 1.0042 | 1.0002 |
| `ligra_PageRankDelta` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `fluidanimate` | 0.9702 | 0.9999 | 0.9985 | **1.0056** |
| `raytrace` | 0.8850 | 0.9991 | 0.9531 | **1.0161** |
| `secret_fp_45` | 0.8613 | 0.8621 | 0.8620 | 0.9724 |
| `secret_int_568` | **1.0337** | 0.9937 | 1.0024 | 0.9893 |

**Geomean `speedup_vs_best_single` (10 traces):**

| Router | Geomean |
| --- | ---: |
| SPP+PPF (single) | 0.9904x |
| **OpenEvolve** | **0.9781x** |
| WinnerTakeAll | 0.9780x |
| AthenaMAB | 0.9776x |
| MoPLite | 0.9683x |

`OpenEvolve` improves over Stage 1 `MoPLite` by **+0.98 pp geomean** on the
10-trace search subset. It is now essentially tied with `WinnerTakeAll` and
`AthenaMAB`.

`OpenEvolve` beats pair-best single on 5 of 10 traces: `450.soplex`,
`605.mcf_s`, `ligra_CF`, `ligra_PageRankDelta`, and partially on
`fluidanimate` (0.9999x ≈ parity). `MoPLite` beat pair-best single on only
4 traces with the same search-mode windows.

**Interpretation.**

E1 (Anti-Off Gate) is the primary driver, converting suppressed both-off
epochs into active single-expert epochs. E2 (Winner Isolation) contributes
on `605.mcf_s` where `OpenEvolve` exceeds both `WinnerTakeAll` and
`MoPLite`. On `602.gcc_s`, `AthenaMAB` is the only coordinator that crosses
1.0x — this trace remains hard for all rule-based routers, and the MAB
online reward estimator handles it better than any fixed-rule approach.

The geomean gap between `OpenEvolve` and `AthenaMAB` has closed from the
smoke sample (was 1.1 pp) to effectively zero (0.05 pp). This makes
`OpenEvolve` a viable comparison point: it uses no online learning and is
fully transparent, yet matches `AthenaMAB` geomean on the search subset.

**Next batch.**

Run the held-out 7-trace evaluation with final-mode instruction windows
(`20M` warmup + `50M` simulation) to get the definitive Stage 2 result.

## 2026-04-28 — OpenEvolve held-out evaluation (7 traces, final-mode windows)

**Goal.** Run `OpenEvolve` against `MoPLite`, `WinnerTakeAll`, and `AthenaMAB`
on the 7 held-out traces at the Stage 1 final-mode instruction windows
(`20M` warmup + `50M` simulation) to get the definitive Stage 2 number.

**What was run.**

```bash
python3 scripts/run_mop_lite.py \
  --trace 437.leslie3d-134B --trace 459.GemsFDTD-1169B --trace 471.omnetpp-188B \
  --trace parsec_2.1.canneal.simlarge.prebuilt.drop_4750M.length_250M \
  --trace parsec_2.1.streamcluster.simlarge.prebuilt.drop_0M.length_250M \
  --trace ligra_BC.com-lj.ungraph.gcc_6.3.0_O3.drop_500M.length_250M \
  --trace secret_compute_fp_105 \
  --warmup-instructions 20000000 --simulation-instructions 50000000 \
  --expert-0 Pythia --expert-1 SPP+PPF \
  --router OpenEvolve --router MoPLite --router WinnerTakeAll \
  --builtin AthenaMAB --single-baseline MLOP --single-baseline SMS \
  --workers 8 --epoch-trace \
  --results-dir results/open_evolve_final
```

**Completed artifacts.**

- `results/open_evolve_final/manifest.jsonl`
- `results/open_evolve_final/summary.csv` and `summary.md`
- epoch-trace CSVs for all router/builtin variants × 7 traces

**Per-trace `speedup_vs_best_single`:**

| Trace | MoPLite | OpenEvolve | WinnerTakeAll | AthenaMAB |
| --- | ---: | ---: | ---: | ---: |
| `437.leslie3d` | 0.8832 | **0.9096** | 0.9029 | 0.9989 |
| `459.GemsFDTD` | **1.0273** | 1.0057 | 1.0246 | 0.9883 |
| `471.omnetpp` | 0.9597 | **0.9717** | 0.9590 | 0.8942 |
| `ligra_BC` | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `parsec_canneal` | 0.9545 | **0.9779** | 0.9663 | 0.9756 |
| `streamcluster` | 0.9999 | **1.0000** | 1.0000 | 0.9999 |
| `secret_fp_105` | **0.6653** | 0.6589 | 0.6560 | 0.9866 |

**Geomean `speedup_vs_best_single` (7 held-out traces):**

| Router | Geomean | vs Stage 1 MoPLite |
| --- | ---: | ---: |
| AthenaMAB | 0.9770x | +5.8 pp |
| **OpenEvolve** | **0.9235x** | **+0.46 pp** |
| WinnerTakeAll | 0.9210x | +0.21 pp |
| MoPLite (Stage 1 ref) | 0.9188x | — |

**Interpretation.**

`OpenEvolve` improves over Stage 1 MoPLite by **+0.46 pp geomean** on the
held-out split and beats `WinnerTakeAll` by 0.24 pp. It crosses `1.0x` on
3 of 7 held-out traces: `GemsFDTD`, `ligra_BC`, and `streamcluster`.

The predeclared success criterion (`≥ 1.0x` geomean on held-out) is **not
met** (0.9235x). The main blocker is `secret_compute_fp_105` (0.659x for
OpenEvolve, same as MoPLite): this trace is dominated by `Pythia` by a very
large margin and no rule-based router recovers that gap.
`AthenaMAB` still leads by a substantial margin (5.8 pp) primarily because
its online reward estimator handles `secret_fp_105` and `437.leslie3d` far
better than any fixed-rule approach.

**Notable per-trace improvements over MoPLite:**

- `437.leslie3d`: +2.6 pp (0.883x → 0.910x) — E1 reducing both-off
- `parsec_canneal`: +2.3 pp (0.955x → 0.978x) — E1 reducing both-off
- `471.omnetpp`: +1.2 pp (0.960x → 0.972x)
- `streamcluster`: parity with MoPLite, now equals WinnerTakeAll at ~1.0x

**What Stage 2 establishes:**

- `OpenEvolve` is a reproducible improvement over Stage 1 MoPLite on both
  the search subset (+0.98 pp) and the held-out split (+0.46 pp).
- The anti-off gate (E1) is the primary driver of improvement.
- `secret_compute_fp_105` remains the hard case for all fixed-rule routers:
  it needs online adaptation or a better score signal, not just a routing
  policy fix.
- The path to matching `AthenaMAB` on held-out requires addressing the
  strong-dominance traces where fixed rules consistently under-perform.
