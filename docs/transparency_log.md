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
  schema doc is maintained in `docs/dataset_schema.md` so downstream scripts
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
  counters, and the per-expert MoP telemetry. That evidence supports a clean
  smoke batch with an explicit caveat, while leaving room for a future metrics-
  only patch that does not destabilize the coordinator path.
- AI-assisted: yes.
