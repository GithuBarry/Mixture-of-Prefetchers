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
4. `docs/operational/README.md` - the index of the remaining operational docs.

## Current project state

The repository contains the complete Stage 1 baseline and finished Stage 2
policy optimization.

**Stage 1** — complete.
- 230 runs across the full 24-trace suite (17 train + 7 held-out).
- `MoPLite` does not beat pair-best single expert in geomean on either split
  (held-out: 0.919×). Failure modes identified: both-off overuse and weak
  winner isolation.
- Artifacts: `data/processed/runs.csv`, `report/tables/router_ablation.md`,
  `report/figures/`.

**Stage 2** — complete.
- `OpenEvolve` (router type 5, `external/athena/src/oogway.cc`) implements
  E1 Anti-Off Gate, E2 Winner Isolation, E3 Squared-Score Budget Split.
- Search subset (10 tr, 5M/10M): MoPLite 0.968× → OpenEvolve **0.978×** (+0.98 pp).
- Held-out (7 tr, 20M/50M): MoPLite 0.919× → OpenEvolve **0.924×** (+0.46 pp),
  crossing 1.0× on 3 of 7 traces.
- 40-iteration automated OpenEvolve search run (CMU AI Gateway); best evolved
  candidate overfit to scout set (0.972× vs manual seed 0.978×).
- Freeze memo: `docs/decisions/stage2_seed_freeze.md`.
- Full results and mechanism analysis: `report/draft.md` §7–§9.
- OpenEvolve artifacts: `openevolve/` (seed, evaluator, config, best evolved program,
  candidate ledger).

## Which file answers which question?

- "What is MoP-lite and what is in scope?"
  - `docs/outsider_guide.md`
  - `docs/operational/mop_stage1_instruction_v2.md`
  - `docs/operational/mop_stage2_instruction_v2.md`
  - `docs/decisions/stage2_seed_freeze.md`
- "What is OpenEvolve and how does it differ from MoPLite?"
  - `report/draft.md` §7
  - `external/athena/src/oogway.cc` (case 5)
  - `openevolve/initial_program.py` (policy as Python)
- "What did the automated OpenEvolve search find?"
  - `openevolve/candidate_ledger.jsonl`
  - `openevolve/best_evolved_program.py`
  - `report/draft.md` §9
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
  - `scripts/make_figures.py`
- "What has actually been run so far, and what happened?"
  - `docs/operational/research_log.md`
  - `data/processed/runs.csv`
  - `report/tables/router_ablation.md`
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
3. `scripts/make_figures.py` regenerates `report/figures/` and `report/tables/`
   only from `data/processed/runs.csv`.

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
