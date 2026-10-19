# Cycle 081 — live hard vs vm_lf_ts_ships on the live bot lineup, full games (063 follow-up ⓐ)

A: `teacher-a-search4-h1-geodens-cap20.json` (geodens_guide, 4 comparisons, 20 s cap — the live hard teacher).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (vm_lf_ts_ships, the base stack and the
teacher D1 would deploy, same search budget). Same A/B as 063; the only difference from 063 is `stop_round 0`
(six rounds) instead of `stop_round 3`.
Queued by the user on 2026-10-18 13:45 ("배포 다 하고 실험 다 시작하면 안되나", E4ⓐ) as the pre-deployment check 063
left open: 063 was +52.2 charges in rounds 1–3 (12 of 12 pairs positive) but −8.6 reference VP at the start of round 4,
and no hard-vs-stack game had been played to round 6. Question: if the games run to the end, does B's final VP fall
below A's (Terrans and Hadsch Hallas in particular)? Judge by round 1–3 charges (1 VP = 1.5 charges) read together
with final VP; also read `game_profile.py` (turns, mines, federations, end-of-game VP by source), Hadsch Hallas errors
and unsearched decisions, and decision time. Plan: if final VP does not fall, the deployment case is strengthened; if
it falls, propose separating the round 4–6 cause.
6 fresh live-quartet seeds (live-quartet-822328 … 832122, from the 2026-10-18 top-up) × 2 seat-swapped games,
agentmaco, commit 35517df, stop_round 0, 1 h 55 min wall time. Result: lab/results/081-live-quartet-hard-vs-ships-full.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Hadsch Hallas | 6 | 125.4 | 104.4 | **−21.1** | [−40.4, −1.7] |
| Taklons | 6 | 119.8 | 174.0 | **+54.2** | [+4.8, +103.7] |
| Terrans | 6 | 129.7 | 157.8 | +28.1 | [−16.8, +73.0] |
| Xenos | 6 | 121.8 | 182.7 | +60.9 | [−19.3, +141.2] |
| **All** | 6 | | | **+30.6** | **[−0.1, +61.2]** |

Per-pair B−A from the seat list (rounded), charges first, then **final VP** (`results.json` pairs):

| | p000 | p001 | p002 | p003 | p004 | p005 | mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Hadsch Hallas charges | −14 | −23 | −42 | +12 | −32 | −28 | −21.1 |
| Taklons charges | +73 | +11 | −14 | +90 | **+108** | +56 | +54.2 |
| Terrans charges | +9 | +37 | +8 | −35 | +81 | +68 | +28.1 |
| Xenos charges | +82 | +121 | −66 | **+135** | +7 | +85 | +60.9 |
| Pair mean, charges | +37.5 | +36.5 | **−28.5** | +50.5 | +41.0 | +45.3 | +30.6 |
| Hadsch Hallas final VP | −13 | +26 | −55 | +25 | +30 | +5 | +3.0 |
| Taklons final VP | +15 | −40 | **−81** | −19 | −18 | −32 | **−29.2** |
| Terrans final VP | −6 | −24 | −37 | +9 | +22 | −4 | −6.7 |
| Xenos final VP | +38 | +10 | −40 | +75 | −12 | +67 | +23.0 |
| Pair mean, final VP | +8.5 | −7.0 | **−53.3** | +22.5 | +5.5 | +9.0 | −2.5 |

Charges: five of six pair means are positive; the overall +30.6 has its CI touching 0 (6 pairs), about 60% of 063's
+52.2 on 12 pairs. **Hadsch Hallas is reversed**: 063 +49.3 [+28.9, +69.8] (12 pairs, 11 positive), here −21.1
[−40.4, −1.7] with five of six pairs negative. The A and B spec files are the ones 063 used; the base-stack code between
c3df952 (063) and 35517df is believed unchanged apart from opt-in factories, but that was not verified line by line,
and 6 pairs on a faction with no faction code is thin — this is a flag, not a result. Taklons +54.2 is significant on
its own; Terrans and Xenos are positive with wide CIs. p002 (live-quartet-825328) is the one pair where B loses both
charges (−28.5, Xenos −66 and Hadsch −42) and every seat's final VP (−53.3: Taklons −81, Hadsch −55, Xenos −40, Terrans
−37; A Xenos 256 charges / 138 VP in game-1-A12).

