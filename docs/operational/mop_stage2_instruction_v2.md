# Prompt Document B
# Stage 2 OpenEvolve charter
# Optimize a serious frozen family, protect the science, and finish the paper

You are the research engineer for Stage 2 of a systems research project.

Stage 1 should leave behind a serious frozen seed family. Stage 2 uses OpenEvolve to improve that family under a clean protocol and to extract design insight from the search.

Your job is broader than “run OpenEvolve.” Your job is to produce a robust optimization study, a trustworthy candidate ledger, a real final dataset, a manual final report, and a strong scientific answer.

This document defines what gets frozen, what gets evolved, how to search, how to decide, what to avoid, and what the final paper must explain.

Completion means the full deliverable set in this document.

---

## 1. Read this first

OpenEvolve time is expensive. Spend it on a serious target.

Current local evidence already says three important things.

- The original `MoPLite` rule is a weak baseline on the default pair.
- Pair and family choice matter.
- Current failure is structural enough that pure weight twiddling is unlikely to be enough.

That means Stage 2 should optimize the **chosen Stage 1 family**, not blindly optimize the old weak rule in place.

If Stage 1 renamed the old rule to something like `MoPLite-v0` or `ScoreFloorRouter`, keep that discipline.

The main scientific question for Stage 2 is:

**Can a compact evolved coordinator beat the strongest constituent single expert under the frozen protocol, and what does the winning policy teach us about coordination at the chosen level?**

---

## 2. Mission

Use OpenEvolve to optimize a frozen, compact coordination family under explicit traffic and usefulness constraints.

The mission has five parts.

- Improve performance against the strongest constituent single expert under a clean development protocol.
- Preserve scientific integrity through a frozen evaluator and clean split discipline.
- Produce a compact and understandable evolved policy.
- Diagnose why search helps or stalls.
- Finish the final report with manually written narrative and evidence-backed claims.

---

## 3. What gets frozen before search begins

Freeze these items before any serious OpenEvolve run.

### Frozen scientific boundary

- chosen cache level
- chosen expert pool
- chosen mainline pair or tiny shortlist of stage-approved pairs
- chosen family or tiny shortlist of stage-approved families
- split protocol or grouped-resampling protocol
- warmup and simulation windows per mode
- metric definitions and dataset schema
- simulator revision
- baseline comparison set

### Frozen reporting boundary

- primary comparator hierarchy
- traffic cap definition
- usefulness or accuracy floor definition
- rules for final clean evaluation
- rules for contaminated evidence versus clean evidence

### Required freeze memo

Create or update:

- `docs/decisions/stage2_seed_freeze.md`

It should say exactly these.

- what is frozen
- what remains evolvable
- what evidence justified the freeze
- what would count as a protocol break

---

## 4. Clean evaluation discipline

### 4.1 The main comparator

For this project, the main optimization target is the best constituent single expert for the chosen family and level.

That is the hard comparator. Keep it primary.

Secondary comparators still matter.

- no-prefetch, for overall usefulness context
- the Stage 1 hand-designed seed
- the strongest prior coordinator baseline available under the same scope

### 4.2 Clean final evaluation

Use one of these paths.

#### Path A. Pristine held-out test exists

- all Stage 2 design decisions happen on training and validation data only
- held-out runs happen once for final confirmation
- the report leads with held-out results

#### Path B. No pristine held-out test remains

- use grouped cross-validation or repeated grouped train and validation splits
- report the distribution across grouped splits
- state clearly that the study lacks a pristine untouched test set

### 4.3 Search must respect the chosen path

A candidate that looked at the test side during search belongs to development. Label it that way.

---

## 5. What OpenEvolve should evolve

OpenEvolve works best when the editable artifact is small, meaningful, and well-constrained.

Use that design.

### The best default evolved artifact

Prefer evolving one compact policy module that maps epoch summary information to an action or budget allocation.

Good targets:

- score function structure
- smoothing or hysteresis rules
- fallback logic
- budget-allocation logic
- off gating and both-on gating rules
- threshold schedules
- small discrete action policies

### Good edit boundary

Keep these outside the editable surface.

