# Documentation Map

This directory is the human-facing map for the repository.

The top level stays small on purpose:

- `docs/outsider_guide.md` is the main advisor-facing guide
- `docs/operational/` contains implementation-heavy and workflow-heavy docs

The goal is that a reader who knows prefetching but not this codebase can
answer three questions quickly:

1. What problem is this repository solving?
2. What exactly was implemented and run?
3. Which file is the source of truth for each claim?

It also keeps authorship clear: which pieces come from upstream Athena and which
pieces are project work in this repository.

## Start here

If you want the shortest path, read these in order:

1. `docs/outsider_guide.md` - project purpose, architecture, pipeline, and the
   current evidence snapshot.
2. `docs/operational/experiment_setup.md` - the official trace suite, split,
   run modes, and exact command-generation path.
3. `docs/operational/environment.md` - the reproducibility contract: toolchain,
   trace handling, producers for each artifact, and regeneration order.
4. `docs/operational/current_status.md` - current status, finished work,
   remaining work, and tracked final-cleanup requests.
5. `docs/operational/README.md` - the index of the remaining operational docs.

## Current project state

The repository now has the finished OpenEvolve report package.

- The project question is documented in `docs/outsider_guide.md`.
- The charter-level source of truth for Stage 1 is
  `docs/operational/mop_stage1_instruction.md`.
- The official full evaluation design is frozen in
  `configs/trace_suites.json`, `configs/run_modes.json`, and
  `docs/operational/experiment_setup.md`.
- The clean final writeup is `deliverables/MoP-Final/MoP-Final-report.md`.
- The current tables and figures come from `scripts/make_stage2_final_assets.py`.
- Historical baseline tables are kept under `report/tables/legacy_stage1/`.

## Which file answers which question?

- "What is MoP-lite and what is in scope?"
  - `docs/outsider_guide.md`
  - `docs/operational/mop_stage1_instruction_v2.md`
  - `docs/decisions/stage2_openevolve_start.md`
  - `docs/decisions/stage2_policy_sweep.md`
- "Which traces and instruction windows count as official?"
  - `docs/operational/experiment_setup.md`
  - `configs/trace_suites.json`
  - `configs/run_modes.json`
- "What does one row in the dataset mean?"
  - `docs/operational/dataset_schema.md`
  - `scripts/build_dataset.py`
- "How do runs flow from Athena to tables and figures?"
  - `docs/operational/environment.md`
  - `scripts/run_mop_lite.py`
  - `scripts/build_dataset.py`
  - `scripts/make_stage2_final_assets.py`
- "What has actually been run so far, and what happened?"
  - `docs/operational/current_status.md`
  - `docs/operational/research_log.md`
  - `data/processed/runs.csv`
  - `report/tables/stage2_final_metrics.md`
- "Why were specific design choices made?"
  - `docs/operational/transparency_log.md`
- "What came from upstream Athena and what did this project add?"
  - `docs/outsider_guide.md`
  - `external/athena/UPSTREAM.md`
- "Where did the trace pool come from before the 24-trace suite was frozen?"
  - `docs/operational/trace_inventory.md`

## Artifact flow

The project has a simple evidence chain:

1. `scripts/run_mop_lite.py` runs Athena and writes raw artifacts under
   `results/mop_lite/`.
2. `scripts/build_dataset.py` converts those raw artifacts into the analysis
   table `data/processed/runs.csv`.
3. `scripts/make_stage2_final_assets.py` regenerates the final report tables
   and figures from the selected simulator summaries and OpenEvolve records.

That separation matters: `results/` is the raw evidence, `data/processed/` is
the analysis entry point, and `report/` is a view over the dataset. After any
new simulator run, regenerate the derived artifacts so the pointers stay
aligned.

## Priority order

Some documents carry more weight than others.

1. `docs/outsider_guide.md` gives the advisor-facing explanation.
2. `docs/operational/experiment_setup.md` defines the official traces, split,
   and run modes.
3. `docs/operational/environment.md` defines how to reproduce and regenerate artifacts.
4. `docs/operational/dataset_schema.md` defines how to read `data/processed/runs.csv`.
5. `docs/operational/research_log.md` records what has happened so far.
6. `docs/operational/transparency_log.md` records why key decisions were made.

Read the charter first for scope, then the guide for orientation, then the
setup and environment docs for exact mechanics.

## Update Instruction For Agents

When updating advisor-facing docs in this repository:

- define every project-specific term when it first appears
- explain settings and design choices, not just list them
- explain how the router actually works, including signals, actions, and budget
  behavior
- distinguish clearly between upstream Athena work and local project work
- avoid FAQ-style writing when the same answers can appear naturally in the main
  sections
- avoid repeated sections and repeated emphasis when one precise explanation is
  enough
- quantify scale whenever possible, such as traces, runs, windows, and epoch
  counts
- do not present hypotheses as validated results; say explicitly when the repo
  does not yet contain evidence for a claim
- merge related explanations so readers do not have to guess where the local C++
  changes or baselines are described
