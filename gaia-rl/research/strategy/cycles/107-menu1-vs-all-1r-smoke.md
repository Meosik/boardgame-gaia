# Cycle 107 — ships_menu1 vs ships_menu1_all — all faction parts at once, 1R smoke (no verdict)

A = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-cap60-p2.json` (ships + plan_menu 1 slot, 105 B).
B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-cap60-p2.json`: A + every faction part so far
(CANDIDATE·GUIDE·SOURCE·RESOLVED·WEAK, E104 mj01 tracks, Taklons charge-4 tile, Xenos AI, artifacts 4 tokens, Moweyds opening,
Navigation+1 tile, TF Mars instant forming, and 10-25 ship_adjacent_mine E61 (ㄱ)·endgame_prices·fed·tokens). Queued 2026-10-24 by
E103 (user "일단 반영할거 다 반영해봐"). Pre-registered verdict: **none** — smoke for errors, timeouts and decision time over 18
factions; 1R charges by faction are reference only. Read alongside: errors, max decision seconds.
Quartets geo·a·b·c·d·e × 2 new seeds = 12 pairs, seat-swapped, both arms cap60-p2, comparisons 4, stop_round 1 (ends at 2R start),
agentmaco, commit 04c278f, 2026-10-25 02:49 → 05:01 (2 h 12 min). **B is not today's all factory**: a017db1 and later E111 fixes
(far start, booster 5, Gleens, Ambas, 087bee7 start placement) came after the start. Result: lab/results/107-menu1-vs-all-1r-smoke.md.

**Health: not clean — 16/24 games, 8 error games.** All 8 are pairs 008–011 (quartets d and e, the Lost Fleet lineups), **both arms**,
crashing at about decision 4 (setup) with `ValueError: tuple.index(x): x not in tuple` in `_colony_cost`
(`teacher_patches.py:325` at 04c278f), reached through `plan_menu_goals → track_plan_goals → _opened_colonies` on the
navigation/AI track: Darkanians·Tinkeroids have home `Asteroid`, Moweyds·SpaceGiants `ProtoPlanet`, not on `RING`. plan_menu is in
both arms, so A crashed too — not a B part. Fixed d218d13 (non-ring home → 3 steps like non-ring targets; test added, 87 pass).
The other `RING.index(home)` sites (`:1253`, `:1842`, `:2295`, `:3724`, `:3931`, `:4103`) are already guarded.
Timeouts 0, fallback timeouts 0, federation limit hits 0. Decisions A 634 · B 640. Decision time A/B mean 24.5 / 23.9 s,
median 22.9 / 24.8, p90 60.0 / 59.4, **max 61.9 / 64.9 s** (cap60 expectation ≈ 80 s — no long path in 1R). Unsearched decisions
418 / 411.

## Charges in round 1 (reference, no verdict)

Charges from 1R start to 2R start (the .md header says 1–3R; stop_round 1). Per-pair B−A from `charges.json` seats.

| Faction | B parts | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| Ambas | all | 84.0 | 61.7 | −22.2 | [−283.3, +238.8] | 0/2 | −2, −43 |
| BalTaks | all | 83.5 | 44.5 | −39.0 | [−331.5, +253.6] | 0/2 | −16, −62 |
| Bescods | all | 91.4 | 85.0 | −6.3 | [−165.2, +152.5] | 1/2 | +6, −19 |
| Firaks | all | 78.1 | 43.9 | −34.2 | [−201.9, +133.5] | 0/2 | −47, −21 |
| Geodens | all | 46.4 | 89.2 | +42.8 | [−191.6, +277.3] | 2/2 | +61, +24 |
| Gleens | all | 106.7 | 80.2 | −26.5 | [−91.2, +38.2] | 0/2 | −21, −32 |
| HadschHallas | all | 74.9 | 57.2 | −17.7 | [−64.1, +28.7] | 0/2 | −14, −21 |
| Itars | all | 112.7 | 105.9 | −6.8 | [−159.6, +145.9] | 1/2 | +5, −19 |
| Ivits | all | 63.9 | 39.5 | −24.3 | [−112.0, +63.4] | 0/2 | −31, −17 |
| Lantids | all | 42.2 | 68.4 | +26.2 | [−188.5, +240.9] | 2/2 | +43, +9 |
| Nevlas | all | 66.2 | 42.8 | −23.3 | [−158.1, +111.4] | 0/2 | −13, −34 |
| Taklons | all | 63.4 | 71.6 | +8.1 | [−349.9, +366.2] | 1/2 | +36, −20 |
| Terrans | all | 106.5 | 92.1 | −14.4 | [−40.5, +11.7] | 1/4 | −14, −28, +9, −24 |
| Xenos | all | 91.5 | 118.4 | +26.9 | [−0.6, +54.5] | 4/4 | +46, +38, +11, +13 |
| Lost Fleet 4 | — | — | — | — | — | — | crashed in setup |
| **All (seat mean)** | | | | −6.1 | [−22.3, +10.0] | | 8 pairs |

Faction-pairs B > A: 12/32. Posted watch replay: `pair-005/game-0-A12` seat 0 — BalTaks B 36 vs 98.
VP at 2R start (not the verdict): +0.6 [−0.6, +1.8].

No verdict (pre-registered). Every faction is n = 2 (Terrans·Xenos 4), CIs span ±100–350, all within the ±50 per-pair same-code
drift (084/088) except BalTaks −62 and Geodens +61. Leaning: 10 of 14 means negative, Xenos 4/4 positive, Geodens·Lantids 2/2.
Reference 106 (ships vs menu1, 24 pairs): +4.3 [+0.0, +8.6].

## Activation (round 1, A → B)

Not counted: the smoke's question is health. Decision counts per faction move both ways (Taklons 37 → 59, Xenos 96 → 108,
Gleens 36 → 25, Ivits 31 → 25; `results.json` summary), so B's parts change play, but which part fired is not measured here.

## Reading (HANDOFF 1 order)

- Errors: ③ implementation — `_colony_cost` assumed a ring home; plan_menu never ran with Lost Fleet factions before (lab lineups were
  base quartets since E87). Fixed d218d13. Only 4 decisions per Lost Fleet seat ran, so a later crash past setup is still possible.
- Charges: ① noise — n = 2, nothing readable. The negative lean (10/14) is not a result; it is a flag for the next A/B. B also lacks
  today's E111 fixes, so it is not the arm that would be measured next.
- Health and timing: no long decisions in 1R (max 65 s); the 6R long path (E108) is not tested by a 1R run.

Code: d218d13 (crash fix, pushed). No deployment change. Lab queue empty after this.

## Proposal (user decision, nothing queued)

- (ㄱ) Re-run the smoke on quartets d·e only (4 seeds × seat swap = 8 games, 1R, ≈ 45 min–1 h) with today's all factory — checks the
  Lost Fleet path past setup and the E111/087bee7 fixes.
- (ㄴ) Then the measured A/B from E107 (나): menu1 vs all, new seeds 4R, 1–3R charges, base quartets (≈ 8–9 h) — the 107 negative
  lean is what it would confirm or clear.
- (ㄷ) E101 (ㄷ) 18-faction 1R mass run after (ㄱ) passes.
Bot recommendation: (ㄱ) → (ㄴ); (ㄷ) after the user has looked at the 106 replays.
