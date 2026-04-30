| split | method | n | speedup_vs_prefetcher_off | oracle_best_prefetcher_cap | ratio_to_oracle_best | ratio_to_worse_prefetcher | beats_worse_prefetcher | below_0.95x_oracle_best | closer_to_oracle_best | both_prefetchers_beat_disabled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| training validation | Manual router | 13 | 1.047685 | 1.086093 | 0.964637 | 1.096428 | 9/13 | 3/13 | 9/13 | 8/13 |
| training validation | OpenEvolve router | 13 | 1.066243 | 1.084810 | 0.982884 | 1.117600 | 11/13 | 2/13 | 10/13 | 7/13 |
| heldout | Manual router | 7 | 0.998069 | 1.022724 | 0.975893 | 1.025138 | 6/7 | 1/7 | 6/7 | 2/7 |
| heldout | OpenEvolve router | 7 | 1.003270 | 1.024333 | 0.979437 | 1.030262 | 5/7 | 1/7 | 3/7 | 3/7 |
| training validation | MLOP | 13 | 0.970026 |  |  |  |  |  |  |  |
| training validation | SPP+PPF | 13 | 1.066940 |  |  |  |  |  |  |  |
| heldout | MLOP | 7 | 0.974379 |  |  |  |  |  |  |  |
| heldout | SPP+PPF | 7 | 1.023725 |  |  |  |  |  |  |  |
