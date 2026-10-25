# Cycle 110 — ships_menu1_all_tier self-play — 18 factions round 1 diagnostic, no verdict

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(all factory + c3815fa starting-booster tier + 7ef9a1b·38fcbce faction booster prefs + 142ec7e·43f2361 colony_options
per-mine income). All four seats the same teacher (user 10-25 night "전부 B팔이면 안 되나? 모두 최선의 플레이를 해야",
"확장 종족까지"; E117, 109·109b dropped). Queued 10-25 night ("그렇게 해").
Pre-registered: **no verdict** — viewing run; A/B charges are same-code drift only. Review turn: health, booster
decision time, faction 1R charges (reference), booster table, `r1_waste.py` candidates, one replay per faction.
Quartets geo·a·b·c·d·e × 2 new seeds = 12 pairs × seat swap 24 games, cap60-p2, 4 comparisons, stop_round 1
(ends at round 2 start), agentmaco, **commit 9fcb58f**, 10-25 23:08 → 10-26 01:03 (1 h 54 min).
Result: lab/results/110-all-tier-selfplay-18f-1r.md.

**Commit note**: 9fcb58f is *before* da83db8 (hold) and 1fdb8f1 (debate 1/1: booster turn returns the tier pick
with no search, required orders before faction prefs) — `git merge-base --is-ancestor 1fdb8f1 9fcb58f` = no. Lab took
110 before the hold arrived. So 110 measured the first tier version (tier pick checked by **one** rollout comparison);
the required-order rule (big-building booster on an R1 big-building round tile, Geodens council → terraform, PG08-T05)
was not in it. 111 (queued later) has 1fdb8f1.

**Health: not clean — 22/24 games.** Both games of `pair-004` (seed quartet-b-63893, Itars·Bescods·BalTaks·Gleens)
crashed at **step 0** (first placement, 3 s after start): `ValueError: No eligible continuation; do not silently pass`
(`preparation.py:555`, `select_goal` returned None inside a placement rollout; `pair-004/game-*/workers.log`).
Same teacher in all seats → deterministic, both games identical. So quartet b has 1 pair. Timeouts 0, fallback-timeout 0,
federation-limit 0. Decisions A 624 · B 616; mean 21.4 / 21.0 s, median 22.1 / 21.5, p90 42.2 / 40.6, max 60.2 / 60.1 s.
**Booster decisions** (88, decision log + `list_decisions.py --rounds 0-0`): all `completed_comparisons` = 1, selected
`current-choice`; mean 10.1 s, max 15.8 s (108d full comparison: up to 61.9 s).

## Charges in round 1 (reference only — same teacher)

From the result table (R1 start → R2 start; B−A is same-code drift):

| Faction | Seats | 1R charges min · median · max | B−A (drift) |
|---|---:|---|---:|
| SpaceGiants | 4 | 99 · 102 · 104 | 0.0 |
| Itars | 2 | 67 · 87 · 106 | −39.4 (1 pair) |
| Terrans | 12 | 59 · 78 · 103 | −1.1 |
| Ambas | 4 | 59 · 73 · 83 | +1.9 |
| Gleens | 2 | 57 · 69 · 81 | −24.1 (1 pair) |
| BalTaks · Bescods | 2 · 2 | 64 · 64 · 64 · 61 · 64 · 67 | +0.1 · −5.7 |
| Darkanians | 4 | 56 · 63 · 69 | 0.0 |
| Geodens | 8 | 46 · 60 · 69 | −0.4 |
| Xenos | 12 | 51 · 58 · 105 | −2.3 |
| Taklons · Ivits · Tinkeroids | 8 · 4 · 4 | 38–75 · 55–56 · 53–58 (median 57 · 56 · 56) | 0.0 |
| HadschHallas | 4 | 51 · 54 · 79 | −13.8 |
| Moweyds | 4 | 45 · 52 · 73 | +6.8 |
| Lantids | 4 | 25 · 44 · 64 | 0.0 |
| **Nevlas** | 4 | **23 · 32 · 41** | 0.0 |
| **Firaks** | 4 | **20 · 29 · 39** | 0.0 |

(`charges.json` seats, recomputed median.) Drift: 13 of 18 factions exactly 0.0 (seat swap reproduces the game),
the rest within the ±30 / ±50 line except Itars −39.4 in its one pair (both seats same code: search timing). Lowest
round 1: Firaks and Nevlas (≈ 30 against a 60–80 field) — the first explain targets. 1R-end VP mean 7.9.

## Activation — booster picks (`list_decisions.py --rounds 0-0`, 22 games; both games of a pair give the same pick)

Pick order:booster per seed (booster ids from `booster_prefs.py`: 1 연구소 3점, 2 광석+토큰 2, 3 광산 1점, 4 큰 건물 4점(+4충전),
5 즉시 가이아, 6 포머 3점, 8 사거리+3, 9 QIC+2돈, 10 행성 종류 점수, 11 4돈+가이아 점수, 12 1테라, 13 광석+지식):

