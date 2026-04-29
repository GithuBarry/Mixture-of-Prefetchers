# EVOLVE-BLOCK-START
"""Stage 2 policy seed for the MLOP + SPP+PPF L2C story.

OpenEvolve may edit only `candidate_policy`. The evaluator rejects keys outside
the documented policy contract, so keep this compact and generic. Do not add
trace names, benchmark-family rules, parser code, simulator paths, or offline
oracle labels.
"""


def candidate_policy():
    """Return a compact router/knob policy for MLOP + SPP+PPF."""
    return {
        "router": "MoP-V1.2",
        "mop_total_budget": 8192,
        "mop_one_shot_epochs": 1,
        "mop_accuracy_floor": 30,
        "mop_guarded_min_budget_share": 10,
        "mop_score_weights": [1.0, 0.25, 1.0],
    }


# EVOLVE-BLOCK-END


def get_policy_config():
    """Fixed entry point used by the evaluator."""
    return candidate_policy()
