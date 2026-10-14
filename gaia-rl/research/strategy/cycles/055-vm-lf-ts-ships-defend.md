# Cycle 055 — research_defend alone (rule 1b)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (vm_lf_ts_ships, the base stack).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-defend-cap20.json` — A + `research_defend_track`
(`install_when(defend=True)`), order only. Round 1 research: Navigation when the next range step newly reaches two or
more defence targets, fewer than two are already reachable and no Academy is built (home-type planets only with an
adjacent faction on the board, one-spade planets only with a cheap spade, Gaia planets only when an opponent also
reaches them and they are a stepping stone or link). Without an adjacent faction: Economy 2 first, then Navigation
(also in rounds 2–3). A sure third federation (two safe, near home-type planets and the tile above Science worth more
than the final-goal standing) sends research to Science up to 4. Otherwise Gaia (asteroid / two transdim) → Economy 2.
Rules 2 and 3 of cycle 054 are not in either arm.
Question (user, 2026-10-14 "일단 해보고"): does rule 1 rewritten to the source text (B18 p.3) and the user's
definitions still lose the charges that cycle 054 lost?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; also look at research tracks, error games,
unsearched decisions and replays. Known caveat: the measure prices an Economy step at break-even.
6 fresh seeds (geo-quartet-609178 … 612632) × 2 seat-swapped games, agentmaco, commit 084ca04, stop_round 3.
Result: lab/results/055-vm-lf-ts-ships-defend.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 143.4 | 127.9 | −15.5 | [−51.8, +20.8] |
| Taklons | 6 | 166.7 | 149.5 | −17.2 | [−49.3, +14.9] |
| Terrans | 6 | 194.0 | 177.3 | −16.7 | [−56.2, +22.9] |
| Xenos | 6 | 126.7 | 157.9 | +31.1 | [−4.2, +66.5] |
| **All** | 6 | | | **−4.6** | **[−17.4, +8.3]** |

Not significant. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −10 | −34 | +35 | −1 | −14 | −69 |
| Taklons | −3 | −25 | −71 | −24 | +2 | +17 |
| Terrans | −1 | −25 | −2 | −67 | +40 | −45 |
| Xenos | +23 | +19 | +88 | +34 | −15 | +38 |
| Pair mean | +2.3 | −16.2 | +12.7 | −14.7 | +3.3 | −14.8 |

Three pair means are positive and three negative. Xenos gains in five of six pairs; the other three factions lean
negative (Geodens and Terrans 4 of 6 negative, Taklons 4 of 6), each with one or two large swings (Taklons p002 −71,
Terrans p003 −67, Geodens p005 −69).

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 6 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 0 | 0 | 15 | 3 | 3 | 1 | 22 |
| A | Taklons | 5 | 1 | 14 | 1 | 7 | 3 | 31 |
| A | Terrans | 4 | 2 | 18 | 3 | 3 | 4 | 34 |
| A | Xenos | 6 | 14 | 1 | 0 | 7 | 0 | 28 |
| B | Geodens | 0 | 1 | 7 | 6 | 8 | 0 | 22 |
| B | Taklons | 4 | 1 | 7 | 4 | 9 | 1 | 26 |
| B | Terrans | 6 | 0 | 15 | 2 | 9 | 0 | 32 |
| B | Xenos | 4 | 6 | 3 | 3 | 7 | 0 | 23 |

The Navigation rush of cycle 054 is gone: B Navigation is 1, 1, 0 for Geodens, Taklons, Terrans, and Xenos goes
down (14 → 6). The Science branch never fires (Science 0–1 in every B row), so the "sure third federation" test is
almost never true. The visible change is AI → Economy (and some Gaia): AI Geodens 15 → 7, Taklons 14 → 7; Economy
Geodens 3 → 8, Taklons 7 → 9, Terrans 3 → 9. That is the branch the measure prices at break-even, while an AI step
pays tokens and charges at once, so the three-faction drop is at least partly the known caveat. Xenos, the one
faction whose Navigation fell, is the one that gained.

VP held at round 4 (reference only): All −0.2 [−3.0, +2.5]; Geodens −2.7, Taklons −0.7, Terrans +1.2, Xenos +1.2.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts_ships | 903 | 12.00 s | 20.00 s | 20.25 s | 28.4 s |
| B ships_defend | 915 | 12.31 s | 20.01 s | 20.26 s | 22.4 s |

No errors, timeouts or fallback decisions. Unsearched decisions 651 vs 662 (Xenos 177 vs 207). Watch replay
published: pair-002/game-1-A12 seat 1 (Xenos on the A arm, 135 charges against 223).

No effect shown: rule 1b alone neither repeats cycle 054's loss (−20.7) nor gains. It does not join the base stack;
the base stack stays vm_lf_ts_ships. No change to the live teacher. Cycle 056 (every timing rule together, 1b
included) is already queued on the remaining six seeds.
