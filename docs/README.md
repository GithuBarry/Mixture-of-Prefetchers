# Documentation Map

This directory is the advisor-facing map for the repository. The goal is that a
reader who knows prefetching but not this codebase can answer three questions
quickly:

1. What problem is this repository solving?
2. What exactly was implemented and run?
3. Which file is the source of truth for each claim?

It also keeps authorship clear: which pieces come from upstream Athena and which
pieces are project work in this repository.

## Start here

If you want the shortest path, read these four documents in order:

1. `docs/outsider_guide.md` - project purpose, architecture, pipeline, and the
   current evidence snapshot.
2. `docs/mop_stage1_instruction.md` - the original Stage 1 charter: mission,
   scope lock, required deliverables, and integrity rules.
3. `docs/experiment_setup.md` - the official trace suite, split, run modes, and
   exact command-generation path.
4. `docs/environment.md` - the reproducibility contract: toolchain, trace
   handling, producers for each artifact, and regeneration order.

## Current project state

The repository currently sits at the smoke-test milestone. Broader search-mode
and final-mode evaluation comes next.

- The project question is documented in `docs/outsider_guide.md`.
- The charter-level source of truth for Stage 1 is
  `docs/mop_stage1_instruction.md`.
- The official full evaluation design is frozen in
  `configs/trace_suites.json`, `configs/run_modes.json`, and
  `docs/experiment_setup.md`.
- The currently materialized analysis artifacts summarize a smoke-mode batch:
  `data/processed/runs_summary.md` reports 10 runs over 2 traces, and
  `report/tables/router_ablation.md` reports coordinator geomeans for that
  smoke batch.
- Stage 2 search has a frozen boundary in `docs/stage2_memo.md`.

## Which file answers which question?

- "What is MoP-lite and what is in scope?"
  - `docs/outsider_guide.md`
  - `docs/mop_stage1_instruction.md`
  - `docs/stage2_memo.md`
- "Which traces and instruction windows count as official?"
  - `docs/experiment_setup.md`
  - `configs/trace_suites.json`
  - `configs/run_modes.json`
- "What does one row in the dataset mean?"
  - `docs/dataset_schema.md`
  - `scripts/build_dataset.py`
- "How do runs flow from Athena to tables and figures?"
  - `docs/environment.md`
  - `scripts/run_mop_lite.py`
  - `scripts/build_dataset.py`
  - `scripts/make_figures.py`
- "What has actually been run so far, and what happened?"
  - `docs/research_log.md`
  - `data/processed/runs.csv`
  - `report/tables/router_ablation.md`
- "Why were specific design choices made?"
  - `docs/transparency_log.md`
- "What came from upstream Athena and what did this project add?"
  - `docs/outsider_guide.md`
  - `external/athena/UPSTREAM.md`
- "Where did the trace pool come from before the 24-trace suite was frozen?"
  - `docs/trace_inventory.md`

## Artifact flow

The project has a simple evidence chain:

1. `scripts/run_mop_lite.py` runs Athena and writes raw artifacts under
   `results/mop_lite/`.
2. `scripts/build_dataset.py` converts those raw artifacts into the analysis
   table `data/processed/runs.csv`.
3. `scripts/make_figures.py` regenerates `report/figures/` and `report/tables/`
   only from `data/processed/runs.csv`.

That separation matters: `results/` is the raw evidence, `data/processed/` is
the analysis entry point, and `report/` is a view over the dataset. After any
new simulator run, regenerate the derived artifacts so the pointers stay
aligned.

## Priority order

Some documents carry more weight than others.

1. `docs/mop_stage1_instruction.md` defines the project contract for Stage 1.
2. `docs/experiment_setup.md` defines the official traces, split, and run
   modes.
3. `docs/environment.md` defines how to reproduce and regenerate artifacts.
4. `docs/dataset_schema.md` defines how to read `data/processed/runs.csv`.
5. `docs/research_log.md` records what has happened so far.
6. `docs/transparency_log.md` records why key decisions were made.

Read the charter first for scope, then the guide for orientation, then the
setup and environment docs for exact mechanics.
