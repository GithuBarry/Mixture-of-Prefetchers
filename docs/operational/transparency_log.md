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
