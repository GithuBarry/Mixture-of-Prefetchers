# Prompt Document A
# MoP-lite Stage 1 Charter
# Baseline Design, Implementation, Dataset, and Manual Report Foundation

You are the research engineer for the first phase of a scaled-down real systems research project.

Your job is to build a **scientifically credible baseline** for **Mixture-of-Prefetchers Lite (MoP-lite)**, a lightweight L2 prefetcher coordinator inside Athena or ChampSim. Your output is more than working code. Your output is a trustworthy implementation, a trustworthy dataset, a transparent reasoning record, and the backbone of a good final report.

This document defines **goals, evidence, and guardrails**. You choose the local abstractions, file layout, and implementation details.

A code patch, a passing build, or a few promising runs mark progress. **Completion means the full deliverable set in this document.**

---

## 1. Mission

Build a baseline coordination mechanism at the **L2 cache** that coordinates **exactly two L2 prefetcher experts per run** using **epoch-level routing** and **explicit traffic and usefulness constraints**.

The scientific question for this phase is:

**Can a small epoch-based manager that composes two strong L2 prefetchers beat the strongest single-prefetcher baseline under explicit traffic and usefulness constraints, while staying simple enough for systematic optimization and clear scientific analysis later?**

Your work in this phase should make that question answerable.

---

## 2. How to think about this project

Work like a paper author, not only like a coder.

Use these norms throughout the project.

- Start from the scientific claim and let the code serve it.
- Keep the contribution centered on one crisp question about **L2 prefetcher coordination**.
- Treat strong baselines as part of the contribution.
- Preserve negative results because they often explain the mechanism.
- Write down the interpretation of each experiment while context is fresh.
- Favor narrow, understandable design moves over broad refactors with blurry causal stories.
- Ask of each feature, metric, and ablation, **what scientific question does this answer**.
- Treat the dataset and the final report as first-class outputs from day one.

A good stage 1 result is a strong baseline and a clean scientific story, even when the absolute gains are modest.

---

## 3. Public facts and assumptions you should treat as the current default

Use these as the working snapshot unless local evidence forces an adjustment.

- Athena is built on ChampSim.
- Athena already includes multiple L2C prefetchers such as **Pythia, SPP+PPF, MLOP, and SMS**.
- Athena already includes **epoch-based coordination ideas** and experiment scripts.
- ChampSim is **trace-based** and uses fixed warmup and simulation instruction windows.
- Athena public materials include artifact-style experiment scripts, aggregated CSV outputs, and a larger trace collection than this course project needs.
- Athena public materials support experiments that coordinate multiple prefetchers at L2C with OCP disabled.
- OpenEvolve comes later. Stage 1 should already expose a **small and optimization-friendly router surface**.

If the local repo diverges from the public materials, document the divergence and adapt while preserving the scientific intent.

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

## 4. Scope lock

Keep the project sharply scoped.

### Mainline scope

- One simulator stack
- One coordination point, which is **L2C**
- One machine configuration held fixed across comparisons
- One decision cadence, which is **epoch based**
- Exactly **two experts per MoP-lite run**
- One router that can select experts and control aggressiveness
- Explicit measurement of performance, traffic, and usefulness
- Default **single-core** mode
- Default **OCP disabled**

### Mainline simplifications

Treat these as part of the intended design, not as missing features.

- Use **epoch-level routing** rather than per-access routing.
- Use **gating, degree scaling, a shared budget, or a combination** as the main coordination actions.
- Keep **cross-expert candidate merge and dedup** outside the mainline implementation unless it becomes almost free after the core system is done.
- Keep the hardware story compact, with counters and thresholds that fit comfortably inside a small hardware budget.

### Stretch scope

Only touch these after the mainline result is stable.

- Re-enable OCP and study interaction.
- Add IPCP if public modules integrate cleanly.
- Extend to multicore.
- Explore three experts.
- Explore deeper candidate merge or dedup.

---

## 5. What MoP-lite means in this project

MoP-lite is a **policy composition manager** over two existing L2 prefetcher experts.

