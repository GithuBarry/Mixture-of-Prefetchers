# Project Guide

This document is the fastest way to understand the repository. It also answers
the questions an advisor is likely to ask first.

The project studies **Mixture-of-Prefetchers Lite (MoP-lite)** inside the
Athena simulator. MoP-lite is a small controller that sits at the **L2 cache**
and coordinates **two existing L2 prefetchers**. It makes one decision per
**epoch**, where an epoch is a fixed instruction window. The Stage 1 question
comes from `docs/mop_stage1_instruction.md`:

> Can a small epoch-based manager combine two strong L2 prefetchers well enough
> to beat the strongest single-prefetcher baseline while staying within traffic
> and usefulness constraints?

## Key terms

- **Athena**: the simulator stack vendored under `external/athena/`. Athena is
  built on ChampSim and already includes several L2 prefetchers.
- **Prefetcher expert**: an existing L2 prefetcher such as `Pythia` or
  `SPP+PPF`. MoP-lite chooses between experts and reuses their inner
  algorithms.
- **Coordinator / router**: the policy that decides which expert is active for
  the next epoch. In this repo, the main coordinator is `MoPLite`. Simple
  comparison routers include `FixedSplit`, `WinnerTakeAll`, `RandomRouter`, and
  `OneShotFit`.
- **Traffic budget**: the cap on prefetch activity. Stage 1 uses a shared
  budget to keep coordination honest.
- **Usefulness / accuracy floor**: a minimum quality bar for issued prefetches.
  Stage 1 uses this to avoid trading IPC for wasteful traffic.
- **Smoke mode / search mode / final mode**: the three named run modes defined
  in `configs/run_modes.json`. They differ in trace set, instruction window,
  and router coverage.

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

- `results/mop_lite/logs/`: Athena stdout/stderr per run.
- `results/mop_lite/metrics/`: parsed metric dictionaries per run.
- `results/mop_lite/epoch_logs/`: per-epoch CSV traces for router runs when
  `--epoch-trace` is enabled.
- `results/mop_lite/manifest.jsonl`: one JSON record per completed run from the
  runner that produced the current raw artifact set.
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
   `results/mop_lite/`.
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
- Both traces are in the **train** side of the official split.
- The coordinator comparison in `report/tables/router_ablation.md` shows:
  - `AthenaMAB`: geomean `speedup_vs_best_single = 0.9639`
  - `MoPLite`: geomean `speedup_vs_best_single = 0.9635`
- The expert-pair table in `report/tables/expert_pair_ablation.md` covers one
  pair so far: `Pythia + SPP+PPF`.

The current smoke snapshot says three useful things.

1. The end-to-end pipeline works: raw runs, dataset build, and report tables all
   exist.
2. The smoke traces favor the best single expert over both coordinators.
3. The current evidence is still an early checkpoint. The official full-suite
   evaluation design lives in `docs/experiment_setup.md` and remains the
   standard for stronger claims.

## Advisor questions

### What is this?

This repository is a Stage 1 systems-research baseline for L2 prefetcher
coordination. It asks whether a small epoch-based controller can coordinate two
existing L2 prefetchers well enough to outperform the strongest single expert
under a traffic budget and a usefulness floor. The charter for that question is
`docs/mop_stage1_instruction.md`.

### Why do this?

Different prefetchers help different workloads. A single global choice leaves
performance on the table when the stronger expert changes across traces or
phases. A lightweight coordinator gives the project a clean way to study
complementarity, traffic control, and later Stage 2 optimization inside one
fixed experimental protocol.

### Why exactly two experts and epoch-level routing?

The Stage 1 charter chooses a small control surface on purpose. Two experts keep
the comparison readable, keep the hardware story compact, and make later search
practical. Epoch-level routing keeps the online decision interface simple and
close to what the simulator can measure reliably at run time. The exact scope
lock is in `docs/mop_stage1_instruction.md` and the frozen Stage 2 boundary is
in `docs/stage2_memo.md`.

### Why these experts?

The default pair is `Pythia + SPP+PPF`, recorded in
`configs/trace_suites.json` as `recommended_expert_pair`. Stage 1 uses that pair
because the project needs one clear baseline pair before broader pair ablations.
The current smoke snapshot also shows that `SPP+PPF` is the stronger single
expert on both smoke traces, which makes it a useful anchor for comparison.

### Why is performance good or bad? What kind of workloads help or hurt?

The current smoke batch gives an early answer.

- `SPP+PPF` is the strongest single expert on both smoke traces.
- `MoPLite` and `AthenaMAB` both trail that best-single reference on the smoke
  pair, as shown in `report/tables/router_ablation.md`.
- The current coordinator behavior looks conservative in the smoke snapshot: the
  MoPLite rows in `data/processed/runs.csv` show limited selected epochs and low
  effective traffic relative to the stronger single expert.

That pattern says the current Stage 1 settings are more successful at keeping
control explicit than at extracting extra performance on these two traces. The
broader train and held-out suite in `docs/experiment_setup.md` is where the
method earns a stronger complementarity claim.

### What does the current result justify?

The current results justify three claims.

1. The end-to-end pipeline works.
2. The Stage 1 baseline methods are implemented and comparable under one
   protocol.
3. The current smoke traces favor the strongest single expert over the current
   coordinators.

The current smoke results justify an infrastructure-readiness claim and a
smoke-subset performance caveat. The full 24-trace protocol is the path to
stronger scientific claims.

### Is the method justified by the results?

The method is justified as a Stage 1 baseline method because it produces a
controlled comparison, exposes per-epoch telemetry, and creates the search-ready
interface Stage 2 needs. The current smoke results justify continuing the method
into broader evaluation. Broader evaluation will justify the project's stronger
performance claims.

### What counts as success at this stage?

Stage 1 success has two levels.

1. Baseline success: the simulator builds, the methods run under one fair
   protocol, the dataset is complete, and the report pipeline works.
2. Stronger scientific success: the coordinator shows evidence-backed wins over
   the best single expert on the official broader evaluation.

The success ladder is written out in `docs/mop_stage1_instruction.md`.

### What evidence would change the current view?

Three kinds of evidence matter most.

1. `search_mode` results on the broader train subset.
2. `final_mode` results on the full official suite.
3. Per-trace cases where the two experts win in different regions and the
   coordinator captures that complementarity under the traffic budget.

Those are the results that can move the project from "working baseline with an
honest smoke result" to a stronger coordination claim.

### What is missing from today's evidence?

Four pieces are still important for a stronger advisor-facing conclusion.

1. `search_mode` coverage across the broader training subset.
2. `final_mode` coverage across the full official suite.
3. Held-out evidence under the frozen split in `data/splits/official_v1.json`.
4. Multi-seed checking for the stochastic router path discussed in
   `docs/transparency_log.md`.

Those pieces turn the current snapshot into a stronger scientific result.

### Where should an advisor look to verify a claim?

Use the shortest path that matches the question.

- Project goal and scope: `docs/mop_stage1_instruction.md`
- Official protocol: `docs/experiment_setup.md`
- Current analysis rows: `data/processed/runs.csv`
- Current summary tables: `report/tables/router_ablation.md`
- Per-run raw evidence: `results/mop_lite/logs/` and `results/mop_lite/metrics/`
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
