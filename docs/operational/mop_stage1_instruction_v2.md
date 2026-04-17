# Prompt Document A
# Stage 1 recovery charter
# Find a serious coordination baseline, freeze an evolvable family, and rebuild the scientific story

You are the research engineer for Stage 1 of a scaled-down systems research project.

Your job is stronger than “make the code run.” Your job is to leave the project with a scientifically serious baseline, a trustworthy dataset, a clean evaluation protocol, a strong Stage 2 seed, and the backbone of a real report.

Current project state already proves that the pipeline works. Current project state also proves that the default mainline is weak. Treat that as useful evidence. Use it to make better decisions.

This document gives goals, boundaries, success criteria, decision rules, failure patterns, and documentation expectations. You choose the local abstractions and file layout. You do not need to preserve the current naming if the current naming blurs the science.

Completion means the full deliverable set in this document.

---

## 1. Read this first

The current repository already contains a real result. The result is scientifically useful and strategically insufficient.

Anchor on these facts from the local artifact.

- The current default `MoPLite` rule on the committed `Pythia + SPP+PPF` L2 pair trails the pair-best single expert badly on held-out traces.
  - `MoPLite` held-out geomean vs pair-best single = `0.918839`
  - `AthenaMAB` held-out geomean vs pair-best single = `0.956029`
  - source: `report/tables/router_ablation.md`
- Pair choice matters.
  - exploratory held-out `MLOP + SMS` with the same `MoPLite` rule reaches `0.984551` vs its pair-best single
  - exploratory held-out `MLOP + Pythia` reaches `1.000381` vs no-prefetch, though still below its pair-best single
  - source: `report/tables/alternate_pair_exploration.md`
- Current failure mode is structural, not only numerical.
  - epoch diagnostics show heavy overuse of `both off` on some traces
  - current router logic maps low-confidence situations into zero action mass too often
  - source: `report/tables/routing_criterion.md` and `external/athena/src/oogway.cc`
- The current project already has enough evidence to say the pipeline is real and the present rule is a weak coordinator.

That means Stage 1 is now a **recovery and redesign stage**, not a “first implementation” stage.

Your goal is to find and freeze a serious hand-designed baseline family for Stage 2. The current `MoPLite` rule is a baseline candidate, not an entitled main character.

---

## 2. Mission

Establish the strongest scientifically credible baseline family for prefetcher coordination that the project can defend in a final report.

That means all of the following.

- Choose the right **coordination level** for this project, with L2 as the default starting point and LLC as an explicit fallback option when local evidence supports it.
- Choose the right **expert pool and pairing strategy**.
- Choose the right **hand-designed control family** for Stage 2 optimization.
- Preserve the current weak rule as a clearly labeled baseline when it remains weak.
- Produce a clean dataset, decision log, transparency log, and manual report foundation.
- Prepare a compact, well-isolated, OpenEvolvable policy surface.

The scientific question for Stage 1 is now:

**Which compact coordination family, at which cache level and with which expert pair, deserves Stage 2 optimization because it has a real path to beating the strongest constituent single expert under explicit traffic and usefulness constraints?**

---

## 3. What success means now

### 3.1 The project already has one success

The repo already has a reproducible simulator path, a processed dataset, figures, and a negative result. That part is established.

### 3.2 The next success must be stronger

Stage 1 is successful only when it leaves behind at least one **serious Stage 2 seed**.

A serious Stage 2 seed has these properties.

- It is chosen through a clean development protocol.
- It is better than the current weak rule by a meaningful margin on the same family and comparator.
- It is close enough to the best constituent single expert that optimization is worth the cost.
- Its mechanism is understandable from real traces.
- Its policy surface is small enough to evolve.

### 3.3 Quantitative gates

Use these as the working gate for promotion into Stage 2.

#### Minimum gate for a serious seed

On development data or grouped resampling data, the chosen family should satisfy all of these.

- geomean vs selected constituent-best single expert of at least `0.98`
- geomean vs no-prefetch of at least `1.01`
- mean traffic overhead within the declared cap, with `20%` as the default reference cap
- usefulness or accuracy floor satisfied under the current metric definition, with `30%` as the default floor
- meaningful gain over the matching `MoPLite-v0` baseline on the same pair and level, with `+0.03` on geomean ratio as a strong rule of thumb
- clear reduction of the current “empty epoch” pathology on traces where at least one expert is individually useful

#### Strong gate

A family is a strong Stage 2 seed when it reaches most of these.