The router acts once per epoch. It reads summary signals for each expert and the system. It chooses which experts are enabled and how aggressive each expert should be during the next epoch. The implementation may use hard gating, degree scaling, a shared traffic budget, or a simple combination of these.

The key contribution in stage 1 is a **clean coordination interface and credible baseline evidence**.

---

## 6. Deliverables

You are done when the deliverables below are complete and coherent.

### A. Runnable baseline environment

Deliver a clean, repeatable environment for building and running the simulator.

Required evidence:

- Build instructions that work on the actual target environment
- A short environment note with compiler, Python, and dependency versions actually used
- A smoke-run command that reaches completion on a short trace
- A note on any Athena-specific setup that matters for local or cluster execution

### B. Baseline experiment matrix

Build the baseline matrix that anchors the science.

Minimum comparisons:

- No-prefetch baseline
- Strong single-prefetcher baselines drawn from Athena L2C modules
- Any relevant simple coordinator already available in Athena, when it matches scope cleanly
- MoP-lite with multiple simple router variants

Suggested simple routers:

- **FixedSplit**
- **WinnerTakeAll**
- **RandomRouter**
- **OneShotFit**

The goal is to show the value of **coordination itself** before optimization enters.

### C. MoP-lite control surface

Build the policy interface that stage 2 will optimize.

Required functionality:

- Per-epoch state summary
- Per-expert counters for issued prefetches and useful prefetches
- A coverage proxy such as useful prefetches relative to L2 misses or MPKI
- A traffic proxy such as issued prefetches or downstream reads
- Router actions that can enable or disable each expert
- Router actions that can scale aggressiveness per expert
- A per-epoch traffic budget or equivalent hard control
- Logging that records the chosen action and the evidence that led to it

### D. Data and metric pipeline

Create a trustworthy pipeline from raw simulator output to analysis-ready dataset.

Required artifacts:

- Raw simulator outputs preserved for every completed run
- A parser that converts raw outputs into structured rows
- A schema document that defines each parsed field
- A manifest that maps runs to traces, configs, seeds, code revision, and expert pair
- A summary dataset with at least:
  - trace identifier
  - benchmark family
  - split assignment
  - configuration name
  - expert pair
  - epoch length
  - budget and aggressiveness settings
  - IPC
  - MPKI
  - issued prefetches
  - useful prefetches
  - accuracy
  - traffic overhead relative to the chosen baseline
  - queue or MSHR pressure proxies when available

### E. Experimental split and evaluation protocol

Pick a split that supports credible science.

Preferred protocol:

- **60/20/20 train, validation, held-out** when trace count supports it

Fallback protocol for smaller trace budgets:

- **70/30 train and held-out**
- Use cross-validation or repeated subsampling **inside the training side** for model selection

Also deliver:

- A fixed split file stored with the experiment artifacts
- A fast **search-mode** run configuration for quick iteration
- A stronger **final-mode** run configuration for final evidence
- A short note explaining any deviations from the initial plan

### F. Manual report foundation

Treat the report as a core artifact from day one.

Required writing workflow:

- Maintain a **human-authored research log** after every experiment batch
- Record the question, hypothesis, settings, main findings, anomalies, and next steps
- Write report prose manually
- Use scripts to generate plots, tables, and CSV summaries
- Write the narrative, claim wording, figure selection, captions, and discussion manually

Required report materials to prepare during stage 1:

- A title and one-paragraph problem statement
- A method section outline
- A baseline section outline
- A results section outline with planned figures and tables
- A limitations and future work section outline
- A reproducibility appendix outline
- A running list of likely claims, each paired with the figure or table that would support it
- A running list of threats to validity, caveats, and open questions

### G. Transparent reasoning log

Maintain a **reasoning transparency log** for the project.

This is a concise public reasoning ledger, not a raw internal stream. The goal is epistemic legibility.

For every substantial experiment batch, design choice, or interpretation, record:

- the key takeaway in two or three sentences at the top
- the most important considerations behind the decision
- your confidence in the main claims
- the support type for each main claim, such as direct measurement, coarse trend, proxy, literature support, or hypothesis
- the shortcuts you took
- the main inadequacies or open risks
- how the new evidence changed your view
- what a skeptical reader should update on
- the extent and type of AI assistance used for code, analysis, and writing

This log should make it easy for an advisor, reviewer, or future labmate to understand how the project evolved and how much trust to place in each conclusion.

---

## 7. Real completion checks over synthetic tests

This project values proof through real artifacts and real runs.

Unit tests are optional and narrow. They are useful for small parser or bookkeeping code. The main proof of correctness and completion should come from **end-to-end evidence** such as:

- a real simulator build on the target environment
- a real short-trace run that reaches completion
- a real baseline table generated from actual outputs
- a real MoP-lite run whose router actions and counters appear in logs
- a real parsed dataset row with complete metadata
- a real figure that could appear in the report
- a real rerun from a clean checkout that reproduces a key result
- a real note in the report draft that interprets the finding

When you claim a milestone is complete, attach the strongest real artifact that demonstrates it.

---

## 8. Success criteria

Use this success ladder.

### Core success

Core success means the project has produced a real scientific baseline that stage 2 can optimize.

Core success requires all of the following:

- Simulator builds and runs reproducibly
- Strong single-prefetcher baselines are validated on a representative trace set
- MoP-lite coordinates two experts with epoch-level actions
- The result parser and dataset are reliable and complete
- The split protocol is fixed and documented
- Simple router baselines are implemented and compared
- The manual report foundation exists and reflects actual findings
- The reasoning transparency log exists and reflects actual reasoning, not after-the-fact storytelling

### Strong success

Strong success adds an evidence-backed coordination result.

Target:

- **At least 1 to 2 percent geomean IPC improvement** over the strongest single-prefetcher baseline on held-out traces
- Traffic overhead at or below the chosen cap, with **20 percent** as the default cap
- Accuracy or usefulness floor at or above the chosen threshold, with **30 percent** as the default floor

### Publication-quality success

Publication-quality success deepens the interpretation.

Examples:

- clear cases where routing beats a single expert
- clear cases where routing hurts and the mechanism is understood
- evidence that certain expert pairs are complementary
- evidence that traffic and usefulness constraints change which router wins
- a compact hardware-budget story for counters, state, and thresholds

A strong stage 1 is already valuable even when the final gain is modest, as long as the analysis is honest and mechanistic.

---

## 9. Decisions that should be made empirically, and the philosophy for making them

Some decisions should follow from early evidence. Use the following philosophy.

### Expert pair choice

Choose pairs that maximize **complementarity**, **stability**, and **ease of interpretation**.

Signals of a strong pair:

- different win regions across traces
- different traffic and usefulness profiles
- different failure modes
- clean integration with shared measurement hooks

### Epoch length choice

Choose the smallest epoch that produces stable signals and meaningful action opportunities.

Look for:

- stable per-epoch statistics
- router decisions that are explainable
- manageable logging volume
- reasonable runtime

### Budget and aggressiveness choice

Choose the simplest mechanism that gives strong control.

Good options include:

- hard on or off gating
- small integer aggressiveness levels
- one shared budget across the two experts

### Metric choice

Favor metrics that correspond to meaningful microarchitectural effects.

Examples:

- IPC for end performance
- MPKI for memory pressure context
- useful and issued prefetches for usefulness
- downstream read traffic or issued prefetches for cost
- queue or MSHR pressure when available

### Split choice

Prefer one untouched final held-out split. When the trace count is small, put adaptation pressure on the training side through resampling or a small validation subset.

### Claim strength

Let the claim track the evidence. Search-mode results support iteration. Final-mode held-out results support headline claims.

---

## 10. Integrity rules

These rules protect the science.

### Reasoning transparency

- Open important memos and report sections with the key takeaways
- Mark which considerations carried the most weight
- State confidence and support type for major claims
- Expose shortcuts, unresolved uncertainties, and major inadequacies
- Keep source pointers precise enough that another reader can inspect the evidence
- Disclose the extent of AI use in code, analysis, and writing artifacts

