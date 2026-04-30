# Legacy Supplemental: Fair Routing Criterion for `Pythia + SPP+PPF`

This table is older baseline-search context. The current OpenEvolve report uses
`MLOP + SPP+PPF` as the selected expert pair.

Criterion:

- both `Pythia` and `SPP+PPF` are individually above disabled prefetching on the trace
- one of them is clearly better

This table reports both favorable and unfavorable criterion-matching cases.

| Trace | Better expert | Epochs | Better expert included | Better expert included on nonzero-useful epochs | Exact best action | `both off` rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `602.gcc_s-734B` | Pythia | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `619.lbm_s-2676B` | SPP+PPF | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `secret_compute_int_243` | Pythia | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `437.leslie3d-134B` | Pythia | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `secret_compute_fp_105` | Pythia | 140 | 0.993 | 0.985 | 0.536 | 0.543 |
| `429.mcf-192B` | SPP+PPF | 30 | 0.933 | 0.333 | 0.900 | 0.933 |
| `parsec_2.1.canneal...` | Pythia | 30 | 0.967 | 0.000 | 0.967 | 1.000 |

Reading guide:

- **Better expert included** asks whether the chosen action at least contains the
  offline-better expert for that epoch.
- **Exact best action** is stricter and requires the chosen action to match the
  offline best action exactly.
- The mixed results show that the current rule has real ranking skill on some
  complementary traces, but its action policy still overuses `both off` or fails
  to isolate the better expert on others.
