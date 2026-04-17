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
  - `ipc_speedup_vs_nopref.png`
  - `ipc_speedup_vs_best_single.png`
  - `win_loss_mop_vs_best_single.png`
  - `accuracy_vs_traffic.png`
  - Tables for router ablation, expert-pair ablation, and hardware budget.
- Froze the split artifact `data/splits/official_v1.json` (copy of
  `configs/trace_suites.json`) with sha256 side-car
  `data/splits/official_v1.sha256`.
- Added `docs/environment.md`, `docs/dataset_schema.md`,
  `docs/research_log.md`, `docs/transparency_log.md`, `docs/stage2_memo.md`,
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
  of **0.9639** for `AthenaMAB` and **0.9635** for `MoPLite`.
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
