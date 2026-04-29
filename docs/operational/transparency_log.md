# Reasoning transparency log

One entry per non-trivial decision. Each entry names the decision, the options
considered, the choice, a confidence level (low / medium / high), the evidence
that supports the choice, and whether an AI assistant (this agent) contributed.
When evidence is missing, the entry says so and the confidence drops to "low".

Format:

```
### <ISO date> — <short decision>
- Options: ...
- Choice: ...
- Confidence: low | medium | high
- Evidence: ...
- AI-assisted: yes | no  (role)
```

---

### 2026-04-17 — MoP-lite fallback when both expert scores ≤ 0
- Options: (a) keep previous behaviour (action 3 = both experts on),
  (b) map to action 0 (both off), (c) map to the fixed split.
- Choice: (b) map to action 0.
- Confidence: medium.
- Evidence: Charter scope lock specifies a usefulness floor; if neither expert
  clears it there is no evidence either expert will be useful, so the
  minimum-traffic action is the only one that respects the traffic budget
  constraint without inventing a score. (a) silently violated the floor; (c)
  is handled by the FixedSplit router already and would erase MoPLite's
  differentiation. Pending empirical check on whether the "both scores ≤ 0"
  case is frequent enough to matter.
- AI-assisted: yes (patch authored by Claude in Opencode).

### 2026-04-17 — Include Athena's built-in MAB coordinator as a baseline
- Options: (a) ignore it (MoPLite vs single experts only),
  (b) include it as `AthenaMAB` alongside the 5 router variants.
- Choice: (b).
- Confidence: high.
- Evidence: The charter asks for MoP-lite to be judged against prior
  coordination, and Athena's MAB is the closest prior work vendored in the
  same simulator — running it costs nothing beyond an extra config file and
  avoids the appearance of cherry-picking a weak comparison. Keeping it
  labelled `AthenaMAB` (not "MAB") preserves attribution.
- AI-assisted: yes (decision surfaced + implemented by assistant, confirmed by
  user).

### 2026-04-17 — Dataset entry point = tidy CSV in `data/processed/`
- Options: (a) parquet only, (b) CSV only, (c) both.
- Choice: (b) CSV only for Stage 1; parquet can be added later if size grows.
- Confidence: medium.
- Evidence: Expected dataset size at Stage 1 is ≤ few thousand rows
  (24 traces × ~10 experiments × few seeds). CSV is the most friction-free
  format for ad-hoc inspection and for the expected reviewer; parquet would
  require pyarrow/pandas without meaningful gain at this scale. Fail-loud
  schema doc is maintained in `docs/operational/dataset_schema.md` so downstream scripts
  can type-coerce safely.
- AI-assisted: yes.

### 2026-04-17 — Split artifact separate from `configs/trace_suites.json`
- Options: (a) treat `configs/trace_suites.json` as the split, (b) copy to
  `data/splits/official_v1.json` with a sha256 stamp.
- Choice: (b).
- Confidence: high.
- Evidence: `configs/` is mutable (new trace suites may be added during
  Stage 2), but the Stage 1 split must be frozen to keep held-out data
  untouched. A sha256-stamped copy under `data/splits/` gives the freeze a
  durable artifact independent of future config churn.
- AI-assisted: yes.

### 2026-04-17 — Report figures: matplotlib default style, no seaborn
- Options: (a) matplotlib only (Agg), (b) seaborn or plotly for prettier
  outputs.
- Choice: (a).
- Confidence: high.
- Evidence: Matplotlib 3.10.8 is already available; adding a second plotting
  stack trades reproducibility for aesthetics. The charter values auditability
  over polish for Stage 1.
- AI-assisted: yes.

### 2026-04-17 — Builtin MAB run treated as a separate experiment kind
- Options: (a) tag it as another "router", (b) introduce an
  `experiment_kind = "builtin"` label.
- Choice: (b).
- Confidence: medium.
- Evidence: Downstream ablations need to distinguish "MoP-lite control-surface
  ablation" from "prior-art comparison"; a distinct kind lets figures and
  tables slice on that axis without heuristics. Cost is a single extra string
  value in the schema.
- AI-assisted: yes.

