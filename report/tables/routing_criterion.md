# Fair routing criterion: `Pythia + SPP+PPF`

Criterion:

- both `Pythia` and `SPP+PPF` are individually above no-prefetch on the trace
- one of them is clearly better

This table reports both favorable and unfavorable criterion-matching cases.

| Trace | Better expert | Epochs | Oracle expert included | Oracle included on nonzero-useful epochs | Exact oracle action | `both off` rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `602.gcc_s-734B` | Pythia | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `619.lbm_s-2676B` | SPP+PPF | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `secret_compute_int_243` | Pythia | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `437.leslie3d-134B` | Pythia | 30 | 1.000 | 1.000 | 0.000 | 0.000 |
| `secret_compute_fp_105` | Pythia | 140 | 0.993 | 0.985 | 0.536 | 0.543 |
| `429.mcf-192B` | SPP+PPF | 30 | 0.933 | 0.333 | 0.900 | 0.933 |
| `parsec_2.1.canneal...` | Pythia | 30 | 0.967 | 0.000 | 0.967 | 1.000 |

Reading guide:

- **Oracle expert included** asks whether the chosen action at least contains the
  offline-better expert for that epoch.
- **Exact oracle action** is stricter and requires the chosen action to match the
  offline oracle exactly.
- The mixed results show that the current rule has real ranking skill on some
  complementary traces, but its action policy still overuses `both off` or fails
  to isolate the better expert on others.
