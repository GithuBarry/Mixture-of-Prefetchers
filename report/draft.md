# MoP-lite Stage 1 report (draft)

> **Status.** All quantitative results below are computed from the merged Stage 1
> dataset in `data/processed/runs.csv`, generated from the committed search-side
> and held-out manifests.

## Title

Two-expert epoch coordination for L2 prefetching on Athena: a scope-locked
Stage 1 baseline.

## Abstract

This report delivers a complete Stage 1 baseline for epoch-level coordination of
two L2 prefetcher experts in Athena. The evidence chain is fully instantiated:
search-side and held-out runs, append-only manifests, a processed dataset,
generated figures and tables, and written experimental logs. Empirically, the
current coordinator family does not outperform the strongest single expert in the
committed pair. Across the full 24-trace Stage 1 set, `MoPLite` reaches
`0.998257x` geomean IPC relative to no-prefetch and `0.941888x` relative to the
better of `Pythia` and `SPP+PPF`, with only 7 of 24 traces above `1.0x` on that
stricter comparator. Stage 1 therefore establishes a reproducible coordination
baseline and a clear negative result for the current pair and rules, rather
than an efficacy win.

## 1. Problem statement

The Stage 1 question is deliberately narrow: can a small epoch-based manager
coordinate exactly two L2 prefetcher experts under an explicit traffic budget
and usefulness floor, and beat strong baselines without losing scientific
clarity? The local scope is fixed to single-core Athena, L2-only coordination,
OCP disabled, instruction-counted epochs, and the expert pair
`Pythia + SPP+PPF`. That scope turns the contribution into a baseline study of
coordination itself rather than a broad search over architecture changes.

## 2. Method

Each coordinated run uses the same two experts and changes only the epoch-level
decision rule. The action space is the same across routers: both off, expert 0
only, expert 1 only, or both on with a shared budget. The compared coordinator
rules are:

- `FixedSplit`: always both on, fixed budget ratio
- `WinnerTakeAll`: send the full budget to the higher-scoring expert
- `RandomRouter`: random single-expert choice
- `OneShotFit`: estimate a winner in the early epochs, then freeze it
- `MoPLite`: use score signs to choose off / one winner / proportional split
- `AthenaMAB`: upstream Athena builtin comparator baseline

The current MoP-lite score combines expert accuracy, a usefulness-derived
coverage proxy, and traffic share, with a hard floor at `30%` accuracy.

## 3. Experimental protocol

The official split is frozen in `data/splits/official_v1.json`. Stage 1 used:

- smoke batch: 2 traces
- train-side batches: 17 traces from the training side
- held-out batch: 7 held-out traces, run only after the search-side batch

Instruction windows:

- search-side batch: `5M` warmup + `10M` simulation
- held-out batch: `20M` warmup + `50M` simulation

The merged dataset contains 230 runs across 24 traces:

- 24 baselines
- 96 single-expert runs
- 86 router runs
- 24 builtin coordinator runs

## 4. Results

### Smoke-batch note

The current repository now has a real end-to-end smoke batch over two traces
(`429.mcf-192B` and `parsec_2.1.fluidanimate...`) with 10 completed runs,
manifest rows, processed dataset output, figures, and tables. These smoke runs
support statements about pipeline correctness and early behavior. They do not
support headline efficacy claims.

Observed smoke geomean IPC vs the best single expert:

- `AthenaMAB`: `0.959924x`
- `MoPLite`: `0.958711x`

Both coordinators trail the strongest single expert (`SPP+PPF`) on the two
smoke traces. That negative result is preserved because it constrains the story
the later training-side search batch is allowed to tell.

### 4.1 Speedup vs no-prefetch

Figure `report/figures/ipc_speedup_summary.png` carries the main baseline story.

Against no-prefetch, some coordinators do achieve small `1+x` gains.

- Train split:
  - `AthenaMAB = 1.009498x`
  - `WinnerTakeAll = 1.003700x`
  - `FixedSplit = 1.001684x`
  - `MoPLite = 0.998605x`
- Held-out split:
  - `AthenaMAB = 1.037783x`
  - `OneShotFit = 1.003241x`
  - `WinnerTakeAll = 0.999658x`
  - `MoPLite = 0.997413x`

