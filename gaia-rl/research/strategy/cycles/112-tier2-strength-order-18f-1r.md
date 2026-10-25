# Cycle 112 — all_tier self-play with strength turn order (`@order`), 18 factions — diagnostic, 1R

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json` (same code as 111).
Part under test: no teacher part — the seed suffix `@order` (engine 1d3fc6c) sets the setup turn order from
`tools/faction_strength.py` (tier · tech tiles · planet layout, equal weights, neighbour/round terms off; user 10-26
"예전 자료는 오염"): weakest faction moves 1st, strongest 4th. Queued 2026-10-26 by the user ("한번 테스트 받아보고 싶긴 하네", E117).
Pre-registered verdict: **none** (same teacher both arms; swapped seats are repeat samples). Read: ① placement order with
faction exceptions + booster reverse order match `@order` ② how the 4th-turn strong faction places and picks boosters
(replays) ③ 1R charges by turn position (reference).
Quartets geo·a·b·c·d·e × 2 new seeds = 12 pairs × seat swap = 24 games, comparisons 4, cap60-p2, stop round 1,
agentmaco, commit 5eb0d0c, 2026-10-26 03:32 → 06:00 (2 h 28 min). Result: lab/results/112-tier2-strength-order-18f-1r.md.

**Health: not clean — 22/24 games.** `pair-005` (quartet-b-67485, Bescods·BalTaks·Itars·Gleens) both games
stopped at step 1 with `ValueError: No eligible continuation` (`preparation.py:555`, workers.log) — the same failure
as 110/111 quartet-b pair-004. This run started at 5eb0d0c, **before** the fix d5946bd/61edf20 (gaia_asteroid_hold
never blocks every candidate), so the fix is not tested here. Timeouts 0, fallback decisions 0, federation-limit
hits 0. Decisions A 667 · B 679; mean 24.1 / 24.7 s, median 25.2 / 25.7 s, p90 52.7 / 51.6 s, max 64.8 / 62.4 s
(cap60 range).

## Charges (reference only — same teacher both arms)

| Faction | A | B | B−A | 95% CI | Pairs |
|---|---:|---:|---:|---|---:|
| Terrans | 95.3 | 98.6 | +3.3 | [−2.3, +8.9] | 6 |
| Xenos | 86.3 | 90.3 | +4.1 | [−4.9, +13.0] | 6 |
| Taklons | 82.5 | 87.4 | +5.0 | [−10.8, +20.7] | 4 |
| Geodens | 72.4 | 71.7 | −0.7 | [−2.9, +1.5] | 4 |
| Nevlas | 42.8 | 55.5 | +12.7 | [−148.7, +174.1] | 2 |
| Ivits | 79.0 | 89.2 | +10.3 | [−120.0, +140.5] | 2 |
| others (12) | | | −8.2 … +4.2 | | 1–2 |
| **All (seat mean)** | | | **+1.8** | [−0.5, +4.0] | 11 |

All factions inside the ±30 same-code drift — as expected, A = B. Posted lab auto replay: `pair-002/game-0-A03`
seat 1 (Nevlas, B 58 vs A 33 — drift, not a result).

## Activation (turn order)

Decision log (`decisions.jsonl.gz`, seat of every searched decision at steps 0–12, all 22 games, bot one-liner)
against each game's `@order`: **all 22 match**.
- Base quartets: first pass in `@order`, second pass reversed, Xenos' 3rd mine after it, then boosters in reverse order
  (e.g. geo `order=2,0,3,1`: seats 2031 · 1302 · 1 · 1302).
- Ivits: placed after the reverse pass, booster first (reverse order) — p001 `2,0,1,3` → 201 · 102 · 3 · 3102.
- Lost Fleet one-building factions (Moweyds, Tinkeroids, SpaceGiants, Darkanians) skip the first pass and place in the
  reverse pass at their reverse position (quartet-d `2,0,1,3`: 13 · 3102 · boosters 3102; quartet-e `1,2,3,0`: 20 · 0321 · 0 · 0321)
  — matches `engine.rs` `starting_placement_queue`.

1R charges by turn position (charges.json, 22 games × 4 seats, reference):

| Turn | Seats | Mean | Min–max | Factions there |
|---:|---:|---:|---|---|
| 1 (weakest) | 22 | 72.3 | 36–114 | Terrans 8 · Lantids 4 · Tinkeroids 4 · Darkanians 4 · BalTaks 2 |
| 2 | 22 | 70.9 | 37–109 | |
| 3 | 22 | 65.7 | 33–105 | |
| 4 (strongest) | 22 | 94.6 | 67–117 | Xenos 8 · Ivits 4 · Ambas 4 · Bescods 2 · Taklons 2 · Geodens 2 |

The 4th seat is highest, but turn position and faction are the same variable here (order comes from strength), so this
does not show that the late turn helps or hurts. Note: `faction_strength.py` put **Terrans weakest in all 8** of their
games, while Terrans are the 2nd-highest charger in the run (95–99) — the ranking disagrees with in-game 1R charges.

## Reading (HANDOFF 1 order)

- ② activation: `@order` works as written for every faction exception (placement and booster order), 22/22.
- ① noise: arms are the same code; every faction within drift.
- ④/⑥ the 1R position means cannot separate order from faction; an order effect needs the same factions at different
  positions (same seed, `@order` permuted).
- ③ the strength tool's Terrans ranking is a scope question for `faction_strength.py` (tier list vs map terms), not a
  turn-order result.
- Health: pair-005 crash = known bug, run predates the fix.
- Second-model review: the result page has no `## 검수` section.

No code or deployment changes. The 18 per-faction replays in the design are **not posted yet** (bot tools need the
work-tree extension rebuilt with `maturin develop` to read `@order` seeds); only the lab auto replay is on the site.
Lab after this: queue empty.

## Proposal (user decision, nothing queued)

- (ㄱ) Publish the 18 per-faction replays (rebuild extension, then publish; 111's removed) — bot turn, lab 0.
- (ㄴ) Order effect: same seeds, two `@order` variants (strength order vs reversed) → same factions at turn 1 and 4,
  1R, 24 games ≈ 2.5 h; also re-runs quartet-b-67485 with the d5946bd fix.
- (ㄷ) Check `faction_strength.py` Terrans ranking (why weakest in 8/8) — bot turn.
Bot recommendation: (ㄱ) + (ㄷ) first, then (ㄴ).