- geomean vs selected constituent-best single of at least `0.99`
- competitive with the strongest hand-designed coordinator baseline available under the same scope
- stable behavior across more than one grouped split, validation batch, or development subsample
- understandable win and loss case studies from epoch traces

#### Headline success

Headline success belongs to the final Stage 2 result only. Keep that discipline.

A headline performance claim means a clean final evaluation that reaches `> 1.00` geomean vs the selected constituent-best single under the frozen protocol.

---

## 4. How to think about the project

Work like a paper author.

Use these norms throughout the project.

- Keep one crisp scientific question in view.
- Treat strong baselines as part of the contribution.
- Let the strongest comparator drive design decisions.
- Preserve negative results when they clarify the mechanism.
- Prefer a smaller and more interpretable control surface when two options look similar.
- Ask of every experiment, “what decision will this resolve?”
- Keep the future OpenEvolve surface small, deterministic, and isolated.
- Keep the report and dataset as first-class outputs.

### Writing style for project documents

Write plainly.

- Lead with the answer.
- Use exact file pointers.
- Give the reader concrete takeaways.
- Keep the interpretation close to the evidence.
- Write report prose manually.
- Use code to generate figures, tables, and datasets.

---

## 5. Naming and claim discipline

The current naming is free to change.

Use this policy unless later evidence makes a better choice obvious.

- `Mixture-of-Prefetchers` or `MoP` is the **project theme**.
- The current rule in `external/athena/src/oogway.cc` becomes a **baseline** name such as `MoPLite-v0`, `ScoreFloorRouter`, or another descriptive label.
- The Stage 1 selected family earns the `MoP` headline name only after it becomes the mainline candidate.
- Figures, tables, configs, and report prose should make this distinction visible.

This matters because the current rule is a weak hand-designed baseline. Naming it like the flagship method weakens the scientific story.

---

## 6. Clean science boundary

### 6.1 Held-out discipline starts now

Current exploratory alternate-pair runs already touched the old held-out split for design ideas.

Treat that old held-out split as **development evidence for pair and family hypotheses**. It still matters. It does not support a fresh final claim.

Choose one of these paths early and record the decision in a memo.

#### Path A. Create a new clean split

Use the larger local Athena trace inventory if it is available on disk or cheaply accessible.

- build `official_v2.json`
- keep benchmark family grouping or strong trace-family grouping
- keep the new test side untouched after the split is frozen
- record the split file and a hash next to the dataset

#### Path B. Use grouped resampling honestly

If a new clean split is out of reach, switch the study to grouped cross-validation or repeated grouped train and validation splits.

- use benchmark-family-aware grouping
- keep final claims phrased as grouped-resampling evidence
- say clearly that no pristine held-out test remains

### 6.2 Freeze what matters once the boundary is chosen

Freeze all of these after the boundary decision.

- split definition
- metric definitions
- warmup and simulation windows per run mode
- simulator revision used for comparisons
- list of included baselines for the chosen family and level

---

## 7. Decision tree

Resolve these decisions in order.

### Decision 1. Which cache level deserves the mainline effort

Default start:

- start at **L2** because the current coordination plumbing already lives there

Decision gate:

- keep L2 if the best development families show near-parity with the best constituent single expert and if the implementation cost stays small
- consider **LLC** if local code inspection shows a modest coordination path and if early evidence suggests stronger expert diversity or cleaner traffic behavior there

Required memo:

- `docs/decisions/cache_level_choice.md`

Your memo should cover these points.

- current support in local code
- expected engineering cost
- expected scientific payoff
- measurement visibility at that level
- reason for the final choice

### Decision 2. Which expert pool is worth serious attention

Default starting pool at L2:

- `Pythia`
- `SPP+PPF`
- `MLOP`
- `SMS`

These already appear in the current baseline and Athena materials.

You may add more experts if they are already present locally and stable at the chosen level.

Required memo:

- `docs/decisions/expert_pool_choice.md`

### Decision 3. Which pairs show enough complementarity

Stage 1 should not assume the current pair is best.

Choose pairs through development evidence.

For each candidate pair, compute and document at least these.

- constituent single-expert geomean and per-trace wins
- disagreement rate across traces
- complementary win regions
- simple pair oracle upper bounds, clearly labeled as offline references
- traffic and usefulness profiles of both singles
- one sentence on why coordination might help for this pair

Promote only a small number of pairs, usually two to four.

Required memo:

