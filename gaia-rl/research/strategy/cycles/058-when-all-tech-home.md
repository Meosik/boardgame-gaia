# Cycle 058 — when_all_tech rerun with the home planet fix

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-cap20.json` (vm_lf_ts_ships_when_all, the base
stack, same as 057).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-cap20.json` — the 057 B arm plus the home
planet fix (7f8a085: ore_terraform and setup_step1 used `_value.HOME`, which only knows Terrans and Taklons, so they
never fired for Xenos and Geodens). round_goal kept (user, 2026-10-15).
Question (user, 2026-10-15 "그럼 다시 해"): with the fix, does when_all_tech still lose round 1–3 charges (057: −17.8,
Terrans −79.3, Xenos −48.2)?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; also look at Xenos and Geodens, error games,
decision time (057 B max 58.3 s), research tracks and replays.
6 fresh seeds (geo-quartet-639673 … 644888) × 2 seat-swapped games, agentmaco, commit 7eb671d, stop_round 3.
Result: lab/results/058-when-all-tech-home.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 148.0 | 125.1 | −22.9 | [−112.6, +66.8] |
| Taklons | 6 | 164.5 | 129.1 | **−35.4** | **[−65.6, −5.1]** |
| Terrans | 6 | 152.9 | 105.4 | **−47.5** | **[−94.9, −0.1]** |
| Xenos | 6 | 152.4 | 136.0 | −16.4 | [−69.4, +36.5] |
| **All** | 6 | | | **−30.6** | **[−57.8, −3.3]** |

Significant loss overall. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −124 | +5 | −109 | +110 | −17 | −2 |
| Taklons | −36 | −52 | −76 | +11 | −35 | −24 |
| Terrans | −43 | −55 | −56 | +34 | −64 | −102 |
| Xenos | −25 | +3 | −2 | −113 | +11 | +27 |
| Pair mean | −57.0 | −24.8 | −60.8 | +10.5 | −26.3 | −25.3 |

Five of six pair means are negative, as in 057. Terrans lose in five pairs (057: all six), so over 057 + 058 Terrans
lose in 11 of 12 pairs. Taklons, which gained in 057 (+33.5), now lose in five pairs. Xenos improve from −48.2 to
−16.4 (three pairs positive) — consistent with the fix, but within noise. Geodens swing ±110 per pair (two B games at
67 and 91). The watch replay is p000-g1, Geodens B 91 against 215 for the A arm in the other game.

VP held at round 4 (reference only): All −1.5 [−5.4, +2.4]; Terrans **+6.3** [+0.7, +12.0], Geodens −4.7,
Taklons −1.5, Xenos −6.2. Same signature as 057: B Terrans trade charges for points now.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A when_all | 874 | 12.41 s | 20.01 s | 20.33 s | 29.6 s |
| B when_all_tech | 923 | 15.18 s | 20.02 s | 22.50 s | **69.9 s** |

No errors, timeouts or fallback decisions. B is 1.22× slower on average and its maximum (69.9 s) is **over the hard
server limit of 60 s** — on the live server that decision would restart the AI process. Unsearched decisions 621 vs 666
(Terrans 130 → 162).

Research steps in rounds 1–3 (`research_counts.py --rounds 1-3`, six seats per arm):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 0 | 0 | 11 | 4 | 7 | 0 | 22 |
| B | Geodens | 0 | 2 | 14 | 3 | 5 | 0 | 24 |
| A | Taklons | 3 | 0 | 8 | 6 | 8 | 2 | 27 |
| B | Taklons | 2 | 2 | 2 | 0 | 14 | 4 | 24 |
| A | Terrans | 3 | 0 | 8 | 1 | 7 | 4 | 23 |
| B | Terrans | 1 | 2 | 0 | 4 | 11 | 0 | 18 |
| A | Xenos | 4 | 6 | 5 | 6 | 2 | 0 | 23 |
| B | Xenos | 1 | 12 | 1 | 2 | 7 | 1 | 24 |

The research shape differs from 057: B Terrans now go to Economy (11) instead of Navigation, and B Taklons drop AI
(8 → 2) and Gaia (6 → 0) for Economy (14). The two factions that lost AI steps are the two significant losers.
track_set is still the first suspect, but the shape moved between seeds, so the evidence is weaker than in 057.

Combined 057 + 058 (12 pairs): about −24 charges, Terrans about −63. The fix helped Xenos in direction only; the
bundle as a whole loses. Base stack stays vm_lf_ts_ships_when_all, no change to the live teacher. Next steps
(user decision): split the bundle (track_set off first) and find the 69.9 s decision.
