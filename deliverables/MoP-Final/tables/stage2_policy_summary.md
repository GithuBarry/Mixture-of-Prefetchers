| Name | Source | Budget | Close-score margin | Accuracy floor | Minimum budget share | Weights | Wider speedup | Final train speedup | Heldout speedup |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MoP-V1 | manual reference | 8192 | none | 30 | 10 | [1.0, 0.5, 1.0] |  | 1.048 | 0.998 |
| MoP-V2 | selected final policy | 9216 | 3% | 30 | 10 | [1.0, 0.55, 1.0] | 1.089 | 1.066 | 1.003 |
| V2 candidate from GPT-5 mini | follow-up model comparison | 9216 | 4% | 31 | 11 | [1.1, 0.66, 1.1] | 1.087 |  |  |
| V2 candidate from GPT-5.4 | follow-up model comparison | 10752 | 1% | 31 | 11 | [1.1, 0.66, 0.9] | 1.088 |  |  |
| V2 candidate from Sonnet 4.6 | follow-up model comparison | 11264 | 6% | 26 | 14 | [1.5, 0.45, 0.75] | 1.087 |  |  |