**Final VP (read together with the verdict, not the verdict): All −2.5 [−30.4, +25.5]** — flat. Four of six pair means
are positive; p002 alone carries the mean (without it +7.7). Seat average A 100.3 → B 97.9. By faction: Xenos
**+23.0** [−24.5, +70.5] (4 pairs positive), Hadsch Hallas +3.0 (3:3), Terrans −6.7 [−29.2, +15.8] (3:3),
**Taklons −29.2** [−62.3, +4.0] (five of six pairs negative, −18 to −81). So the two factions the question named,
Terrans and Hadsch Hallas, do not fall outside noise; Taklons does, and in the same pairs where its round 1–3 charges
are the largest gain (+54.2): charges went up and VP came down.

**Where B's early charges go, and where A gets its VP back (`game_profile.py`, mean per seat, A → B).**

| | turns | mines on board | upgrades/seat | research levels | ships entered | pass VP | build VP | upgrade VP | ship entry+action | charge VP | end research | end missions | final |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hadsch Hallas | 48.0 → 45.3 | 4.3 → 7.2 | 12.0 → 9.5 | 13.5 → 12.5 | 2.5 → 2.8 | 15.2 → 16.0 | 5.5 → 6.7 | 13.3 → 14.7 | −4.3 → −8.0 | −5.3 → −7.3 | 25.3 → 25.3 | 14.0 → 23.5 | 95.0 → 98.0 |
| Taklons | 37.5 → 48.0 | 3.2 → 4.8 | 9.2 → 6.8 | 12.2 → 15.3 | 0.0 → 2.0 | 9.2 → 6.5 | **15.7 → 0.8** | **18.8 → 9.2** | 0.0 → −0.8 | −3.8 → −7.3 | 20.7 → 25.3 | 26.5 → 24.5 | 113.3 → 84.2 |
| Terrans | 29.2 → 46.3 | 3.0 → 4.8 | 5.8 → 6.3 | 10.5 → 17.7 | 0.7 → 2.3 | **18.5 → 6.7** | 4.3 → 5.2 | 13.2 → 10.5 | −2.3 → +0.3 | −1.5 → −5.8 | 17.3 → **30.7** | 23.0 → 22.3 | 100.5 → 93.8 |
| Xenos | 49.3 → 54.5 | 6.3 → 7.0 | 9.0 → 9.7 | 11.7 → 14.7 | 2.5 → 3.0 | 9.2 → 11.7 | 4.0 → 3.0 | 12.2 → 20.3 | −0.3 → −0.8 | −9.2 → −7.2 | 20.0 → 28.0 | 20.8 → 25.8 | 92.5 → 115.5 |

