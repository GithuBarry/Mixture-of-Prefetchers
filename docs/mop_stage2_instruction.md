# Prompt Document B
# MoP-lite Stage 2 Charter
# OpenEvolve Optimization, Final Dataset, Transparent Reasoning, and Manual Report

You are the research engineer for the second phase of a scaled-down real systems research project.

Your job is to take a **frozen, working MoP-lite baseline** and optimize it with **OpenEvolve**. Your output is more than a better score. Your output is a credible optimization study, a trustworthy final dataset, a transparent reasoning record, and a manually written final report that explains both **what improved** and **why**.

This document defines **goals, evidence, and guardrails**. You choose the local abstractions, file layout, and implementation details.

A candidate that compiles or even wins on a few search traces marks progress. **Completion means the full deliverable set in this document.**

---

## 1. Mission

Starting from a stable MoP-lite baseline, use OpenEvolve to optimize the router policy under explicit performance and traffic goals.

The scientific question for this phase is:

**Given a small realistic epoch-based router interface for coordinating two L2 prefetcher experts, what policy structure and parameter choices improve IPC under explicit traffic and usefulness constraints, and what design insights emerge from that search?**

This phase should support a final report that explains **what the learned policy does**, **why it helps or hurts**, and **how much trust readers should place in the result**.

---

## 2. How to think about this phase as an academic project

Treat OpenEvolve as a tool for structured scientific search, not as a magic source of wins.

Use these norms throughout the phase.

- Freeze the question before you widen the search.
- Preserve the strongest fair baselines from stage 1.
- Keep every optimized degree of freedom visible and interpretable.
- Distinguish clearly between search-time signals and final claims.
- Prefer robust held-out gains and strong mechanism stories.
- Let the report explain why the winning policy wins.
- Treat null results, overfitting, and brittleness as publishable evidence when they are diagnosed clearly.
- Treat the dataset and the final report as first-class outputs from day one.

A good stage 2 result is a disciplined optimization study with a clear story, even when the headline gain is modest.

---

## 3. Public facts and assumptions you should treat as the current default

Use these as the working snapshot unless local evidence forces an adjustment.

- Athena already supports multiple L2C prefetchers and coordination mechanisms.
- Stage 1 should already expose a compact router interface with per-epoch state and actions.
- OpenEvolve works around an **initial program**, an **evaluator**, and a **configuration**.
- OpenEvolve supports deterministic seeding and experiment logging.
- Athena public materials describe artifact-scale runs that are too expensive for the inner loop of search.
- A staged evaluation design is therefore part of the intended methodology.
- The final comparison set should include the strongest single-prefetcher baseline and the strongest simple MoP-lite heuristics from stage 1.

If the local toolchain diverges from the public materials, document the divergence and adapt while preserving the scientific intent.

### Local-first discovery checklist for low-internet environments

When internet access is weak, start from the local repo and local artifacts. Look first for:

- the top-level README and any artifact README files
- configuration directories and example configs
- experiment or script directories that launch batches and summarize outputs
- existing figures, CSV summaries, or result manifests
- included papers, slides, notes, or appendices that explain the framework
- comments near the relevant L2C prefetcher and coordination code paths

Record every repo fact you rely on in your research log so later reasoning does not depend on memory.

---

## 4. Freeze line

Begin stage 2 by freezing the following items.

### Frozen items

- simulator stack and core machine configuration
- trace split definition
- parser and dataset schema
- definition of useful prefetch and traffic overhead
- set of allowed router observations
- set of allowed router actions
- evaluation metric family
- stage 1 baselines used for comparison

### Tunable items

Expose only a compact and well-justified set of router choices to optimization.

Examples:

- epoch length
- total budget
- per-expert aggressiveness caps
- score weights
- threshold values
- expert enablement rules
- small discrete allocation rules

The optimizer should search over the router policy. It should not turn the project into a different simulator study.

---

## 5. Optimization target

The primary target remains:

- **geomean IPC on held-out traces relative to the strongest single-prefetcher baseline**

under constraints such as:

- **traffic overhead cap**, with **20 percent** as the default cap
- **usefulness or accuracy floor**, with **30 percent** as the default floor

This phase adds a second target:

- **interpretability of the learned policy**

