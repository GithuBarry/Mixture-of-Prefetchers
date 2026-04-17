# Project Guide

This document is the fastest way to understand the repository. It is written for
someone who knows the field in general but does not yet know this codebase,
Athena, or the local workflow.

The project studies **Mixture-of-Prefetchers Lite (MoP-lite)** inside the
Athena simulator.

Athena is a **trace-based computer architecture simulator** that is vendored
under `external/athena/`. It is built on ChampSim. In plain terms, Athena does
not run applications directly on real hardware. It replays recorded workload
traces and reports cache, bandwidth, and prefetch metrics for a chosen machine
configuration.

MoP-lite is a small controller that sits at the **L2 cache** inside that
simulator and coordinates **two existing L2 prefetchers**. It makes one
decision per **epoch**, where an epoch is a fixed instruction window inside one
measured run. In this project, one epoch is **500,000 retired instructions**
(`og_instr_epoch_len=500000` in `external/athena/config/mop_lite.ini` and
`external/athena/config/mop_lite_mab.ini`). The Stage 1 question comes from
`docs/mop_stage1_instruction.md`:

> Can a small epoch-based manager combine two strong L2 prefetchers well enough
> to beat the strongest single-prefetcher baseline while staying within traffic
> and usefulness constraints?

## Key terms

- **Athena**: the trace-based simulator stack vendored under `external/athena/`.
  Athena is built on ChampSim and already includes several L2 prefetchers and
  coordination mechanisms.
- **ChampSim**: the underlying simulator framework Athena builds on.
- **Trace**: a recorded execution stream that Athena replays. In this project,
  one trace stands in for one workload input.
- **Run**: one trace evaluated under one experiment setting, such as
  `Baseline`, `Pythia`, `SPP+PPF`, `AthenaMAB`, or `MoPLite`.
- **Warmup**: the first part of a run, used to fill caches and other simulator
  state before measurement starts.
- **Simulation window**: the measured part of a run after warmup. The reported
  IPC and prefetch metrics come from this part.
- **Epoch**: a fixed chunk inside the measured simulation window. At the end of
  each epoch, the coordinator can change which expert or experts are active for
  the next epoch. Stage 1 uses instruction-based epochs of 500,000 retired
  instructions.
- **Prefetcher expert**: an existing upstream Athena L2 prefetcher such as
  `Pythia` or `SPP+PPF`. MoP-lite chooses between experts and reuses their inner
  algorithms.
- **`SPP+PPF`**: the upstream Athena prefetcher exposed as
  `spp_ppf_dev` in `external/athena/scripts/config.py`. It is one of the strong
  single-prefetcher baselines in this repository and one half of the default
  Stage 1 expert pair. The upstream source code shows that it carries a
  signature table, a pattern table, a prefetch filter, and a perceptron-like
  component (`external/athena/prefetcher/ppf_dev.cc`).
- **Coordinator / router**: the policy that decides which expert is active for
  the next epoch. In this repo, the main coordinator is `MoPLite`. Simple
  comparison routers include `FixedSplit`, `WinnerTakeAll`, `RandomRouter`, and
  `OneShotFit`.
- **`AthenaMAB`**: this repo's label for Athena's built-in MAB-style
  coordinator, where MAB means **multi-armed bandit**. It is an upstream Athena
  baseline that this project runs under the same two-expert protocol.
- **Traffic budget**: the cap on prefetch activity. Stage 1 uses a shared
  budget to keep coordination honest.
- **Usefulness / accuracy floor**: a minimum quality bar for issued prefetches.
  Stage 1 uses this to avoid trading IPC for wasteful traffic.
- **Smoke mode / search mode / final mode**: the three named run modes defined
  in `configs/run_modes.json`. They differ in trace set, instruction window,
  and router coverage.

## One run in plain terms

One Stage 1 run looks like this.

1. Athena replays one workload trace.
2. The run spends an initial warmup window filling caches and predictor state.
3. The run then enters the measured simulation window.
4. That measured window is divided into epochs of 500,000 retired instructions.
5. At each epoch boundary, the coordinator reads the previous epoch's summary
   signals and chooses the next epoch's expert configuration.
6. Athena writes raw stdout, stderr, parsed metrics, and optional per-epoch CSV
   traces.
7. The project scripts turn those raw outputs into `data/processed/runs.csv`
   and then into report tables and figures.

