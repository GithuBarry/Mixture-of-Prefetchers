# Stage 2 memo: what OpenEvolve / search should optimize

This memo freezes the contract between Stage 1 and Stage 2. Stage 2 is allowed
to search over the **control surface** below; it **must not** touch anything
in the frozen list. Violations invalidate the evaluation protocol and any
held-out number that results.

## Frozen (do not change in Stage 2)

| Item | Source of truth | Reason |
| --- | --- | --- |
| Expert pair (Pythia + SPP+PPF) | `configs/trace_suites.json:recommended_expert_pair` | Stage 1 is explicitly a two-expert coordinator study. |
| Expert implementations | `external/athena/config/pythia.ini`, `.../spp_ppf_dev.ini` | Changing the experts changes the identification problem. |
| Simulator revision | `git_revision` stamp per run | Mixing revisions invalidates cross-run comparisons. |
| Split (`data/splits/official_v1.json`) + its sha256 | `data/splits/official_v1.sha256` | Held-out protection requires an immovable boundary. |
| Metric definitions | `docs/operational/dataset_schema.md` | Redefining IPC / MPKI / accuracy changes the ground truth. |
| Warmup / simulation windows per mode | `configs/run_modes.json` | Changing the window changes the benchmark. |
| OCP disabled | Enforced in `initialize_mop_epoch` (oogway.cc) | Scope lock per charter. |
| Epoch granularity = retired instructions | `og_epoch_by_inst=true` in `mop_lite.ini` | Enables portable, wall-clock-independent decisions. |

## Search surface (Stage 2 may vary)

| Knob | Current value | Reasonable search range | Notes |
| --- | --- | --- | --- |
| `mop_router_type` | `MoPLite` (4) | {FixedSplit, WinnerTakeAll, OneShotFit, MoPLite} | Search over router *rule*, not the existence of the router. `RandomRouter` is kept in Stage 1 only as a sanity-check baseline. |
| `mop_total_budget` | 2048 | 1024 – 4096 (≤ 20% of baseline L2 traffic, respecting charter) | Feasibility upper-bounded by the traffic-budget constraint. |
| `mop_fixed_split_ratio` | 50 | 20 – 80 | Only meaningful under FixedSplit; do not tune in other routers. |
| `mop_accuracy_floor` | 30 | 20 – 60 | Usefulness floor per expert; too high → both-off dominates, too low → floor is toothless. |
| `mop_score_weights` | `1.0,0.25,1.0` | Each in [0,2] | Relative weights of (accuracy, coverage, traffic-penalty). Stage 2 may learn these, not redefine them. |
| `mop_one_shot_epochs` | 4 | 2 – 16 | Only meaningful under OneShotFit. |
| `og_instr_epoch_len` | 500 000 | 100 000 – 2 000 000 | Coarser epochs → stabler decisions, slower adaptation. |
| `mop_seed` | 1 | {1, 2, 3} minimum for RandomRouter; irrelevant otherwise | Seed is stamped regardless, so Stage 2 runs can be deduped. |

## Deliverable from Stage 2

A single configuration (or a small set), produced without touching the
held-out traces, that:

1. Improves geomean `speedup_vs_best_single` on the **train** split
   over the Stage 1 MoPLite baseline.
2. Respects the 20% L2 traffic cap relative to Baseline
   (`l2c_prefetch_issued` per run, using the current coordinator fallback proxy
   when the raw cache-issued counter stays at zero).
3. Respects the 30% accuracy floor (`downstream_prefetch_accuracy`) on the
   train split, using the same traffic denominator as item 2.
4. Survives the held-out evaluation **only once**, as the final confirmation
   run. That single held-out evaluation is the only permissible use of the
   held-out traces in Stage 2.

## Out of scope for Stage 2

- Adding a third expert, swapping the expert pair, or redefining the router
  action space.
- Changing metric definitions, warmup/sim windows, or split.
- Introducing per-access ML inference (Stage 3 territory, if ever).
- Editing `data/splits/official_v1.json`, `oogway.cc` metric emission, or
  the manifest schema.
