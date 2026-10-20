# Cycle 093 — ships_byfaction_guide vs ships_byfaction_guide_src, quartets a · b · c, 4 rounds (the resolved-conflict parts alone)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-guide-cap20.json` (091's B arm,
092's A arm: deployment stack + `CANDIDATE_FACTION_PARTS` + `GUIDE_FACTION_PARTS`).
B = `...-ships-byfaction-guide-src-cap20.json`: the same plus `SOURCE_FACTION_PARTS` (research/strategy/conflicts/
base-factions.md, the conflicts that had a conclusion) — **opening_only** for Ambas (1RL+4M · 1AC+2M · 1RL+5M · 1RL+6M),
Bescods (1RL+4M · 1RL+5M · 2RL+1M), Gleens (1RL+4M · 6M · 7M), Nevlas (1PI+1RL+1M · 1PI+1RL+2M · 1PI+1TS+2M), Lantids
(1PI+3M … 1PI+6M); **track_steps_src** for Nevlas (round 1 Science 3), Lantids (Economy 2 first) and Ivits (Science 2
first) — the PG order that replaces the experiment teacher's B-blog order (N1 · L1 · I1); **building_due** for Firaks
(institute due round 2) and Itars (round 3): while the faction has no institute, the institute upgrade leads the other
big-building upgrades. BalTaks, HadschHallas, Terrans and Xenos run the same code on both arms (drift yardstick).
Queued by the user on 2026-10-20 ("아직 테스트 하지 않은 종족들의 부품을 구현하거나, 미구현 부분 해결해").
Pre-registered verdict: charges gained in rounds 1–3 per faction (1 VP = 1.5 charges); read alongside: activation
(round-1 buildings and the institute round from upgrade_counts, round-1 tracks from research_counts, the round-1 plan
labels), decision time, errors; if bad, HANDOFF 1's order.
quartet-a (Lantids · Ivits · Firaks · Nevlas) × 6 seeds + quartet-b (Bescods · Gleens · Itars · BalTaks) × 6 +
quartet-c (Ambas · Terrans · HadschHallas · Xenos) × 4 = 16 seat-swapped pairs, hard budget (4 comparisons, 20 s), stop
at the start of round 4, agentmaco, commit d319487, 21:12 → 00:54 (3 h 43 min). Result: lab/results/093-guide-vs-src-4r.md.

**Health: clean.** 32 of 32 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 2303 vs 2304; A mean 11.39 s, median 16.08 s, p90 20.25 s, max 31.1 s; B mean 11.08 s, median
14.93 s, p90 20.27 s, max 27.5 s. Unsearched 1626 vs 1609. The parts cost no time.

## Charges in rounds 1–3 (the verdict)

| Faction | B parts in 093 | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| **Nevlas** | opening_only, track_steps_src (Sci 3) | 131.5 | 142.7 | **+11.2** | [−12.1, +34.4] | 5 / 6 | −26 · +39 · +10 · +11 · +27 · +6 |
| **Lantids** | opening_only, track_steps_src (Eco 2) | 147.9 | 148.9 | +1.1 | [−105.7, +107.8] | 3 / 6 | **−122 · −89 · +119 · +119** · −26 · +5 |
| **Ivits** | track_steps_src (Sci 2) | 151.4 | 149.4 | −2.0 | [−27.2, +23.2] | 2 / 6 | +1 · −12 · **0** · +42 · −15 · −27 |
| **Firaks** | building_due (PI by R2) | 141.7 | 129.7 | −12.0 | [−64.3, +40.3] | 3 / 6 | −70 · +22 · −61 · −32 · +52 · +17 |
| **Bescods** | opening_only | 219.8 | 228.4 | +8.6 | [−8.7, +25.8] | 3 / 6 | −6 · +25 · +33 · −4 · **0** · +4 |
| **Gleens** | opening_only | 187.7 | 195.5 | +7.9 | [−49.4, +65.1] | 2 / 6 | +104 · −35 · −7 · −6 · −43 · +35 |
| **Itars** | building_due (PI by R3) | 138.0 | 145.4 | +7.4 | [−27.7, +42.5] | 2 / 6 | +68 · +23 · −10 · −22 · −9 · −6 |
| **Ambas** | opening_only | 157.9 | 155.6 | −2.3 | [−9.7, +5.1] | 0 / 4 | **0 · 0** · −9 · **0** |
| BalTaks (same code) | — | 197.8 | 184.2 | −13.6 | [−43.9, +16.7] | 2 / 6 | −31 · −27 · +24 · −40 · +23 · −30 |
| HadschHallas (same code) | — | 144.4 | 144.5 | +0.1 | [−5.0, +5.1] | 1 / 4 | −4 · **0** · +4 · **0** |
| Terrans (same code) | — | 196.7 | 189.8 | −6.9 | [−37.2, +23.4] | 1 / 4 | +7 · **0** · −35 · **0** |
| Xenos (same code) | — | 155.8 | 154.7 | −1.1 | [−3.9, +1.8] | 0 / 4 | −1 · **0** · −4 · **0** |
| **All (seat mean)** | | | | **+0.2** | [−10.8, +11.2] | | 16 pairs |