- `docs/decisions/pair_selection.md`

### Decision 4. Which hand-designed family deserves OpenEvolve time

Current weak `MoPLite-v0` should be one baseline among several.

Evaluate multiple serious families before freezing Stage 2.

Use real trace evidence to choose the winner.

Required memo:

- `docs/decisions/family_selection.md`

---

## 8. Work order

Use this order unless a local blocker forces a change.

### Phase A. Reproduce and sanitize the current state

Goals:

- rerun at least one representative current result from scratch
- rebuild the processed dataset and key figures
- confirm that the current negative result is reproducible
- verify current metric parsing by manual spot checks against raw outputs

Completion evidence:

- one rerun command in the log
- rebuilt `runs.csv`
- rebuilt core figure set
- manual audit of at least five dataset rows against raw outputs

### Phase B. Build the single-expert map

Goals:

- evaluate the stable single experts at the selected level under one fair protocol
- understand where each expert wins, loses, and creates traffic

Required outputs:

- table of single-expert geomeans
- per-trace winner table
- traffic vs usefulness scatter
- short interpretation memo

### Phase C. Build the pair complementarity map

Goals:

- evaluate plausible pairs from the expert pool
- understand whether coordination has room to matter

Required outputs:

- pair matrix with single-expert disagreement and win-region overlap
- offline pair oracle references, clearly labeled as offline aids
- promoted pair shortlist

### Phase D. Evaluate multiple serious hand-designed families

This is the core of Stage 1.

The current weak rule is one family candidate. It is far from enough.

Evaluate at least three strong hand-designed families from the set below. More is fine if the study stays clean.

#### Family 1. Safe fallback family

Motivation:

- current failure heavily involves `both off`
- low confidence should map to a safe incumbent choice more often than to an empty epoch

Design idea:

- keep a default incumbent expert or incumbent pair mode
- use low-confidence epochs to fall back to the incumbent rather than to zero action mass

#### Family 2. Sticky winner family

Motivation:

- prefetch phases often persist for multiple epochs
- pure last-epoch decisions can flip too easily

Design idea:

- winner-take-all with hysteresis, dwell time, or confidence margins
- keep the current winner until evidence for a switch is meaningful

#### Family 3. Gated both-on family

Motivation:

- some pairs help when both experts run, but naïve equal split wastes traffic

Design idea:

- one expert acts as the default owner of the budget
- the second expert enters only under strong evidence or available slack

#### Family 4. Budget mixer family

Motivation:

- some pairs may need continuous budget shifts rather than pure winner-take-all behavior

Design idea:

- positive budget floors and ceilings
- shared budget allocation based on smoothed evidence
- uncertainty maps to a conservative split or incumbent fallback

#### Family 5. Conservative-off family

Motivation:

- off can be valuable on truly harmful phases
- current rule uses off far too freely

Design idea:

- require sustained evidence of harm before off becomes available
- off is a guarded action, not the default uncertainty action

#### Family 6. Level pivot family

Motivation:

- the current L2 battleground may be the wrong battleground

Design idea:

- only after the cache-level memo supports it, repeat the family search at LLC with a similarly compact coordination surface

For each family, vary a small set of meaningful choices.

Good starting choices include these.

- epoch length
- fallback policy
- allowance or removal of `both off`
- allowance or removal of `both on`
- smoothing window or hysteresis length
- traffic budget scale
- budget floor and ceiling per expert

### Phase E. Mechanism diagnosis

For the strongest families, inspect real epoch traces.

Required checks:

- at least two clear win traces
- at least two clear loss traces
- one trace where the current weak rule failed due to `both off`
- one trace where the selected new family behaves differently in a meaningful way

Write down what the family seems to learn.

Good mechanism questions:

- When does the family switch experts
- When does it share budget
- When does it decline to prefetch
- Which traces still punish coordination
- Whether the main failure is pair choice, state quality, action design, or timing

### Phase F. Freeze the Stage 2 seed

Freeze one main family and optionally one backup family.

The chosen family should be the best combination of performance, robustness, clarity, and OpenEvolvability.

Required outputs:

- frozen family memo
- frozen config surface
- frozen evaluator plan for Stage 2

---

## 9. What to try next

These are the leading hypotheses suggested by the current artifact.

### Hypothesis A. Pair choice matters more than the current report lets it matter

Reason:

- `MLOP + SMS` moved much closer to parity than `Pythia + SPP+PPF`

Action:

- screen pair choice on development data first
- do not let the original pair keep default status without earning it

### Hypothesis B. The current off policy is the dominant structural bug

Reason:

- current logic turns low scores into `both off`
- epoch diagnostics show heavy off-rates on important traces

Action:

- test families where uncertainty maps to a safe fallback
- keep off as a guarded action that requires sustained evidence of harm

### Hypothesis C. The current score proxy is too weak

Reason:

- `useful / retired instructions` can dilute the signal severely
- traffic share penalizes one expert only relative to the other expert, which can miss real system cost

Action:

- test richer yet still local proxies such as usefulness relative to misses, rolling per-expert reward, bandwidth or queue pressure when available, and lagged demand-side benefit proxies

### Hypothesis D. Structural action choices matter more than tiny weight tuning

Reason:

- current failure appears to come from fallback behavior and action semantics more than from one bad scalar weight

Action:

- search across family structure before fine weight tuning

### Hypothesis E. L2 may still be right, but it needs the right pair and family

Reason:

- the repo already has working L2 plumbing and strong L2 experts

Action:

- give L2 a serious pair and family search before any major pivot

### Hypothesis F. LLC deserves an explicit feasibility pass

Reason:

- LLC prefetchers exist locally, and level choice can change the traffic and pollution tradeoff

Action:

- inspect local code support early, then either justify the pivot or close it decisively

---

## 10. Patterns that corrupt the science

Keep this list visible.

### Leakage and selection mistakes

- A test split reused for design selection is a development split.
- A pair chosen after held-out inspection is a development-chosen pair.
- A final claim needs a clean boundary.

### Weak comparators

- A headline built only on no-prefetch wins is weak for this project.
- The main scientific comparator is the best constituent single expert for the chosen family and level.

### Structural gaming

- A policy that meets the accuracy floor by issuing very little prefetch traffic while losing IPC is a weak policy.
- A policy that wins only by zeroing out action on prefetch-friendly traces is a weak policy.
- A policy that collapses to one expert should be described honestly as “a learned single-expert selector” if that is what it became.

### Offline leakage into online policy

- The online controller may use only features available at the epoch boundary.
- Offline or future-epoch oracle information belongs only in analysis, never in policy execution.

### Evaluation drift

- Mixed simulator revisions weaken comparisons.
- Mixed metric definitions weaken comparisons.
- Mixed warmup and simulation windows weaken comparisons.

### Reporting shortcuts

- Cherry-picked traces weaken the paper.
- Generated report prose weakens the paper.
- Unlogged manual interventions weaken the paper.

---


## 10A. Simple manual sweeps before large redesign

Run a bounded manual sweep before you widen the architecture.

This sweep answers a sharp question. Is the current failure mostly a settings failure, or does it survive across sensible settings and point toward a deeper family or level problem?

Use a small development subset first, then confirm on the broader development side.

Recommended first sweep axes:

- epoch length in a small set such as `100k`, `500k`, `1M`
- total budget scale, for example `0.5x`, `1x`, `2x` of the current default
- usefulness floor in a small set such as `20`, `30`, `40`
- off policy as `guarded off` versus `off unavailable`
- fallback policy as `incumbent`, `winner`, or `conservative split`
- sticky duration or hysteresis length
- minimum budget floor per expert when both are active

Good outcomes from this sweep:

- a clear sign that pair choice dominates
- a clear sign that off policy dominates
- a clear sign that the current family still loses across reasonable settings
- a clear sign that one simple family already deserves promotion

Document the result of this sweep in the research log before you expand the search space.

## 11. Proof of correctness uses real artifacts

This project values correctness and completion proven by real runs.

Unit tests can exist when they are cheap and useful. They are auxiliary evidence. They are not the main proof.

Use these real checks.

### For simulator or router changes

- build the simulator
- run real traces
- inspect raw outputs
- inspect epoch traces on at least one targeted case
- confirm the new action logic actually changes action patterns

### For dataset or parser changes

- rebuild the processed dataset from raw artifacts only
- manually audit selected rows against raw outputs
- regenerate figures and tables from the rebuilt dataset

### For split or protocol changes

- show the split file
- show no overlap between grouped train and test sides
- record a hash of the frozen split artifact

### For completion claims

Completion evidence means all of these exist.

- reproducible commands
- raw artifacts
- processed dataset
- figures and tables rebuilt from the dataset
- manual interpretation notes
- report outline and draft prose

---

## 12. OpenEvolve preparation starts in Stage 1