The main takeaway from this comparison is limited upside: some coordinators
clear `1.0x` relative to no-prefetch, but the gains are small, split-dependent,
and do not identify `MoPLite` as the strongest rule.

### 4.2 Speedup vs best single expert

This is the decisive Stage 1 comparison; `report/tables/router_ablation.md` and
`report/figures/win_loss_mop_vs_best_single.png` both show that no evaluated
coordinator exceeds the pair-best single expert in geomean.

Against the better of the two coordinated experts (`Pythia`, `SPP+PPF`), every
coordinator remains below `1.0x` in geomean.

- Train split:
  - `AthenaMAB = 0.961926x`
  - `WinnerTakeAll = 0.956400x`
  - `FixedSplit = 0.954480x`
  - `MoPLite = 0.951546x`
- Held-out split:
  - `AthenaMAB = 0.956029x`
  - `OneShotFit = 0.924208x`
  - `WinnerTakeAll = 0.920907x`
  - `MoPLite = 0.918839x`
  - `FixedSplit = 0.917028x`

`MoPLite` beats the pair-best single expert on 6 of 17 train traces and only
1 of 7 held-out traces (7 of 24 overall). More importantly, every coordinator remains below `1.0x`
in geomean on both splits. Under the committed Stage 1 scope, the result is
therefore negative for coordination efficacy, not merely mixed.

### 4.3 Distinct single-expert profiles

Figure `report/figures/single_expert_profiles.png` shows that the single
prefetchers have genuinely different win regions, which is the precondition for
a meaningful coordination problem. On the full 17-trace train split, `MLOP`
wins 8 traces, `Pythia` 5, `SMS` 2, and `SPP+PPF` 2. On the held-out split,
`Pythia` wins 3 traces, `SMS` 3, and `MLOP` 1. That means the current negative
MoPLite result is not because the experts are indistinguishable; it is because
the present coordination rule is not exploiting their differences well enough.

### 4.4 Router ablation

The router ablation shows two things clearly.

1. The ranking depends on the comparator.
   - vs no-prefetch, `AthenaMAB` and `OneShotFit` look best on held-out.
   - vs pair-best single, `AthenaMAB` is best, but still below `1.0x`.
2. The current `MoPLite` rule is not the strongest simple coordinator baseline.
   `AthenaMAB` is stronger on the full training side, and `OneShotFit`
   is stronger on held-out traces.

### 4.5 Failure-mode diagnostics

Two focused epoch-trace diagnostics make the mechanism sharper.

- On `602.gcc_s`, `MoPLite` includes the offline-better expert in `100%` of
  epochs, yet still loses overall.
- On `secret_compute_fp_105`, `MoPLite` includes the offline-better expert in
  `98.5%` of nonzero-usefulness epochs, but exact action match is only `53.6%`,
  and the router chooses `both off` in `54.3%` of epochs.

So the main failure mode is not simply "wrong expert chosen". The evidence now
points more toward overuse of `both off`, insufficient isolation of the winning
expert, and/or budget-sharing behavior that leaves performance on the table.

### 4.6 What the Stage 1 evidence supports

The current evidence supports three claims and rules out two stronger ones.

Supported:

- the measurement pipeline is reproducible and audit-friendly
- coordination can beat no-prefetch on some splits and traces
- the current `Pythia + SPP+PPF` rules are not strong enough to beat the
  pair-best single expert in geomean

Not supported:

- Stage 1 does **not** justify the claim that the current `MoPLite` rule is the
  best coordinator in this repo. It is not; `AthenaMAB`, `WinnerTakeAll`, or
  `OneShotFit` are stronger depending on which comparator is used.
- Stage 1 does **not** support a headline claim that two-expert coordination,
  under the committed pair and protocol, beats the strongest constituent expert.

### 4.7 Expert-pair ablation

Stage 1 still ships with one committed pair only: `Pythia + SPP+PPF`. So the
expert-pair ablation table is structurally present but scientifically narrow.
The current data do not justify claims about other pairs in the mainline result.
Supplemental held-out exploratory batches do suggest that pair choice matters:
`MoPLite` reaches `0.999778x` vs no-prefetch with `MLOP + SMS` and `1.000381x`
with `MLOP + Pythia`, both better than the main pair. But even those alternate
pairs stay below `1.0x` vs their own pair-best single expert, so pair choice
alone does not rescue the current router policy.