### 2026-04-17 — Deferred: multi-seed runs
- Options: (a) single seed (1) for all Stage 1 routers, (b) 3 seeds for
  stochastic routers (RandomRouter only at the moment), (c) 3 seeds for all
  routers.
- Choice: (a) for smoke; (b) should be revisited before reporting final-mode
  numbers, because RandomRouter is the only one whose output depends on the
  seed.
- Confidence: low (deferred).
- Evidence: FixedSplit, WinnerTakeAll, OneShotFit, and MoPLite as configured
  are deterministic given trace and epoch counters. RandomRouter is the sole
  seed-sensitive variant. Running 3 seeds for RandomRouter in `final_mode` is
  cheap (7 heldout × 3 seeds × 1 experiment); running 3 seeds for all routers
  triples the compute with low expected variance.
- AI-assisted: yes.

### 2026-04-17 — Smoke-batch interpretation after pipeline hardening
- Options: (a) treat the smoke run only as a systems check, (b) record the
  smoke numbers as real evidence while keeping the claim strength narrow.
- Choice: (b).
- Confidence: high.
- Evidence: The smoke batch now completes end-to-end with preserved raw logs,
  manifest rows, generated figures, and a processed dataset. The evidence is
  limited in scope (2 training-side traces, smoke-length windows), so it
  supports statements about runner correctness and early behavior, not headline
  efficacy. The measured geomean speedup vs best single expert is `0.959924x`
  for `AthenaMAB` and `0.958711x` for `MoPLite`.
- AI-assisted: yes.

### 2026-04-17 — Current handling of the MoPLite traffic-counter mismatch
- Options: (a) block all result generation until a new MoP-specific issued-
  traffic counter is added, (b) keep the current smoke batch and document the
  limitation explicitly while using raw cache-issued counts plus downstream DRAM
  / queue-congestion proxies.
- Choice: (b).
- Confidence: medium.
- Evidence: The attempted in-simulator patch for a new per-expert granted/
  issued counter introduced a regression and was reverted. The current Athena
  metric surface still provides `Core_0_L2C_prefetch_issued`,
  `Channel_0_dbus_congested`, `Channel_0_RQ_row_buffer_miss`, queue-full
  counters, and the per-expert MoP telemetry. Stage 1 now uses a documented
  fallback traffic proxy for coordinator rows when the raw cache-issued counter
  is zero but the per-expert issue counters are nonzero. That preserves a usable
  accuracy/traffic analysis with an explicit caveat, while leaving room for a
  future measurement-only simulator patch.
- AI-assisted: yes.

### 2026-04-17 — Primary report baseline = no-prefetch; pair-best single = secondary comparator
- Options: (a) keep the strongest single expert as the headline baseline,
  (b) treat no-prefetch as the primary baseline and the pair-best single as a
  stricter secondary comparator.
- Choice: (b).
- Confidence: high.
- Evidence: No-prefetch is deployable and protocol-stable; the pair-best single
  expert is a postmortem pair-local reference. The completed data support
  useful claims against both. On the training-side subset, `WinnerTakeAll`
  reaches `1.011080x` vs no-prefetch while still landing at `0.975024x` vs the
  pair-best single. That distinction matters for honest reporting.
- AI-assisted: yes.

### 2026-04-17 — Rerun safety via run-group isolation
- Options: (a) keep one flat artifact directory and hope users avoid reruns,
  (b) isolate each invocation under a unique `run_group_id` and reject
  incomplete run groups during dataset construction.
- Choice: (b).
- Confidence: high.
- Evidence: Append-only manifests are only trustworthy if the referenced logs
  and metrics are not overwritten in place. The final Stage 1 workflow now uses
  per-invocation artifact subdirectories plus within-`run_group_id` comparisons
  in `build_dataset.py`, so partial reruns cannot silently corrupt the analysis.
- AI-assisted: yes.

### 2026-04-17 — Best-single reference scoped to the coordinated pair only
- Options: (a) compare each coordinator to the best of every single-prefetcher
  baseline present in the batch, (b) compare to the better of `expert_0` and
  `expert_1` only.
