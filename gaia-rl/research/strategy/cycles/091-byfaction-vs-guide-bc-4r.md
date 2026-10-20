# Cycle 091 — ships_byfaction vs ships_byfaction_guide on quartets b and c, 4 rounds (the rest of the faction guides)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-cap20.json` (the B arm of 085–087:
deployment stack + `CANDIDATE_FACTION_PARTS`, i.e. track_set for the ten base factions, Terrans track_income).
B = `...-ships-byfaction-guide-cap20.json`: the same plus `GUIDE_FACTION_PARTS` — **track_steps** (round targets
for a track level), **track_caps** (the level a guide stops a track at), **building_limits**, the BalTaks academy
start (**opening_only** + **fixed_academy** with the Taklons budget tools), track_set for the four Lost Fleet
factions, **tile_prefs** (standard tiles a guide asks for or avoids: HadschHallas, Bescods, Ambas, BalTaks, Itars,
Ivits, Lantids, Geodens) and **niche_tracks** (HadschHallas: the Gaia / Terraforming / AI track the others leave
alone once Economy 2 or Navigation 2; Xenos: Gaia 2 in rounds 1–3 when no Gaia faction is at the table).
Queued by the user on 2026-10-20 ("기존 자료에 있는 내용 쓸만하면 반영 … 그 후에 실험 시작하자", 5a R2 ⑤).
Pre-registered verdict: charges gained in rounds 1–3 by faction (1 VP = 1.5 charges); read alongside: activation
(research_counts, upgrade_counts, the tile numbers taken), decision time, errors; if bad, HANDOFF 1's order
(noise → activation → implementation → conflicts → measure → conditions → source).
quartet-b (BalTaks, Bescods, Gleens, Itars) × 6 seeds + quartet-c (Ambas, HadschHallas, Terrans, Xenos) × 6 seeds,
seat-swapped pairs, hard budget (4 comparisons, 20 s), stop at the start of round 4, agentmaco, commit 3be52cc,
14:05 → 17:01 (2 h 57 min). Result: lab/results/091-byfaction-vs-guide-bc-4r.md.

**Health: clean.** 24 of 24 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1803 vs 1795; A mean 11.48 s, median 17.85 s, max 22.0 s; B mean 11.29 s, median 16.86 s,
max 24.8 s. Unsearched 1279 vs 1248. The new parts cost no time.

## Charges in rounds 1–3 (the verdict)

| Faction | B parts in 091 | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| **Itars** | track_caps (Nav 2), tile_prefs (6, 8, 4, 10, 7) | 170.3 | 106.8 | **−63.4** | **[−86.0, −40.8]** | **0 / 6** | −92 · −59 · −58 · −83 · −58 · −31 |
| BalTaks | track_steps (Gaia 4 R1), caps (AI 4), building_limits, opening_only + fixed_academy + budget, tile_prefs (3, 5, 10; avoid 2) | 163.3 | 178.8 | +15.5 | [−3.5, +34.4] | 5 / 6 | +9 · +25 · +39 · +28 · −9 · +1 |
| Bescods | track_steps (Sci 2 R1, Eco 2 R2, Nav 2 R3), caps (Nav 2, Eco 4), tile_prefs (6; avoid 3) | 219.5 | 203.6 | −15.9 | [−39.0, +7.1] | 2 / 6 | −10 · −16 · −5 · −36 · −45 · +16 |
| Gleens | track_steps (Nav 2 R1), caps (Nav 4) | 179.3 | 172.0 | −7.3 | [−23.5, +8.9] | 2 / 6 | −2 · −24 · −15 · +11 · +9 · −22 |
| Ambas | caps (Gaia 1), building_limits, tile_prefs (avoid 2) | 144.1 | 144.6 | +0.5 | [−36.0, +37.0] | 3 / 6 | +16 · −5 · −52 · −24 · +45 · +23 |
| HadschHallas | track_steps (Eco 2), caps (Nav 2, Eco 4), tile_prefs (2; avoid 3), niche_tracks | 141.7 | 156.1 | +14.3 | [−23.2, +51.9] | 4 / 6 | +54 · +2 · +59 · −31 · −10 · +12 |
| Terrans | **none (same code)** | 172.0 | 174.3 | +2.3 | [−46.5, +51.1] | 4 / 6 | −38 · +39 · +42 · +15 · −72 · +27 |
| Xenos | niche_tracks — **never fires** (Terrans at the table is a Gaia faction) = same code | 142.1 | 149.5 | +7.4 | [−49.8, +64.6] | 2 / 6 | −23 · −42 · +67 · −23 · −21 · +86 |
| **All (seat mean)** | | | | **−5.8** | [−18.6, +6.9] | | 12 pairs |

