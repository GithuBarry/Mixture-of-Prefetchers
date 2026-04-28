# Dataset schema: `data/processed/runs.csv`

Tidy long-form table. **One row = one simulator run** (one trace × one
experiment). Produced by `scripts/build_dataset.py` from
one or more manifest files joined with the referenced metrics JSON files and
annotated with `data/splits/official_v1.json`.

`runs.csv` is a derived artifact. The canonical schema lives in this document
and in `scripts/build_dataset.py`. After any new raw run batch, regenerate the
CSV before using it for analysis or report updates.

## Identity

| Column                | Type    | Description                                                                 |
| --------------------- | ------- | --------------------------------------------------------------------------- |
| `run_group_id`        | string  | Per-invocation identifier used to isolate reruns inside append-only manifests. |
| `trace`               | string  | Athena trace name (see `external/athena/scripts/config.py`).                |
| `benchmark_family`    | string  | `SPEC`, `PARSEC`, `LIGRA`, or `CVP`, inferred from the trace name.          |
| `split_side`          | string  | `train` / `heldout` / `search_subset` / `other`.                            |
| `experiment`          | string  | `Baseline`, single-expert name, LLC-prefetcher name, router name, or builtin coordinator name. |
| `experiment_kind`     | string  | `baseline` / `single` / `llc` / `router` / `builtin`.                       |
| `router`              | string  | Router name if `experiment_kind == "router"`, else empty.                   |
| `llc_prefetcher`      | string  | LLC-prefetcher name if `experiment_kind == "llc"`, else empty.              |
| `builtin_coordinator` | string  | Name if `experiment_kind == "builtin"`, else empty.                         |
| `expert_0`            | string  | Expert 0 name for router/builtin runs.                                      |
| `expert_1`            | string  | Expert 1 name for router/builtin runs.                                      |
| `seed`                | int     | MoP-lite seed (routers only; empty otherwise).                              |

## Primary metrics

| Column                         | Type  | Description                                                        |
| ------------------------------ | ----- | ------------------------------------------------------------------ |
| `ipc`                          | float | `Core_0_cumulative_IPC`                                            |
| `speedup_vs_baseline`          | float | `ipc / Baseline.ipc` for the same trace                            |
| `speedup_vs_best_single`       | float | `ipc / max(ipc of expert-0 or expert-1 runs on same trace)`        |
| `baseline_ipc`                 | float | Convenience column (same for every row of the same trace)          |
| `best_single_ipc`              | float | Convenience column                                                 |
| `traffic_overhead_vs_baseline` | float | `(downstream_prefetch_issued - Baseline.downstream_prefetch_issued) / Baseline.downstream_prefetch_issued`; when baseline has zero traffic, this degenerates to a 0/1 indicator for whether traffic was introduced at all. |

## Cache / prefetch traffic