That is why the repository keeps talking about traces, runs, warmup,
simulation, and epochs. Those are the core units of evidence here.

## Scope

The Stage 1 charter in `docs/mop_stage1_instruction.md` sets the scope.
The short version is:

- one simulator stack: Athena / ChampSim
- one coordination point: L2 cache
- one fixed machine configuration
- one decision cadence: epoch-level
- exactly two experts per coordinated run
- explicit measurement of IPC, traffic, and usefulness
- single-core execution
- OCP disabled

The Stage 2 boundary lives in `docs/stage2_memo.md`. That memo freezes the
parts Stage 2 should keep fixed and lists the router knobs Stage 2 may search.

## Provenance: upstream foundation and project work

This section matters for authorship and for claim scope.

### Upstream foundation

The repository builds on upstream Athena, documented in
`external/athena/UPSTREAM.md`.

Upstream Athena provides the foundation this project starts from:

- the ChampSim-based simulator stack under `external/athena/`
- existing L2 prefetchers such as `Pythia`, `SPP+PPF`, `MLOP`, and `SMS`
- Athena trace definitions and download metadata in
  `external/athena/scripts/config.py`
- existing coordination ideas inside Athena, including the builtin MAB-style
  coordinator we evaluate as `AthenaMAB`

Those components are part of the inherited simulator environment. Advisor-facing
claims about algorithm ownership should attribute them to Athena.

### Project work in this repository

This project adds the Stage 1 study built around that foundation.

- a scoped two-expert MoP-lite baseline study at L2
- local simulator edits in `external/athena/src/oogway.cc` to enforce the Stage
  1 scope and emit the telemetry the study needs
- the project-side runners in `scripts/run_mop_lite.py` and
  `scripts/run_single_prefetcher_baselines.py`
- the frozen experiment protocol in `configs/trace_suites.json`,
  `configs/run_modes.json`, and `data/splits/official_v1.json`
- the dataset and reporting pipeline in `scripts/build_dataset.py` and
  `scripts/make_figures.py`
- the advisor-facing documentation and research logs under `docs/`

The project contribution is the scoped coordination baseline, the evaluation
protocol, the local instrumentation, and the evidence pipeline built around
Athena.

## Why Python runs the compiled simulator

The core simulator is Athena / ChampSim under `external/athena/`, which builds
to the compiled binary `external/athena/bin/champsim`. The performance-critical
cache, prefetch, and epoch-control logic stays in Athena's C++ code.

Python sits around that binary because the project needs experiment management,
not a second simulator implementation.

The Python layer in `scripts/` handles the parts that are easier to audit and
reproduce outside the simulator core:

- loading Athena's trace metadata from `external/athena/scripts/config.py`
- downloading or locating official traces
- building the exact simulator flag string for each baseline or router run
- launching many runs across traces and configurations with controlled
  concurrency
- grouping outputs under a `run_group_id`
- stamping provenance such as git revision, host, seed, flags, and timestamps
  into `results/mop_lite/manifest.jsonl`
- parsing raw simulator stdout into machine-readable metrics and then into
  `data/processed/runs.csv`

That split is deliberate. C++ owns the microarchitectural behavior. Python owns
the experiment orchestration and evidence pipeline.

## What we changed in the simulator

The main local simulator work for Stage 1 lives in
`external/athena/src/oogway.cc`. The project did not write Athena from scratch.
It patched the upstream coordinator path to support this specific study.

The main local C++ changes are:

- scope enforcement: `initialize_mop_epoch()` forces `set_ocp_enabled(false)` so
  the Stage 1 L2-only, OCP-disabled scope is enforced in the simulator itself
- budgeted two-expert control: the MoP-lite path resets per-epoch budget
  tracking, applies the project budget knobs, and configures one-expert or
  two-expert budgets for the next epoch
- MoP-lite scoring and routing: `mop_score()` and `mop_decision()` implement the
  Stage 1 accuracy / coverage / traffic rule and the router variants
  `FixedSplit`, `WinnerTakeAll`, `RandomRouter`, `OneShotFit`, and `MoPLite`
- fail-safe routing behavior: when both expert scores are non-positive,
  `mop_decision()` returns action `0`, which means both experts stay off for the
  next epoch
