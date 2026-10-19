# Cycle 088 — charge levels of all 18 factions, byfaction_guide self-play, 4 rounds

User (2026-10-19, E23): "추천 순서대로 해. 대신 6라운드는 멀었고 골고루 4라운드로 해서 제일 충전 못받는 종족이 뭔지
봐야게썽", "확장 종족 빌드 고정이 맞나? 연구소나 아카데미 스타트 해도 되잖아?" → Lost Fleet factions are not
fixed to one build.
A = B = `...-ships-byfaction-guide-cap20.json` at commit 1fd9a14 — **before** `tile_prefs` / `niche_tracks`
(a3ff9d1, measured by 091). No A/B verdict: this is a level table. Six quartets × six seeds × seat-swapped pairs =
72 games, hard budget (4 comparisons, 20 s), stop at the start of round 4, agentmaco, 23:03 → 07:35 (8.5 h).
Quartets: a Lantids · Ivits · Firaks · Nevlas, b BalTaks · Bescods · Gleens · Itars, c Ambas · HadschHallas ·
Terrans · Xenos, geo Xenos · Taklons · Terrans · Geodens, d Moweyds · Tinkeroids + Taklons · Geodens, e SpaceGiants ·
Darkanians + Terrans · Xenos (Lost Fleet factions share home planet types, so four of them never fit one game).
Result: lab/results/088-charges-all-factions-4r.md.

**Health: clean.** 72 / 72 games, 0 errors, 0 timeouts, 0 fallback timeouts, 0 federation-limit hits on all 18
factions, including the four Lost Fleet factions (first full run for them). Mean 11.2 s, median 15.1 s, p90 20.2 s,
max 32.9 s (inside the 60 s guard). Unsearched decisions 3781 / 5347 (71%) and 3720 / 5286 (70%).

**Same-code drift.** The arms are identical, so B−A is pure timing noise: run total −4.3 [−8.7, +0.2], faction means
−22.0 (Ivits) … +5.0 (Gleens), single pairs up to ±90 (Ivits p003 162 vs 255). A faction gap below ≈ 25 charges is
not readable from six seeds.

## Charges in rounds 1–3 per faction (both arms pooled, seat-game mean)

"vs quartet" = faction level minus the seat mean of its own quartet (opponents differ per quartet, so this is the
fairer cross-faction reading). Terrans, Xenos, Taklons, Geodens are split by quartet.

| Rank | Faction | Quartet | Charges | vs quartet |
|---:|---|---|---:|---:|
| 1 | **HadschHallas** | c | **123.7** | **−29.2** |
| 2 | Xenos | e | 130.9 | **−25.6** |
| 3 | **Firaks** | a | **133.1** | −20.1 |
| 4 | Nevlas | a | 142.5 | −10.7 |
| 5 | **Itars** | b | 143.6 | **−30.3** |
| 6 | Darkanians | e | 151.9 | −4.6 |
| 7 | SpaceGiants | e | 155.5 | −1.0 |
| 8 | Terrans | geo | 157.3 | −12.8 |
| 9 | Ambas | c | 157.5 | +4.6 |
| 10 | Taklons | geo | 158.6 | −11.5 |
| 11 | Gleens | b | 160.3 | −13.6 |
| 12 | Terrans | c | 160.8 | +7.9 |
| 13 | Lantids | a | 161.8 | +8.6 |
| 14 | Taklons | d | 162.5 | −8.7 |
| 15 | Geodens | d | 167.6 | −3.6 |
| 16 | Xenos | c | 169.7 | +16.8 |
| 17 | Tinkeroids | d | 171.2 | +0.0 |
| 18 | Xenos | geo | 173.1 | +3.0 |
| 19 | Ivits | a | 175.4 | +22.2 |
| 20 | Moweyds | d | 183.6 | +12.4 |
| 21 | BalTaks | b | 184.4 | +10.5 |
| 22 | Terrans | e | 187.8 | +31.3 |
| 23 | Geodens | geo | 191.5 | +21.4 |
| 24 | **Bescods** | b | **207.4** | **+33.5** |

Faction totals over all quartets: Terrans 168.6 (18 pairs), Xenos 157.9 (18), Taklons 160.5 (12), Geodens 179.6 (12).
Quartet seat means: a 153.2, b 173.9, c 152.9, geo 170.1, d 171.2, e 156.5.

- **Lowest in absolute terms: HadschHallas 123.7** (seat range 87–163, every seed below its quartet mean except one).
  Third time HadschHallas is the weak point (081 −21.1 vs live hard). Then Firaks 133.1 and Nevlas 142.5 — quartet a is
  a low-charge table overall.
- **Lowest against its own table: Itars −30.3** (143.6 in quartet b at 173.9; seats 99–190, three seeds ≈ 100–120).
  083's "Itars 51–52" was one seed and 086 cleared Itars against live hard, but here it is again last on its table.
- **Xenos depends on the table**: 169.7 / 173.1 with c / geo, 130.9 with the Lost Fleet quartet e (every pair ≤ 166) —
  Terrans in the same e games score 187.8. Opponent and map effect, not a Xenos defect by itself.
- **Lost Fleet factions are mid-pack**: Moweyds 183.6, Tinkeroids 171.2, SpaceGiants 155.5, Darkanians 151.9 —
  no build-lock needed to keep them from failing (E23 answer holds).
- **Top: Bescods 207.4** (+33.5 on its table), Geodens on geo 191.5.

Caveats: charges are what a faction *receives* when others build next to it, so a low number can be a placement
choice (spread-out, isolated start) and not a weakness; for Itars (Gaia-phase token sink) and HadschHallas (credit
economy) the HANDOFF 1 step ⑤ "metric mismatch" is a live possibility. Six seeds per quartet, ±25 drift.

## Not measured here

`research_counts.py` / `upgrade_counts.py` replay the moves from the seed; the bot venv is built from the newer
engine (Lost Fleet tech face per seed, 25 VP check), so the replay diverges (`IndexError` at a candidate index) and
the round 1–3 research and upgrade footprint could not be counted. The lab rebuilt its engine after 088 too, so
these games cannot be replayed on either side without a 1fd9a14 build.

## Reading

- The user's question is answered: **HadschHallas receives the fewest charges** (absolute), **Itars the fewest
  against its own table**, Firaks second on both. Quartet-specific Xenos-in-e is the only other −25.
- All 18 factions run clean on the byfaction stack at hard budget, including all four Lost Fleet factions.
- 091 (byfaction vs byfaction_guide, quartets b and c) runs on the new engine with `tile_prefs` (HadschHallas, Itars
  included) and `niche_tracks` (HadschHallas) — it is the first test of whether the guide parts move the two weakest
  factions, and its folders can be replayed with the current bot venv for the research footprint.

No code was changed and nothing was deployed.

## Proposal (user decision, nothing queued)

- (ㄱ) **Lab time 0, after 091**: `research_counts.py` / `upgrade_counts.py` on 091 for HadschHallas and Itars, plus one
  explain of a low seat each (is it isolation, a late first mine, or token burning?).
- (ㄴ) **Firaks / Nevlas (quartet a)**: not in 091. Same design as 091 on quartet a (byfaction vs byfaction_guide,
  6 seeds 4R ≈ 1.5 h) once faction parts for Firaks/Nevlas exist; candidates come from PG17 / PG10 in `claims-new/`
  (both read in full, not reflected yet).
- (ㄷ) **HadschHallas / Itars faction parts from the claims** (PG19 has only 4 rows for HadschHallas; PG23 Itars read
  in full) as search-order candidates (Lost Fleet adjusted, E28), then measure on quartet c / b with
  ships_byfaction_guide as A.
