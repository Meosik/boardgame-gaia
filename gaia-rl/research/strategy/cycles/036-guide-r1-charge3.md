# Cycle 036 — guide_r1_charge3 vs hard (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-r1-charge3-cap20.json` — 035's B (`guide_r1`) plus the home-planet
setup fallback (①-b), the Economy/Science income double count removed (guide_r1 4), Geodens 1PI+4M
first when its conditions hold (guide_r1 5), Geodens research order from the BGG opening articles
(guide_r1 6), and `install_charge_r3`: comparisons started in rounds 0–3 roll out to the start of
round 4 and the leaf is valued in LF charges without VP (`guide_potential` − held VP − final goal
rank − booster pass VP).
Question: does judging rounds 0–3 by collected charges instead of VP fix the guide packages' loss?
User asked for 6 pairs and to judge mainly by rounds 1–2 play; no deploy condition was set.
6 fresh seeds (geo-quartet-410058 … 422992) × 2 seat-swapped games, agentmaco, commit 071fc78.
Result: lab/results/036-guide-r1-charge3.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | −44.2 | [−59.3, −29.0] | 103.7 | 59.5 |
| Taklons | 6 | −23.3 | [−44.8, −1.8] | 87.0 | 63.7 |
| Terrans | 6 | −20.7 | [−50.4, +9.1] | 102.7 | 82.0 |
| Xenos | 6 | +1.2 | [−27.7, +30.0] | 114.8 | 116.0 |
| **Seat mean** | 6 | **−21.8** | **[−40.7, −2.8]** | 102.0 | 80.3 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1218 | 3.84 s | 1.47 s | 12.38 s | 24.2 s |
| B charge3 | 1554 | 10.19 s | 10.35 s | 20.16 s | 22.0 s |

No errors, timeouts or fallback decisions in either arm.

B is significantly worse overall, the worst of the three guide packages (034 −10.0, 035 −16.6,
036 −21.8). Geodens B scores 60, 50, 58, 56, 65, 68 — all six below 70, against A 85–124. The
Geodens-specific changes in 036 (1PI+4M, BGG research order) did not lift the collapse seen in
035; it got slightly worse (−41.2 → −44.2). Taklons now also lose significantly (B 46–79), and
Terrans B splits into two good games (114, 139) and four poor ones (53–73).

Charge evaluation ignores VP until round 4, so in rounds 0–3 federations, VP-scoring advanced
tiles, round scoring and fleet entry VP costs look free. B makes more decisions (1554 vs 1218,
Taklons 430 vs 249), the same pattern as 034/035: more small actions, less building. The median
decision time is 10.4 s (A 1.5 s), so many comparisons likely stop at the 20 s cap before
finishing their round-4 rollouts; unsearched decisions also rise (1190 vs 928).

Xenos is flat in all three guide packages (+5.9, −0.7, +1.2), so the loss is concentrated in the
three factions run by the frozen four-faction value with the guide patches.

Not separated: guide_values (−19.3 Geodens already in 034) vs the 035 parts vs charge3. The user
asked to judge by rounds 1–2 play; this summary only has final scores, so a round-1/2 look at the
Geodens B games is still owed. The live hard teacher stays; no deploy proposal.