- telemetry for analysis: the MoP path emits end-of-run counters such as
  `mop_pref_{0,1}_issued_total`, `useful_total`, `budget_total`, and
  `selected_epochs`
- per-epoch trace output: when `--epoch-trace` is enabled, Athena writes epoch
  CSV rows with budget shares, retired instructions, accuracy, coverage, and
  router scores

The project also added `external/athena/config/mop_lite_mab.ini` so the upstream
Athena MAB-style coordinator can be run under the same two-expert comparison
protocol and labeled clearly as `AthenaMAB`.

## What lives where

### Core implementation

- `external/athena/src/oogway.cc`: coordination logic, epoch accounting, and
  telemetry emitted by Athena.
- `external/athena/config/mop_lite.ini`: main MoP-lite configuration.
- `external/athena/config/mop_lite_mab.ini`: Athena's built-in MAB-style
  coordinator used as a baseline.

### Experiment runners

- `scripts/run_mop_lite.py`: main Stage 1 runner. It executes baseline,
  single-expert, router, and builtin coordinator runs and writes raw artifacts.
- `scripts/run_single_prefetcher_baselines.py`: smaller runner for standalone
  single-prefetcher baselines.
- `scripts/build_dataset.py`: converts raw run artifacts into the analysis
  table `data/processed/runs.csv`.
- `scripts/make_figures.py`: rebuilds report figures and markdown tables from
  `data/processed/runs.csv`.
- `scripts/print_run_commands.py`: prints concrete commands for each named run
  mode.

### Configuration

- `configs/trace_suites.json`: official 24-trace suite, train/held-out split,
  search subset, smoke subset, and recommended router lists.
- `configs/run_modes.json`: `smoke_mode`, `search_mode`, and `final_mode`.

### Raw and derived artifacts

- `results/mop_lite/runs/<run_group_id>/logs/`: Athena stdout/stderr per run.
- `results/mop_lite/runs/<run_group_id>/metrics/`: parsed metric dictionaries
  per run.
- `results/mop_lite/runs/<run_group_id>/epoch_logs/`: per-epoch CSV traces for
  router runs when `--epoch-trace` is enabled.
- `results/mop_lite/manifest.jsonl`: one JSON record per completed run from the
  runner. It is append-only and is partitioned by `run_group_id`.
- `data/processed/runs.csv`: analysis-ready dataset built from raw artifacts.
- `report/tables/` and `report/figures/`: report views generated from
  `data/processed/runs.csv`.

### Human-written context

- `docs/mop_stage1_instruction.md`: original charter and success criteria.
- `docs/experiment_setup.md`: official traces, splits, and run modes.
- `docs/environment.md`: toolchain, trace handling, and regeneration order.
- `docs/dataset_schema.md`: column-level meaning of `runs.csv`.
- `docs/research_log.md`: chronological record of what has been run.
- `docs/transparency_log.md`: key design decisions and their evidence.

## How the pipeline works

The evidence path has three stages.

1. `scripts/run_mop_lite.py` runs Athena and writes raw outputs under
   `results/mop_lite/runs/<run_group_id>/`.
2. `scripts/build_dataset.py` reads those outputs and writes
   `data/processed/runs.csv`.
3. `scripts/make_figures.py` reads `data/processed/runs.csv` and writes the
   current report tables and figures.

This layout matters for reading evidence.

- Raw simulator behavior lives in `results/`.
- Cross-run analysis lives in `data/processed/runs.csv`.
- Presentation lives in `report/`.

After any new simulator batch, run `scripts/build_dataset.py` and
`scripts/make_figures.py` so the derived artifacts match the raw ones.

## Current evidence snapshot

The current materialized evidence is a **smoke-mode batch**.

- `data/processed/runs_summary.md` reports **10 runs** over **2 traces**.
  That total comes from 2 traces multiplied by 5 experiments: `Baseline`,
  `Pythia`, `SPP+PPF`, `MoPLite`, and `AthenaMAB`.
- Both traces are in the **train** side of the official split.
- The coordinator comparison in `report/tables/router_ablation.md` shows:
  - `AthenaMAB`: geomean `speedup_vs_best_single = 0.9599`
  - `MoPLite`: geomean `speedup_vs_best_single = 0.9587`
- The expert-pair table in `report/tables/expert_pair_ablation.md` covers one
  pair so far: `Pythia + SPP+PPF`.

The current smoke snapshot says three useful things.

