# Cycle 098 — ships_byfaction vs ships_byfaction_guide on quartet b after the tile_prefs scope fix, 4 rounds

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-cap20.json` (deployment stack +
`CANDIDATE_FACTION_PARTS`: track_set for the ten base factions, Terrans track_income).
B = `...-ships-byfaction-guide-cap20.json`: the same plus `GUIDE_FACTION_PARTS` — the 091 design with one code
change (E39, 2026-10-20): **tile_prefs scope**. `TILE_PREFS[...]['only']` — Itars `'ability'` (the list 6 · 8 · 4 · 10 · 7
of B7-01 "의회로 가져갈 기술" applies only to the tile chosen by the institute's Gaia-phase move,
`ItarsGaiaTechTile`), Bescods `'big'` (tile 6 of B13-04 only when the tile comes with an institute or academy
upgrade); lab tiles of both factions go back to the search. Everything else as in 091: track_steps, track_caps,
building_limits, the BalTaks academy start (opening_only + fixed_academy + the Taklons budget tools), track_set
for the four Lost Fleet factions, tile_prefs for the other factions, niche_tracks.
Queued by the bot on 2026-10-20 (user "테스트 오래 걸리는데 미리 만드는거 어때"; HANDOFF E35 (ㄱ)+(ㄴ)).
Pre-registered verdict: charges gained in rounds 1–3 by faction — **Itars must come back near 0** (otherwise ③ has
another cause); **BalTaks is judged on the 12-pair pool** of 091's six pairs and the six new seeds here. Read
alongside: tile_counts (Itars / Bescods tiles 2 and 5 back, tile 6 count), research_counts, upgrade_counts (BalTaks
round-1 academies), decision time, errors.
quartet-b (BalTaks, Bescods, Gleens, Itars), **12 seeds = the six 091 seeds** (22815 23084 26518 32942 34244 42996;
pairs p000–p005, does the Itars −63 recur?) **+ six seeds not used in 091** (5187 5744 6886 7905 10311 10743, the
first six of `seeds-quartet-b.txt`, used in 083 / 086 / 088 for other comparisons; pairs p006–p011), seat-swapped
pairs, hard budget (4 comparisons, 20 s), stop at the start of round 4, agentmaco, commit c81db25, 09:13 → 12:05
(2 h 52 min). Result: lab/results/098-byfaction-vs-guide-b-fix-4r.md.

**Health: clean.** 24 of 24 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1724 vs 1734; A mean 11.47 s, median 15.10 s, p90 20.23 s, max 34.0 s; B mean 11.10 s,
median 13.26 s, p90 20.28 s, max 35.1 s (both arms, same shape as 088's 32.9 s). Unsearched 1268 vs 1233. The
parts cost no time.

## Charges in rounds 1–3 (the verdict)

| Faction | B parts | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005 = 091 seeds · p006 … p011 new) |
|---|---|---:|---:|---:|---|---:|---|
| **Itars** | caps (Nav 2), tile_prefs **ability tile only** | 183.3 | 175.0 | **−8.3** | [−35.0, +18.4] | 5 / 12 (1 tie) | +11 · 0 · −74 · −11 · −13 · +53 · +8 · −15 · **−94** · +46 · −16 · +4 |
| BalTaks | track_steps (Gaia 4 R1), caps (AI 4), building_limits, academy start, tile_prefs (3, 5, 10; avoid 2) | 169.2 | 187.4 | **+18.2** | [−6.0, +42.3] | 8 / 12 | +3 · −5 · +32 · −22 · +50 · −51 · **+87 · +28 · +62 · +26 · −8 · +16** |
| Bescods | track_steps (Sci 2 R1, Eco 2 R2, Nav 2 R3), caps (Nav 2, Eco 4), tile_prefs **big-building tile only** | 227.4 | 202.4 | **−25.0** | [−53.0, +3.0] | 3 / 12 | +83 · −4 · +16 · −56 · −17 · −23 · **−48 · −92 · −57 · −35 · −25 · −41** |
| Gleens | track_steps (Nav 2 R1), caps (Nav 4) | 194.5 | 183.1 | −11.4 | [−27.6, +4.7] | 3 / 12 | −33 · −15 · −29 · −11 · +59 · −19 · −31 · +3 · −24 · −7 · −32 · +3 |
| **All (seat mean)** | | | | **−6.6** | [−16.7, +3.4] | | 12 pairs |

Posted watch replay: `pair-008/game-0-A03` seat 1 — Itars B 126 vs Itars A 220 in the other game (the −94 pair).

VP at the start of round 4 (not the verdict): all −2.2 [−4.4, +0.1]; **Itars −5.2 [−10.3, +0.0]** (18.2 → 13.0),
Bescods −3.4 (13.5 → 10.1), Gleens −1.7, BalTaks +1.6 (9.8 → 11.3).

**Itars: the fix holds.** 091 read −63.4 with six of six pairs negative (−92 · −59 · −58 · −83 · −58 · −31) on the
same six seeds; on those seeds now **−5.7** (+11 · 0 · −74 · −11 · −13 · +53), on the new six −11.2, both inside
the ±30 same-code drift of 084 / 088, with the ±94 single-pair swings 088 warned of. ③ (scope) is closed.

**BalTaks — the pre-registered pool.** 091 (six pairs, +15.5, 5 / 6: +9 · +25 · +39 · +28 · −9 · +1) + the six new
seeds here (+35.2, 5 / 6) = **12 pairs +25.3 [+7.6, +43.0], 10 / 12 positive** — exactly on 088's 25-charge
readability line, CI clear of zero. Caution before calling it confirmed: **the six 091 seeds replayed here with the
BalTaks code unchanged on both arms** (only the Itars and Bescods opponents changed) **read +1.1, 3 / 6** against
091's +15.5, 5 / 6 — the same seeds, the same BalTaks parts, a 14-charge swing from the opponents' play alone. All
18 BalTaks pair observations: mean +17.3, 13 / 18 positive. Direction positive and consistent, size at the line,
seed-level reproduction poor. Verdict: **positive, borderline** — adoption is the user's call (below).

**Bescods: still negative with the tile scope fixed.** Tile 6 is now 0 / 12 on both arms in rounds 1–3 (091: B 6 / 6),
tile 2 is back (6 vs 6), tile 5 6 → 7 — the tile part is out of the picture, and what is left (track_steps + caps)
reads **−25.0, 9 / 12 negative, the six new seeds 6 / 6 negative** (091: −15.9, 2 / 6 positive, with the tile error).
On the line, negative side. Not noise by sign count; see the footprint below.

**Gleens −11.4 (3 / 12)** after 091's −7.3 (2 / 6): 18 observations ≈ −10, 5 / 18 positive. Below the line, but the
lean has not changed sign in either run.

## Activation (rounds 1–3, A → B, 12 seat-games per arm)

**Standard tiles taken** (`tools/tile_counts.py`; engine ids 2 ore+charge income, 3 four credits, 4 ore+QIC,
5 knowledge+credit income, 6 big buildings power 4, 7 VP now, 8 VP per Gaia mine, 9 knowledge per planet type,
10 charge-4 action):

| Faction | A tiles | B tiles | Note |
|---|---|---|---|
| **Itars** | 2 ×7 · 3 ×2 · 5 ×9 · 9 ×2 · 10 ×6 · adv ×1 (27) | 2 ×5 · 3 ×3 · 5 ×9 · 8 ×1 · 9 ×1 · 10 ×8 · adv ×1 (28) | **tile 6: 0 → 0** (091 B 6 / 6); tiles 2 and 5 back (091 B 0 / 0) |
| **Bescods** | 2 ×6 · 5 ×6 · 9 ×1 · 10 ×4 · adv ×1 (18) | 2 ×6 · 4 ×1 · 5 ×7 · 10 ×3 (17) | **tile 6: 0 → 0** (091 B 6 / 6); tile 2 back (091 B 0) |
| BalTaks | 2 ×6 · 3 ×4 · 4 ×1 · 5 ×8 · 9 ×1 · 10 ×8 (28) | 2 ×2 · **3 ×12** · 5 ×11 · 8 ×1 · 9 ×2 · 10 ×7 (35) | prefs 3 / 5 / 10, avoid 2 — as written |
| Gleens | 2 ×5 · 3 ×3 · 5 ×7 · 9 ×3 · 10 ×4 (22) | 2 ×4 · 3 ×2 · 5 ×6 · 9 ×1 · 10 ×2 (15) | no tile part; 7 fewer tiles = fewer labs / academies |

`ItarsGaiaTechTile` was played 0 times in rounds 1–3 on either arm, so the Itars preference list had nothing to act
on inside the window — the remaining Itars B parts in this window are the Navigation cap (Nav 2 → 3, nothing to cap)
and a handful of tile 10 / 8 choices; the −8.3 is drift.

**Research** (`research_counts.py --rounds 1-3`, TF / Nav / AI / Gaia / Eco / Sci; counts ResearchAdvance plus the
track of a tile choice):

| Faction | A | B | Footprint |
|---|---|---|---|
| Itars | 10 / 2 / 1 / 27 / 5 / 1 = 46 | 10 / 3 / 4 / 21 / 6 / 6 = 50 | 091: 25 → 15; now level (knowledge income back) |
| BalTaks | 9 / 0 / 18 / 13 / 6 / 5 = 51 | 11 / 0 / 10 / 30 / 2 / 2 = 55 | track_steps Gaia 4 R1: Gaia 13 → 30; cap AI 4: 18 → 10 |
| **Bescods** | 0 / **26** / 2 / 0 / 7 / 5 = 40 | 0 / **2** / 3 / 2 / 6 / 15 = 28 | **cap Nav 2: 26 → 2**; Sci 5 → 15; research −12 |
| Gleens | 1 / 15 / 0 / 39 / 0 / 2 = 57 | 2 / 20 / 0 / 26 / 0 / 0 = 48 | track_steps Nav 2 R1: Nav 15 → 20, Gaia 39 → 26 |

**Bescods' own engine is untouched**: `BescodsLowestResearchAdvance` (the faction-board action, lowest track up)
36 → 36 in rounds 1–3 (three a seat-game, every round, both arms; `action_counts.py`). track_caps works as a swap
among ResearchAdvance / tile-track candidates (`track_set_scores`), so it cannot block the ability. What changed
is the paid research: ResearchAdvance 22 → 15, and with it Build 27 → 23, Upgrade 50 → 42 (TS 22 → 17, RL 21 → 18,
PI 3 → 5, AC 4 → 2), FormFederation 9 → 7. A's 26 Navigation steps in 36 seat-rounds are what the rollout chose
when the faction's tracks (track_set: Science, Economy, Navigation) were open; B caps Navigation at 2 and leads
with Science 2 → Economy 2 → Navigation 2, and the buildings that Navigation reach paid for in rounds 2–3 are
missing. VP at R4 13.5 → 10.1 moves with the charges.

**Upgrades** (`upgrade_counts.py --rounds 1-3`, TS / RL / PI / AC; round-1 academies in brackets): **BalTaks
22 / 22 / 0 / 9 [R1 AC 0 / 12] → 24 / 24 / 0 / 11 [R1 AC 10 / 12]** (091: 0 → 5 / 6; round-1 plan labels B
`BGG-R1-1AC+1M` ×36 · `1AC+2M` ×18 vs A `1RL+2M` ×47 — the academy start is now the BalTaks round-1 opening in
10 of 12 seat-games, the two misses are `local-baseline` games); Bescods 22 / 21 / 3 / 4 → 17 / 18 / 5 / 2;
Itars 22 / 21 / 1 / 10 → 21 / 22 / 1 / 11 (091: academies 5 → 2; now level); Gleens 24 / 24 / 0 / 7 →
21 / 19 / 0 / 4. Builds (rounds 1–3): BalTaks 19 → 20, Bescods 27 → 23, Gleens 28 → 42, Itars 31 → 22.

## Reading (HANDOFF 1 order)

- **Itars: ③ closed.** −63.4 (6 / 6) → −8.3 (5 / 12, 091 seeds −5.7); tile 6 never taken, income tiles 2 and 5
  back, research 25 → 15 became 46 → 50, academies level. The remaining Itars guide parts (Nav cap, ability-tile
  preference) did nothing measurable in rounds 1–3 — the ability tile was never played in the window, so the
  preference is unmeasured here (it acts in rounds 3–6, ⑤), not refuted. The weak Itars baseline that 092 / 093
  carried on both arms is fixed from this commit on; 092's Itars re-measure (E56 "아이타는 098 뒤") can proceed.
- **BalTaks: positive, at the line.** Pre-registered 12-pair pool +25.3 [+7.6, +43.0], 10 / 12; 098's own 12 pairs
  +18.2 [−6.0, +42.3], 8 / 12; 18 observations +17.3, 13 / 18. Mechanically complete (R1 academy 10 / 12, Gaia 4
  first, the guide's tiles). Against it: the six 091 seeds replayed at +1.1 with the BalTaks code unchanged —
  the seed-level number is opponents' noise, only the pooled sign is stable. ⑤ also applies: B11's gain from the
  academy start (knowledge → Gaia 4 → gaiaformers) is rounds 3–6.
- **Bescods: −25.0, 9 / 12, new seeds 6 / 6 negative, with the tile error gone** → the track parts are what is
  left and the footprint is one number: **Navigation 26 → 2** (cap 2) with Science 5 → 15. Builds and upgrades
  fall with it. ② fired as written; ③ no scope error found (the ability is untouched, the cap is a swap);
  **④ / ⑤ candidate**: the rollout valued Navigation reach in rounds 1–3 (A took 26 steps unprompted) because it
  pays in buildings now; B13's "Navigation 2 and stop" is a whole-game plan (institute, lowest-track engine,
  federation) whose return is later — or the cap is simply wrong for this board (⑥: the guide is base-game, the
  lab is Lost Fleet). A paid-research explain on one new-seed pair would separate ④ from ⑤ before any re-run.
- **Gleens −11.4 (3 / 12)**, 18 observations ≈ −10, 5 / 18 positive: below the line, negative lean twice. Parts =
  Navigation 2 first, Gaia 39 → 26 — Gleens score Gaia planets, so delaying Gaia research in rounds 1–3 costs
  charges on the window's own terms. Unreadable by the rule, but the lean is the same direction as Bescods: a
  Navigation-first track_steps entry costing 1–3R charges.
- Health clean; decision time unchanged; both arms max 34–35 s (088 shape).

Nothing changed in code or deployment in this cycle (the tile_prefs scope fix of E39 is the measured change). Lab
queue after 098: 099 (seed scan) → 101 (ships vs ships_menu); 097 and 100 are held (`_` prefix).

## Proposal (user decision, nothing queued)

- (ㄱ) **BalTaks academy start → adopt at faction level** (the user's "integrate, then fix by replay" preference):
  move BalTaks' guide parts (opening_only + fixed_academy + budget tools, track_steps Gaia 4, caps AI 4,
  tile_prefs 3 / 5 / 10) from `GUIDE_FACTION_PARTS` into the BalTaks row of `CANDIDATE_FACTION_PARTS` (one bot
  turn, no new number; `ships` deployment stack unchanged until byfaction itself is adopted). Evidence: 12-pair
  pool +25.3 [+7.6, +43.0], 10 / 12, mechanism complete. If the user wants it above the line with margin first:
  six more quartet-b seeds (after 099 adds them) in the same run as (ㄷ), ≈ 45 min, decided on 18 pairs.
- (ㄴ) **Bescods: lab 0 explain before any re-run** — `explain_ab_decisions.py` on the first paid research of
  Bescods B and A in `pair-007` (B 177 vs A 269, the −92 pair): is the Navigation step A takes paying for a
  round-2/3 building the cap denies B (④), or is B's Science 2 → Economy 2 an investment the window cannot see
  (⑤)? Then one of: drop the Navigation cap to a track_steps entry only (order, no cap), or keep the Bescods
  guide parts out of the candidate set with the reason written in the status table (⑦ only after that).
- (ㄷ) **Gleens**: same question, lower priority — read Gleens in the same explain turn (one pair, Gaia vs
  Navigation at the first research), no separate run.
- (ㄹ) **Itars**: nothing to run; the ability-tile preference is measured only in a 6-round design (⑤) and can
  ride along the next quartet-b 6R run, if any.

Bot recommendation: (ㄱ) as the user's decision now, (ㄴ)+(ㄷ) as one bot turn (lab 0) before the next quartet-b
queue entry.