- Choice: (b).
- Confidence: high.
- Evidence: The project question is about coordinating a fixed two-expert pair,
  not about beating an unrelated single-prefetcher skyline. Search and held-out
  batches include `MLOP` and `SMS` for context, but using them inside
  `speedup_vs_best_single` would change the meaning of the central claim.
- AI-assisted: yes.

### 2026-04-17 — Final Stage 1 interpretation after search + held-out batches
- Options: (a) call Stage 1 a performance success because some coordinators are
  above `1.0x` vs no-prefetch, (b) call Stage 1 a baseline success but a
  negative performance result vs the strongest single expert.
- Choice: (b).
- Confidence: high.
- Evidence: On the held-out split, `AthenaMAB` reaches `1.037783x` vs no-
  prefetch, and `OneShotFit` reaches `1.003241x`, but all coordinators remain
  below `1.0x` vs the pair-best single. `MoPLite` lands at `0.997413x` vs
  no-prefetch and `0.918839x` vs pair-best single, winning only 1 of 7 held-out
  traces on the stricter comparator. The infrastructure and measurement story
  are strong; the efficacy story is cautionary.
- AI-assisted: yes.

### 2026-04-17 — Fair routing criterion must include failures, not only wins
- Options: (a) report only traces where the router looks good, (b) predeclare a
  criterion and report both favorable and unfavorable traces inside it.
- Choice: (b).
- Confidence: high.
- Evidence: The criterion used was: both `Pythia` and `SPP+PPF` individually
  above no-prefetch, with one clearly better. Within that set, some traces show
  perfect inclusion of the offline-better expert, while others still fail due to
  overuse of `both off`. Reporting both sides prevents cherry-picking.
- AI-assisted: yes.

### 2026-04-17 — Main Stage 1 question reframed as "better than blind fixed choice?"
- Options: (a) headline MoPLite vs AthenaMAB, (b) headline MoPLite vs the best
  postmortem single expert, (c) headline whether routing can beat choosing one
  individually-good expert blindly when two experts win different subsets.
- Choice: (c), while still reporting AthenaMAB and pair-best-single as context.
- Confidence: high.
- Evidence: This framing matches the actual scientific question of coordination
  under complementarity better than a pure prior-method or skyline framing. The
  completed data show that even on a fair complementary subset, MoPLite does not
  yet beat blind fixed choice.
- AI-assisted: yes.

### 2026-04-17 — Plot design principle: one question per figure
- Options: (a) dense multipurpose figures, (b) fewer figures with a single clear
  question each.
- Choice: (b).
- Confidence: high.
- Evidence: The figure set was simplified so `ipc_speedup_summary.png` uses only
  prefetch-off normalization, `single_expert_profiles.png` answers where experts
  differ, `mop_vs_reference_rows.png` separates pair-best from full-batch best,
  and `router_compare_criterion.png` focuses only on router decisions.
- AI-assisted: yes.

### 2026-04-17 — Simplicity claim vs AthenaMAB phrased qualitatively, not as a byte-count win
- Options: (a) claim MoPLite is cheaper than AthenaMAB, (b) claim only that
  MoPLite has a smaller, more transparent control surface unless a careful state
  accounting proves more.
- Choice: (b).
- Confidence: high.
- Evidence: AthenaMAB maintains per-arm reward/count state and discounted-UCB
  updates. MoPLite uses fixed rule-based scoring over two experts. That supports
  a transparency/simplicity claim, but not a precise hardware-byte superiority
  claim from Stage 1 alone.
- AI-assisted: yes.

### 2026-04-17 — Presentation constraints from user review were treated as explicit project guidance
- Options: (a) keep the report/plots as an internal incremental artifact,
  (b) rewrite the presentation layer so an outsider reader sees a stable,
  non-incremental story with explicit visual and reporting constraints.
- Choice: (b).
- Confidence: high.
- Evidence: The user repeatedly required that: plots should answer one question
  each, failures should be shown rather than cherry-picked away, the report
  markdown itself should embed the key plots, the final story should emphasize
  "better than blind fixed choice?" over a pure MoPLite-vs-AthenaMAB framing,
  and the approved color palette should be respected. Those requests materially
  changed the final figure set and wording, so they belong in the public
  reasoning ledger rather than only the chat history.
- AI-assisted: yes.