Terrans and Xenos ran the same code on both arms, so quartet c carries its own drift yardstick: faction means
+2.3 and +7.4, single pairs up to ±86, CI half-width ≈ 50 with 6 pairs. Nothing in quartet c is readable against
that (HadschHallas +14.3, Ambas +0.5). Quartet b has no same-code faction; 088's rule applies (a faction
difference under 25 cannot be read) — BalTaks +15.5 and Bescods −15.9 are below it, **Itars −63.4 is not**: six of
six pairs negative, the smallest −31, the CI entirely outside the ±30 drift of 084/088.

Posted watch replay: `pair-000/game-1-A13` seat 0 — Itars B 103 vs Itars A 194 in the other game of the pair.

VP at the start of round 4 (not the verdict): all −1.0 [−3.3, +1.2]; Bescods −5.8 (18.0 → 12.2), Ambas −2.8,
Itars −0.7 (15.7 → 15.0), BalTaks −1.2, Gleens +2.0, the rest within ±1.

## Activation (rounds 1–3, A → B, 6 seat-games per arm)

**Standard tiles taken** (new `tools/tile_counts.py`; engine ids 2 ore+charge income, 3 four credits, 4 ore+QIC,
5 knowledge+credit income, 6 big buildings power 4, 7 VP now, 8 VP per Gaia mine, 9 knowledge per planet type,
10 charge-4 action):

| Faction | A tiles | B tiles |
|---|---|---|
| **Itars** | 2 ×4 · 3 ×1 · 5 ×5 · 9 ×1 · 10 ×3 (14) | **6 ×6 · 8 ×4** · 4 ×1 · 9 ×1 · 10 ×1 (13) — tiles 2 and 5 never |
| Bescods | 2 ×4 · 4 ×1 · 5 ×1 · 10 ×2 (8) | **6 ×6** · 5 ×1 · 7 ×1 · 8 ×1 · 10 ×2 (11) — tile 2 never |
| BalTaks | 2 ×5 · 3 ×2 · 5 ×3 · 10 ×2 (12) | 3 ×6 · 5 ×5 · 10 ×5 · 2 ×1 (17) |
| HadschHallas | 2 ×1 · 4 ×4 · 5 ×2 · 8 ×2 · 9 ×1 · 10 ×2 (12) | **2 ×6** · 4 ×3 · 5 ×2 · 8 ×1 · 10 ×2 (14), tile 3 none on either arm |
| Ambas | 2 ×3 · 4 ×1 · 5 ×4 · 8 ×1 · 10 ×3 · adv ×1 (13) | 2 ×2 · 3 ×2 · 4 ×2 · 5 ×5 · 10 ×4 (15) |
| Gleens | 2 ×4 · 5 ×3 · 9 ×1 · 10 ×6 (14) | 2 ×4 · 5 ×2 · 9 ×1 · 10 ×3 (10) |
| Terrans (same code) | 2 ×4 · 3 ×2 · 5 ×5 · 7 ×1 · 10 ×2 (14) | 2 ×2 · 3 ×2 · 4 ×1 · 5 ×4 · 8 ×1 · 9 ×1 · 10 ×5 (16) |
| Xenos (same code) | 2 ×1 · 3 ×1 · 4 ×4 · 5 ×2 · 7 ×1 · 10 ×2 (11) | 2 ×2 · 3 ×1 · 4 ×4 · 5 ×2 · 8 ×2 · 10 ×2 (13) |