| Faction | Picks (order: booster) |
|---|---|
| Ambas | 3: 행성 종류 · 2: 큰 건물 |
| BalTaks | 1: 광석+지식 |
| Bescods | 3: 4돈+가이아 |
| Darkanians | 4: 행성 종류 · 1: 큰 건물 |
| Firaks | 4: 포머 3점 · 2: 광석+지식 |
| Geodens | 2: 1테라 · **1: QIC+2돈 (2 seeds)** · 3: 행성 종류 |
| Gleens | 4: 즉시 가이아 |
| HadschHallas | 4: 연구소 3점 (2 seeds) |
| Itars | 2: 광산 1점 |
| Ivits | 3: 1테라 · 4: 행성 종류 |
| Lantids | 2: 사거리+3 · 1: 사거리+3 |
| Moweyds | 1: 1테라 · 2: 1테라 |
| Nevlas | 1: 큰 건물 · 3: 광산 1점 |
| SpaceGiants | 1: 큰 건물 · 3: 즉시 가이아 |
| Taklons | 3: 행성 종류 · 4: 연구소 3점 · 2: 큰 건물 · 3: 광석+지식 |
| Terrans | 1: QIC+2돈 · 2: 사거리+3 · 2: 광산 1점 · 3: 4돈+가이아 · 2: 1테라 · 4: 1테라 |
| Tinkeroids | 4: 연구소 3점 · 4: 행성 종류 |
| Xenos | 4: 즉시 가이아 · 3: 즉시 가이아 · 1: 사거리+3 · 1: 1테라 · 3: 광산 1점 · 2: 사거리+3 |

Geodens first pick QIC+2돈 twice: the all factory opens Geodens with a council (E106), where PG08-T05 says 1테라 is
best — the rule 1fdb8f1 added after this run. 4th seats mostly end with a VP booster (연구소·행성 종류), as expected.

**Waste candidates** (`r1_waste.py`, round 1, candidates only — E117 debate: a flag is a defect only after explain):
88 seats, 62 with a ship entry; **ship-unused 39** (A 19 · B 20), **gaia-skipped 16** (8 · 8). Largest `pass_gaia`:
Ambas pair-007 g0-A23 s2 (10 options at pass), Terrans pair-000 both games s3 (8), Firaks pair-002 s0 (5, also the lowest
charges), Geodens pair-009 s3 `pass_ship` 11 after 2 entries.

## Reading (HANDOFF 1 order)

- No verdict (pre-registered). Same-teacher drift: ① noise only; 13/18 factions reproduce exactly on seat swap.
- **Crash pair-004**: ③ implementation — a placement rollout reached a state where `select_goal` found no eligible
  candidate. Not yet reproduced; 111 uses the **same 12 seeds** and will meet quartet-b-63893 again (likely the same
  crash, unless the 1fdb8f1 / 6b0bc65 changes avoid that rollout path).
- Booster part ② fired in its first form (1 comparison, ≤ 16 s); the required-order rule is ③ absent from this run, so
  the Geodens QIC first picks are not a judgement on the current code.
- Firaks / Nevlas ≈ 30 charges: candidates for explain (Firaks pair-002 also skipped 5 gaia options).

No code or deployment changes. **Replays**: 18 posted (one per faction, seat focus, game closest to that faction's
median 1R charges) + lab auto `pair-005/game-1-A03` Itars = 19 on the site; older experiments removed by
`publish_replays.py`. List: Ambas p006 g0-A02 s1 · BalTaks p005 g0-A12 s3 · Bescods p005 g0-A12 s1 · Darkanians p010
g0-A01 s0 · Firaks p002 g0-A03 s0 · Geodens p008 g0-A03 s1 · Gleens p005 g0-A12 s0 · HadschHallas p006 g0-A02 s0 · Itars
p005 g0-A12 s2 · Ivits p002 g0-A03 s1 · Lantids p002 g0-A03 s2 · Moweyds p008 g0-A03 s3 · Nevlas p002 g0-A03 s3 ·
SpaceGiants p010 g0-A01 s3 · Taklons p000 g0-A02 s1 · Terrans p010 g0-A01 s2 · Tinkeroids p008 g0-A03 s0 · Xenos p000
g0-A02 s0. Lab queue after this: 111-all-tier2-selfplay-18f-1r, 112-tier2-strength-order-18f-1r.

No second-model review section in the result page.

## Proposal (user decision, nothing queued)

- (ㄱ) Bot turn before 111 starts: reproduce pair-004 step 0 (quartet-b-63893) and fix the empty continuation, or hold
  111 with `_` until fixed — otherwise 111 likely loses the same pair (≈ 10 min of lab, 1 of 12 pairs).
- (ㄴ) User watches the 18 replays and names frames → explain (Firaks, Nevlas lowest first).
- (ㄷ) explain one `gaia-skipped` case (Ambas p007 or Terrans p000) and one Geodens `pass_ship` 11 case.
Bot recommendation: (ㄱ) now, (ㄴ) in parallel; 111 then answers the current booster code.