- parser code
- dataset schema
- figure generation code
- split files
- report prose
- baseline metric extraction

### Policy input contract

The evolved policy may use only information available at the epoch boundary under the frozen protocol.

Good examples:

- previous-epoch per-expert usefulness and traffic counters
- rolling summaries of recent epochs
- queue or bandwidth proxies that are already part of the frozen measurement surface
- frozen system-level signals already emitted by the simulator

### Forbidden policy inputs

The evolved policy must never use these.

- trace name
- split identifier
- benchmark family label
- future epoch information
- offline oracle labels
- post-processed CSV summaries from other runs
- hand-entered benchmark-specific rules

### Action contract

Keep the action space compact.

Good examples:

- expert A only
- expert B only
- both with a controlled split
- guarded off action when the chosen family supports it

The evolved policy should stay simple enough that the final report can explain it.

---

## 6. Search shape

### 6.1 Start from more than one strong template

Current evidence suggests structural change matters.

Run OpenEvolve from a small set of serious Stage 1 templates, not from one weak template only.

Good template set:

- Stage 1 selected mainline family
- one backup family with a different fallback philosophy
- optionally the current weak `MoPLite-v0` only as a historical baseline seed

Each template should still obey the same frozen evaluator.

### 6.2 Keep the number of families small

OpenEvolve should search deeply inside a small serious space. It should not become a vague re-litigation of Stage 1.

A good default is one main family and one backup family.

### 6.3 Use diversity on policy behavior

OpenEvolve supports quality-diversity search. Use that strength.

Useful diversity dimensions for this problem include these.

- average off-rate
- average both-on rate
- average expert-0 budget share
- traffic-overhead bucket
- action entropy or switch rate
- complexity bucket, such as policy length or rule count

These dimensions help search explore meaningfully different coordinators instead of tiny variants of the same weak local optimum.

---


## 6A. Recommended first evolvable knob set

OpenEvolve should start from a compact knob set that matches the current failure modes.

Good first evolvable dimensions:

- family template identifier when Stage 2 allows two or three pre-approved templates
- epoch length when Stage 1 left it evolvable
- fallback mode
- off availability or off guard strength
- both-on availability or both-on guard strength
- sticky duration or hysteresis margin
- budget scale
- minimum and maximum budget share per expert
- score weights or other small scalar coefficients
- smoothing window length

Good second-wave dimensions after the search is stable:

- slightly richer score formulas
- small conditional rules
- small discrete allocation schedules

Poor first-wave dimensions:

- broad simulator rewrites
- parser changes
- metric-definition changes
- giant policy code surfaces

Search should first discover the right behavior class, then refine the settings inside that class.

## 7. Objective design

Use an objective that matches the science.

### Primary target

Primary target:

- geomean improvement versus the strongest constituent single expert on development data

### Secondary targets

Secondary targets:

- geomean versus no-prefetch
- traffic overhead
- usefulness or accuracy
- tail robustness across traces or grouped splits
- policy simplicity

### Good default fitness shape

A strong default fitness is a weighted combination of these terms.

- mean log-ratio versus constituent-best single on development data
- a smaller positive weight on mean log-ratio versus no-prefetch
- a strong penalty for traffic-cap violation
- a strong penalty for usefulness-floor violation
- a penalty for catastrophic per-trace slowdowns
- a modest penalty for pathological off-rate on traces where one constituent single is clearly helpful
- a modest complexity penalty

Keep the final report focused on the real metrics, not only on the internal fitness value.

### Why this matters

Optimizing only against no-prefetch invites easy wins and weak science. The main question here is coordination versus the best constituent single expert.

---

## 8. What to evolve first

Search should begin with the dimensions that current evidence says matter most.

### First-order structural choices

These deserve early search attention.

- uncertainty fallback rule
- whether `both off` is allowed and under what evidence
- both-on gating rule
- sticky winner or hysteresis behavior
- budget floor and ceiling behavior
- smoothing window length

### Second-order numerical choices

These matter after the structural choices are sensible.

- score weights
- threshold values
- margin values
- epoch length if Stage 1 left it evolvable
- small budget values or ratios

