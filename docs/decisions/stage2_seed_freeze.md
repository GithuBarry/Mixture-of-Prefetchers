# Stage 2 seed freeze memo

**Date:** 2026-04-28
**Status:** frozen

---

## What is frozen

### Scientific boundary

| Item | Frozen value |
| --- | --- |
| Cache level | L2C only (`og_l2c_only_coordination=true`, OCP disabled) |
| Expert pool | Athena built-ins: `Pythia`, `SPP+PPF`, `MLOP`, `SMS` |
| Mainline expert pair | `Pythia + SPP+PPF` |
| Coordination family | `OpenEvolve` (router type 5, `oogway.cc`) — the Stage 2 seed |
| Stage 1 baseline family | `MoPLite` (router type 4) — kept as labeled comparison |
| Simulator revision | pinned in each manifest row as `git_revision` |
| Split protocol | `data/splits/official_v1.json` (sha256: `data/splits/official_v1.sha256`) — 17 train / 7 held-out, benchmark-family-aware |
| Train-side windows | 5M warmup + 10M simulation (search mode) |
| Held-out windows | 20M warmup + 50M simulation (final mode) |
| Metric definitions | `docs/operational/dataset_schema.md` — primary metric is `speedup_vs_best_single` (IPC / max(IPC of Pythia, IPC of SPP+PPF) per trace per run group) |
| Traffic cap | 2048 prefetches per epoch (`mop_total_budget=2048`) |
| Usefulness floor | 30% accuracy (`mop_accuracy_floor=30`) |
| Baseline comparison set | `Baseline` (no-prefetch), `Pythia`, `SPP+PPF`, `MLOP`, `SMS`, `MoPLite`, `WinnerTakeAll`, `AthenaMAB` |

### Reporting boundary

| Item | Frozen value |
| --- | --- |
| Primary comparator | pair-best single expert (`max(Pythia, SPP+PPF)` per trace) |
| Secondary comparators | no-prefetch, Stage 1 MoPLite, AthenaMAB |
| Traffic cap definition | `mop_total_budget=2048` per epoch; enforced via `allow_prefetch()` in `oogway.cc` |
| Usefulness floor | 30% prefetch accuracy; scores below floor set to zero in `mop_score()` |
| Final clean evaluation rules | held-out 7 traces run once under 20M/50M windows after all design decisions finalized on train side |
| Contaminated vs clean evidence | any result touching the held-out split during design = development evidence only |

---

## What remains evolvable

The following are intentionally left open for the automated OpenEvolve search:

- `mop_winner_isolation_threshold` — the score-ratio above which E2 routes exclusively (current default: 3.0)
- `mop_accuracy_floor` — the accuracy % below which a score is zeroed (current: 30)
- `mop_score_weights` — the [accuracy, coverage, traffic] weight triple (current: [1.0, 0.25, 1.0])
- `og_instr_epoch_len` — epoch length in instructions (current: 500000)
- `mop_total_budget` — total prefetch budget per epoch (current: 2048)
- `mop_fixed_split_ratio` — fixed split ratio used by FixedSplit baseline (not OpenEvolve)
- The routing logic itself inside `mop_decision()` case 5 and `configure_mop_epoch()` case 5 — the editable surface for OpenEvolve

Everything outside this list (parser code, metric definitions, split files, dataset schema, figure generation, baseline metric extraction) is **not evolvable**.

---

## Evidence that justified the freeze

### Why `Pythia + SPP+PPF` as the mainline pair

Stage 1 committed to this pair before any held-out runs. Exploratory alternate-pair evidence (`MLOP + SMS`, `MLOP + Pythia`) showed pair choice matters but did not turn MoPLite into a winner vs its own pair-best single. Switching pairs at Stage 2 would restart the scientific question. The committed pair remains the cleanest story.

### Why `OpenEvolve` (type 5) as the seed, not `MoPLite` (type 4)

Stage 1 epoch-trace diagnostics identified two concrete failure modes:
1. `both off` overuse — 90–97% of epochs on `429.mcf` and `fluidanimate`
2. No winner isolation — proportional split even when one expert dominates by 3–10×

`OpenEvolve` addresses both (E1 anti-off gate, E2 winner isolation, E3 squared-score split). On the 10-trace search subset it improves geomean from 0.968x (MoPLite) to 0.978x (+0.98 pp) and on the 7-trace held-out split from 0.919x to 0.924x (+0.46 pp). It is closer to the strong-success gate (≥0.99x) than MoPLite, and its policy surface is small and isolated in `oogway.cc` case 5.

### Why L2C only

Stage 1 scope was explicitly locked to L2C. OCP was disabled in `initialize_mop_epoch()` and in the base config. Changing the cache level now would invalidate the Stage 1 comparison baseline.

### Why the current split remains valid

The held-out 7 traces were run only once — for the Stage 2 final evaluation — after all design decisions (E1/E2/E3 logic, threshold values, score weights) were finalized on the train side. No held-out information was used during the design of `OpenEvolve`. The split is clean under Path A (§4.2 of the Stage 2 charter).

---

## What would count as a protocol break

- Running any new experiment on the held-out 7 traces before the final evaluation
- Changing the metric definition of `speedup_vs_best_single`
- Changing the expert pair mid-search
- Using trace name, split label, or benchmark family as a policy input
- Tuning any frozen parameter (warmup/sim windows, split file, simulator revision) without creating a new freeze memo
- Reporting a result as held-out when it was generated during design-side search

---

## File pointers

| Artifact | Path |
| --- | --- |
| Split definition | `data/splits/official_v1.json` |
| Split hash | `data/splits/official_v1.sha256` |
| Metric schema | `docs/operational/dataset_schema.md` |
| Router implementation | `external/athena/src/oogway.cc` (cases 4 and 5) |
| Seed config | `external/athena/config/mop_lite_open_evolve.ini` |
| Knob definitions | `external/athena/inc/knobs.def` (lines containing `mop_`) |
| Run mode configs | `configs/run_modes.json` — `open_evolve_mode` |
| Stage 1 baseline results | `report/tables/router_ablation.md`, `data/processed/runs.csv` |
| Stage 2 search results | `results/open_evolve_search/summary.csv` |
| Stage 2 held-out results | `results/open_evolve_final/summary.csv` |
| Research log | `docs/operational/research_log.md` |
| Transparency log | `docs/operational/transparency_log.md` |
