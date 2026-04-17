# Stage 1 report — outline

Working outline for the Stage 1 MoP-lite report. Each section lists the
content to be filled in and — crucially — the **evidence** each claim will
lean on (which figure, which table, which CSV column).

## 1. Problem statement

- What "L2 prefetcher coordination with two experts" means in this codebase.
- Why this is worth doing now (heterogeneous workloads, traffic caps, the
  known failure mode of single prefetchers).
- Scope lock recap: L2C only, OCP off, single-core, two experts, epoch-level
  routing, 20% traffic cap, 30% accuracy floor.

## 2. Method

- The five router variants (FixedSplit, WinnerTakeAll, RandomRouter,
  OneShotFit, MoPLite), one paragraph each, referencing `oogway.cc` line
  numbers.
- The builtin comparator: `AthenaMAB`, briefly, noting attribution.
- Control surface (link to `docs/operational/stage2_memo.md`).
- Hardware budget: table `report/tables/hardware_budget.md`.

## 3. Experimental protocol

- Simulator, revision, toolchain (link to `docs/operational/environment.md`).
- Traces, split, warmup/sim windows (link to
  `data/splits/official_v1.json`).
- Metric definitions (link to `docs/operational/dataset_schema.md`).
- Run modes (smoke / search / final) and which results use which mode.
- Reproducibility: manifest JSONL + sha256-stamped split + pinned flags.

## 4. Results

### 4.1 Are we faster than no-prefetch?

Evidence: `report/figures/ipc_speedup_summary.png`.
Claim line: "Some coordinators beat no-prefetch in geomean, but the gains are
small and comparator-dependent."

### 4.2 Can we beat the best single expert?

Evidence:
- `report/figures/ipc_speedup_summary.png`
- `report/figures/win_loss_mop_vs_best_single.png`
- `report/tables/router_ablation.md` (geomean per router × split)
Claim line: "No tested coordinator beats the pair-best single expert in geomean
on either split."

### 4.3 Do the single experts have distinct win regions?

Evidence: `report/figures/single_expert_profiles.png`.
Claim line: "Yes. Different single experts win different traces, so the
coordination problem is real rather than degenerate."

### 4.4 Router ablation

Evidence: `report/tables/router_ablation.md`.
Claim line: "Dropping the usefulness floor (FixedSplit) regresses [N]% on
traffic-sensitive traces; dropping the score (RandomRouter) regresses [M]%."

### 4.5 Fair routing criterion

Evidence: `report/tables/routing_criterion.md`.
Claim line: "Under a predeclared complementary-trace criterion, the router shows
real ranking skill on some traces but still fails because of its action policy
on others."

### 4.6 Expert-pair ablation

Evidence: `report/tables/expert_pair_ablation.md`.
Placeholder for now; Stage 1 ships with only (Pythia, SPP+PPF).

Supplemental evidence: `report/tables/alternate_pair_exploration.md`.

## 5. Limitations and threats to validity

- Single-core only: concurrency effects on a shared LLC are unmeasured.
- Two experts only: the coordinator problem at K>2 may behave differently.
- One seed for deterministic routers: we rely on simulator determinism
  rather than multi-seed averaging.
- Trace suite: 24 traces across SPEC/PARSEC/LIGRA/CVP is broad but not
  exhaustive; domain shifts exist.
- Held-out evaluation cardinality: 7 traces — enough to detect large
  regressions, not enough to resolve sub-1% differences.

## 6. Reproducibility appendix

- Full command list to reproduce every figure/table (smoke, search, final).
- Paths to logs, metrics, manifest, and processed dataset.
- Git SHA, Python, gcc, Athena build line.

## 7. Claim ↔ evidence table

Every numeric claim in §4 lists, in one table, the figure/table/file it comes
from and the expected sign/direction of the effect. Reviewers should be able
to spot-check each claim from exactly one artifact.