tile_prefs fired exactly as written: every Itars B seat-game took tile 6 and most took tile 8; every Bescods B
seat-game took tile 6; HadschHallas B took tile 2 six times; BalTaks B moved to 3 / 5 / 10.

**Research** (`research_counts.py --rounds 1-3`, TF / Nav / AI / Gaia / Eco / Sci):

| Faction | A | B | Footprint |
|---|---|---|---|
| Itars | 6 / 1 / 3 / 12 / 2 / 1 = 25 | 2 / 0 / 1 / 9 / 3 / 0 = **15** | research −10 (knowledge income tile 5 gone) |
| BalTaks | 4 / 0 / 7 / 8 / 2 / 1 = 22 | 6 / 0 / 1 / 12 / 2 / 3 = 24 | track_steps Gaia 4 in R1: Gaia 8 → 12, AI 7 → 1 |
| Bescods | 0 / 5 / 5 / 0 / 1 / 4 = 15 | 0 / 1 / 0 / 0 / 2 / 8 = 11 | track_steps Science first: Sci 4 → 8, Nav 5 → 1, AI 5 → 0 |
| Gleens | 0 / 6 / 0 / 17 / 0 / 1 = 24 | 3 / 10 / 0 / 9 / 0 / 0 = 22 | track_steps Nav 2 R1: Nav 6 → 10, Gaia 17 → 9 |
| HadschHallas | 3 / 17 / 1 / 1 / 5 / 0 = 27 | 4 / 5 / 4 / 4 / 11 / 0 = 28 | caps Nav 2: 17 → 5; track_steps Eco 2: 5 → 11; niche Gaia / AI / TF 5 → 12 |
| Ambas | 13 / 0 / 2 / 1 / 5 / 2 = 23 | 13 / 0 / 3 / 0 / 5 / 2 = 23 | caps Gaia 1: 1 → 0 |
| Terrans (same code) | 3 / 0 / 13 / 3 / 9 / 3 = 31 | 4 / 0 / 8 / 2 / 9 / 1 = 24 | drift alone moves research by 7 |
| Xenos (same code) | 1 / 18 / 0 / 2 / 4 / 0 = 25 | 1 / 14 / 1 / 0 / 4 / 0 = 20 | drift |

**Upgrades** (`upgrade_counts.py`, TS / RL / PI / AC, rounds 1–3; round-1 academies in brackets): Itars 12 / 12 /
0 / 5 → 11 / 11 / 1 / **2**; Bescods 13 / 8 / 2 / 4 → 13 / 12 / 3 / **0**; **BalTaks 11 / 11 / 0 / 4 [R1 AC 0] →
12 / 12 / 0 / 5 [R1 AC 5 of 6]** (every B round-1 plan was 1AC+1M or 1AC+2M; A played 1RL+2M / 1RL+3M); HadschHallas
16 / 11 / 0 / 4 → 20 / 12 / 0 / 5 (round-1 trading stations 8 → 13); Ambas academies 4 → 2 (building_limits);
Gleens 12 / 13 / 0 / 3 → 11 / 10 / 0 / 4; Terrans 12 / 13 / 0 / 8 → 12 / 14 / 0 / 6; Xenos 18 / 10 / 0 / 2 → 13 /
11 / 0 / 3. Itars B also opened with the institute more often (round-1 plan labels 1PI+1TS+1M / +2M 16 of 42 vs
A 7 of 51); no opening part is on for Itars in 091, so that is plan drift behind the changed tile values.

## Reading (HANDOFF 1 order)