Two of the 16 pairs (quartet c pair-013 and pair-015) are identical through round 3 in every seat, pair-012 differs by
single digits: on quartet c the source parts changed almost nothing. The drift yardstick is therefore BalTaks alone
on quartet b (−13.6, pairs ±30) and the ±120 Lantids swings on quartet a. **No faction crosses 088's 25-charge line**;
nothing is adopted and nothing is rejected on this run. Nevlas +11.2 with 5 of 6 pairs positive is the only consistent
lean. VP at the start of round 4 (not the verdict): all −0.2 [−2.5, +2.1]; Lantids +6.7 [−0.0, +13.4] (5.5 → 12.2),
Terrans −4.0 (same code), Itars −3.3, BalTaks −3.0 (same code).

Posted watch replay: `pair-000/game-0-A02` seat 1 — Lantids **B** 51 vs Lantids A 172 in the other game of the pair
(the −122 pair).

## Activation (A → B)

**Round-1 BGG opening plans selected** (new `tools/plan_labels.py --prefix BGG-R1-`, the "via" plan of every
decision, whole run; A picks / B picks):

| Faction | A (guide catalog) | B (source list) | Fired? |
|---|---|---|---|
| Gleens | 49: 1RL+2M ×25 · 1RL+4M ×15 · 1RL+1TS+2M ×5 · 1TS+5M ×3 | **60: 1RL+4M ×60** | **yes, fully** (RL+4M forecasts complete) |
| Bescods | 53: 1RL+1TS+2M ×29 · 1RL+1TS+1M ×11 · 1RL+5M ×7 · 1AC+2M ×6 | 16: 1RL+4M ×15 · 1RL+5M ×1 | partly (16 vs 53; the rest current-choice / local-baseline) |
| Lantids | 48: **1PI+2M ×37** · 1RL+4M ×5 · 1RL+1TS+2M ×4 · 1PI+3M ×2 | 14: 1PI+3M ×14 | partly (14 vs 48) |
| Ambas | 25: 1RL+1TS+1M ×9 · 1RL+2M ×7 · 1RL+3M ×6 · 1RL+1TS+2M ×3 | 3: 1AC+2M ×3 | **no** (3 of 4 pairs identical) |
| Nevlas | 53: 1RL+1TS+1M ×24 · 1RL+2M ×20 · 1PI+1RL+1M ×5 · 1RL+1TS+2M ×4 | **0** (value-max 1PI+1RL+1M ×7 only) | **no** |

Exactly what 092 found for HadschHallas and E56 predicted for 093: a list of big-mine or two-building openings
(PI+RL, PI+3–6M, AC+2M, RL+5–6M) rarely completes a forecast inside the 20 s search, so the B arm plays the search's
own picks (current-choice / local-baseline) in round 1 — the part measures "no opening planner", not the source. Only
RL+4M (Gleens, part of Bescods) completes reliably.

