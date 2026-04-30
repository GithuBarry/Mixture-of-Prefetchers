# EVOLVE-BLOCK-START
"""Reconstructed failed GPT-5.4 candidate for one exact retry."""


def candidate_policy():
    return {
        "router": "MoP-V1.3",
        "mop_total_budget": 12288,
        "mop_one_shot_epochs": 1,
        "mop_accuracy_floor": 30,
        "mop_guarded_min_budget_share": 10,
        "mop_sticky_margin_pct": 1,
        "mop_score_weights": [1.24, 0.56, 0.88],
    }


# EVOLVE-BLOCK-END


def get_policy_config():
    return candidate_policy()