### 2026-04-28 — LLC-prefetcher support added as a separate experiment kind
- Options: (a) modify `Baseline`/`nopref.ini`, (b) add LLC prefetching to the
  existing L2 coordinator runs, (c) add a separate `experiment_kind = "llc"`
  with explicit LLC-only flags and matched baselines.
- Choice: (c).
- Confidence: high.
- Evidence: The no-prefetch baseline is a measurement instrument and must stay
  unchanged. A short local screen showed that naive L2+LLC stacking can regress
  geomean (`SPP+PPF + LLC-AMPM` at `0.9994x` vs no-prefetch in the 13-trace
  1M screen). A longer 13-local-trace `5M`/`10M` check then showed `LLC-AMPM`
  at only `0.9654x` geomean, so LLC support should be treated as an evaluation
  surface, not a result claim. A separate experiment kind lets the project
  evaluate the last-level-cache angle without hiding traffic or changing the
  meaning of existing Stage 1 rows.
- AI-assisted: yes.

### 2026-04-28 — `MoPLiteGuarded` kept explicit, not promoted to defaults
- Options: (a) add `MoPLiteGuarded` to recommended/default run modes
  immediately, (b) keep it available only through explicit `--router
  MoPLiteGuarded` until the Stage 2 seed decision is cleaner.
- Choice: (b).
- Confidence: high.
- Evidence: Search-side data show a modest improvement over old `MoPLite`
  (`1.002849x` relative geomean) and a small no-prefetch gain (`1.004932x`),
  but the candidate remains below pair-best single (`0.970158x`). That makes it
  a reasonable Stage 2 seed, not a new default result. Keeping it explicit
  avoids silently changing the Stage 1 reproduction path.
- AI-assisted: yes.

### 2026-04-28 — Forced-single probing treated as candidate family, not a win
- Options: (a) present removal of `both on` / `both off` as the fix,
  (b) add an explicit forced-single router and report the filtered dev result
  with failures and overshoots.
- Choice: (b).
- Confidence: high for the dev result, low for final claims.
- Evidence: On five filtered local traces where both routees beat no-prefetch,
  8192-budget `WinnerTakeAll` reached `1.035682x` vs no-prefetch and
  `0.991810x` vs pair-best; `ProbeThenWinner` reached `1.035570x` and
  `0.991703x`. The desired between-and-closer behavior held on only two of
  five traces. This supports forced-single routing as a Stage 2 candidate, not
  as a completed effectiveness claim.
- AI-assisted: yes.

### 2026-04-29 — Stage 1 finish frozen as high-risk negative result
- Options: (a) promote the best no-prefetch gains as Stage 1 success,
  (b) freeze only if a MoP variant reaches the predeclared `0.98x` pair-best
  threshold, (c) freeze a high-risk negative result and carry only a tiny Stage
  2 seed shortlist forward.
- Choice: (c).
- Confidence: high for the train/search screen outcome, medium for Stage 2
  seed usefulness.
- Evidence: L2C `AMPM` reached `1.062585x` vs no-prefetch on the 10-trace
  train/search qualification screen but never beat the best existing single
  expert by the required `>=2%` margin, so it was not promoted. Corrected
  `stage1_pair_screen_1m` runs with `mop_one_shot_epochs=1` and
  `mop_total_budget=8192` completed for `Pythia + SPP+PPF` and
  `MLOP + SPP+PPF`. The best MoP cells were `MoP-V1.1` on `Pythia + SPP+PPF`
  at `1.065671x` vs no-prefetch and `0.957672x` vs pair-best, and `MoP-V0` on
  `MLOP + SPP+PPF` at `1.065933x` vs no-prefetch and `0.961801x` vs pair-best.
  `MoP-V1.2` was correctly single-action after the probe (`single_action_rate =
  1.0`) but still reached only `0.960353x` vs pair-best on `MLOP + SPP+PPF`.
  `MLOP + Pythia` and `MLOP + SMS` corrected screens hit `SIGBUS` on
  `secret_compute_int_568` for `MoP-V1.2`; `MLOP + SMS` failed again when run
  alone, so those partial dirs are documented as compatibility risks, not
  completed evidence.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 OpenEvolve scaffold smoke

