# Cycle 046 — remaining frozen formulas replaced with guide prices (vm_lf)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-cap20.json` (043/044 B arm, 045 A arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-cap20.json` — A + `install_lf_frozen`: expansion/gaia opportunity →
net value of reachable mines at LF prices, gaia-area tokens → B02 token value, Taklons PI term and neighbour leech →
`lf_leech_value` (largest own building power per opponent in range), setup placement hand coefficients → 0, Xenos leech hand
formula → guide charge price minus VP cost. No vp1, no leech rule.
Question: does removing the last hand-tuned frozen terms raise the charges gained in rounds 1–3?
Set before the run (user, 2026-10-08 "그렇게 해"): judge by round 1–3 charges at 1 VP = 1.5 charges (same rate in both arms).
6 fresh seeds (geo-quartet-516995 … 524057) × 2 seat-swapped games, agentmaco, commit a448882, stop_round 3.
Result: lab/results/046-guide-r1-charge3-lf-more-vm-lf.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 150.3 | 171.7 | +21.5 | [−64.6, +107.5] |
| Taklons | 6 | 156.9 | 140.9 | −16.0 | [−44.6, +12.6] |
| Terrans | 6 | 141.1 | 145.1 | +4.0 | [−23.0, +31.0] |
| Xenos | 6 | 144.9 | 151.7 | +6.8 | [−37.4, +51.0] |
| **All** | 6 | | | **+4.1** | **[−30.3, +38.4]** |

Not significant. Per-pair B−A from the game list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +22 | +143 | −85 | −13 | −24 | +86 |
| Taklons | −29 | +4 | +3 | −17 | +5 | −64 |
| Terrans | +5 | +52 | −20 | +7 | −14 | −7 |
| Xenos | +3 | +53 | −7 | −64 | +11 | +45 |
| Pair mean | +0.3 | +63.0 | −27.3 | −21.8 | −5.5 | +15.0 |

Three of six pairs positive (p000 barely). p001 alone (+63, Geodens +143: A 72 vs B 215) carries the overall mean;
without it the remaining five pairs average −7.9. Geodens swings ±85–143 per pair, so its +21.5 is noise. Taklons is the only
faction leaning negative (p005 −64, p000 −29) — Taklons is where the frozen PI term was replaced by `lf_leech_value`.

VP held at round 4 (not used for the verdict): +2.6 [−2.7, +7.9].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A lf_more_vm | 878 | 11.29 s | 15.73 s | 20.21 s | 29.0 s |
| B vm_lf | 843 | 11.80 s | 18.80 s | 20.32 s | 28.0 s |

No errors, timeouts or fallback decisions — the untested `install_lf_frozen` code ran cleanly in all 12 games.
Unsearched decisions 609 vs 600.

No change to the live teacher. Replacing the frozen formulas neither helps nor clearly hurts charges; it removes hand
coefficients (the teacher-scope agreement), so it can stand as the base for further work if the user agrees. With 6 pairs the
CI half-width is ~±34 charges, so effects under ~30 are not detectable — 041–046 have all been inside that band.