A slightly smaller improvement with a compact, understandable policy is often more valuable than a larger but brittle one.

---

## 6. Search surface guidance

Start small and discrete. Expand only after the loop is stable.

### Good initial knob set

- epoch length in `{100k, 500k, 1M}` committed instructions
- total budget in `{16, 32, 64}` prefetches per epoch or the nearest equivalent exposed control
- per-expert aggressiveness cap in `{1, 2, 4, 8}`
- accuracy floor in `{0.2, 0.3, 0.4}`
- score weights in `{0, 0.5, 1, 2}`
- optional binary flag for whether both experts can be active in the same epoch

### Pair-selection guidance

Use one of these two strategies and label it clearly.

**Preferred strategy**

- Freeze one or two expert pairs based on stage 1 complementarity evidence
- Optimize the router within those pairs

**Secondary strategy**

- Include expert-pair choice as a discrete optimization dimension when compute budget allows
- Keep pair selection visible in the analysis because it mixes architectural design choice with router tuning

### Policy representation guidance

A good default is a small rule-based router with a score such as:

`score = w1 * accuracy + w2 * coverage_proxy - w3 * traffic_proxy`

and actions such as:

- choose expert A only
- choose expert B only
- choose both with a budget split
- raise or lower aggressiveness under a shared budget

This style keeps the evolved artifact small, auditable, and close to the project motivation.

---

## 7. Evaluation pipeline

Build a staged evaluator so search is affordable and final claims are strong.

### Stage 0: static and smoke validation

Every candidate should pass:

- build or syntax checks
- configuration validation
- one or two short smoke traces
- basic metric sanity checks

### Stage 1: fast screening

Evaluate on:

- a small training subset
- short simulation lengths
- the full objective and constraints

Use this stage to discard obviously weak policies quickly.

### Stage 2: stronger training evaluation

Evaluate promising candidates on:

- a broader training set
- longer runs
- the full objective

### Stage 3: validation gate

Evaluate the strongest candidates on:

- validation traces or training-side resampling when using a two-way split
- final search-mode lengths or near-final lengths

### Stage 4: final held-out test

Run the chosen policy on:

- the held-out test set
- the strongest evaluation lengths you can afford
- the exact same protocol used for baseline comparisons

The final report should lead with Stage 4, not with inner-loop search wins.

---

## 8. Objective design

Use an objective that reflects both value and cost.

A strong default is:

`fitness = geomean_IPC - lambda * traffic_overhead - mu * max(0, floor - accuracy)`

with an additional strong penalty for traffic-cap violations.

Design principles:

- reward true end performance
- penalize excess traffic consistently
- penalize usefulness collapse consistently
- keep the objective smooth enough for search to learn from it
- keep the final report focused on held-out IPC, traffic, and usefulness rather than only on the internal fitness value

---

## 9. Deliverables

You are done when the deliverables below are complete and coherent.

### A. Frozen stage 1 snapshot

Deliver a frozen reference point for the optimization study.

Required evidence:

- a code revision or branch that captures the frozen baseline
- a note that lists exactly what is frozen
- a small reproduction command that reruns a representative baseline case

### B. OpenEvolve integration

Build a clean optimization loop around the frozen baseline.

Required components:

- an initial program representing the current router policy
- an evaluator that compiles or runs the candidate and returns structured metrics
- a configuration file with seeds and budget settings
- artifact logging for failures and metric traces

Practical expectations:

- keep the evaluator deterministic for a fixed code revision and seed
- cache expensive invariant work only when correctness stays intact
- record every evaluated candidate with code hash, config, and metrics
- preserve the best few candidates, not only the best one
- maintain a reasoning note for any manual intervention, search-space change, or evaluator change

### C. Search ledger and parsed dataset

Create a dataset that supports re-analysis.

Required contents:

- raw search logs
- candidate ledger with candidate identity, code hash, seed, config, score, and component metrics
- parsed run-level dataset for final experiments
- split files
- configuration files for optimization and final evaluation
- code revision mapping
- figure-generation scripts
- manually written notes that map figures to claims

### D. Transparent reasoning log

Maintain a **reasoning transparency log** throughout optimization.

This is a concise public reasoning ledger, not a raw internal stream. The goal is epistemic legibility.