- Goal: start Stage 2 without changing the frozen Stage 1 evaluation boundary.
- Decision: use L2C `MLOP + SPP+PPF` as the active one-story pair, with
  `MoP-V1.2 ProbeSingle` as the main seed and `MoP-V1.1 Guarded` as backup.
  The Stage 2 search surface is restricted to `candidate_policy()` in
  `stage2/openevolve/initial_policy.py`; `WinnerTakeAll`, `OneShotFit`, and
  constituent singles remain comparators only.
- Evidence: the CMU AI Gateway was smoke-tested with the key supplied through
  the environment only; no key was written to the repository. A real simulator
  stage0 run reached `1.006177x` vs pair-best, `1.007034x` vs no-prefetch, and
  `1.006678x` vs weaker routee on one trace. A three-trace stage1 seed run
  reached `0.931329x` vs pair-best, `1.028310x` vs no-prefetch, and
  `1.012950x` vs weaker routee. A reviewer found that candidate import/IO
  leakage and stale-cache reuse were not fail-closed, so the evaluator was
  tightened to literal-policy parsing, train/search split assertions, and
  cache keys that include evaluator, runner, config, and split inputs. The
  committed candidate ledger keeps only post-hardening seed reruns.
- Artifacts: `docs/decisions/stage2_openevolve_start.md`,
  `stage2/openevolve/`, `stage2/openevolve/candidate_ledger.jsonl`,
  `results/stage2_openevolve/smoke_llama8b_iter1`, and
  `results/stage2_openevolve/stage1_llama8b_full_iter3`.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 deterministic policy sweep

- Goal: give OpenEvolve a stronger seed by sweeping the same frozen policy
  surface without touching heldout traces.
- Decision: promote `MoP-V1.2` with `mop_score_weights = [1.0, 0.5, 1.0]`.
  This keeps the same router, budget, probe window, and guards as the prior
  seed, but raises the accuracy component of the score.
- Evidence: the 36-candidate serial stage1 sweep completed with no failed
  records. The tuned seed reached `0.936679x` vs pair-best, `1.033235x` vs
  no-prefetch, and `1.018669x` vs weaker routee, slightly ahead of the old
  seed in combined score. On the 10-trace search confirmation it reached
  `0.958714x` vs pair-best, `1.065858x` vs no-prefetch, and `1.105995x` vs
  weaker routee. On the 13 locally available train traces it reached
  `0.965420x` vs pair-best, `1.047570x` vs no-prefetch, and `1.096829x` vs
  weaker routee.
- Caveat: full 17-trace train confirmation with `--skip-download` failed
  loudly because four train traces are missing locally. No heldout traces were
  used. Athena was unstable under multi-candidate parallelism, so selection
  runs used serial candidate evaluation with explicit retries.
- Artifacts: `docs/decisions/stage2_policy_sweep.md`,
  `stage2/openevolve/selection_ledger.jsonl`,
  `results/stage2_openevolve/sweeps/stage1_tight_serial_20260429`,
  `results/stage2_openevolve/sweeps/stage2_confirm_top3_20260429`, and
  `results/stage2_openevolve/sweeps/stage3_local_train_confirm_top2_20260429`.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 OpenEvolve smoke hardening

- Goal: verify the Stage 2 OpenEvolve loop with the tuned seed before spending
  more model budget.
- Decision: keep `MoP-V1.2` with `mop_score_weights = [1.0, 0.5, 1.0]` as the
  active seed. The only valid new cheap-model candidate used
  `mop_score_weights = [1.0, 0.4, 1.0]`; it lost to the active seed on the
  10-trace search confirmation.
- Evidence: after behavior-hash cache hardening, the active seed reached
  `0.958273x` vs pair-best, `1.064585x` vs no-prefetch, and `1.108183x` vs
  weaker routee on stage2. The `[1.0, 0.4, 1.0]` candidate reached
  `0.958214x`, `1.062867x`, and `1.106615x`.
- Caveat: the cheap 8B model repeatedly tried to add metric keys such as
  `single_action_rate`; the evaluator rejected those edits fail-closed. One
  stage2 retry hit an Athena `SIGBUS` and then succeeded on retry.
