# Cycle 047 — direct lab/PI upgrades, knowledge spending, ship-aware setup (vm_lf_ts)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-cap20.json` (046 B arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` — A + `ts_chain_direct` (ts_chain lifts no trading
station while a lab/PI upgrade is legal, nor a station already in a federation) + `knowledge_spend` (pass BLOCKED with 4+
knowledge while research is legal) + `ship_setup` (inside the opponent-adjacency filter, starting places within 3 hexes of a
ship first, the faction's income-fitting ship first). Order only, no new values.
Question: do these three fixes from the 046 p001-g1 analysis raise the charges gained in rounds 1–3?
Set before the run (user, 2026-10-08 "일단 테스트해"): judge by round 1–3 charges at 1 VP = 1.5 charges.
6 fresh seeds (geo-quartet-524468 … 533466) × 2 seat-swapped games, agentmaco, commit 4a413b4, stop_round 3.
First run on the engine with the map-rule fix (no two same-type planets adjacent).
Result: lab/results/047-guide-r1-charge3-lf-more-vm-lf-ts.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 169.1 | 156.0 | −13.0 | [−68.2, +42.1] |
| Taklons | 6 | 154.6 | 151.2 | −3.4 | [−34.9, +28.1] |
| Terrans | 6 | 141.4 | 154.3 | +12.9 | [−13.7, +39.4] |
| Xenos | 6 | 151.8 | 133.4 | −18.4 | [−108.1, +71.4] |
| **All** | 6 | | | **−5.5** | **[−42.6, +31.6]** |

Not significant. Per-pair B−A from the game list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −93 | −16 | +21 | −31 | −22 | +63 |
| Taklons | +10 | −63 | +6 | −4 | +15 | +15 |
| Terrans | +5 | −15 | +28 | −15 | +27 | +47 |
| Xenos | −183 | +9 | −24 | +56 | −4 | +37 |
| Pair mean | −65.3 | −21.3 | +7.8 | +1.5 | +4.0 | +40.5 |

Four of six pairs positive, but p000 (Xenos A 262 vs B 79, −183; Geodens −93) drags the mean below zero; without p000 the
other five pairs average +6.5. Terrans — where ts_chain_direct and knowledge_spend were checked (046 p001-g1 steps 27, 64) —
is positive in 4 of 6 pairs (+12.9), not significant. Xenos and Geodens swing ±60–180 per pair, so their means are noise.

VP held at round 4 (not used for the verdict): +1.2 [−2.4, +4.9].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf | 850 | 12.15 s | 20.01 s | 20.26 s | 31.3 s |
| B vm_lf_ts | 872 | 12.46 s | 20.01 s | 20.32 s | 22.8 s |

No errors, timeouts or fallback decisions; the rebuilt engine (map fix) and the new patches ran cleanly in all 12 games.
Unsearched decisions 618 vs 655.

No change to the live teacher. The three order fixes neither help nor clearly hurt; the one-pair Xenos collapse (p000) is the
only large effect and should be looked at before reading anything into the sign. 6 pairs still cannot resolve effects under
~35 charges (041–047 all inside that band).