For every important search decision, record:

- the key takeaway in two or three sentences at the top
- the most important considerations behind the choice
- your confidence in the main interpretation
- the support type for each main claim, such as direct measurement, validation trend, proxy, literature support, or hypothesis
- the shortcuts or approximations taken
- the main inadequacies or open risks
- how the new evidence changed your view
- what a skeptical reader should update on
- the extent and type of AI assistance used for code, analysis, and writing

This log should make the optimization trace understandable to an advisor, reviewer, or future labmate.

### E. Manual final report

Treat the report as a core artifact.

Required writing workflow:

- maintain a **human-authored research log** after every experiment batch
- maintain the reasoning transparency log beside it
- write report prose manually
- use scripts to generate plots, tables, and CSV summaries
- write the abstract, introduction, method narrative, captions, discussion, limitations, and conclusion manually

Required report outputs:

- a complete final report draft in Markdown, LaTeX, or another plain-text authoring format
- one-sentence takeaway notes for every figure and table
- a claims-to-evidence map for the main results
- a brief AI-use disclosure note in the report or appendix

---

## 10. Real completion checks over synthetic tests

This phase values proof through real runs, real search artifacts, and real analysis products.

Lightweight tests are optional and narrow. They are useful for small utilities. The main proof of correctness and completion should come from **end-to-end artifacts** such as:

- a real evaluator run on the frozen baseline
- a real candidate ledger with scores and metadata
- a real reproduced score for the same candidate under the same seed
- a real comparison table against stage 1 baselines
- a real held-out evaluation for the final selected policy
- a real figure that explains why the evolved policy helps or hurts
- a real report section that interprets the evidence

When you claim a milestone is complete, attach the strongest real artifact that demonstrates it.

---

## 11. Success criteria

Use this success ladder.

### Core success

Core success means the optimization workflow itself is solid.

Requirements:

- the stage 1 baseline is frozen and reproducible
- OpenEvolve can evaluate the router end to end
- the evaluator is deterministic within an agreed tolerance
- the search produces multiple valid candidate policies
- all candidates are logged with enough metadata to reproduce them
- final comparisons include strong baselines from stage 1
- the manual report foundation exists and reflects actual findings
- the reasoning transparency log exists and reflects actual reasoning, not after-the-fact storytelling

### Strong success

Strong success means optimization delivers a credible improvement or a clear insight.

Examples:

- the evolved router beats the best simple MoP-lite heuristic on held-out traces
- the evolved router improves over the strongest single-prefetcher baseline while satisfying the constraints
- the evolved router reveals a compact policy rule that generalizes better than hand tuning
- the optimization exposes a meaningful tradeoff frontier between IPC and traffic

### Publication-quality success

Publication-quality success deepens the story.

Examples:

- robust gains across benchmark families
- a clear interpretation of why the evolved router behaves as it does
- pair-specific insights about expert complementarity
- constraint sensitivity studies that change the selected policy in an interpretable way
- evidence that a compact router approaches the value of much more complex coordination

A strong stage 2 is already valuable when it reveals overfitting pressure, limited headroom, or the true shape of the coordination tradeoff.

---

## 12. Decisions that should be made empirically, and the philosophy for making them

Some decisions should follow from evidence inside the optimization study. Use the following philosophy.

### Search space size

Choose the smallest search space that still captures the meaningful policy degrees of freedom.

### Candidate advancement

Promote candidates based on consistent gains and clean constraint behavior, not only on raw score.

### Sim budget allocation

Spend compute where it changes confidence most. Fast screening helps breadth. Final-mode reevaluation creates trust.

### Interpretation priority

Prefer robust held-out gains, cleaner mechanism stories, lower traffic, and simpler policies over fragile training peaks.

### Final candidate choice

Choose the candidate that gives the strongest held-out scientific story under the frozen protocol. That story can center on performance, efficiency, interpretability, or diagnosed limits.

---

## 13. Integrity rules

These rules protect the optimization study.

### Reasoning transparency

- Open important memos and report sections with the key takeaways
- Mark which considerations carried the most weight
- State confidence and support type for major claims
- Expose shortcuts, unresolved uncertainties, and major inadequacies
- Keep source pointers precise enough that another reader can inspect the evidence
- Disclose the extent of AI use in code, analysis, and writing artifacts

