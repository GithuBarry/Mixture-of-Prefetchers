# Alternate-pair exploratory baselines (held-out)

These runs are **supplemental** and do not replace the committed mainline pair
(`Pythia + SPP+PPF`). They ask whether changing the expert pair alone is enough
to make `MoPLite` competitive.

| Pair | Coordinator | Geomean vs no-prefetch | Geomean vs pair-best single |
| --- | --- | ---: | ---: |
| `Pythia + SPP+PPF` | MoPLite | 0.997413 | 0.918839 |
| `Pythia + SPP+PPF` | AthenaMAB | 1.037783 | 0.956029 |
| `MLOP + SMS` | MoPLite | 0.999778 | 0.984551 |
| `MLOP + SMS` | AthenaMAB | 0.992960 | 0.977837 |
| `Pythia + SMS` | MoPLite | 0.998842 | 0.913791 |
| `Pythia + SMS` | AthenaMAB | 1.025563 | 0.938237 |
| `MLOP + Pythia` | MoPLite | 1.000381 | 0.923328 |
| `MLOP + Pythia` | AthenaMAB | 1.003271 | 0.925995 |

Main takeaway:

- pair choice matters materially
- `MLOP + SMS` gives the best `MoPLite` result vs its pair-best single expert
- `MLOP + Pythia` gives the best `MoPLite` result vs no-prefetch
- but **no tested alternate pair** makes `MoPLite` beat its own pair-best single
  expert on held-out traces
