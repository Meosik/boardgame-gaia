# Cycle 057 — replay fixes and every common guide rule (when_all_tech)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-cap20.json` (vm_lf_ts_ships_when_all, the base
stack since cycle 056).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-cap20.json` — A + the 056 replay fixes
(setup next to an opponent first instead of blocked, distinct setup spots with 50 s, former_use, burn_when,
terrans_former, tech_when) + every common guide rule that has a number and a time (GUIDE_MORE, GUIDE_REST, GUIDE_LAST,
GUIDE_FINAL: leech_lf, round_goal, artifact_vp, final_mission, contested_order, mine_tile, track_set, gaia_both,
taklons_brainstone, adv_immediate, faction_more, r1_basics, terrans_gaia_cond, tokens_lf, cover_tile, nav3_ai, …) +
the ship_ids fix. Order only; each rule has a flag (HANDOFF section 5).
Question (user, 2026-10-15 "일단 돌려봐. 문제 생기는 부분의 판단은 물어보면 되는 거지"): does the full rule set gain
round 1–3 charges over the base stack?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; also look at error games (first league run of
about 60 rules), decision time (root engine forks in round_goal and artifact_vp, 50 s setup), unsearched decisions,
research tracks and replays.
6 fresh seeds (geo-quartet-631794 … 638181) × 2 seat-swapped games, agentmaco, commit 0f14486, stop_round 3.
Result: lab/results/057-when-all-tech.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 106.2 | 129.1 | +22.8 | [−53.2, +98.9] |
| Taklons | 6 | 140.0 | 173.5 | +33.5 | [−27.7, +94.8] |
| Terrans | 6 | 169.1 | 89.8 | **−79.3** | **[−117.7, −40.8]** |
| Xenos | 6 | 159.1 | 110.8 | −48.2 | [−123.9, +27.4] |
| **All** | 6 | | | **−17.8** | [−47.7, +12.2] |

Not significant overall; Terrans lose significantly. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +36 | +124 | +37 | +54 | −88 | −26 |
| Taklons | 0 | −12 | −41 | +91 | +65 | +97 |
| Terrans | −139 | −105 | −45 | −47 | −76 | −63 |
| Xenos | −13 | −105 | −96 | +61 | −11 | −125 |
| Pair mean | −29.0 | −24.5 | −36.3 | +39.8 | −27.5 | −29.3 |

Five of six pair means are negative. Terrans lose in all six pairs: B arm 40–110 charges, A arm 140–200. The worst is
p000-g0 (B Terrans 40 against 179 in the other game), the auto-published watch replay. Xenos lose in five pairs, three
of them by about 100 or more. Geodens, the 056 loser, turn positive (4 of 6 pairs) and Taklons gain in the three later
pairs.

VP held at round 4 (reference only): All −0.6 [−4.9, +3.8]; Terrans **+6.5** [−1.0, +14.0] (one B game 31 VP),
Geodens −3.3, Taklons −0.8, Xenos −4.7. B Terrans give up a large part of their charges for a small VP lead at
round 4 — the signature of rules that take points now (round_goal, tech/track rules) over the engine. Not yet checked.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A when_all | 876 | 11.82 s | 18.94 s | 20.35 s | 42.7 s |
| B when_all_tech | 846 | 15.35 s | 20.01 s | 23.16 s | 58.3 s |

No errors, timeouts or fallback decisions in the first league run of the full rule set. B is 1.30× slower on average and
its maximum (58.3 s) is just under the hard server limit of 60 s. Unsearched decisions 610 vs 638. Decisions: Taklons
207 → 246 (unsearched 143 → 190), Xenos 275 → 219.

Not measured: research tracks and action counts (`research_counts.py` and `action_counts.py` are refused on the bot).
To fill in (from `gaia-rl`):
`GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:tools .venv/bin/python tools/research_counts.py
~/projects/gaia-lab/gaia-rl/runs/lab-057-when-all-tech --rounds 1-3`.

Not significant, loss direction carried by Terrans (significant) and Xenos. Per the user's way of working
("문제 생기는 부분의 판단은 물어보면 되는 거지"), the next step is to find which rules break Terrans and Xenos —
replay p000-g0 B Terrans and p005-g0 B Xenos (67 vs 192) — and ask the user before turning rules off. Base stack stays
vm_lf_ts_ships_when_all until the user decides. No change to the live teacher.