- Artifacts: `results/stage2_openevolve/stage1_tuned_llama8b_iter5_behaviorhash`,
  `results/stage2_openevolve/stage2/047993d2d251398b`, and
  `results/stage2_openevolve/stage2/1662bd615d89c4e8`.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 OpenEvolve built-in feature smoke

- Goal: remove action-metric names from the OpenEvolve diversity map so the
  cheap model is less likely to add metrics as policy keys.
- Decision: use built-in `complexity` and `diversity` MAP-Elites features in
  `stage2/openevolve/config_smoke.yaml`. Keep `[1.0, 0.5, 1.0]` as the active
  seed.
- Evidence: the cheap 5-iteration run found a valid `[0.7, 0.3, 1.0]` candidate.
  It improved the 10-trace stage2 search confirmation to `0.960233x` vs
  pair-best and `1.066260x` vs no-prefetch, but failed the 13-trace local-train
  confirmation with `0.963380x` vs pair-best and `1.044298x` vs no-prefetch,
  below the active seed's `0.964299x` and `1.047360x`. It also raised
  catastrophic rate from `0.230769` to `0.307692`.
- Artifacts: `results/stage2_openevolve/stage1_tuned_llama8b_iter5_builtinfeatures`,
  `results/stage2_openevolve/stage2/d1291eb1c25956db`,
  `results/stage2_openevolve/stage2/38d624d27e711ce2`,
  `results/stage2_openevolve/stage3/d1291eb1c25956db`, and
  `results/stage2_openevolve/stage3/38d624d27e711ce2`.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 GPT-5.4-mini sticky-single promotion

- Goal: spend more model budget only after smoke evidence, and decide whether
  OpenEvolve should be allowed to change anything beyond scalar policy knobs.
- Decision: allow one narrow router-side extension, `MoP-V1.3 StickySingle`,
  rather than broad simulator edits. `MoP-V1.3` is `MoP-V1.2` plus one exposed
  `mop_sticky_margin_pct` knob. Promote the GPT-5.4-mini candidate:
  `router=MoP-V1.3`, `mop_total_budget=9216`, `mop_one_shot_epochs=1`,
  `mop_accuracy_floor=30`, `mop_guarded_min_budget_share=10`,
  `mop_sticky_margin_pct=5`, `mop_score_weights=[1.0, 0.55, 1.0]`.
- Evidence: Kimi/Moonshot IDs were probed through the CMU AI Gateway but were
  not available to this team; `gpt-5.4-mini` was available. On the 10-trace
  train/search subset, the promoted candidate reached `0.977466x` vs pair-best,
  `1.087038x` vs no-prefetch, and `1.130068x` vs weaker routee, with
  catastrophic rate `0.200000`. The rebuilt-binary `MoP-V1.2` reference reached
  `0.959129x`, `1.062249x`, `1.106171x`, and catastrophic rate `0.300000`.
  On the 13-trace local train-window confirmation, the promoted candidate
  reached `0.982234x` vs pair-best, `1.067489x` vs no-prefetch, and
  `1.116795x` vs weaker routee. The rebuilt-binary `MoP-V1.2` reference reached
  `0.965888x`, `1.049788x`, and `1.096860x`.
- Caveat: this still does not beat the pair-best single expert overall. It is a
  stronger Stage 2 seed because it closes the pair-best gap while improving over
  no-prefetch and the weaker routee on train/search evidence. Heldout traces
  were not used.
- Artifacts: `results/stage2_openevolve/stage2_gpt54mini_iter4`,
  `results/stage2_openevolve/stage2/48b15535009fa381`,
  `results/stage2_openevolve/stage3/48b15535009fa381`,
  `results/stage2_openevolve/stage2/696ab41d0e1b93bf`, and
  `results/stage2_openevolve/stage3/696ab41d0e1b93bf`.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 GPT-5.4-mini continuation after promotion

- Goal: continue spending a small amount of model budget around the promoted
  `MoP-V1.3` sticky-single seed, while preserving the train-only boundary.
