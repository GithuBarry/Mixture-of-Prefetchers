# Reproducibility Appendix

This appendix documents the implementation names, artifact paths, and rebuild commands used to produce the final report materials.

## Public Names And Code Names

| Report term | Implementation or artifact name | Meaning |
| --- | --- | --- |
| manual `MoP-V1` router | `MoP-V1.2`, `ProbeThenWinner`, router type `6` | probes both experts for one epoch, then selects the higher-scoring expert |
| OpenEvolve-selected `MoP-V2` router | `MoP-V1.3` | selected OpenEvolve policy. `mop_sticky_margin_pct` is one evolved policy key |
| disabled prefetching | `Baseline`, `no-prefetch`, `nopref`, `gm_vs_nopref` | universal `1.0x` performance baseline |
| best expert | `pair-best`, `pair_best`, `gm_vs_pair_best` | per-trace `max(MLOP, SPP+PPF)` |
| worse constituent prefetcher | `weaker`, `gm_vs_weaker` | per-trace `min(MLOP, SPP+PPF)` |
| training-split validation | `stage3` in some result paths and ledger rows | 13-trace training-split validation run |
| wider validation | `stage2` in some result paths and ledger rows | 10-trace training validation run |
| quick evaluation | `stage1` in some result paths and ledger rows | 3-trace OpenEvolve candidate screening |
| smoke evaluation | `stage0` in some result paths and ledger rows | one-trace compile and runtime check |

The main report uses simplified terminology. Existing code and older logs keep `MoP-V1.2` for public `MoP-V1`, `MoP-V1.3` for public `MoP-V2`, and `stage0`, `stage1`, `stage2`, and `stage3` because those are evaluator identifiers and result-directory names.

## Current Figures

| Figure | Path | What it shows |
| --- | --- | --- |
| Router geomean | `report/figures/stage2_pre_post_geomean.png` | disabled-prefetching baseline at `1.0x`, `MoP-V1` manual router, `MoP-V2` OpenEvolve router, best expert |
| Heldout trace profile | `report/figures/stage2_heldout_trace_profile.png` | per-trace speedup for `MLOP`, `SPP+PPF`, public `MoP-V1`, and public `MoP-V2` |
| Routing behavior stats | `report/figures/stage2_routing_behavior_stats.png` | selected epochs, budget share, and useful-prefetch share for public `MoP-V1` and public `MoP-V2` |
| OpenEvolve trajectory | `report/figures/stage2_scale_model_comparison.png` | valid generated candidates and best-so-far curves for GPT-5 mini, GPT-5.4, and Sonnet 4.6 |
| V1 to V2 trace delta | `report/figures/stage2_v1_v2_trace_delta.png` | per-trace speedup change from public `MoP-V1` to public `MoP-V2` |

All current performance plots use disabled prefetching as the `1.0x` baseline. The best expert result appears as a reference line or marker when shown.

## Number Formatting

Figures, tables, and report prose round displayed speedups to at most three decimal places, such as `1.033x` or `0.998x`. Comparisons to the per-trace best expert use `xx.x% of best expert`. Raw JSON, CSV, and ledger artifacts keep full precision for reproducibility.

## Confidence Intervals

Reported confidence intervals are deterministic trace-bootstrap 95% intervals with 10,000 resamples over trace-level speedups. They quantify sensitivity to the sampled trace set. Each trace and configuration pair has one simulator run, so the intervals are trace-set intervals.

## Plot Colors

Plots use a consistent color palette. OpenEvolve router results use `#dc267f`. Manual router results use `#fe6100`. Constituent prefetchers use `#648fff` for the main expert hue, with opacity separating Expert 1 and Expert 2 in per-trace plots. The best expert uses `#3f6fd1`, a darker blue reference. Disabled prefetching uses black. Light grey is reserved for gridlines and range guides. Model-search plots use `#dc267f`, `#785ef0`, and `#648fff` because all three curves come from OpenEvolve runs.

## Current Tables

