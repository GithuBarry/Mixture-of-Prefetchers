| name | source | budget | sticky_margin | accuracy_floor | min_budget_share | weights | wider_speedup | final_train_speedup | heldout_speedup |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MoP-V1 | manual reference | 8192 | none | 30 | 10 | [1.0, 0.5, 1.0] |  | 1.048 | 0.998 |
| MoP-V2 | selected GPT-5.4-mini plus GPT-5.4-nano/local-grid policy | 9216 | 3% | 30 | 10 | [1.0, 0.55, 1.0] | 1.089 | 1.066 | 1.003 |
| V2 candidate from GPT-5 mini | later model comparison sweep | 9216 | 4% | 31 | 11 | [1.1, 0.66, 1.1] | 1.087 |  |  |
| V2 candidate from GPT-5.4 | later model comparison sweep | 10752 | 1% | 31 | 11 | [1.1, 0.66, 0.9] | 1.088 |  |  |
| V2 candidate from Sonnet 4.6 | later model comparison sweep | 11264 | 6% | 26 | 14 | [1.5, 0.45, 0.75] | 1.087 |  |  |