- Decision: keep the existing promoted seed:
  `router=MoP-V1.3`, `mop_total_budget=9216`, `mop_one_shot_epochs=1`,
  `mop_accuracy_floor=30`, `mop_guarded_min_budget_share=10`,
  `mop_sticky_margin_pct=5`, `mop_score_weights=[1.0, 0.55, 1.0]`.
- Evidence: a `10240` budget, sticky `10`, weights `[1.0, 0.5, 1.0]`
  candidate improved the 10-trace train/search window to `0.982001x` vs
  pair-best, `1.089827x` vs no-prefetch, and `1.133480x` vs weaker routee, but
  failed 13-trace train-window confirmation twice with simulator `SIGBUS`.
  A later safer candidate, budget `8960`, sticky `5`, weights
  `[1.0, 0.56, 1.0]`, reached `0.977240x` vs pair-best, `1.087744x` vs
  no-prefetch, and `1.131943x` vs weaker routee on the 10-trace train/search
  window. Its composite score was a tiny improvement over the promoted seed,
  but it lowered pair-best geomean and then failed the 13-trace train-window
  confirmation on the MLOP single baseline for `secret_compute_int_568`.
- Caveat: these are useful negative continuation results, not promotion
  evidence. Heldout traces were not used.
- Artifacts: `results/stage2_openevolve/stage2_gpt54mini_postpromote_iter4`,
  `results/stage2_openevolve/stage2_gpt54mini_postfail_iter4`,
  `results/stage2_openevolve/stage2/53e5b8b728c0a657`,
  `results/stage2_openevolve/stage2/bf4d587210a19f36`,
  `results/stage2_openevolve/stage3/53e5b8b728c0a657`, and
  `results/stage2_openevolve/stage3/bf4d587210a19f36`.
- AI-assisted: yes.

## 2026-04-29 — Stage 2 minimal nano and sticky-margin grid

- Goal: continue Stage 2 search after the full GPT-5.4-mini prompt began
  triggering CMU AI Gateway prompt filtering, without changing the evaluator,
  traces, metrics, or expert pair.
- Decision: promote the sticky-margin-only policy
  `router=MoP-V1.3`, `mop_total_budget=9216`, `mop_one_shot_epochs=1`,
  `mop_accuracy_floor=30`, `mop_guarded_min_budget_share=10`,
  `mop_sticky_margin_pct=3`, `mop_score_weights=[1.0, 0.55, 1.0]`.
- Evidence: a minimal GPT-5.4-nano prompt found a nearby weight tweak
  `[1.0, 0.57, 1.0]`; it improved 13-trace robustness counts but slightly
  lowered the main geomeans and was not promoted. A tiny serial local grid then
  found sticky `3`. On the 10-trace train/search subset, sticky `3` reached
  `0.980137x` vs pair-best, `1.089214x` vs no-prefetch, and `1.130177x` vs
  weaker routee. On the 13 locally available train traces, it reached
  `0.982884x` vs pair-best, `1.066243x` vs no-prefetch, and `1.117600x` vs
  weaker routee, with beats-weaker rate `0.846154` and catastrophic rate
  `0.153846`. A final 4-iteration minimal-nano pass centered on sticky `3`
  produced no valid improvement; all generated mutations were rejected by the
  literal-policy guard before simulator execution.
- Caveat: sticky `3` slightly lowers the 13-trace no-prefetch geomean compared
  with the previous sticky `5` seed (`1.066243x` vs `1.067489x`). It is promoted
  because it improves the primary pair-best comparator, weaker-routee geomean,
  beats-weaker count, and catastrophic count. Heldout traces were not used.
  Full 17-trace train confirmation still awaits the missing train traces.
- Artifacts: `results/stage2_openevolve/stage2_gpt54nano_minimal_iter8_20260429`,
  `results/stage2_openevolve/sweeps/stage2_v13_local_grid_20260429`,
  `results/stage2_openevolve/stage2/7883aa5c4c1a14dc`,
  `results/stage2_openevolve/stage3/7883aa5c4c1a14dc`,
  `results/stage2_openevolve/stage2/a52ed8a4151ad6cc`,
  `results/stage2_openevolve/stage3/a52ed8a4151ad6cc`, and
  `results/stage2_openevolve/stage2_gpt54nano_after_sticky3_iter4_20260429`.
- AI-assisted: yes.