| Table | Path |
| --- | --- |
| Final metric table | `report/tables/stage2_final_metrics.md` |
| OpenEvolve scale summary | `report/tables/stage2_scale_model_summary.md` |
| IPC, instruction-count, and cycle-count check | `report/tables/stage2_instruction_cycle_check.md` |
| Policy summary | `report/tables/stage2_policy_summary.md` |

`stage2_final_metrics.md` reports speedup over disabled prefetching, trace-bootstrap intervals, percent of the per-trace best expert, and routing checks such as beating the worse expert or falling below `95.0%` of the best expert.

The OpenEvolve weighted score used for candidate selection is:

```text
log(percent of best expert)
+ 0.25 * log(speedup vs disabled prefetching)
+ 0.20 * log(speedup vs worse prefetcher)
- 0.12 * tail-loss rate
- 0.03 * off-action rate
```

The public plots show IPC speedup over disabled prefetching. The score-selected line can move down in IPC when the weighted score improves through better best-expert closeness, weaker-prefetcher margin, or tail-loss behavior.

## OpenEvolve Evaluator Details

The main report keeps evaluator mechanics brief. The OpenEvolve evaluator used these training-only evaluation sets:

| Public wording | Code name | Trace count and window |
| --- | --- | --- |
| smoke evaluation | `stage0` | 1 training trace, `500K` warmup, `1M` simulation |
| quick evaluation | `stage1` | 3 training traces, `500K` warmup, `1M` simulation |
| wider validation | `stage2` | 10 training traces, `500K` warmup, `1M` simulation |
| training-split validation | `stage3` | 13 training traces, `500K` warmup, `1M` simulation |

## Result Directories

The following result directories were used to generate the final summaries. Raw simulator outputs are not part of the clean deliverable package.

| Purpose | Path |
| --- | --- |
| Manual `MoP-V1` 13-trace training-split validation | `results/stage2_openevolve/comparators/stage3_v12_current_20260429` |
| OpenEvolve `MoP-V2` 13-trace training-split validation | `results/stage2_openevolve/stage3/a52ed8a4151ad6cc` |
| Manual `MoP-V1` heldout reference | `results/stage2_openevolve/heldout/final_v12_reference_20260429` |
| OpenEvolve `MoP-V2` heldout | `results/stage2_openevolve/heldout/final_v13_20260429` |
| GPT-5 mini 80-iteration scale run | `results/stage2_openevolve/scale/gpt5mini_stage1_iter80_20260430` |
| GPT-5.4 80-iteration scale run | `results/stage2_openevolve/scale/gpt54_stage1_iter80_20260429_224042` |
| Sonnet 4.6 30-iteration scale run | `results/stage2_openevolve/scale/claude_sonnet46_stage1_iter30_20260430` |

The automated summary script did not complete for the manual `MoP-V1` heldout set. `summary.csv`
and `summary.md` were rebuilt from 28 complete metric JSON files, recorded in
`results/stage2_openevolve/heldout/final_v12_reference_20260429/summary_rebuild_provenance.json`.

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
| Clean deliverable folder | `deliverables/MoP-Final/` |

## Rebuild Commands

Final figures and tables:

```bash
python3 scripts/make_stage2_final_assets.py \
  --heldout-v12 results/stage2_openevolve/heldout/final_v12_reference_20260429 \
  --heldout-v13 results/stage2_openevolve/heldout/final_v13_20260429
```

Clean deliverable package:

```bash
python3 scripts/package_final_deliverables.py
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

## Name Mapping Notes

| Report term | Internal name or path term |
| --- | --- |
| training-split validation | `stage3` |
| wider validation | `stage2` |
| quick evaluation | `stage1` |
| disabled prefetching | `nopref` |
| best expert | `pair_best` |

The `official_v1` split metadata still lists an earlier recommended pair, `Pythia + SPP+PPF`. The final report uses the later manual-selection result, `MLOP + SPP+PPF`. Historical pre-OpenEvolve tables were moved to `report/tables/legacy_stage1/` so the main table folder contains only current report tables. Raw simulator outputs are ignored by git; the committed ledgers, tables, figures, and deck are the portable evidence layer.
