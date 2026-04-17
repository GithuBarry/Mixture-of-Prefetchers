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
committed pair. On the 10-trace search subset, `MoPLite` reaches `1.000874x`
geomean IPC relative to no-prefetch but `0.965182x` relative to the better of
`Pythia` and `SPP+PPF`. On the 7-trace held-out split, it reaches `0.997413x`
relative to no-prefetch and `0.918839x` relative to the pair-best single expert,
with only 1 of 7 held-out traces above `1.0x` on that stricter comparator.
Stage 1 therefore establishes a reproducible coordination baseline and a clear
negative result for the current pair and rules, rather than an efficacy win.

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
- train-side search batch: 10 traces from the training side
- held-out batch: 7 held-out traces, run only after the search-side batch

Instruction windows:

- search-side batch: `5M` warmup + `10M` simulation
- held-out batch: `20M` warmup + `50M` simulation

The merged dataset contains 167 runs across 17 traces:

- 17 baselines
- 68 single-expert runs
- 65 router runs
- 17 builtin coordinator runs

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

- Train-side search subset:
  - `WinnerTakeAll = 1.011080x`
  - `AthenaMAB = 1.004727x`
  - `FixedSplit = 1.004193x`
  - `MoPLite = 1.000874x`
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

- Train-side search subset:
  - `WinnerTakeAll = 0.975024x`
  - `AthenaMAB = 0.968898x`
  - `FixedSplit = 0.968383x`
  - `MoPLite = 0.965182x`
- Held-out split:
  - `AthenaMAB = 0.956029x`
  - `OneShotFit = 0.924208x`
  - `WinnerTakeAll = 0.920907x`
  - `MoPLite = 0.918839x`
  - `FixedSplit = 0.917028x`

`MoPLite` beats the pair-best single expert on 4 of 10 search traces but only
1 of 7 held-out traces. More importantly, every coordinator remains below `1.0x`
in geomean on both splits. Under the committed Stage 1 scope, the result is
therefore negative for coordination efficacy, not merely mixed.

### 4.3 Accuracy vs traffic

The traffic/accuracy figure should be read as an operating-point view, not as a
ranking plot. For coordinator runs, Athena's raw `Core_0_L2C_prefetch_issued`
counter can remain zero even when the per-expert MoP issue counters are
nonzero. Coordinator rows therefore use the documented fallback traffic proxy
`pref0_issued_total + pref1_issued_total` when the raw cache-issued counter is
zero. That keeps coordinator points observable, but makes the coordinator
traffic measure non-identical to the single-expert case.

### 4.4 Router ablation

The router ablation shows two things clearly.

1. The ranking depends on the comparator.
   - vs no-prefetch, `AthenaMAB` and `OneShotFit` look best on held-out.
   - vs pair-best single, `AthenaMAB` is best, but still below `1.0x`.
2. The current `MoPLite` rule is not the strongest simple coordinator baseline.
   `WinnerTakeAll` is stronger on the train-side search subset, and `OneShotFit`
   is stronger on held-out traces.

### 4.5 What the Stage 1 evidence supports

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

### 4.6 Expert-pair ablation

Stage 1 still ships with one committed pair only: `Pythia + SPP+PPF`. So the
expert-pair ablation table is structurally present but scientifically narrow.
The current data do not justify claims about other pairs.

### 4.7 Hardware budget
See `report/tables/hardware_budget.md`. The Stage 1 control surface fits in
~100 B of state and sub-kHz arithmetic, so the budget discussion is
decoupled from the measured IPC.

## 5. Limitations

- The train-side batch is the official 10-trace `search_mode` subset, not the
  full 17-trace training side.
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
| Some coordinators beat no-prefetch on the train-side search subset | `data/processed/runs.csv`, `report/figures/ipc_speedup_summary.png` | `speedup_vs_baseline` | `> 1.0` |
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

# Run held-out batch
python3 scripts/run_mop_lite.py <heldout trace list and flags> --workers 15 --results-dir results/mop_lite_final

# Build merged dataset + figures
python3 scripts/build_dataset.py --manifest results/mop_lite_search/manifest.jsonl --manifest results/mop_lite_final/manifest.jsonl
python3 scripts/make_figures.py
```

The manifests at `results/mop_lite_search/manifest.jsonl` and
`results/mop_lite_final/manifest.jsonl` fully identify each run. Each
figure/table in `report/` is regenerated deterministically from
`data/processed/runs.csv`.
