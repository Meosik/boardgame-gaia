# Cycle 040 — guide_r1_charge3_lf_more vs hard, fresh-seed recheck (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-cap20.json` — unchanged from 039.
Question: does 039's charge gain (+29.7 [+0.2, +59.2]) hold on fresh seeds?
Set before the run (user, 2026-10-07): judge by charges gained in rounds 1–3 only; propose replacing the
hard teacher if significant.
6 fresh seeds (geo-quartet-460222 … 465474) × 2 seat-swapped games, agentmaco, commit 2ed9f2f.
Result: lab/results/040-guide-r1-charge3-lf-more-rep.md (first run with the lab's automatic charge table).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, round-1 start to round-4 start,
1 VP = 1.5 charges).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 68.0 | 143.2 | +75.2 | [+3.3, +147.0] |
| Taklons | 6 | 101.1 | 131.6 | +30.5 | [+7.3, +53.7] |
| Terrans | 6 | 110.6 | 132.4 | +21.8 | [−7.2, +50.9] |
| Xenos | 6 | 124.0 | 125.7 | +1.6 | [−34.1, +37.4] |
| **All** | 6 | | | **+32.3** | **[−0.9, +65.5]** |

Overall not significant (the CI just crosses 0), so the pre-set deploy condition is not met.
The point estimate repeats 039 (+29.7 → +32.3) and the faction pattern is the same: Taklons significant
in both runs, Geodens largest and most variable (significant this time), Terrans positive but not
significant, Xenos about 0 in both. Across the 12 pairs of 039+040 the gain is consistent in direction;
a pooled test needs the 039 per-pair charges (not in the repo).
Geodens A has one game at −12 charges (pair-003/game-0-A13), which widens its CI; B Geodens ranges
100–203.
This is the measure the charge3 arm optimizes, so it favours B.

Final VP (not used for the verdict):

| Faction | Pairs | B−A VP | 95% CI |
|---|---:|---:|---|
| Geodens | 6 | −40.0 | [−60.5, −19.5] |
| Taklons | 6 | −19.3 | [−38.7, +0.0] |
| Terrans | 6 | −15.0 | [−46.1, +16.1] |
| Xenos | 6 | −6.3 | [−17.7, +5.0] |
| **Seat mean** | 6 | **−20.2** | **[−34.3, −6.1]** |

The charge gain and the final-VP loss point in opposite directions again, most sharply for Geodens
(+75 charges, −40 VP; B final 41–72 against A 78–114).

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1238 | 4.39 s | 1.79 s | 13.47 s | 24.9 s |
| B charge3_lf_more | 1607 | 10.70 s | 11.36 s | 20.26 s | 26.5 s |

No errors, timeouts or fallback decisions. Both arms stayed under 27 s this time (039: 37.9 / 42.5 s).
B makes more decisions (1607 vs 1238; Taklons 410 vs 266, Terrans 393 vs 262) and leaves more decisions
unsearched (1248 vs 947).

The live hard teacher stays; no deploy is proposed.
