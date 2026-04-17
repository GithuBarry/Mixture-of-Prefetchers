# MoP-lite Stage 1 report (draft)

> **Status: scaffold only.** Section bodies will be filled after real runs
> land in `data/processed/runs.csv`. No numbers or figures are asserted here
> yet. This file will be updated *after* every experiment batch, with new
> numbers traceable to the exact manifest rows that produced them.

## Title

Two-expert epoch coordination for L2 prefetching on Athena: a scope-locked
Stage 1 baseline.

## Abstract (TBD)

Single placeholder paragraph — to be written once §4 is populated with real
numbers. The abstract will state the geomean speedup of MoP-lite vs the best
single expert on train and held-out splits, with both numbers pulled from
`data/processed/runs.csv`.

## 1. Problem statement

See `report/outline.md` §1. Body to be written after smoke + search results
are in. The scope lock is already documented in the charter; this section
will restate it in reviewer-friendly language.

## 2. Method

See `report/outline.md` §2. Router-variant descriptions will cite specific
line ranges in `external/athena/src/oogway.cc` (actions 0–3, budget accounting
in `train_and_take_action`, router dispatch in the MoPLite case).

## 3. Experimental protocol

See `docs/operational/environment.md`, `docs/operational/dataset_schema.md`, and
`data/splits/official_v1.json`. The body of this section will mostly link
those documents rather than duplicate them.

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
_Pending `report/figures/ipc_speedup_vs_nopref.png`._

### 4.2 Speedup vs best single expert
_Pending `report/figures/ipc_speedup_vs_best_single.png` and
`report/figures/win_loss_mop_vs_best_single.png`._

### 4.3 Accuracy vs traffic
_Pending `report/figures/accuracy_vs_traffic.png`._

### 4.4 Router ablation
_Pending `report/tables/router_ablation.md`._

### 4.5 Expert-pair ablation
_Pending `report/tables/expert_pair_ablation.md`. Stage 1 ships with one
pair (Pythia + SPP+PPF); this table becomes meaningful once a second pair is
added._

### 4.6 Hardware budget
See `report/tables/hardware_budget.md`. The Stage 1 control surface fits in
~100 B of state and sub-kHz arithmetic, so the budget discussion is
decoupled from the measured IPC.

## 5. Limitations

See `report/outline.md` §5. The threats-to-validity list will be finalized
once the measurement noise floor is known (requires ≥3 seeds on the one
stochastic router).

## 6. Claim ↔ evidence table

_Populated once §4 has concrete claims. Each row will have the form:_

| Claim | Artifact | Column(s) | Direction |

## 7. Reproducibility appendix

```
# Toolchain
python3 --version   # 3.12.12
gcc --version       # 11.4.0

# Build Athena
make -C external/athena -j$(nproc)

# Run smoke matrix (2 traces × {Baseline, Pythia, SPP+PPF, MoPLite, AthenaMAB})
python3 scripts/run_mop_lite.py --mode smoke_mode --epoch-trace

# Build dataset + figures
python3 scripts/build_dataset.py
python3 scripts/make_figures.py
```

The manifest at `results/mop_lite/manifest.jsonl` fully identifies each run.
Each figure/table in `report/` is regenerated deterministically from
`data/processed/runs.csv`.