- **B converts charges into research levels** (+1.0 to +7.2 levels per seat, end research VP Terrans +13.4, Xenos
  +8.0, Taklons +4.6) and into ships (Taklons 0 → 2.0 entries, Terrans 0.7 → 2.3; entry cost and action VP roughly
  cancel). A hard converts into **round-tile and booster VP in rounds 4–6**: Taklons build VP 15.7 → 0.8 and upgrade
  VP 18.8 → 9.2 (−24.5 together, the whole Taklons gap) with rounds 4–6 Build 21 → 8 and Upgrade 26 → 16
  (`action_counts.py`); B Taklons has more mines on the board (4.8 vs 3.2) but builds them when the tile does not pay.
  Terrans pass VP 18.5 → 6.7 (−11.8): A hard Terrans take 29 turns a game (B 46), pass early on VP boosters and keep
  Gaia-forming (rounds 1–3 GaiaFormation 13 → 0, Gaia research 16 → 2 — the stack's "Terrans Gaia later" rule), which
  B's +13.4 end research only just covers.
- Rounds 4–6 moves A / B: Taklons PowerAction 10 / 26, RebellionGainTechTile 0 / 5; Terrans 6 / 9 and 0 / 13;
  research advances equal for Taklons (29 / 29), Terrans 17 / 30. B's extra turns in rounds 4–6 go to power and
  tech-tile actions, not to scoring builds.
- Hadsch Hallas and Xenos are the two factions where B's end missions rise (+9.5, +5.0) and VP does not fall;
  Hadsch Hallas has 0 errors, 0 timeouts, 0 fallback decisions, unsearched 331 (A) vs 319 (B) — the stack still runs
  cleanly on it; its round 1–3 charge loss comes with Navigation 3 → 11 and ship entries 7 → 14 in rounds 1–3 against
  A's Economy 16 (hard goes Economy early: Taklons 20 of 20, Hadsch 16 of 24).

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1664 | 3.59 s | 1.15 s | 11.15 s | 22.8 s |
| B vm_lf_ts_ships | 1936 | 10.06 s | 9.29 s | 20.27 s | 25.3 s |

No errors, timeouts or fallback decisions on either arm. B makes 16% more decisions (Terrans 323 → 462) and is 2.8×
slower on average; its maximum of 25.3 s is inside the live hard guard of 60 s. Unsearched decisions 1199 (A) vs 1447
(B), 72% / 75%. The posted watch replay is pair-003/game-0-A13 seat 1, Xenos on the A arm, 99 charges against 234 for
the B-arm Xenos in the other game (final 60 vs 135).

**Reading.** On the pre-set fork, the answer is "does not fall, overall": B ends the full game level with the live hard
teacher (−2.5, CI wide, four of six pairs positive) while gaining +30.6 charges in rounds 1–3 and +23 final VP for
Xenos. That keeps the D1 case where 052 and 063 put it (rounds 1–3, 24 pairs all positive) and adds "no final-VP loss
on the live lineup" as a 6-pair statement. What it does not do is strengthen the case: the +30.6 charges (≈ 20 VP at
1.5) do not survive to the end, Taklons loses in five of six pairs through round 4–6 build and upgrade timing, and
Hadsch Hallas' round 1–3 gain from 063 did not reproduce. This is the first full-game measurement of the verdict
scale against the live teacher: the round 1–3 charge lead and the final VP are different quantities here, and the gap
(about 20 VP per seat) is what A hard recovers in rounds 4–6 from round tiles and boosters.

**Proposal (user decision, nothing queued, no code change, no deployment).**

- D1 (teacher swap): 081 does not contradict the basis (052·063) and reports final VP level on the live lineup; the
  known cost is Taklons in rounds 4–6. Whether to deploy now or after a repeat is the user's call — the bot's reading
  is that 081 is a "not worse" result, not a "better" one, for the full game.
- (ㄱ) **081 repeat on 6 fresh live-quartet seeds, 6 rounds** (21 unused seeds in `lab/seeds-live-quartet.txt`, 39 minus 18 used by 063 and 081,
  ≈ 2 h): pool to 12 pairs for both charges and final VP; tells whether Taklons −29.2 and the Hadsch Hallas charge
  reversal are real.
- (ㄴ) **Lab time 0, bot work**: `explain_ab_decisions.py` on B Taklons in p002 game-1-A12 seat 3 (54 VP) and p001
  game-0-A23 seat 1 (70 VP) rounds 4–6 — why power/tech actions instead of a mine or upgrade when the round tile pays —
  and on p002 as a pair (all four B seats lost). Names the round 4–6 cause before any rule is written.
- (ㄷ) 082 (normal level, 2 comparisons, 5 s) is running since 11:28 and answers the default-level question separately.

Bot recommendation: (ㄴ) now, (ㄱ) as the next lab slot after 082; D1 timing is the user's. The rule-experiment slots
E9 (ㄴ) geodens_b14_tech alone and E7 ships_land_safe are unchanged.