**Round-1 upgrades** (`upgrade_counts.py --rounds 1-1`, TS / RL / PI / AC): Ambas 4 / 4 / 0 / 1 → 4 / 4 / 0 / 1;
Bescods 9 / 5 / 0 / 1 → 7 / 5 / **1** / 1; Gleens 8 / 5 / 0 / 0 → 6 / 6 / 0 / 0; Lantids 6 / 2 / **4** / 0 → 6 / 4 /
**2** / 0 (the institute list produced *fewer* round-1 institutes: when PI+3M does not complete the search builds a
lab); Nevlas 9 / 6 / 0 / 0 → 10 / 6 / 0 / 0 (no institute either arm); Firaks 9 / 3 / 3 / 0 → 7 / 5 / 1 / 0 (building_due
cannot fire in round 1 — search drift); Itars 9 / 3 / 3 / 1 → 10 / 4 / 2 / 1.
**Rounds 1–3**: Lantids 6 / 2 / 4 / 2 → **11 / 7 / 3 / 2**; Firaks 12 / 16 / 4 / 1 → 14 / 14 / **5** / 1 (institute 4 → 5
of 6 seat-games: building_due fired once); Itars 13 / 8 / **3** / 2 → 11 / 6 / **3** / 4 (institutes unchanged: the
part had nothing to lead — academies 2 → 4 instead); Nevlas AC 5 → 3; Bescods PI 2 → 3; the rest within ±2.

**Research, rounds 1–3** (`research_counts.py --rounds 1-3`, TF / Nav / AI / Gaia / Eco / Sci): **track_steps_src
fired fully in all three factions** — Nevlas 1 / 7 / 7 / 1 / **14** / **1** → 2 / 6 / 10 / 1 / **7** / **10**; Lantids 0 /
**10** / 4 / 1 / **0** / 0 → 2 / **0** / 6 / 0 / **11** / 0; Ivits 0 / 0 / 2 / 1 / **11** / **0** → 1 / 2 / 4 / 0 / **0** /
**11**. Others: Firaks Eco 24 → 19, Itars Gaia 15 → 11 · Eco 0 → 3, Gleens Nav 13 → 10 · Gaia 11 → 15, Bescods Sci 9 →
10, Ambas unchanged; same-code factions within ±2.

## Reading (HANDOFF 1 order)

- **opening_only (5 factions): ② not activated for Ambas and Nevlas, half for Bescods and Lantids, full for Gleens.**
  The cause is the same forecast-completion limit as 092 (HadschHallas) and the `opening_only` note in
  `teacher_patches.py` (BalTaks before `fixed_academy`): the 20 s search finishes about one forecast a decision, and
  big-mine / two-building forecasts almost never finish. Where it did fire (Gleens, 60 of 60 picks RL+4M) the charges
  are unreadable (+7.9, pairs +104 … −43). Lantids' list even lowered round-1 institutes 4 → 2 (the opposite of the
  source) and the faction swung ±120 per pair. Nothing to adopt; the part cannot be judged on a cap20 teacher.
- **track_steps_src (Nevlas · Lantids · Ivits): ② fired as written.** Nevlas Science 1 → 10 (Economy 14 → 7),
  Lantids Economy 0 → 11 (Navigation 10 → 0), Ivits Science 0 → 11 (Economy 11 → 0). Charges: **Nevlas +11.2, 5 of 6
  pairs positive = leans positive, unconfirmed** (under 25, and opening_only was off on the same arm so this is the
  track order alone for Nevlas); Lantids unreadable (±120, confounded by the half-fired opening list); Ivits −2.0 =
  drift (one identical pair, the rest ±40). I1 · N1 · L1 did no visible harm by round 4; the sources claim the gain in
  rounds 4–6 (⑤ measure), which this 4R run does not see.
- **building_due (Firaks R2 · Itars R3): ② fired weakly or not at all.** Firaks institutes 4 → 5 of 6 by round 3,
  charges −12.0 with pairs −70 · −61 · +52 (Firaks is the noisiest faction in 092 and 093 alike — inside drift);
  Itars institutes 3 → 3 (the search already had no institute-vs-lab choice to reorder in rounds 1–3; academies 2 →
  4 is drift), charges +7.4 unreadable. No evidence either way.
- Quartet c (Ambas · same-code HadschHallas · Terrans · Xenos) was almost deterministic across arms (2 identical pairs
  of 4): the Ambas list changed one decision in one pair. Four pairs cannot read a drift yardstick; BalTaks −13.6 on
  quartet b (pairs ±30) is the run's drift lean.
- The run's "all +0.2 [−10.8, +11.2]" and VP −0.2 are flat; nothing to act on.

