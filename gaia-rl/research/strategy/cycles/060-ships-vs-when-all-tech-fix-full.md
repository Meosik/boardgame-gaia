# Cycle 060 — vm_lf_ts_ships vs when_all_tech_fix, full game

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (vm_lf_ts_ships, the base stack after 053,
before when_all).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-fix-cap20.json` — the 059 B arm: the three
layers added since 056 (when_all timing rules, when_all_tech, the 058 replay fixes).
Question (user, 2026-10-16 "한번 해봐. 풀 라운드로"): are the three layers together a loss against the stack they were
built on?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges, final VP for reference only. If B is
significantly negative, propose to put the base stack back to vm_lf_ts_ships and use it as the PPO teacher. Also look at
decision time (059 B max 51.5 s) and the round 4–6 score.
6 fresh seeds (geo-quartet-669360 … 680380) × 2 seat-swapped games, agentmaco, commit fae5508, stop_round 0 (all 6
rounds).
Result: lab/results/060-ships-vs-when-all-tech-fix-full.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 178.5 | 141.7 | −36.8 | [−115.5, +41.9] |
| Taklons | 6 | 147.7 | 153.3 | +5.7 | [−54.3, +65.6] |
| Terrans | 6 | 144.2 | 120.7 | −23.5 | [−54.1, +7.1] |
| Xenos | 6 | 160.3 | 114.8 | **−45.5** | [−74.1, −17.0] |
| **All** | 6 | | | **−25.0** | [−41.4, −8.7] |

Significant. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −146 | +72 | +3 | −69 | −11 | −70 |
| Taklons | +57 | −54 | +87 | −31 | −39 | +15 |
| Terrans | −36 | +14 | −37 | −22 | +5 | −45 |
| Xenos | −15 | −93 | −59 | −42 | −31 | −34 |
| Pair mean | −34.9 | −15.3 | −1.7 | −41.2 | −19.0 | −33.3 |

All six pair means are negative. Xenos lose in all six pairs, Terrans and Geodens in four. Taklons split 3–3. The
watch replay is p000-g0, Geodens B 68 against 214 for the A arm in the other game.

Final VP (reference only, not the verdict): All +2.2 [−7.9, +12.3]; Taklons **+26.8** [+8.3, +45.4] (5 pairs
positive), Geodens +17.2 (no pair negative), Terrans −1.5, Xenos −33.8 (5 pairs negative). B Taklons and Geodens
end higher although Geodens gain fewer charges in rounds 1–3; Xenos lose both.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts_ships | 1772 | 11.94 s | 17.03 s | 20.41 s | 42.2 s |
| B when_all_tech_fix | 1683 | 13.72 s | 18.87 s | 21.09 s | 52.7 s |

No errors, timeouts or fallback decisions. B is 1.15× slower on average, max 52.7 s (under the hard server limit of
60 s). Unsearched decisions 1369 vs 1372.

Research counts and booster choices were not collected.

The pre-set condition is met: the three layers since 056 lose about 25 charges in rounds 1–3 against vm_lf_ts_ships,
with every pair negative. This matches 056 (−16.6) and 057–059 (about −28) measured layer by layer. Xenos is the
clearest loser here (−45.5, 6 of 6 pairs), Terrans keep the direction of 057–059. Proposed (user decision pending):
put the base stack back to vm_lf_ts_ships and use it as the PPO teacher. Live teacher unchanged.