### Strong suggestion

If current failure came from `both off`, evolve safer fallback behavior before you spend large budget on fine weight tuning.

---

## 9. Staged evaluator design

Build a staged evaluator so search stays affordable and the final claim stays strong.

### Stage 0. Validity gate

Every candidate should pass these.

- syntax or compile check
- config validation
- one short smoke run
- basic metric sanity checks

### Stage 1. Cheap scout evaluation

Run on a small development subset with short windows.

Purpose:

- reject clearly bad candidates fast
- surface compile errors and constraint violations quickly

### Stage 2. Broader development evaluation

Run promising candidates on a broader development subset or grouped fold set.

Purpose:

- compare candidates on the real scientific objective
- collect per-trace and per-group behavior

### Stage 3. Robustness gate

Run finalists on stronger windows, more traces, or more grouped splits.

Purpose:

- reduce lucky winners
- expose catastrophic tails

### Stage 4. Final clean evaluation

Run the selected candidate once under the frozen final protocol.

Purpose:

- produce the headline table for the report

The final report should lead with Stage 4 when a pristine test exists.

---

## 10. OpenEvolve system message guidance

OpenEvolve documentation places heavy weight on the system message. Treat it as a research artifact.

Your system message should include these.

- the scientific question in one paragraph
- the primary comparator hierarchy
- the exact files or modules that the model may edit
- the frozen files and frozen definitions
- known failure modes from Stage 1
- the meaning of the main metrics
- traffic and usefulness constraints
- examples of good policy moves
- examples of weak policy patterns
- the requirement for simple, explainable changes
- the requirement to preserve determinism and artifact logging

Good system messages help the search stay in the science.

---

## 11. Artifact side-channel guidance

OpenEvolve supports artifact-driven iteration. Use it well.

Good artifacts to feed back into the search process:

- compile errors and warnings
- constraint-violation summaries
- per-trace outlier summaries
- small epoch-trace snippets from win and loss cases
- action-rate summaries such as off-rate and both-on rate
- comparisons to the current seed family

Bad artifacts:

- hand-written benchmark-specific advice that leaks the answer
- hidden references to the held-out test side
- post hoc editorial claims instead of raw evidence

---

## 12. Candidate ledger and real evidence

Every evaluated candidate must leave behind a clean record.

Required fields for the ledger include these.

- candidate identifier
- parent identifier or seed template
- code hash or diff hash
- config hash
- seed
- stage of evaluation reached
- score and component metrics
- per-trace metrics where available
- constraint status
- artifact paths
- promotion or rejection reason

The ledger should support later analysis of what the search actually explored.

---

## 13. Real-artifact correctness checks

This project values correctness proven by real runs.

Unit tests can help. Real artifacts remain the main proof.

### For promoted candidates

Require all of these before promotion to the next stage.

- real compile or run success
- raw metrics saved
- parsed metrics saved
- one manual spot check against raw output
- one manual mechanism check from epoch traces on a targeted trace

### For the final candidate

Require all of these.

- rerun from scratch under the frozen final protocol
- deterministic reproduction check when applicable
- dataset rebuild from raw artifacts only
- figure and table regeneration from the rebuilt dataset
- manual interpretation memo with wins, losses, and remaining risks

---

## 14. Patterns that weaken Stage 2

Keep this list visible.

### Protocol drift

- changing split rules during search
- changing metric definitions during search
- changing warmup or simulation windows without a freeze update
- silently switching simulator revision

### Objective mistakes

- optimizing against no-prefetch only
- ignoring catastrophic tails while chasing geomean
- rewarding low traffic alone even when IPC collapses

### Search-space mistakes

- evolving the parser or evaluator instead of the policy
- letting the editable surface get too large
- optimizing a weak template only because it was already there
- overusing manual interventions without a log

### Leakage

- candidate behavior keyed on trace identity or split identity
- using held-out data during candidate selection
- benchmark-specific rules disguised as generic logic

### Reporting shortcuts

- selecting one lucky seed as the final story
- hiding failed families or failed candidate clusters
- generating the report automatically from the dataset

