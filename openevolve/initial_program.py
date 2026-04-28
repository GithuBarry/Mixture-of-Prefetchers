"""
MoP-lite OpenEvolve seed policy — Stage 2 search target.

This file defines the coordination policy for the OpenEvolve router (type 5).
OpenEvolve should modify ONLY the values in POLICY_CONFIG and the logic inside
mop_decision() and configure_budget() to improve geomean speedup_vs_best_single
on the search_subset traces (Pythia + SPP+PPF pair, L2C-only coordination).

FROZEN (do not modify):
  - The function signatures and return types
  - The input variable names and what they represent
  - The action encoding: 0=both_off, 1=expert1_only, 2=expert0_only, 3=both_on
  - The budget encoding: float in [0.0, 1.0] representing expert0 share of total budget
  - POLICY_CONFIG keys (you may change values only)

EVOLVABLE:
  - All numeric values in POLICY_CONFIG
  - The conditional logic inside mop_decision() and configure_budget()
  - Additional intermediate variables and rules (keep them explainable)

FORBIDDEN:
  - Using trace_name, split_id, or benchmark_family as inputs
  - Reading external files or making network calls
  - Non-deterministic behavior (no random.random() calls)
  - Changing the return types or function signatures
"""

# --- Evolvable policy configuration ---
# OpenEvolve: modify these values to improve coordination performance.
POLICY_CONFIG = {
    # Score weight for expert prefetch accuracy (useful / issued)
    "accuracy_weight": 1.0,

    # Score weight for coverage proxy (useful / retired_insts)
    "coverage_weight": 0.25,

    # Score weight for traffic penalty (issued / total_issued)
    "traffic_weight": 1.0,

    # Accuracy floor: score is zeroed when accuracy < this threshold (%)
    "accuracy_floor": 30,

    # E2 winner isolation: route exclusively when score_winner >= this * score_loser
    "isolation_threshold": 3.0,

    # E1 fallback: minimum history epochs before trusting cumulative issued counts
    # (below this, fall back to both_on to avoid cold-start bias)
    "history_warmup_epochs": 1,
}


def mop_score(issued: float, useful: float, total_issued: float, retired_insts: float) -> float:
    """Compute the MoP score for one expert given its epoch-boundary counters.

    Inputs (all non-negative floats from the previous epoch):
      issued        -- prefetches issued by this expert this epoch
      useful        -- prefetches marked useful (L2C + LLC) this epoch
      total_issued  -- total issued across both experts this epoch
      retired_insts -- retired instructions this epoch

    Returns a float score >= 0. Zero means the expert should not be trusted.
    """
    cfg = POLICY_CONFIG
    if issued <= 0.0:
        return 0.0
    accuracy = 100.0 * useful / issued
    if accuracy < cfg["accuracy_floor"]:
        return 0.0
    coverage = useful / (retired_insts + 1.0)
    traffic = issued / (total_issued + 1.0)
    return (
        cfg["accuracy_weight"] * (accuracy / 100.0)
        + cfg["coverage_weight"] * coverage
        - cfg["traffic_weight"] * traffic
    )


def mop_decision(
    score0: float,
    score1: float,
    hist_issued0: int,
    hist_issued1: int,
    epoch_count: int,
) -> int:
    """Choose the routing action for the next epoch.

    Inputs:
      score0        -- mop_score() result for expert 0 (current epoch)
      score1        -- mop_score() result for expert 1 (current epoch)
      hist_issued0  -- cumulative issued count for expert 0 across all past epochs
      hist_issued1  -- cumulative issued count for expert 1 across all past epochs
      epoch_count   -- total number of epochs completed so far (0-indexed)

    Returns one of: 0 (both_off), 1 (expert1_only), 2 (expert0_only), 3 (both_on)
    """
    cfg = POLICY_CONFIG
    threshold = cfg["isolation_threshold"]
    warmup = cfg["history_warmup_epochs"]

    # E1: Anti-Off Gate
    # When both scores are zero, avoid both_off; route to historically better expert.
    if score0 <= 0.0 and score1 <= 0.0:
        if epoch_count < warmup or (hist_issued0 == 0 and hist_issued1 == 0):
            return 3  # no history yet: keep both on
        return 2 if hist_issued0 >= hist_issued1 else 1

    # Degenerate single-sided cases
    if score0 <= 0.0:
        return 1
    if score1 <= 0.0:
        return 2

    # E2: Winner Isolation
    if score0 >= threshold * score1:
        return 2
    if score1 >= threshold * score0:
        return 1

    return 3  # both positive and close: proportional split


def configure_budget(
    action: int,
    score0: float,
    score1: float,
    total_budget: int,
) -> tuple[int, int]:
    """Compute (budget0, budget1) given the chosen action and scores.

    Inputs:
      action        -- output of mop_decision()
      score0        -- mop_score() result for expert 0
      score1        -- mop_score() result for expert 1
      total_budget  -- total prefetch budget for this epoch (e.g. 2048)

    Returns (budget0, budget1) where budget0 + budget1 <= total_budget.
    """
    if action == 0:
        return (0, 0)
    if action == 2:
        return (total_budget, 0)
    if action == 1:
        return (0, total_budget)
    # action == 3: both on — E3 squared-score split
    sq0 = score0 * score0
    sq1 = score1 * score1
    sq_sum = sq0 + sq1
    if sq_sum > 0.0:
        b0 = int(round(total_budget * sq0 / sq_sum))
        b0 = max(0, min(b0, total_budget))
        return (b0, total_budget - b0)
    return (total_budget // 2, total_budget - total_budget // 2)
