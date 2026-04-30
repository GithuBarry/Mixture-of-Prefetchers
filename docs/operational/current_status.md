# Current Status

Updated: 2026-04-30

## Branch And Release Pointer

| Item | Current value |
| --- | --- |
| Active branch | `MoP-Final` |
| Latest pushed commit before this cleanup pass | `ca31e05` |
| Release tag | `v3-finish` |
| Public repository | https://github.com/GithuBarry/Mixture-of-Prefetchers/ |
| Clean deliverable folder | `deliverables/MoP-Final/` |

## Finished Work

- Built the Athena L2C mixture router around `MLOP + SPP+PPF`.
- Selected public names: `MoP-V1` for the manual one-probe router and `MoP-V2` for the OpenEvolve-tuned router.
- Ran train-only OpenEvolve search and model comparisons with GPT-5 mini, GPT-5.4, and Sonnet 4.6.
- Evaluated the selected router on 13 training-validation traces and 7 heldout traces.
- Generated final report, poster, slide deck, figures, tables, and writing logistics.
- Added a clean deliverable package under `deliverables/MoP-Final/`.
- Removed public wording that assumed insider context and old raw router names.
- Updated collaboration text to name Barry Wang and Hamza El Alaoui.

## Current Public Result

All headline performance uses disabled prefetching as `1.000x`.

| Evaluation set | MoP-V1 | MoP-V2 | Best expert |
| --- | ---: | ---: | ---: |
| 13 training-validation traces | `1.048x` | `1.066x` | `1.085x` |
| 7 heldout traces | `0.998x` | `1.003x` | `1.024x` |

The fair interpretation is a full-policy improvement from `MoP-V1` to `MoP-V2`. OpenEvolve changed the budget, coverage weight, and close-score margin together. A budget-only ablation is the clean next experiment for isolating budget causality.

## User Requests Tracked In This Final Cleanup

| Request | Status |
| --- | --- |
| Keep the final branch named `MoP-Final` | Done |
| Force-update the previous commit so older collaborator wording is hidden from branch history | Done |
| Remove assistant collaborator wording and add Hamza | Done |
| Ask an independent subagent to review outsider wording and scientific defensibility | Done |
| Remove public weird/internal wording | Done for public report, README, slides, and deliverable tables |
| Keep disabled prefetching as `1.000x` in all performance plots | Done |
| Keep best expert as a separate reference | Done |
| Use `MoP-V1` and `MoP-V2` public names | Done |
| Make the V1 to V2 trace-delta plot readable | Done in this cleanup pass |
| Add the GitHub repo URL to the final report | Done in this cleanup pass |
| Remove public-facing local path clutter | Done for the final report and visible poster footer |
| Explain whether the budget increase is defensible | Done in this cleanup pass |

## Remaining Work

Known unfinished user requests after this cleanup pass: none.

## Working Preferences To Preserve

- Lead status updates with `Global: xx% finished.`
- Keep public writing plain and outsider-readable.
- Use disabled prefetching as the `1.000x` baseline.
- Show best expert as a separate reference.
- Keep raw code names and result-directory names in writing logistics.
- Keep final report and deliverables free of local path clutter when possible.
- Use the project palette: `#ffb000`, `#fe6100`, `#dc267f`, `#785ef0`, `#648fff`, plus black, white, and light grey.
- Round report and presentation numbers to three decimals unless extra precision is needed.
- Prefer one clean deliverable folder for submission-facing artifacts.