### Frozen evaluation protocol

- Once optimization begins, the core evaluation protocol stays fixed
- Any later changes should be labeled as a new experiment tier

### Held-out isolation

- Held-out traces remain untouched until the final candidate is selected
- Validation is where model selection happens

### Deterministic scoring

- The same candidate under the same binary, inputs, and seed should produce the same evaluator result within a small tolerance

### Honest ablations

- When a new policy wins, compare it against the right near neighbors
- Good near neighbors include the same expert pair with simpler rules, the same rules with fixed weights, or the same weights with different caps

### Reporting integrity

- Keep all completed runs, including failures and negative outliers, in the raw dataset
- Use explicit filters with written justification
- Report geomean and per-trace behavior together
- Keep the final report manual and evidence-driven

---

## 14. Forbidden shortcuts and failure modes

These patterns undermine the science.

### Test-set steering

Choosing the final candidate after repeated held-out inspection weakens generalization.

### Search-space inflation without justification

A huge unconstrained search space often produces fragile results and weak interpretation.

### Evaluator leakage

Any evaluator feature that lets the candidate use future information inside the simulated policy compromises realism.

### Binary drift across candidates

Changing unrelated simulator code during optimization muddies attribution. Freeze the simulator outside the router surface.

### Metric cherry-picking

Selecting whichever metric looks best after search weakens the report. Predefine the key metrics and report them consistently.

### Candidate resurrection through manual patching

Manual edits after search can be useful as a separate engineering branch. Keep them clearly separate and report them honestly.

### Hidden failure filtering

Failed builds and crashed candidates are informative. Keep records of them. Report the selection policy for which candidates advance to later stages.

### Script-written paper

A paper with auto-generated prose usually loses the research story. Plots and tables can come from scripts. The narrative, captions, limitations, and takeaways should be written manually.

---

## 15. What to analyze and write in the final report

The report should explain both performance and mechanism.

### Required quantitative views

1. Overall held-out IPC relative to no-prefetch, strongest single-prefetcher, and strongest simple router
2. Per-trace win and loss plot
3. Traffic overhead and usefulness for every compared method
4. Accuracy versus traffic or IPC versus traffic frontier
5. Ablation of evolved policy components
6. Sensitivity to traffic cap and epoch length
7. Expert-pair analysis when more than one pair was studied

### Required qualitative discussion

Address these questions explicitly.

- Which signals ended up mattering most
- Which expert pairings were easiest to coordinate
- When the evolved policy chose one expert versus both
- How the constraints shaped the policy
- Why some traces remain negative outliers
- What part of the gain came from selection and what part came from aggressiveness control

### Report structure guidance

The final report should include:

- Abstract with the main quantitative claim and scope
- Introduction with motivation and hypothesis
- Background on prefetcher diversity and coordination
- Method with simulator setup, router interface, and optimization setup
- Results with held-out evaluation first
- Ablations and sensitivity studies
- Failure cases and limitations
- Reproducibility details
- Conclusion with concrete design insights

For every major section, keep a small reasoning-transparency layer in notes or appendix:

- what the section is trying to establish
- which pieces of evidence carry the most weight
- confidence in the main claims
- shortcuts or caveats that matter for interpretation
- what the reader should update on

Write the report manually. Use scripts for plots, tables, and data extraction. Use your own words for the research narrative, figure captions, limitations, and takeaways.

---

## 16. Expected output package

Your stage 2 handoff should contain:

1. Frozen baseline snapshot
2. OpenEvolve program, evaluator, and configuration
3. Search logs and candidate ledger
4. Best evolved router and a small set of strong runner-up policies
5. Final held-out evaluation outputs
6. Final parsed dataset and summary tables
7. Final figures and tables
8. A manually written research log
9. A manually written reasoning transparency log
10. A manually written final report draft grounded in the figures and tables
11. A concise memo that states the main contribution, the main limitation, and the most important next experiment

---

## 17. Final instruction

Use OpenEvolve as a disciplined optimizer for a real architecture study. Keep the search small, the protocol frozen, the baselines strong, the candidate history intact, the reasoning transparent, the conclusions honest, and the report manual.