- **Verdict: Itars fails** (−63.4, 6 / 6, CI far outside drift); everything else is unreadable at 6 pairs. All
  −5.8 [−18.6, +6.9]. ① Not noise. ② The parts fired as written (table above). ③ **Implementation — scope**:
  B7-01's tile list ("의회로 가져갈 기술은 큰 건물 4티어·가이아당 3점·1정보 1광석·4충전·즉발 점수·행동당·패스당") is
  the list of tiles to take **with the institute's ability** (4 Gaia-area tokens → a tile, the Itars-PI Gaia-tech
  move), where a tile costs tokens and income tiles are poor value. The code applies the preference to **every**
  standard tile choice, so the round-1 lab and the academies took tile 6 (big-building power, no income) and tile 8
  (VP per Gaia mine) instead of tile 5 (knowledge + credit) and tile 2 (ore + charge). With no knowledge income
  research fell 25 → 15, academies 5 → 2, charges 170 → 107. The same scope error sits under Bescods: B13-04 puts
  the big-building tile at the institute / academy step **after** two labs ("연구소 2개 → 행성 의회와 지식 아카데미(4티어
  기술) → 연방 선언"), the code took it with the first lab in all six seat-games (tile 2 4 → 0, academies 4 → 0,
  charges −15.9, VP at R4 18.0 → 12.2).
- **BalTaks academy start works mechanically** (R1 academies 0 → 5 of 6, Gaia 8 → 12, the guide's tiles) and leans
  positive (+15.5, 5 / 6, CI touching 0, VP −1.2) — below 088's 25-charge readability line, so "direction positive,
  unconfirmed". The 086 question (R1 academies 0 / 12) is answered: the budget tools let the academy be paid.
- **HadschHallas parts fire as written** (Navigation stopped at 2, Economy 2 first, niche tracks 5 → 12 steps, tile
  2 six times) and the charges lean positive (+14.3, 4 / 6), but quartet c's same-code pairs swing ±86, so this
  cannot be read here. 088's "lowest charges" question stays open; 092 / 093 (A = guide) carry these parts on both
  arms.
- **Xenos niche_tracks has no trigger in quartet c** (Terrans is a Gaia faction) — it was measured nowhere. Gleens
  (−7.3) and Ambas (+0.5): fired, unreadable.
- 092–094 (guide vs weak / src / res) run with `byfaction_guide` as the A arm, so the Itars and Bescods tile scope
  is on both arms there and cancels in the difference; their Itars baseline is weak until fixed, nothing in the
  queue needs changing.

Nothing changed in code or deployment (only `tools/tile_counts.py` added). 092 → 093 → 094 → 095 → 096 stay queued.

## Proposal (user decision, nothing queued)

- (ㄱ) **Fix tile_prefs scope (③) and re-measure quartet b.** Itars: apply the preference only to the institute's
  Gaia-phase tile choice (the Itars-PI Gaia-tech move), never to lab / academy tiles. Bescods: apply tile 6 only
  when the tile comes with an institute or academy upgrade (B13-04's step), not with a lab. Other factions'
  prefs are income or action tiles and stay. Then byfaction vs byfaction_guide, quartet b, the same six seeds, 4R
  (≈ 1.5 h for both quartets, ≈ 45 min for b alone). Expected: Itars back near 0, Bescods tile 2 back.
- (ㄴ) **BalTaks academy start, six new quartet-b seeds** (12-pair pool with 091) in the same run as (ㄱ): decide on
  the pooled charges; keep the Taklons budget tools with it.
- (ㄷ) Quartet c: no re-run yet; read HadschHallas again from 092 / 093 (A = guide on both arms gives a cleaner
  HadschHallas baseline) and, if the user wants a direct read, a 12-seed quartet-c run (drift needs the pool).

Bot recommendation: (ㄱ) as a bot turn (code + tests, then the user's yes to queue), (ㄴ) in the same queue entry.