Nothing changed in code or deployment (only `tools/plan_labels.py` added). 094 (`src vs res`, on hold) compares this
src stack against `RESOLVED_FACTION_PARTS` where science_when replaces track_steps_src for Nevlas and Ivits — with the
opening lists not firing on either arm, 094 would measure the science condition only.

## Proposal (user decision, nothing queued)

- (ㄱ) **Judge the track order alone.** Split `SOURCE_FACTION_PARTS` so a factory carries only `track_steps_src`
  (Nevlas · Lantids · Ivits; a flag + spec, no new values), then guide vs guide_src_tracks on quartet a: 093's six
  seeds + six new = 12 pairs, 4R (≈ 2 h 40 min). Nevlas' +11.2 (5 of 6) is the only lean worth confirming, and the
  Lantids read needs the opening list out of the way. 094 (science_when vs fixed order) only makes sense after this.
- (ㄴ) **Make the opening lists playable before measuring them again** (same as 092's (ㄱ) for HadschHallas): one
  smoke seat-game per opening_only faction on a cap60 spec (lab command ≈ 10 min) to see whether PI+RL, PI+3M, AC+2M,
  RL+5M forecasts complete at 60 s; if they do, re-run the opening_only factions on cap60 both arms; if not, the
  lists need the fixed-opening coach path (`fixed_academy`-style enforcement) — engineering, user decision.
- (ㄷ) **Lab 0: explain the Lantids −122 pair** — `explain_ab_decisions.py` on `pair-000/game-0-A02` seat 1 (B 51 vs
  A 172): what the B arm played in round 1 with the PI+3M list (institutes 4 → 2) and whether the economy-first track
  step took the knowledge the institute needed.
- (ㄹ) building_due: no re-measure; fold into plan_menu's Firaks / Itars rows (E54) as an upgrade-plan rule later.

Bot recommendation: (ㄷ) now as a bot turn, (ㄱ) as the next lab slot after 096 / 098, (ㄴ) before any opening_only
re-run (also covers 092's HadschHallas list).

## Follow-up (user 2026-10-21 "그렇게 해")

- (ㄷ) **Lantids −122 explained** (`explain_ab_decisions.py --arm B --steps 24 32 43`, `list_decisions.py --seat 1`
  on both games of pair-000): setup (−1,−1 · 1,−6, booster 5) and the first two round-1 moves (trading station,
  mine at −1,1) are identical in both arms. The split is step 32: **B upgrades to the institute** — the PI+3M
  forecast had completed (value 214 with 2 mines; status `fallback-no-verified-route`) and value-max took it because
  the cut list held nothing else — while A upgrades the same site to a research lab (tile 3), builds two more mines,
  Navigation, Eclipse. B then plays Economy (track_steps_src; knowledge only) and passes; **in round 2 B builds
  nothing** (Eclipse exploration and free actions — the institute's 4 ore 6 credits on a two-mine income), and only
  in round 3 trading station, lab, two mines, a federation. So the loss is ③ implementation of the opening list,
  not the track order: cutting the catalog to institute openings lets value-max pick an institute forecast whose
  target (3 mines) was not reached, and removes the lab route the search rated higher — the same shape as 092's
  Firaks (secondary plans deleted).
- (ㄱ) implemented: flag `source_tracks`, `SOURCE_TRACK_PARTS`, factory `..._ships_byfaction_guide_srctracks`
  (track_steps_src only; opening_only and building_due off), spec `...-byfaction-guide-srctracks-cap20.json`, test
  extended (47 pass). **Queued 098b `098b-guide-vs-srctracks-4r`**: guide vs srctracks, quartet a, 093's six seeds
  + six new (five unused + quartet-a-37936 moved from the held 094) = 12 pairs, 4R.
- (ㄴ) **Queued 098a `098a-src-cap60-opening-smoke`**: guide vs src on new cap60-p2 specs (60 s cap, 2 comparison
  processes, same rules), one seed per quartet a · b · c, stop at the start of round 2, no verdict — read
  `plan_labels.py --prefix BGG-R1-` on the B arm against 093's counts (Ambas 3, Bescods 16, Nevlas 0, Lantids 14,
  Gleens 60).
- Lab order: 096 → 098 → 098a → 098b → 099 → 101. 094 stays on hold (five quartet-a seeds left; redesign after 098b).
