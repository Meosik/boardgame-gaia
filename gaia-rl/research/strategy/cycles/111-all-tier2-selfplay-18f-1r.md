# Cycle 111 — all_tier (booster value v2) self-play — 18 factions, round 1 diagnostic, no verdict

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json` (all four seats the
same teacher, 061 precedent). Booster value v2 against 110: 1fdb8f1 (immediate return, required order — 1R big-building
tile, Geodens council start → 1테라) + 6b0bc65…e379dbf (booster value = LF02 charge value + first-opening pass score at
1 VP = 1.0 charge + situation terms; range +3 always 9, power tokens base 8 — LF04 L4-18; instant gaia 5 when not
reachable in 1R; faction prefs unchanged). Queued 2026-10-26 01:09 (E117, user's second booster critique "맨 윗 순서는 다
비슷비슷 … 사거리 3·가이아포밍 2는 너무 작다 … 파워토큰 +2 평가가 박하다").
Pre-registered verdict: **none** (diagnostic). Same 12 seeds as 110 to observe the combined change (no cause split,
design review 1/1). Read alongside: health, booster picks vs 110 by seed and seat, `r1_waste.py` candidates, one replay
per faction.
Quartets geo·a·b·c·d·e × 2 seeds = 12 pairs × seat swap (24 games), comparisons 4, cap60-p2, stop after round 1,
agentmaco, commit 1b65403, 2026-10-26 01:15 → 03:32 (2 h 17 min). Result: lab/results/111-all-tier2-selfplay-18f-1r.md.

**Health: not clean — 22/24 games.** `pair-004` (quartet-b-63893: Itars · Bescods · BalTaks · Gleens) crashed in **both
games again** with `No eligible continuation` (`preparation.py:555`, via `teacher_patches.py:1527 → :380` rollout, from
`:4527`/`:1760` search) — in 110 at step 0 (placement), now in round 1 after the boosters (decision log ends at step 15).
Same seed, same error, two code versions → **reproducible bug on this seed**, not chance. Timeouts 0, fallback 0,
federation misses 0. Decisions A 668 · B 670; mean 24.3 / 23.7 s, median 24.2 / 23.3, p90 57.9 / 55.0, max 66.4 / 66.4 s
(cap60 range).

## Round 1 charges (reference only — same teacher both arms)

Seat-swap drift A vs B (results .md): all factions inside ±30 (BalTaks −29.0 n=1 the edge); exact 0.0 in 7/18
(Darkanians, Firaks, Ivits, Lantids, Nevlas, SpaceGiants, Gleens +0.1). All −1.6 [−4.4, +1.2].

**111 vs 110, same game folder and seat** (88 seats, `charges.seats` of both result .json; not a verdict — all four seats
changed and two games of a pair are near copies, so ≈ 44 independent seats):

| Faction | Seats | 110 mean | 111 mean | 111−110 | Seats up |
|---|---:|---:|---:|---:|---:|
| Xenos | 12 | 69.8 | 92.9 | +23.1 | 8/12 |
| Terrans | 12 | 80.7 | 96.6 | +16.0 | 9/12 |
| Taklons | 8 | 56.7 | 69.7 | +12.9 | 7/8 |
| Geodens | 8 | 59.0 | 63.6 | +4.5 | 2/8 (−50 … +80) |
| Tinkeroids | 4 | 55.8 | 78.2 | +22.4 | 4/4 |
| Nevlas | 4 | 32.1 | 53.0 | +21.0 | 4/4 |
| Ivits | 4 | 55.6 | 71.8 | +16.2 | 4/4 |
| Gleens | 2 | 68.9 | 96.0 | +27.2 | 2/2 |
| Bescods | 2 | 63.9 | 83.5 | +19.6 | 2/2 |
| BalTaks | 2 | 63.7 | 72.1 | +8.4 | 1/2 |
| Lantids | 4 | 44.2 | 50.8 | +6.6 | 2/4 |
| Darkanians | 4 | 62.6 | 67.2 | +4.6 | 2/4 |
| SpaceGiants | 4 | 101.6 | 104.9 | +3.3 | 2/4 |
| Firaks | 4 | 29.4 | 27.0 | −2.4 | 2/4 |
| Moweyds | 4 | 55.3 | 52.2 | −3.1 | 2/4 |
| Ambas | 4 | 72.0 | 67.5 | −4.5 | 0/4 |
| **HadschHallas** | 4 | 59.3 | 26.3 | **−32.9** | 0/4 (−63 … 0) |
| **Itars** | 2 | 86.8 | 48.8 | **−38.0** | 0/2 |
| **All** | 88 | | | **+8.7** | 54/88 |

Posted watch replay (lab auto): `pair-008/game-0-A03` seat 1 Geodens (B 60 vs A 18). 1R-end VP mean 7.4 / 7.0 (110: 7.9).

## Activation — booster picks vs 110 (`list_decisions.py --rounds 0-0`, 88 common seats)

- **Placement changed in 70/88 seats, booster in 56/88**; 46 of the 56 booster changes come with a changed placement
  (the placement rollout sees the new booster values), so most changes are not booster-only.
- Same placement, different booster (10 seats = 5 seeds × 2 games): **Geodens p009 first pick QIC+2돈 → 1테라** (the
  1fdb8f1 council rule fired), Terrans p000 first QIC+2돈 → 1테라, Terrans p006 광산 1점 → 사거리+3, Moweyds p008 first
  1테라 → 광석+토큰 2, Xenos p006 first 사거리+3 → 광석+토큰 2.
- Pick totals 110 → 111 (110: 88 seats, 111: 96 incl. pair-004's round-1 games): 광석+토큰 2 **0 → 10**, 연구소 3점 8 → 4, 4돈+가이아 4 → 2, 행성 종류 12 → 10,
  QIC+2돈 6 → 8, 1테라 14 → 14, 사거리+3 10 → 10, 큰 건물 10 → 10. The power-token booster (raised to base 8) now
  gets taken; VP boosters drop.
- Losing factions: **HadschHallas** all 4 seats 4th pick 연구소 3점 → 광산 1점 (p006) / 4돈+가이아 (p007), with changed
  placement; **Itars** p005 2nd pick 광산 1점 → 광석+지식 / 광석+토큰 2. Contra-rule: Geodens p000 2nd pick
  1테라 → QIC+2돈 (placement changed — check whether that start is a council opening).

**Waste candidates** (`r1_waste.py`, round 1, 96 seats incl. pair-004 round 1; candidates only, E117 debate):
with ship entry 67, **ship-unused 40** (A 21 · B 19; 110: 39 of 88), **gaia-skipped 10** (5 · 5; 110: 16). Recurring:
Firaks pair-002 `pass_gaia` 5 in both games (also the lowest charges again, 24–30), Terrans p000/p010 gaia-skipped both
games, SpaceGiants p011 both games, Moweyds p008 `pass_ship` 7, Darkanians p010 `pass_ship` 3.

## Reading (HANDOFF 1 order)

- No verdict (pre-registered). Within-run drift is ① noise only (all inside ±30).
- 111 vs 110: the whole table gains +8.7 charges per seat, 54/88 up, with Xenos/Terrans (12 seats each) +23/+16 —
  the direction the user's critique aimed at (more power tokens, fewer early VP boosters). It is an observation, not a
  result: ④ all seats changed together and placements moved in 70/88 seats, so the booster value cannot be separated
  from the placement change, and cross-run differences carry the ±30 drift.
- HadschHallas −33 (0/4) and Itars −38 (n=2) are outside ±30 — explain targets (② the HadschHallas VP booster
  preference lost to a raw-value term, or ③ the new opening pass score misjudges their council openings).
- **Crash pair-004**: ③ implementation, now reproduced on the same seed in two runs (setup in 110, round 1 in 111) —
  a rollout reaches a state with no eligible goal. It also blocks quartet b data (1 pair per run). Fix before any
  run that reuses quartet-b-63893.
- Firaks still lowest (27, unchanged) with 5 skipped gaia options at pass in the same seed — first explain target.

No code or deployment changes. **Replays**: 18 posted (one per faction, seat focus, game closest to that faction's
median 1R charges) + lab auto 1 = 19 on the site; 110's removed by `publish_replays.py`. List: Ambas p006 g0-A02 s1 ·
BalTaks p005 g0-A12 s3 · Bescods p005 g0-A12 s1 · Darkanians p010 g0-A01 s0 · Firaks p002 g0-A03 s0 · Geodens p008
g0-A03 s1 · Gleens p005 g0-A12 s0 · HadschHallas p006 g0-A02 s0 · Itars p005 g0-A12 s2 · Ivits p002 g0-A03 s1 · Lantids
p002 g0-A03 s2 · Moweyds p008 g0-A03 s3 · Nevlas p002 g0-A03 s3 · SpaceGiants p010 g0-A01 s3 · Taklons p001 g0-A23 s0 ·
Terrans p001 g1-A01 s2 · Tinkeroids p009 g0-A13 s0 · Xenos p000 g0-A02 s0. Lab after this: 112-tier2-strength-order-18f-1r
(new seeds with `@order`).

No second-model review section in the result page.

## Proposal (user decision, nothing queued)

- (ㄱ) Bot turn: reproduce pair-004 (quartet-b-63893, game-0-A01 to step 16) and fix the empty continuation in the
  rollout (`teacher_patches.py:380`/`:1527` → `preparation.py:555`), with a test. Lab 0.
- (ㄴ) Explain turn (lab 0): HadschHallas p006 s0 4th booster (연구소 3점 → 광산 1점) and Itars p005 s2; Firaks p002 s0
  gaia skipped at pass; Geodens p000 s2 QIC+2돈 second pick.
- (ㄷ) User watches the 18 replays and names frames → explain.
Bot recommendation: (ㄱ) + (ㄴ) in one bot turn while 112 runs; keep the booster v2 values (whole table +8.7, no reason
to roll back) unless the explain finds a defect.
