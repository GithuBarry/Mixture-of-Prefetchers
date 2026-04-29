# Stage 2 Seed Freeze Memo

Date: 2026-04-28

Status: provisional Stage 2 seed; search-side confirmation is positive versus
old `MoP-V0` (`MoPLite`) but still negative versus pair-best single.

## Frozen Boundary

The Stage 2 candidate seed is `MoP-V1.1` (`MoPLiteGuarded`), an explicit router variant
available through `scripts/run_mop_lite.py --router MoPLiteGuarded`.

Frozen for this candidate:

- cache level: two L2C prefetcher coordination
- expert pair: `Pythia + SPP+PPF`
- baseline router: `MoP-V0` (`MoPLite`) with `mop_router_type=4`
- candidate router: `MoP-V1.1` (`MoPLiteGuarded`) with `mop_router_type=5`
- no-prefetch baseline: unchanged `BASE + config/nopref.ini`
- primary comparator: pair-best constituent single expert on the same trace
- secondary comparators: no-prefetch, old `MoP-V0` (`MoPLite`), and `AthenaMAB`
- search-side evaluation: official `search_subset` unless explicitly labeled as a local dev screen
- final evaluation: held-out or full-suite evaluation only after train/search decisions are frozen

## Candidate Definition

`MoP-V1.1` (`MoPLiteGuarded`) keeps the Stage 1 score signal but changes two structural
decisions that the Stage 1 logs identified as failure modes.

- If both expert scores are nonpositive, choose `both on` instead of `both off`.
- When both experts are enabled, split budget proportionally by score but clamp
  each expert to at least `mop_guarded_min_budget_share` percent of the total
  budget.

The initial guarded minimum budget share is `10%`. Treat this as part of the
candidate seed unless a train-only search explicitly changes it.

## Evolvable Items

Allowed Stage 2 search dimensions:

- guarded minimum budget share
- whether guarded fallback always uses both-on or uses a stricter off condition
- both-on margin or confidence rule
- score weights
- accuracy floor
- epoch length, only if the protocol labels this as a Stage 2 tuning dimension

Not allowed without a new freeze memo:

- changing the no-prefetch baseline
- changing trace splits
- tuning on held-out traces
- dropping losing traces
- comparing only to no-prefetch while hiding pair-best-single results

## Evidence So Far

Development evidence only:

- two-trace smoke run: `MoP-V1.1` (`MoPLiteGuarded`) reached `1.0205x` vs no-prefetch, old
  `MoPLite` was approximately neutral, and `SPP+PPF` remained the strongest
  single-expert reference.
- 13-local-trace 1M scout: `MoP-V1.1` (`MoPLiteGuarded`) improved old `MoP-V0` (`MoPLite`) from
  `1.0098x` to `1.0115x` vs no-prefetch, and from `0.9583x` to `0.9600x` vs
  pair-best single.
- official 10-trace search subset at `5M` warmup + `10M` simulation:
  `MoP-V1.1` (`MoPLiteGuarded`) reached `1.004932x` vs no-prefetch, old `MoP-V0` (`MoPLite`) reached
  `1.002077x`, and `MoPLiteGuarded / MoPLite` was `1.002849x`. It remained
  below pair-best single at `0.970158x`.

This is not enough to claim final success. It is enough to use
`MoP-V1.1` (`MoPLiteGuarded`) as the compact Stage 2 seed family for train-side search.

Follow-up note: `docs/decisions/stage2_forced_single_probe.md` adds a second
explicit Stage 2 candidate family, `MoP-V1.2` (`ProbeThenWinner`), after a filtered dev sweep
showed that removing both mixed actions after an initial probe improves the
candidate set but still does not solve the pair-best-single problem.

## Protocol Breaks

The following would invalidate clean Stage 2 claims unless clearly labeled as
development-only evidence:

- using held-out results to choose the candidate or tune thresholds
- editing evaluator success criteria after seeing results
- replacing `MoPLite` in default modes before a freeze decision
- reporting local dev traces as official split evidence
- presenting `MoP-V1.1` (`MoPLiteGuarded`) as a win without pair-best-single comparison
