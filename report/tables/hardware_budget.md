# MoP-lite hardware / storage budget (Stage 1)

Scope-locked Stage 1 control surface (see charter § MoP-lite control surface):

| Component                    | Configuration                              | Approx. storage |
| ---                          | ---                                        | ---             |
| Per-epoch counters (2 experts)| `pref_issued[2]`, `pref_useful[2]` (uint64)| 32 B            |
| Usefulness/coverage cache    | `pref_acc[2]`, coverage deltas (float)     | 16 B            |
| Budget registers             | `mop_total_budget`, share per expert       | 8 B             |
| Router state                 | `action` (3 values), epoch counter         | 4 B             |
| One-shot fit scratchpad      | `score_sum[2]`, `score_count`              | 24 B            |
| Score weights (frozen)       | 3 floats                                   | 12 B            |
| Accuracy floor / fixed ratio | 2 uint8                                    | 2 B             |
| **Total (rounded)**          |                                            | **≈ 100 B**     |

The epoch length is 500 000 retired instructions (`og_instr_epoch_len`), so
update frequency ≈ 2 kHz at 1 GHz effective IPC — entirely negligible
arithmetic cost. No per-access ML inference is introduced in Stage 1.