### 4.8 Hardware budget
See `report/tables/hardware_budget.md`. The Stage 1 control surface fits in
~100 B of state and sub-kHz arithmetic, so the budget discussion is
decoupled from the measured IPC.

## 5. Limitations

- Stage 1 now covers the full official split (`17` train traces + `7` held-out
  traces), but it still spans only 24 traces total.
- `RandomRouter` was run with one seed only in Stage 1.
- Coordinator traffic and accuracy use a documented fallback proxy when Athena's
  raw cache-issued counter remains zero for coordinator rows.
- Only one expert pair is committed.
- The strongest single-expert comparator is postmortem; it is useful and fair
  as a strict reference, but it is not an online baseline.

Anticipated validity questions:

- **"Are you beating prior coordination?"**
  Not in the strongest sense. `MoPLite` does not beat `AthenaMAB` on the current
  Stage 1 evidence.
- **"Is best-single a fair baseline?"**
  It is fair as a strict postmortem comparator and is reported as such. The
  primary deployable baseline remains no-prefetch.
- **"Did you hide negative traces?"**
  No. The held-out per-trace losses are preserved in `data/processed/runs.csv`
  and `report/figures/win_loss_mop_vs_best_single.png`.
- **"Does the traffic metric change under coordination?"**
  Yes, for coordinator rows a documented fallback proxy is used when Athena's
  raw cache-issued counter stays at zero. That caveat is explicit in the schema,
  memo, and report.
- **"Then why is Stage 1 still useful?"**
  Because the baseline is now scientifically legible: fixed split, fixed pair,
  fixed metrics, reproducible manifests, and clear negative/positive regions for
  Stage 2 to optimize against.

## 6. Claim ↔ evidence table

| Claim | Artifact | Column(s) | Direction |
| --- | --- | --- | --- |
| Some coordinators beat no-prefetch on the 17-trace train split | `data/processed/runs.csv`, `report/figures/ipc_speedup_summary.png` | `speedup_vs_baseline` | `> 1.0` |
| The single experts have distinct win regions, so coordination is a real problem rather than a degenerate one | `report/figures/single_expert_profiles.png`, `data/processed/runs.csv` | trace-level best single expert | heterogeneous winners |
| The current `MoPLite` rule does not beat the pair-best single expert in geomean on train or held-out | `report/tables/router_ablation.md` | `speedup_vs_best_single` | `< 1.0` |
| `MoPLite` still has localized win regions | `report/figures/win_loss_mop_vs_best_single.png`, `data/processed/runs.csv` | `speedup_vs_best_single` by trace | mixed, with some `> 1.0` |
| Held-out no-prefetch wins do not imply wins vs the strongest single expert | `data/processed/runs.csv` | `speedup_vs_baseline`, `speedup_vs_best_single` | comparator-dependent |
| The Stage 1 contribution is a trustworthy baseline and measurement foundation, but the current two-expert policy does not outperform the pair-best single expert | `docs/operational/research_log.md`, `report/tables/router_ablation.md`, `data/processed/runs.csv` | multiple | negative vs pair-best single |

## 7. Reproducibility appendix

```
# Toolchain
python3 --version   # 3.12.12
gcc --version       # 11.4.0

# Build Athena
make -C external/athena -j$(nproc)

# Run search-side batch
python3 scripts/run_mop_lite.py --mode search_mode --workers 15 --results-dir results/mop_lite_search

# Run remaining training traces
python3 scripts/run_mop_lite.py <remaining train trace list and flags> --workers 15 --results-dir results/mop_lite_train_extra

# Run held-out batch
python3 scripts/run_mop_lite.py <heldout trace list and flags> --workers 15 --results-dir results/mop_lite_final

# Build merged dataset + figures
python3 scripts/build_dataset.py --manifest results/mop_lite_search/manifest.jsonl --manifest results/mop_lite_train_extra/manifest.jsonl --manifest results/mop_lite_final/manifest.jsonl
python3 scripts/make_figures.py
```

The manifests at `results/mop_lite_search/manifest.jsonl`,
`results/mop_lite_train_extra/manifest.jsonl`, and
`results/mop_lite_final/manifest.jsonl` fully identify each run. Each
figure/table in `report/` is regenerated deterministically from
`data/processed/runs.csv`.