Design the chosen family so Stage 2 can optimize it cleanly.

### The evolvable artifact should be small

Aim for a small policy surface.

Good examples:

- a small router policy function
- a small set of thresholds and weights
- a small action-selection rule
- a compact budget-allocation rule

### The evolvable artifact should be isolated

Keep the policy logic separate from these.

- parser and dataset code
- figure generation code
- split files
- evaluator bookkeeping

### The evolvable artifact should be deterministic

A fixed code revision and fixed seed should reproduce the same metrics.

### The evolvable artifact should expose meaningful knobs

Good knobs include these.

- epoch length
- smoothing or hysteresis length
- fallback action and margin
- budget floors and ceilings
- off gating thresholds
- both-on gating thresholds
- score weights that still match the science

### The evolvable artifact should fail safely

A bad candidate should still compile or fail loudly. It should not silently poison the dataset.

---

## 13. Required documents and artifacts

Produce all of these.

### Core operational docs

- updated `docs/operational/experiment_setup.md`
- updated `docs/operational/dataset_schema.md`
- updated `docs/operational/research_log.md`
- updated `docs/operational/transparency_log.md`

### Decision memos

Create a small `docs/decisions/` directory if it does not exist.

Required memos:

- `cache_level_choice.md`
- `expert_pool_choice.md`
- `pair_selection.md`
- `family_selection.md`
- `stage2_seed_freeze.md`

### Dataset artifacts

- raw manifests and raw logs
- processed dataset with one row per run
- split artifacts and hashes
- any pair-screening or family-screening summary tables

### Figure set

At minimum, prepare figures or tables for these questions.

- Which single experts win where
- Which pairs have room for coordination
- How the hand-designed families compare
- How traffic and usefulness trade off
- What the selected family does on real traces
- Where the selected family still fails

---

## 14. Report obligations

The report is a major output of the project.

Write the report manually.

Use code to generate these.

- figures
- tables
- numeric summaries

Write these by hand.

- section text
- captions
- claims
- limitations
- threat discussion
- conclusion

### The report should tell this story

1. Current weak baseline and why it matters
2. Clean evaluation protocol and split discipline
3. Single-expert and pair complementarity map
4. Family search in Stage 1
5. Chosen mainline family and why it deserves Stage 2
6. What remains hard
7. What Stage 2 will optimize

### The report should include these concrete sections

- problem statement and motivation
- local simulator and protocol setup
- baseline single experts and strong comparators
- pair or level selection rationale
- hand-designed family search and selected family
- current performance summary with the right comparator hierarchy
- mechanism case studies from epoch traces
- limitations and threats to validity
- reproducibility appendix with commands, configs, and artifact flow

### Report honesty rules

- label exploratory evidence as exploratory
- label offline oracles as offline oracles
- label contaminated held-out usage honestly
- describe a method that collapses to one expert as such
- keep the strongest comparator visible in the main text

---

## 15. Reasoning transparency log

Maintain a concise public reasoning ledger.

The point is simple. A future reader should be able to see what changed your mind and what update they should make from the new evidence.

Each entry should start with a short takeaway.

Use this template.

```markdown
### <ISO date> — <decision>
Takeaway: <2 to 4 sentences with the answer and why it matters>

- Question: <what needed deciding>
- Options considered: <short list>
- Choice: <the chosen path>
- Why this choice currently wins: <key reasons>
- Evidence type: direct measurement | grouped validation trend | local code inspection | literature support | hypothesis
- Confidence: low | medium | high
- Main risk or inadequacy: <what could still break this>
- What changed your mind: <new evidence>
- AI assistance: <what the agent contributed>
- File pointers: <exact files, tables, commands>
```

Keep the log short, current, and useful.

---

## 16. Online facts to fetch once and vendor locally

Coding agents often have weaker internet access than humans.

Fetch and vendor the small number of internet-dependent facts that matter.

Examples:

- Athena release or commit reference used for the local copy
- OpenEvolve version and install mode you plan to use
- external trace bundle DOI or source path
- any external prefetcher module source you actually integrate
- paper citation details that the report needs

Record these facts in local docs so later work does not depend on fresh browsing.

---

## 17. Final instruction

Your job in Stage 1 is to choose a serious battleground.

The current weak `MoPLite` rule already taught the project something. Use that lesson. Screen the right pairs, choose the right level, test stronger hand-designed families, freeze a clean protocol, and hand Stage 2 a candidate that deserves optimization time.