---

## 15. Stage 2 success criteria

Use these to decide whether Stage 2 succeeded.

### Minimum success

- best evolved candidate improves on the Stage 1 seed under the main comparator on development data
- the improvement survives the robustness gate
- the candidate respects the declared traffic and usefulness constraints
- the policy remains simple enough to explain

### Strong success

When a clean held-out test exists:

- final candidate reaches `> 1.00` geomean vs the strongest constituent single expert on the clean test side
- final candidate stays within the declared traffic cap and usefulness floor
- final candidate’s mechanism can be explained from real traces

When the study uses grouped resampling instead of a pristine held-out test:

- final candidate shows consistent `> 1.00` or clear near-parity across grouped splits
- variance and tail behavior are reported honestly
- the report makes the evidence boundary explicit

### Valuable negative result

A negative result remains valuable when all of these are true.

- the search space was serious and well-justified
- the evaluation was clean
- the strongest families still fail to beat the constituent-best single expert
- the report explains why, with mechanism evidence

---

## 16. Required outputs

Produce all of these.

### OpenEvolve artifacts

- initial program or seed template files
- evaluator file
- config files
- system message text
- candidate ledger
- raw search logs
- artifact directories for promoted candidates

### Frozen final artifacts

- final chosen policy
- full final-run raw artifacts
- processed final dataset
- regenerated figures and tables
- freeze memo update if needed

### Analysis documents

- search summary memo
- top-candidate comparison memo
- mechanism case-study memo
- limitations memo
- updated transparency log

---

## 17. Final report obligations

The final report is a core output of Stage 2.

Write the report manually.

Use code to generate these.

- figures
- tables
- numeric summaries

Write these by hand.

- section prose
- claim wording
- captions
- discussion
- limitations
- conclusion

### The report should tell this story

1. Why the initial baseline was weak
2. What Stage 1 froze and why
3. What Stage 2 evolved and why those degrees of freedom mattered
4. How the search was evaluated
5. What the best evolved policy achieved
6. What the search taught us about coordination
7. Where the method still fails
8. How much confidence the reader should place in the result

### Report sections to prepare

- final problem framing and contribution
- frozen protocol and search boundary
- evolved policy family and objective design
- search process summary
- final performance tables under the right comparator hierarchy
- mechanism analysis from epoch traces
- ablations or family comparisons that support the explanation
- limitations and threats to validity
- reproducibility appendix with commands, configs, and artifact flow

### Report honesty rules

- state whether the test side was pristine or development-contaminated
- keep the strongest constituent single expert visible in the main comparison table
- include failed families or failed search themes in brief form
- separate exploratory evidence from claim-grade evidence

---

## 18. Reasoning transparency log

Maintain a concise public reasoning ledger during Stage 2.

The goal is simple. A skeptical reader should be able to see what changed your mind, how much confidence to place in the update, and what still looks fragile.

Use this template.

```markdown
### <ISO date> — <decision or update>
Takeaway: <2 to 4 sentences with the answer and why it matters>

- Question: <what was being decided>
- Choice: <current answer>
- Evidence type: direct measurement | grouped validation trend | local code inspection | hypothesis | literature support
- Confidence: low | medium | high
- Main supporting facts: <short list>
- Main inadequacy or risk: <short list>
- What changed your mind: <new evidence>
- AI assistance: <what the agent contributed>
- File pointers: <exact files, tables, commands>
```

Keep the log useful. Each entry should tell the next reader what update to make.

---

## 19. Online facts to fetch once and vendor locally

Coding agents often have weaker internet access than humans.

Fetch and vendor the few internet-dependent facts that Stage 2 really needs.

Examples:

- OpenEvolve version and install path
- any provider-specific config details you rely on
- Athena commit or release reference for the simulator snapshot
- citation details for the final report

Record these facts in local docs or config comments so the workflow stays local after setup.

---

## 20. Final instruction

Stage 2 is not a license to wander.

Freeze a serious family, evolve the policy surface that matters, optimize against the right comparator, protect the evaluation boundary, and finish with a final report that explains both the number and the mechanism.
