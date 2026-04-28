# Stage 2 Forced-Single Probe

Date: 2026-04-28

This is a dev-only follow-up to the guarded-router seed. It tests the hypothesis
that the current router loses value because it is too indecisive: `both off`
suppresses useful prefetching, while `both on` splits budget when one expert
should dominate.

## Implementation

Added explicit router `ProbeThenWinner` (`mop_router_type=6`). It keeps the
initial constructor behavior, where both experts are enabled for the first epoch
to collect signal. After the configured probe window
(`mop_one_shot_epochs`), it removes actions `0` and `3` from the policy and
chooses exactly one expert by the current MoP score each epoch.

The existing `WinnerTakeAll` router is a close comparator because it also uses
single-expert actions after the initial both-on epoch. `OneShotFit` with
`mop_one_shot_epochs=1` tests the more aggressive variant that freezes the
winner after one observed epoch.

The runner now exposes these knobs for explicit dev sweeps:

- `--mop-total-budget`
- `--mop-accuracy-floor`
- `--mop-guarded-min-budget-share`
- `--mop-one-shot-epochs`

These overrides are captured in manifests and processed datasets.

## Dev Protocol

Filtered to local traces where both routees beat no-prefetch and the routees
separate by at least about 1% in a 1M scout:

- `450.soplex-92B`
- `471.omnetpp-188B`
- `649.fotonik3d_s-7084B`
- `parsec_2.1.canneal.simlarge.prebuilt.drop_5000M.length_15M`
- `parsec_2.1.fluidanimate.simlarge.prebuilt.drop_9500M.length_250M`

All runs used the same local trace files, `Pythia + SPP+PPF`, no download,
500K warmup, 1M simulation, and epoch tracing.

Dev result directories:

- `results/_dev_forced_single_probe`
- `results/_dev_forced_single_budget1024`
- `results/_dev_forced_single_budget4096`
- `results/_dev_forced_single_budget8192`

## Observed Signal

At the default 2048 budget, forced-single routers improved over old `MoPLite`
and `MoPLiteGuarded` on the five-trace filtered set, but still fell below the
worse single routee on four of five traces.

Budget sweep geomeans over the five filtered traces:

| Budget | Router | vs no-prefetch | vs pair-best | Between routees | Closer to better |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1024 | WinnerTakeAll | 1.006498 | 0.964627 | 1/5 | 0/5 |
| 1024 | OneShotFit | 1.009149 | 0.967167 | 1/5 | 1/5 |
| 1024 | ProbeThenWinner | 1.008226 | 0.966283 | 1/5 | 0/5 |
| 2048 | WinnerTakeAll | 1.013463 | 0.969898 | 1/5 | 1/5 |
| 2048 | OneShotFit | 1.013713 | 0.970138 | 0/5 | 0/5 |
| 2048 | ProbeThenWinner | 1.013440 | 0.969876 | 1/5 | 1/5 |
| 4096 | WinnerTakeAll | 1.019778 | 0.976142 | 3/5 | 1/5 |
| 4096 | OneShotFit | 1.018899 | 0.975301 | 1/5 | 0/5 |
| 4096 | ProbeThenWinner | 1.020452 | 0.976788 | 3/5 | 1/5 |
| 8192 | WinnerTakeAll | 1.035682 | 0.991810 | 2/5 | 2/5 |
| 8192 | OneShotFit | 1.031759 | 0.988053 | 2/5 | 1/5 |
| 8192 | ProbeThenWinner | 1.035570 | 0.991703 | 2/5 | 2/5 |

Best forced-single setting per trace:

| Trace | Best forced-single setting | Pythia | SPP+PPF | Router | Router/best | Router/worse | Between and closer |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `450.soplex-92B` | WinnerTakeAll, budget 8192 | 1.0906 | 1.0760 | 1.0662 | 0.9776 | 0.9909 | no |
| `471.omnetpp-188B` | ProbeThenWinner, budget 8192 | 1.0226 | 1.0140 | 1.0302 | 1.0074 | 1.0159 | no, overshoots |
| `649.fotonik3d_s-7084B` | WinnerTakeAll, budget 8192 | 1.0299 | 1.0442 | 1.0256 | 0.9822 | 0.9958 | no |
| `parsec_2.1.canneal...` | ProbeThenWinner, budget 8192 | 1.0382 | 1.0094 | 1.0361 | 0.9980 | 1.0264 | yes |
| `parsec_2.1.fluidanimate...` | OneShotFit, budget 4096 | 1.0113 | 1.0273 | 1.0300 | 1.0026 | 1.0186 | no, overshoots |

## Interpretation

The indecision hypothesis is partly right. Removing `both off` and `both on`
after the initial probe improves the five-trace dev geomean, and larger budgets
matter. But the result still does not produce the desired between-and-closer
shape across the filtered set. On some traces the router remains below the worse
single; on others it overshoots the better single at larger budgets.

This suggests Stage 2 should treat forced-single routing as a serious candidate
family, but not as a solved result. The next promising policy surface is small:
single-expert action after an initial probe, plus a tuned budget scale and a
guard against overshoot. It should still be evaluated against no-prefetch, both
routee singles, and pair-best single.
