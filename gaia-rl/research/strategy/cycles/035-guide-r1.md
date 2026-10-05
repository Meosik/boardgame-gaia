# Cycle 035 — guide_r1 vs hard (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-r1-cap20.json` — 034's B (`guide_values` + `uiqoo_openings`) plus
`install_free_conversions` (frozen conversion bans lifted, values decide), `install_academy_first`
(round-1 academy goal upgrades before new mines; order only), setup comparisons limited to spots within
distance 2 of an opponent building when any exist, Terrans Gaia research last in rounds 1–3, and the
QIC range double count removed from `guide_potential`. The home-planet setup fallback (①-b, e0f2106)
was added after the run started and is not in this test.
Question: does the round-1 guide package recover 034's loss? User asked for 6 pairs and to judge
mainly by rounds 1–2 play; no deploy condition was set.
6 fresh seeds (geo-quartet-395465 … 406729) × 2 seat-swapped games, agentmaco, commit 7888704
(queue name `035-guide-values-free-academy`). Result: lab/results/035-guide-values-free-academy.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | −41.2 | [−58.9, −23.4] | 103.0 | 61.8 |
| Taklons | 6 | −10.5 | [−37.4, +16.4] | 102.0 | 91.5 |
| Terrans | 6 | −14.0 | [−33.4, +5.4] | 96.5 | 82.5 |
| Xenos | 6 | −0.7 | [−29.6, +28.3] | 106.8 | 106.2 |
| **Seat mean** | 6 | **−16.6** | **[−28.6, −4.6]** | 102.1 | 85.5 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1359 | 4.28 s | 1.72 s | 13.70 s | 21.3 s |
| B guide_r1 | 1568 | 7.72 s | 4.08 s | 20.13 s | 21.6 s |

No errors, timeouts or fallback decisions in either arm.

B is significantly worse overall, and worse than 034 (−10.0). Geodens collapse: B scores
46, 33, 67, 41, 107, 77 against A 89–123; four of six games are below 70, which is not normal play.
Geodens get no new opening in either 034 or 035, so their loss comes from the shared changes:
`guide_values` (already −19.3 in 034) and, new in 035, free conversions, academy_first and the
setup filter. The extra ~22 VP drop since 034 points at one of the new parts, not the values alone.

Decision counts again rise for Taklons (465 vs 330) and Terrans (371 vs 290); Geodens fall (295 vs
324). Unsearched decisions rise (1232 vs 1016), so more choices follow the default ranking under the
new values. B is 1.8× slower on average (p90 at the 20 s cap) but stayed under the cap.

The user asked to judge by rounds 1–2 play; this summary only has final scores. Before any next
A/B the Geodens B games (low ones first) need a round-1/2 look to find which part breaks.

Not separated: guide_values vs free conversions vs academy_first vs setup filter. The two guide
packages (034, 035) are both negative; the live hard teacher stays.
