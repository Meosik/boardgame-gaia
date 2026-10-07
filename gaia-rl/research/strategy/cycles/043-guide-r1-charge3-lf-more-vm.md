# Cycle 043 — value_max + ts_chain on top of guide_r1_charge3_lf_more (20 s cap, games stop at round 4)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-cap20.json` (039/040 B arm, 041/042 A arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-cap20.json` — A + `install_value_max`:
① value_max: play the first move of the completed comparison with the highest value, ignoring opening match and
round-1 completion (fixes the 042 p004-g0 "fallback-no-verified-route" picks and `select_forecast` ignoring values);
② ts_chain: in rounds 1–3, a trading-station upgrade whose leftover ore and credits pay for a research lab or
planetary institute goes ahead of non-upgrade moves (order only, no new values).
Question: does playing the best compared plan raise charges gained in rounds 1–3?
Set before the run (user, 2026-10-08 "그렇게 해봐"): judge by round 1–3 charges.
6 fresh seeds (geo-quartet-489116 … 496072) × 2 seat-swapped games, agentmaco, commit beed01a, stop_round 3.
Result: lab/results/043-guide-r1-charge3-lf-more-vm.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5 charges).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 159.5 | 174.4 | +14.9 | [−66.6, +96.3] |
| Taklons | 6 | 158.9 | 171.6 | +12.7 | [−13.9, +39.3] |
| Terrans | 6 | 140.1 | 174.5 | +34.5 | [−13.5, +82.5] |
| Xenos | 6 | 151.0 | 158.4 | +7.4 | [−41.7, +56.5] |
| **All** | 6 | | | **+17.4** | **[−20.3, +55.1]** |

Not significant; all four factions positive. Per-pair B−A from the game list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | **−121** | +52 | +42 | +41 | −27 | +100 |
| Taklons | +2 | −7 | −9 | +32 | +4 | +55 |
| Terrans | +21 | +35 | +48 | +19 | −28 | +112 |
| Xenos | −67 | +38 | +65 | −1 | +27 | −20 |
| Pair mean | −41.3 | +29.5 | +36.5 | +22.8 | −6.0 | +61.8 |

Four of six pairs positive. pair-000 is the outlier (Geodens A 241 vs B 120, Xenos A 205 vs B 138);
pair-005 is the largest gain (Terrans +112, Geodens +100).
Terrans gain in 5 of 6 pairs — the reverse of 042 (sheden_r1, Terrans −22.9 in 5 of 6).
Geodens gain in 4 of 6 pairs, the target of the value_max fix (042 p004-g0 steps 18 and 54).

VP held at round 4 (not used for the verdict): +2.0 [−2.3, +6.4]; Xenos +7.3 [−1.2, +15.9].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A lf_more | 867 | 11.32 s | 16.64 s | 20.20 s | 29.2 s |
| B lf_more_vm | 839 | 12.11 s | 19.59 s | 20.26 s | 27.9 s |

No errors, timeouts or fallback decisions. B's median is 3 s higher (more decisions run to the 20 s cap);
p90 and max are the same. Unsearched decisions 586 vs 603.

No change to the live teacher. value_max + ts_chain points the right way in every faction but six pairs cannot
separate +17 from zero; a fresh-seed repeat is the next check.