1. The end-to-end pipeline works: raw runs, dataset build, and report tables all
   exist.
2. The smoke traces favor the best single expert over both coordinators.
3. The current evidence is still an early checkpoint. The official full-suite
   evaluation design lives in `docs/experiment_setup.md` and remains the
   standard for stronger claims.

## Contribution and ownership

This repository is a Stage 1 systems-research baseline for L2 prefetcher
coordination. The project asks whether a small epoch-based controller can
coordinate two existing L2 prefetchers well enough to outperform the strongest
single expert under a traffic budget and a usefulness floor. The charter for
that question is `docs/mop_stage1_instruction.md`.

The project contribution is a scoped baseline study on top of Athena. It has
four project-owned pieces:

1. a fixed Stage 1 question about two-expert L2 coordination
2. local Athena-side instrumentation and scope-enforcing patches
3. a reproducible evaluation protocol with a frozen split and named run modes
4. a dataset-and-report pipeline that turns runs into advisor-readable evidence

The underlying simulator, the single-prefetcher experts, and the builtin
`AthenaMAB` coordinator come from Athena. This repository contributes the local
study design, the local MoP-lite baseline path, the local patches, and the
evidence pipeline.

That ownership split applies to the results as well.

- Results for `Pythia` and `SPP+PPF` measure upstream Athena modules under this
  repo's protocol.
- Results for `AthenaMAB` measure an upstream Athena coordinator under this
  repo's protocol.
- Results for `MoPLite` measure the local Stage 1 coordinator path and local
  instrumentation in this repository under the same protocol.

The docs describe Python scripts and C++ edits together because both layers are
part of the scientific method here. The C++ layer defines simulator behavior.
The Python layer defines which runs happen, how they are grouped, and how the
outputs become evidence.

## Design choices

The project studies coordination because different prefetchers help different
workloads and different phases of the same workload. A single fixed expert is a
strong baseline. A small coordinator gives the project a way to test whether
complementarity exists under explicit traffic control.

The Stage 1 control surface stays intentionally small.

- exactly two experts per coordinated run
- one decision per epoch
- one fixed machine configuration
- one L2-only coordination point
- explicit IPC, traffic, and usefulness measurements

That design keeps the baseline readable, keeps the hardware story compact, and
makes Stage 2 search practical. The Stage 2 boundary is frozen in
`docs/stage2_memo.md`.

The Stage 1 baseline also freezes a small set of default settings so the project
has one clear reference point before any optimization begins.

- **Expert pair = `Pythia + SPP+PPF`**: Stage 1 is explicitly a two-expert
  coordination study, and Stage 2 keeps this pair fixed so the search problem
  stays about coordination rather than expert replacement.
- **Epoch length = 500,000 retired instructions**: Stage 2's frozen-contract
  memo keeps instruction-based epochs because they are portable across hosts and
  independent of wall-clock speed. The same memo describes the tradeoff clearly:
  coarser epochs give stabler decisions, finer epochs adapt faster.
- **Router list = `FixedSplit`, `WinnerTakeAll`, `RandomRouter`, `OneShotFit`,
  `MoPLite`**: the simple routers show what plain coordination can do before any
  tuning. `RandomRouter` is mainly a sanity-check baseline. `MoPLite` is the
  main local rule.
- **OCP disabled**: the Stage 1 charter locks the study to L2-only
  coordination. The local C++ code enforces that choice directly.
- **Budget / floor / score weights**: `mop_total_budget=2048`,
  `mop_accuracy_floor=30`, `mop_fixed_split_ratio=50`, and
  `mop_score_weights=1.0,0.25,1.0` define a compact, interpretable baseline
  control surface. Stage 2 may tune these values within documented ranges, but
  Stage 1 needs one stable starting point first.
- **Warmup and simulation windows by mode**: `smoke_mode`, `search_mode`, and
  `final_mode` exist because the project has three different needs: quick system
  validation, affordable train-side iteration, and stronger final evidence.

The default expert pair is `Pythia + SPP+PPF`, recorded in
`configs/trace_suites.json` as `recommended_expert_pair`. Stage 1 uses that pair
because the project needs one clear baseline pair before broader pair ablations.
In the current smoke snapshot, `SPP+PPF` is the stronger single expert on both
smoke traces, which makes it the current comparison anchor.