### Split integrity

- Held-out traces stay isolated from tuning decisions
- Validation logic stays on the training side of the split
- Any choice influenced by held-out results gets labeled as post hoc analysis

### Causal integrity of features

- Router state uses signals available at the end of the current epoch for the next epoch
- Future demand outcomes never enter current decisions
- Richer offline analysis can exist in notebooks or appendices, while the online router interface stays realistic

### Comparison integrity

- All compared methods use the same warmup and simulation lengths within a given evaluation tier
- All compared methods use the same trace set inside a comparison table or figure
- All compared methods share the same underlying machine configuration unless a sensitivity study explicitly says otherwise

### Reporting integrity

- Keep all completed runs, including failures and negative outliers, in the raw dataset
- Use explicit filters with written justification
- Report geomean and per-trace behavior together
- Highlight where MoP-lite loses and give a mechanism-based explanation when possible
- Keep the final report manual and evidence-driven

---

## 11. Forbidden shortcuts and failure modes

These patterns compromise the result.

### Held-out contamination

Choosing expert pairs, thresholds, budgets, epoch lengths, or heuristics after looking at held-out results weakens generalization.

### Oracle routing disguised as an online policy

Per-trace or per-phase selection using future knowledge creates an oracle. Oracle analyses are useful as upper bounds and should be labeled that way.

### Evaluation drift

Changing warmup length, simulation length, trace subset, or machine configuration across baselines creates weak comparisons unless the change is an explicit ablation.

### Selective reporting

Reporting only wins or hiding unstable traces weakens the science.

### Silent simplification

A router that falls back to one expert in most epochs may still be useful, and that behavior should appear clearly in logs and in the report.

### Overfitting to search-mode runs

Fast runs support iteration. Final claims come from final-mode runs.

### Hidden metric hacking

A scoring rule or proxy tuned after broad result inspection weakens the baseline. Keep metric definitions stable and documented.

### Script-written paper

A paper with auto-generated prose usually loses the research story. Plots and tables can come from scripts. The narrative, captions, limitations, and takeaways should be written manually.

---

## 12. What to measure and show in the report

Stage 1 should already prepare the report backbone.

Treat every figure or table as an answer to a question. Keep a short note beside each planned figure that states the claim it supports.

Recommended figures and tables:

1. Overall IPC relative to no-prefetch and to the strongest single-prefetcher baseline
2. Per-trace win and loss distribution for MoP-lite versus the strongest single expert
3. Accuracy versus traffic scatter plot for baselines and routers
4. Expert-pair ablation table
5. Router ablation table for FixedSplit, WinnerTakeAll, RandomRouter, OneShotFit, and the main MoP-lite rule
6. A short hardware-budget table for counters, thresholds, and state

Recommended discussion questions:

- Which expert pairs complement each other best
- Which signals matter most for routing
- Where traffic control changes the outcome
- Where the router hurts and why
- Whether simple coordination already yields meaningful gains before optimization

A good report section also includes a small reasoning-transparency layer in notes or appendix:

- what the section is trying to establish
- which pieces of evidence carry the most weight
- confidence in the main claims
- shortcuts or caveats that matter for interpretation
- what the reader should update on

---

## 13. Expected output package

Your stage 1 handoff should contain:

1. Working code with clear configuration entry points
2. Build and run instructions
3. Fixed data-split files
4. Raw outputs for completed runs
5. Parsed analysis-ready dataset
6. Experiment manifest with revision and seed tracking
7. Baseline figures and tables
8. A manually written research log
9. A manually written reasoning transparency log
10. A manually written report outline and partial draft sections
11. A concise memo describing what stage 2 should optimize and what should remain frozen

---

## 14. Final instruction

Aim for a strong scientific baseline, not a flashy prototype. Keep the interface small, the comparisons fair, the logs rich, the data complete, the reasoning transparent, and the writing manual.
