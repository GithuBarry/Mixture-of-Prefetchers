# Writing Logistics And Artifact Map

This note holds repo-specific names, paths, and bookkeeping details that would distract from the main report.

## Public Names And Code Names

| Public wording | Code or artifact name | Meaning |
| --- | --- | --- |
| manual `MoP-V1.2` router | `MoP-V1.2`, `ProbeThenWinner`, router type `6` | probes both experts for one epoch, then selects the higher-scoring expert |
| OpenEvolve-selected `MoP-V1.3` router | `MoP-V1.3`, sticky-single router | `MoP-V1.2` plus `mop_sticky_margin_pct` |
| disabled prefetching | `Baseline`, `no-prefetch`, `nopref`, `gm_vs_nopref` | universal `1.0x` performance baseline |
| oracle best prefetcher cap | `pair-best`, `pair_best`, `gm_vs_pair_best` | per-trace `max(MLOP, SPP+PPF)` |
| worse constituent prefetcher | `weaker`, `gm_vs_weaker` | per-trace `min(MLOP, SPP+PPF)` |
| training validation | `stage3` in some result paths and ledger rows | 13-trace training validation run |
| wider validation | `stage2` in some result paths and ledger rows | 10-trace training validation run |
| quick evaluation | `stage1` in some result paths and ledger rows | 3-trace OpenEvolve candidate triage |
| smoke evaluation | `stage0` in some result paths and ledger rows | one-trace compile and runtime check |

The main report uses public wording. Existing code and older logs keep `stage0`, `stage1`, `stage2`, and `stage3` names because those are evaluator identifiers and result-directory names.

## Current Figures

| Figure | Path | What it shows |
| --- | --- | --- |
| Router geomean | `report/figures/stage2_pre_post_geomean.png` | disabled-prefetching baseline at `1.0x`, manual router, OpenEvolve router, oracle cap |
| Heldout trace profile | `report/figures/stage2_heldout_trace_profile.png` | per-trace speedup for `MLOP`, `SPP+PPF`, `MoP-V1.3`, and oracle cap |
| Model comparison | `report/figures/stage2_model_comparison.png` | first model-comparison pass, valid and rejected candidate counts |
| OpenEvolve trajectory | `report/figures/stage2_scale_model_comparison.png` | valid generated candidates and best-so-far curves for GPT-5 mini, GPT-5.4, and Sonnet 4.6 |

All current performance plots use disabled prefetching as the `1.0x` baseline. The oracle best prefetcher appears as a cap or reference line.

## Current Tables

| Table | Path |
| --- | --- |
| Final metric table | `report/tables/stage2_final_metrics.md` |
| OpenEvolve scale summary | `report/tables/stage2_scale_model_summary.md` |
| IPC, instruction-count, and cycle-count check | `report/tables/stage2_instruction_cycle_check.md` |

`stage2_final_metrics.md` uses the new public column names:

- `speedup_vs_prefetcher_off`
- `oracle_best_prefetcher_cap`
- `ratio_to_oracle_best`
- `ratio_to_worse_prefetcher`
- `beats_worse_prefetcher`
- `below_0.95x_oracle_best`
- `closer_to_oracle_best`
- `both_prefetchers_beat_disabled`

## Raw Result Directories

Raw simulator outputs live under ignored `results/...` directories on the producing machine.

| Purpose | Path |
| --- | --- |
| Manual `MoP-V1.2` 13-trace training validation | `results/stage2_openevolve/comparators/stage3_v12_current_20260429` |
| OpenEvolve `MoP-V1.3` 13-trace training validation | `results/stage2_openevolve/stage3/a52ed8a4151ad6cc` |
| Manual `MoP-V1.2` heldout reference | `results/stage2_openevolve/heldout/final_v12_reference_20260429` |
| OpenEvolve `MoP-V1.3` heldout | `results/stage2_openevolve/heldout/final_v13_20260429` |
| GPT-5 mini 80-iteration scale run | `results/stage2_openevolve/scale/gpt5mini_stage1_iter80_20260430` |
| GPT-5.4 30-iteration scale run | `results/stage2_openevolve/scale/gpt54_stage1_iter30_20260430` |
| Sonnet 4.6 30-iteration scale run | `results/stage2_openevolve/scale/claude_sonnet46_stage1_iter30_20260430` |

## Committed Evidence

| Evidence | Path |
| --- | --- |
| OpenEvolve evaluator | `stage2/openevolve/evaluator.py` |
| Initial policy seed | `stage2/openevolve/initial_policy.py` |
| Candidate ledger | `stage2/openevolve/candidate_ledger.jsonl` |
| Model-comparison ledger | `stage2/openevolve/model_comparison_ledger.jsonl` |
| Final report | `report/stage2_final_report.md` |
| Slide deck source | `slides/mop_stage2_final/src/deck.mjs` |
| Slide deck output | `slides/mop_stage2_final/output/output.pptx` |
| Slide previews | `slides/mop_stage2_final/scratch/slide-01.png` through `slide-08.png` |
| Slide quality report | `slides/mop_stage2_final/scratch/quality-report.json` |

## Rebuild Commands

Final figures and tables:

```bash
python3 scripts/make_stage2_final_assets.py \
  --heldout-v12 results/stage2_openevolve/heldout/final_v12_reference_20260429 \
  --heldout-v13 results/stage2_openevolve/heldout/final_v13_20260429
```

Manual heldout summary rebuild:

```bash
python3 scripts/rebuild_mop_summary_from_metrics.py \
  --results-dir results/stage2_openevolve/heldout/final_v12_reference_20260429 \
  --expert-0 MLOP \
  --expert-1 SPP+PPF \
  --expected-runs 28
```

Representative OpenEvolve scale command:

```bash
PYTHONPATH=external/openevolve STAGE2_EVAL_STAGE=stage1 \
  python3 external/openevolve/openevolve-run.py \
  stage2/openevolve/initial_policy.py stage2/openevolve/evaluator.py \
  --config stage2/openevolve/config_scale_gpt5mini.yaml \
  --output results/stage2_openevolve/scale/gpt5mini_stage1_iter80_20260430 \
  --iterations 80
```

## Known Discrepancies

- The public report says "training validation", while some paths say `stage3`.
- The public report says "wider validation", while some paths say `stage2`.
- The public report says "quick evaluation", while some paths say `stage1`.
- The public report says "disabled prefetching", while some raw metric keys say `nopref`.
- The public report says "oracle best prefetcher cap", while some raw metric keys say `pair_best`.
- The `official_v1` split metadata still lists a historical recommended pair of `Pythia + SPP+PPF`. The final OpenEvolve report uses the later manual-selection result, `MLOP + SPP+PPF`.
- Raw simulator outputs are ignored by git. The committed ledgers, tables, figures, and deck are the portable evidence layer.