| Column                          | Description                                                   |
| ------------------------------- | ------------------------------------------------------------- |
| `l2c_load_miss`                 | `Core_0_L2C_load_miss`                                        |
| `l2c_mpki`                      | 1000 × `l2c_load_miss / total_instructions`                   |
| `l2c_prefetch_issued_raw`       | Raw `Core_0_L2C_prefetch_issued` from the simulator           |
| `l2c_prefetch_issued`           | Issued-traffic proxy used for analysis. For single-expert runs this matches `l2c_prefetch_issued_raw`. For coordinator runs it falls back to `pref0_issued_total + pref1_issued_total` when the raw cache-issued counter is zero but the coordinator's per-expert issue counters are nonzero. |
| `l2c_prefetch_useful`           | `Core_0_L2C_prefetch_useful`                                  |
| `l2c_prefetch_useless`          | `Core_0_L2C_prefetch_useless`                                 |
| `l2c_prefetch_late`             | `Core_0_L2C_prefetch_late`                                    |
| `l2c_total_miss`                | `Core_0_L2C_total_miss`                                       |
| `l1d_load_miss`                 | `Core_0_L1D_load_miss`                                        |
| `llc_prefetch_issued`           | `Core_0_LLC_prefetch_issued`                                  |
| `llc_prefetch_useful`           | `Core_0_LLC_prefetch_useful`                                  |
| `downstream_prefetch_issued`    | Effective L2C issued traffic plus LLC-issued traffic.          |
| `downstream_prefetch_useful`    | `l2c_prefetch_useful + llc_prefetch_useful`                    |
| `downstream_prefetch_accuracy`  | `downstream_prefetch_useful / downstream_prefetch_issued`      |
| `l2c_rq_full`                   | `Core_0_L2C_rq_full` queue-pressure proxy                     |
| `l2c_wq_full`                   | `Core_0_L2C_wq_full` queue-pressure proxy                     |
| `l2c_pq_full`                   | `Core_0_L2C_pq_full` prefetch-queue pressure proxy            |
| `dram_rq_row_buffer_miss`       | `Channel_0_RQ_row_buffer_miss` downstream-traffic proxy       |
| `dram_bus_congested`            | `Channel_0_dbus_congested` downstream congestion proxy        |
| `dram_mshr_full`                | `Core_0_DDRP_dram_MSHR_full` MSHR-pressure proxy              |
| `branch_pred_mpki`              | `Core_0_branch_pred_mpki`                                     |
| `cycles`                        | `Core_0_cycles`                                               |
| `total_instructions`            | `Core_0_total_instructions`                                   |

## MoP-lite per-expert telemetry

Populated for router and builtin coordinator runs; zero/NaN for single-expert
and baseline runs.

| Column                         | Description                                                          |
| ------------------------------ | -------------------------------------------------------------------- |
| `pref{0,1}_issued_total`       | `Core_0_mop_pref_{0,1}_issued_total`; epoch-sampled per-expert activity counter from the prefetcher modules. Useful for debugging / internal signal interpretation. |
| `pref{0,1}_useful_total`       | `Core_0_mop_pref_{0,1}_useful_total`                                 |
| `pref{0,1}_budget_total`       | `Core_0_mop_pref_{0,1}_budget_total`                                 |
| `pref{0,1}_selected_epochs`    | `Core_0_mop_pref_{0,1}_selected_epochs`                              |
| `pref{0,1}_accuracy`           | `useful_total / issued_total` |

## Configuration snapshot

These columns are **stamped once per run** so experiments remain identifiable
after the configs evolve:

`warmup_instructions`, `simulation_instructions`, `epoch_len_instructions`,
`mop_total_budget`, `mop_accuracy_floor`, `mop_fixed_split_ratio`,
`mop_guarded_min_budget_share`, `mop_score_weights`, `mode`, `host`,
`git_revision`, `duration_s`, `start_utc`, `end_utc`, `trace_path`, `log_path`,
`stderr_path`, `metrics_path`, `epoch_trace_prefix`, `flags`.

## Invariants

- Every run is reproducible from `flags` alone (given the same binary at `git_revision`).
- `run_group_id` partitions reruns of the same trace/experiment matrix so derived
  speedups are computed within a single invocation, not across mixed batches.
- incomplete `run_group_id` batches are rejected by `build_dataset.py`; partial
  reruns do not silently contribute rows to the merged analysis dataset.
- `speedup_vs_best_single` uses the better of the two coordinated experts
  (`expert_0`, `expert_1`) for that run group and trace, not the best of every
  single-prefetcher baseline that happened to be included in the batch.
- `experiment == "Baseline"` rows have `experiment_kind == "baseline"`; `single`,
  `router`, and `builtin` rows have non-empty `l2c_prefetcher_types` in `flags`,
  while `llc` rows have non-empty `llc_prefetcher_types`.
- For every `(run_group_id, trace)` there must be a complete experiment matrix
  before the CSV is considered valid (`build_dataset.py` fails otherwise).
- `heldout` rows are never generated during search / development runs.
