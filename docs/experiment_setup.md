# Experiment setup (MoP-lite milestone)

This document is the **canonical description** of the official trace suite, splits, run modes, and example commands. Machine-readable copies live under `configs/`.

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