## Interpretation of current evidence

The current smoke batch gives an early read on both performance and method.

- `SPP+PPF` is the strongest single expert on both smoke traces.
- `MoPLite` and `AthenaMAB` both trail that best-single reference on the smoke
  pair, as shown in `report/tables/router_ablation.md`.
- The current coordinator behavior looks conservative in the smoke snapshot: the
  `MoPLite` rows in `data/processed/runs.csv` show limited selected epochs and
  low effectiveness relative to the stronger single expert. The traffic
  accounting for coordinator rows currently uses a documented fallback proxy
  when the raw cache-issued counter stays at zero.

This pattern says the current Stage 1 settings are better established as a
controlled baseline than as a winning final policy on these two traces.

The current smoke results justify three claims.

1. The end-to-end pipeline works.
2. The Stage 1 baseline methods are implemented and comparable under one
   protocol.
3. The current smoke traces favor the strongest single expert over the current
   coordinators.

The method is still justified as a Stage 1 baseline method because it produces a
controlled comparison, exposes per-epoch telemetry, and creates the search-ready
interface Stage 2 needs. Broader evaluation is what will support stronger
performance claims.

Stage 1 success therefore has two levels.

1. Baseline success: the simulator builds, the methods run under one fair
   protocol, the dataset is complete, and the report pipeline works.
2. Stronger scientific success: the coordinator shows evidence-backed wins over
   the best single expert on the official broader evaluation.

The success ladder is written out in `docs/mop_stage1_instruction.md`.

Three kinds of evidence matter most for moving the current view.

1. `search_mode` results on the broader train subset.
2. `final_mode` results on the full official suite.
3. Per-trace cases where the two experts win in different regions and the
   coordinator captures that complementarity under the traffic budget.

Four pieces are still important for a stronger advisor-facing conclusion.

1. `search_mode` coverage across the broader training subset.
2. `final_mode` coverage across the full official suite.
3. Held-out evidence under the frozen split in `data/splits/official_v1.json`.
4. Multi-seed checking for the stochastic router path discussed in
   `docs/transparency_log.md`.

## Verifying claims

Use the shortest path that matches the claim.

- Project goal and scope: `docs/mop_stage1_instruction.md`
- Official protocol: `docs/experiment_setup.md`
- Current analysis rows: `data/processed/runs.csv`
- Current summary tables: `report/tables/router_ablation.md`
- Per-run raw evidence: `results/mop_lite/runs/<run_group_id>/`,
  `results/mop_lite/manifest.jsonl`
- Design reasons: `docs/transparency_log.md`

## What the main metrics mean

- **IPC**: instructions per cycle. This is the main performance metric.
- **MPKI**: cache misses per thousand instructions. It gives memory-pressure
  context.
- **`speedup_vs_baseline`**: IPC relative to the no-prefetch baseline.
- **`speedup_vs_best_single`**: IPC relative to the better of the two single
  experts on the same trace. This is the key MoP-lite comparison.
- **`l2c_prefetch_issued`**: effective L2 prefetch traffic used in analysis.
- **`downstream_prefetch_accuracy`**: useful downstream prefetches divided by
  effective issued prefetches.

`docs/dataset_schema.md` defines the full column list and the exact meaning of
each field.

## Reading order by question

Use this path for common questions.

### "What is the project trying to prove?"

1. `docs/mop_stage1_instruction.md`
2. `docs/outsider_guide.md`

### "Which traces and run lengths count as official?"

1. `docs/experiment_setup.md`
2. `configs/trace_suites.json`
3. `configs/run_modes.json`

### "How do I inspect current evidence?"

1. `data/processed/runs_summary.md`
2. `report/tables/router_ablation.md`
3. `data/processed/runs.csv`
4. `results/mop_lite/logs/` and `results/mop_lite/metrics/`

### "How does a run become a report table?"

1. `scripts/run_mop_lite.py`
2. `scripts/build_dataset.py`
3. `scripts/make_figures.py`
4. `docs/environment.md`

### "Which decisions were deliberate?"

1. `docs/transparency_log.md`
2. `docs/research_log.md`

## Bottom line

The repository already has a complete Stage 1 smoke pipeline with raw runs,
dataset generation, report tables, and a frozen experiment design. The next
important evidence jump comes from broader `search_mode` and `final_mode`
coverage under the same documented protocol.
