# Router / coordinator ablation

Geometric mean of IPC speedup vs no-prefetch and vs the pair-best single expert, by split side.
Reported only for (experiment, split) cells that contain runs.

| Coordinator | Split | Runs | Geomean vs no-pref | Geomean vs pair-best single | Min vs pair-best | Max vs pair-best |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| AthenaMAB | heldout | 7 | 1.0378 | 0.9560 | 0.8746 | 1.0007 |
| AthenaMAB | train | 17 | 1.0095 | 0.9619 | 0.6548 | 1.0997 |
| FixedSplit | heldout | 7 | 0.9954 | 0.9170 | 0.6580 | 1.0210 |
| FixedSplit | train | 17 | 1.0017 | 0.9545 | 0.5793 | 1.1923 |
| MoPLite | heldout | 7 | 0.9974 | 0.9188 | 0.6666 | 1.0235 |
| MoPLite | train | 17 | 0.9986 | 0.9515 | 0.5762 | 1.1772 |
| OneShotFit | heldout | 7 | 1.0032 | 0.9242 | 0.6561 | 1.0407 |
| RandomRouter | heldout | 7 | 0.9983 | 0.9196 | 0.6571 | 1.0229 |
| WinnerTakeAll | heldout | 7 | 0.9997 | 0.9209 | 0.6558 | 1.0238 |
| WinnerTakeAll | train | 17 | 1.0037 | 0.9564 | 0.5735 | 1.2016 |
