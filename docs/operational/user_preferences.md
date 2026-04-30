# User Preferences

Updated: 2026-04-30

## Reporting Style

- Lead with global progress for large project updates.
- Give full context because the user may skip intermediate tool output.
- Keep prose plain and direct.
- Avoid unexplained internal names in public-facing writing.
- Keep raw artifact paths and code-name mappings in writing logistics.
- Use `MoP-V1` and `MoP-V2` as the public router names.

## Evaluation Style

- Treat disabled prefetching as the universal `1.000x` baseline.
- Show best expert separately as a reference.
- State heldout limits clearly.
- Keep trace split and heldout use explicit.
- Explain IPC using the fixed retired-instruction window and cycle ratio.
- Attribute OpenEvolve gains to the whole selected policy unless an ablation isolates one knob.

## Plotting Style

- Use only these colors plus black, white, and light grey:
  - `#ffb000`
  - `#fe6100`
  - `#dc267f`
  - `#785ef0`
  - `#648fff`
- Keep legends outside plot content.
- Make labels readable.
- Avoid cluttered confidence intervals when they make a plot harder to read.

## Git Style

- Use branch `MoP-Final` for the final public branch.
- Keep tag `v3-finish` on the final pushed commit.
- When explicitly requested, force-update the most recent pushed commit to hide incorrect final wording from branch history.
