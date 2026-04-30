| split | method | n | speedup_vs_prefetcher_off | speedup_95ci | best_expert_speedup | best_expert_95ci | percent_of_best_expert | percent_of_best_expert_95ci | beats_worse_prefetcher | below_95pct_of_best_expert | closer_to_best_expert | both_prefetchers_beat_disabled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| training-split validation | MoP-V1 manual router | 13 | 1.048 | [0.986, 1.124] | 1.086 | [1.031, 1.158] | 96.5% | [92.6%, 99.8%] | 9/13 | 3/13 | 9/13 | 8/13 |
| training-split validation | MoP-V2 OpenEvolve router | 13 | 1.066 | [1.017, 1.135] | 1.085 | [1.031, 1.156] | 98.3% | [94.7%, 101.3%] | 11/13 | 2/13 | 10/13 | 7/13 |
| heldout | MoP-V1 manual router | 7 | 0.998 | [0.964, 1.043] | 1.023 | [0.964, 1.091] | 97.6% | [92.0%, 100.9%] | 6/7 | 1/7 | 6/7 | 2/7 |
| heldout | MoP-V2 OpenEvolve router | 7 | 1.003 | [0.957, 1.053] | 1.024 | [0.969, 1.093] | 97.9% | [94.6%, 100.2%] | 5/7 | 1/7 | 3/7 | 3/7 |
| training-split validation | MLOP | 13 | 0.970 | [0.845, 1.087] |  |  |  |  |  |  |  |  |
| training-split validation | SPP+PPF | 13 | 1.067 | [1.018, 1.136] |  |  |  |  |  |  |  |  |
| heldout | MLOP | 7 | 0.974 | [0.943, 0.999] |  |  |  |  |  |  |  |  |
| heldout | SPP+PPF | 7 | 1.024 | [0.967, 1.093] |  |  |  |  |  |  |  |  |
