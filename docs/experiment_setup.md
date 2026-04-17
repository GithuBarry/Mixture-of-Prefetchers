# Experiment setup (MoP-lite milestone)

This document is the **canonical description** of the official trace suite,
splits, run modes, and example commands. Machine-readable copies live under
`configs/`.

The current workspace already contains a smoke-mode evidence snapshot. The
official broader protocol in this file still defines the target evaluation for
advisor-facing conclusions.

## Why these modes exist

- `smoke_mode` answers a build-and-pipeline question: can the full stack run
  end to end on two short traces?
- `search_mode` answers an iteration question: can we compare router choices on
  a broader training subset at lower cost?
- `final_mode` answers the strongest evaluation question: how does the method
  behave on the full official suite under report-style instruction windows?

## Provenance of this protocol

The candidate trace pool and trace metadata come from Athena, mainly through
`external/athena/scripts/config.py` and the associated Zenodo trace bundle.

The official 24-trace suite, the train/held-out split, the search subset, and
the three named run modes are project decisions in this repository. They are the
evaluation protocol for this study, not inherited Athena defaults.

## Basic evaluation terms

- **Trace**: one recorded workload execution stream replayed by Athena.
- **Warmup**: the initial part of a run that fills caches and predictor state.
- **Simulation window**: the measured part of a run after warmup.
- **Epoch**: a fixed chunk inside the measured window. For the Stage 1 MoP-lite
  path, one epoch is 500,000 retired instructions.
- **Train / held-out split**: the fixed boundary between traces that may guide
  development and traces reserved for stronger confirmation.

## Why these settings exist

The protocol is designed around three goals: fairness, manageable runtime, and
clear interpretation.

- The **24-trace suite** is large enough to cover multiple benchmark families
  and small enough to remain runnable for a course-scale Stage 1 study.
- The **17 / 7 train / held-out split** keeps a real untouched evaluation side
  while preserving enough training-side coverage for iteration.
- The **10-trace search subset** makes router debugging and train-side sweeps
  affordable.
- The **2-trace smoke subset** gives a cheap end-to-end systems check before the
  larger batches run.
- The three **run modes** separate system validation, iteration, and final
  evidence so each activity uses an appropriate runtime budget.
- The **5M / 10M** search-side windows keep early iteration affordable while
  preserving a real measured phase.
- The **20M / 50M** final-mode windows give a stronger report-style evaluation
  tier and align with the standalone baseline runner defaults in this repo.
- The **500,000-instruction epoch** gives the coordinator a stable, portable
  decision cadence inside those windows.
- The default expert pair **`Pythia + SPP+PPF`** gives Stage 1 one stable,
  interpretable two-expert baseline before pair search is allowed.

## Official trace suite

- **24 traces** total (`configs/trace_suites.json` → `trace_sets.full_suite`).
- **Rationale**: Stay inside the 20–30 target; balance **SPEC**, **PARSEC**, **LIGRA**, and **CVP**; favor one representative per benchmark *family* in this suite (each PARSEC/LIGRA algorithm appears at most once; SPEC benchmarks are diverse: memory-heavy, server, FP, compiler, etc.); include a mix of `adverse: true` and `false` workloads from `TRACE_DATA` where practical; all traces are in the **same** Zenodo bundle the runners already use (see `README.md`).

## Train / held-out split

- **17 train** / **7 held-out** (~71% / 29%), stored as `trace_sets.train` and `trace_sets.heldout`.
- **Benchmark-level rule**: For any benchmark family that appears **more than once** in the official 24-trace suite, we kept all those traces in **one** side of the split. In this suite each PARSEC/LIGRA/CVP family appears only once, so the split is by **whole benchmark** (one trace per family in the suite), not by random shards of the same executable.

## Search subset

- **10 traces**, all from **training** only (`trace_sets.search_subset` ⊆ `trace_sets.train`).
- Used for fast router debugging and sanity runs with shorter instruction windows (see `run_modes.search_mode`).

## Small smoke test

- **2 traces** (`trace_sets.small_smoke_test_subset`): `fluidanimate` + `429.mcf-192B` — both in **train**, quick to download and run.

## Run modes (`configs/run_modes.json`)

| Mode | Warmup | Simulation | Trace set | Notes |
| --- | --- | --- | --- | --- |
| **search_mode** | 5M | 10M | `search_subset` | Matches current `run_mop_lite.py` defaults; uses a reduced router list in config for faster iteration |
| **final_mode** | 20M | 50M | `full_suite` | Matches current `run_single_prefetcher_baselines.py` defaults (report-style windows) |
| **smoke_mode** | 5M | 10M | `small_smoke_test_subset` | Minimal MoP-lite (`MoPLite` only) and tiny baseline set |

**Experts (MoP-lite)** default to **Pythia** + **SPP+PPF** (`recommended_expert_pair` in `trace_suites.json`).

### Instruction counts and Athena `knobs`

Athena’s `TRACE_DATA` may attach per-trace `knobs` (e.g. 100M/150M) for PARSEC/LIGRA/CVP. The **project** runners replace the `BASE` warmup and simulation counts with `--warmup-instructions` and `--simulation-instructions`. Use the run-mode table above for reproducibility.

## Example commands

Generate commands (includes all `--trace` repetitions):

```bash
python3 scripts/print_run_commands.py search_mode
python3 scripts/print_run_commands.py final_mode
python3 scripts/print_run_commands.py smoke_mode
```

List traces for a mode’s trace set:

```bash
python3 scripts/print_run_commands.py search_mode --list-traces
```

**Held-out evaluation only** (manual): copy `--trace` lines from `configs/trace_suites.json` → `trace_sets.heldout` or use:

```bash
python3 -c "import json; from pathlib import Path; d=json.loads(Path('configs/trace_suites.json').read_text()); print(' '.join(f\"--trace {repr(t)}\" for t in d['trace_sets']['heldout']))"
```

Pre-download the **full suite** (bash):

```bash
args=()
while IFS= read -r line; do args+=(--trace "$line"); done < <(python3 scripts/print_run_commands.py final_mode --list-traces)
python3 scripts/run_single_prefetcher_baselines.py --download-only "${args[@]}"
```

## Files

| File | Role |
| --- | --- |
| `configs/trace_suites.json` | `full_suite`, `train`, `heldout`, `search_subset`, smoke subset, router recommendations |
| `configs/trace_suites.yaml` | Same content as `trace_suites.json` (JSON is valid YAML 1.2) |
| `configs/run_modes.json` | `search_mode`, `final_mode`, `smoke_mode` |
| `configs/run_modes.yaml` | Same content as `run_modes.json` |
| `docs/trace_inventory.md` | How the candidate pool was derived |
| `scripts/print_run_commands.py` | Emit concrete CLI invocations |
