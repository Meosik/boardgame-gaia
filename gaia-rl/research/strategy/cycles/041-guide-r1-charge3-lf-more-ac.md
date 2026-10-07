# Cycle 041 — academy_r1 on top of guide_r1_charge3_lf_more (20 s cap, games stop at round 4)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-cap20.json` (039/040 B arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-ac-cap20.json` — A + `_guide['academy_r1']`: while a round-1
academy goal remains, upgrade and funding moves go first (new mines, research, gaia, ships and pass only when
nothing progresses), burns that open the ore/credit power actions count as funding, and an opening whose
comparison finished the academy in round 1 is chosen first. Order only, no new values.
Question: does pushing the round-1 academy raise charges gained in rounds 1–3?
Set before the run (user, 2026-10-07 "일단 테스트 해봐"): judge by round 1–3 charges; also count round-1 academies.
6 fresh seeds (geo-quartet-467751 … 475119) × 2 seat-swapped games, agentmaco, commit 03a1611.
First run with `stop_round 3`: every game ended at the start of round 4 (VP below is VP held at that point).
Result: lab/results/041-guide-r1-charge3-lf-more-ac.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5 charges).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 133.0 | 120.4 | −12.5 | [−57.9, +32.9] |
| Taklons | 6 | 153.8 | 153.1 | −0.7 | [−14.3, +12.9] |
| Terrans | 6 | 171.1 | 177.9 | +6.8 | [−11.1, +24.7] |
| Xenos | 6 | 119.2 | 142.5 | +23.2 | [−11.4, +57.9] |
| **All** | 6 | | | **+4.2** | **[−6.2, +14.6]** |

Not significant. Most game pairs are identical or nearly so (pairs 000, 001, 005 give the same charges in
both seatings). The spread comes from pair-002: Geodens B 56 vs A 154 and Xenos B 135 vs A 54 in the same
seed, which set the Geodens and Xenos means.

Round-1 academies (`academy_rounds.py`, seats whose first AC appears in round 1):

| Arm | Geodens | Taklons | Terrans | Xenos | Total |
|---|---:|---:|---:|---:|---:|
| A lf_more | 0 | 1 | 0 | 1 | 2 / 24 |
| B lf_more_ac | 0 | 2 | 0 | 3 | 5 / 24 |

academy_r1 moves round-1 academies from 2 to 5 of 24 seats (040: 1 of 48), only for Taklons and Xenos.
Terrans still build the first AC in round 2–3 and Geodens open with PI (5 of 6 in both arms).
Most seats still miss the round-1 academy, so the ordering alone does not close the ore gap seen in 040.

VP held at round 4 (not used for the verdict): −1.3 [−6.9, +4.2].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A lf_more | 798 | 11.73 s | 16.21 s | 20.21 s | 35.5 s |
| B lf_more_ac | 826 | 11.72 s | 16.29 s | 20.21 s | 35.9 s |

No errors, timeouts or fallback decisions. Same cost per decision in both arms.
With stop_round 3 the 12 games took 85 minutes.

No change to the live teacher; academy_r1 has no measurable charge effect yet.
