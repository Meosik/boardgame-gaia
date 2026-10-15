# Cycle 059 — when_all_tech with the 058 replay fixes

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-cap20.json` (vm_lf_ts_ships_when_all, the base
stack, same as 057 and 058).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-fix-cap20.json` — the 058 B arm
(when_all_tech with the home planet fix) plus the fixes from the 058 replays: ore_free_steps, pass_booster_late,
booster_root, convert_when, setup_reach, form_early (with the bowl I power action first, f010f4a). tokens_lf kept.
Question (user, 2026-10-16 "그냥 돌려"): do the replay fixes turn the 058 loss (−30.6, Terrans −47.5, Taklons −35.4)
around?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; also look at boosters, decision time (058 B max
69.9 s), research tracks, ship actions after entry and replays.
6 fresh seeds (geo-quartet-645941 … 663895) × 2 seat-swapped games, agentmaco, commit e84670d, stop_round 3.
Result: lab/results/059-when-all-tech-fix.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 140.7 | 131.6 | −9.0 | [−69.6, +51.6] |
| Taklons | 6 | 165.0 | 139.3 | −25.7 | [−84.9, +33.4] |
| Terrans | 6 | 179.3 | 122.0 | −57.3 | [−127.6, +13.0] |
| Xenos | 6 | 143.5 | 92.5 | −51.1 | [−134.9, +32.8] |
| **All** | 6 | | | **−35.8** | [−74.9, +3.3] |

Not significant (the interval just reaches 0), but the largest mean loss of the three when_all_tech runs. Per-pair B−A
from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +62 | +1 | −7 | −114 | −1 | +4 |
| Taklons | −78 | +6 | −69 | −29 | +71 | −54 |
| Terrans | −71 | −7 | −134 | −137 | −7 | +12 |
| Xenos | −155 | −125 | +45 | −65 | +26 | −32 |
| Pair mean | −60.5 | −31.3 | −41.3 | −86.3 | +22.3 | −17.5 |

Five of six pair means are negative, as in 057 and 058. Terrans lose in five pairs; over 057 + 058 + 059 they lose
in 16 of 18 pairs. Xenos fall back to −51.1 (057: −48.2, 058: −16.4), with two B games at 84 and 74 against 239 and
251 for the A arm. Taklons lose in four pairs. Geodens are flat apart from p003 (B 121 vs A 235). The watch replay is
p000-g1, Xenos B 84 against 239 for the A arm in the other game.

VP held at round 4 (reference only): All −1.5 [−4.8, +1.8]; Geodens **−7.0** [−11.0, −3.0], Terrans +2.7, Taklons
0.0, Xenos −1.8. B Geodens hold fewer points in all six seats (A 4–19, B 1–9).

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A when_all | 936 | 12.09 s | 19.01 s | 20.39 s | 27.3 s |
| B when_all_tech_fix | 878 | 14.89 s | 20.02 s | 21.93 s | 51.5 s |

No errors, timeouts or fallback decisions. B is 1.23× slower on average; its maximum fell from 69.9 s to 51.5 s, under
the hard server limit of 60 s. Unsearched decisions 659 vs 668.

Research counts and booster choices were not collected (the bot may not run `research_counts.py`).

Over the three runs (18 pairs) when_all_tech loses about −28 charges, Terrans about −61. The replay fixes did not
help: each fix corrected a move the user pointed at, but the bundle under them (about 60 order rules from the common
guides and the four factions) keeps losing, mainly with Terrans. Base stack stays vm_lf_ts_ships_when_all, no change
to the live teacher.
