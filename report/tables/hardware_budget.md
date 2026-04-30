# Router Hardware And Storage Budget

The selected OpenEvolve policy uses public `MoP-V2` with a per-epoch prefetch budget of `9216`, about `18.4` prefetches per 1K retired instructions. The router stores a small amount of epoch-level state and updates once every `500K` retired instructions.

| Component | Configuration | Approx. storage |
| --- | --- | ---: |
| Per-expert counters | issued and useful counters for `MLOP` and `SPP+PPF` | 32 B |
| Score state | accuracy, coverage, traffic summaries | 24 B |
| Budget registers | total budget and per-expert shares | 12 B |
| Router state | previous action, epoch counter, close-score tie state | 8 B |
| One-epoch probe scratchpad | score sums and counts | 24 B |
| Score weights | three floats | 12 B |
| Threshold knobs | accuracy floor and close-score tie margin | 4 B |
| Rounded total | compact epoch-level metadata | about 120 B |

The router adds epoch-level arithmetic. It does no per-access model inference. With a `500K` retired-instruction epoch, the overhead is dominated by normal simulator bookkeeping rather than router computation.

Historical note: older MoP-lite tables used a `2048` default budget from `external/athena/config/mop_lite.ini`. The selected OpenEvolve policy in the final report uses `9216`.
