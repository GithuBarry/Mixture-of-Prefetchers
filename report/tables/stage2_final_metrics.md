| split | method | n | speedup_vs_prefetcher_off | best_expert_speedup | percent_of_best_expert | beats_worse_prefetcher | below_95pct_of_best_expert | closer_to_best_expert | both_prefetchers_beat_disabled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| training-split validation | Manual router | 13 | 1.048 | 1.086 | 96.5% | 9/13 | 3/13 | 9/13 | 8/13 |
| training-split validation | OpenEvolve router | 13 | 1.066 | 1.085 | 98.3% | 11/13 | 2/13 | 10/13 | 7/13 |
| heldout | Manual router | 7 | 0.998 | 1.023 | 97.6% | 6/7 | 1/7 | 6/7 | 2/7 |
| heldout | OpenEvolve router | 7 | 1.003 | 1.024 | 97.9% | 5/7 | 1/7 | 3/7 | 3/7 |
| training-split validation | MLOP | 13 | 0.970 |  |  |  |  |  |  |
| training-split validation | SPP+PPF | 13 | 1.067 |  |  |  |  |  |  |
| heldout | MLOP | 7 | 0.974 |  |  |  |  |  |  |
| heldout | SPP+PPF | 7 | 1.024 |  |  |  |  |  |  |
