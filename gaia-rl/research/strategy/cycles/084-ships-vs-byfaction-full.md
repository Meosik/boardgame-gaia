# Cycle 084 — ships vs ships_byfaction on the measured quartet, 6 rounds (faction-table verdict)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (base stack).
B = `...-ships-byfaction-cap20.json`: the same stack with `CANDIDATE_FACTION_PARTS` switched on — **Terrans
track_income** (074 + 076), **Geodens former_use** (079), **Taklons opening_budget + budget_guard + opening_release**
(077). Xenos have no candidate part, so both arms play Xenos with the same code. Queued by the user on 2026-10-19
("종족별로 적용한다", "종족별 규칙 넣고 실험 시작", 5a E15). Pre-registered verdict: the charges gained in rounds 1–3
(1 VP = 1.5 charges) **per faction** — a faction whose B−A is positive moves its part from `CANDIDATE_FACTION_PARTS`
to `BASE_FACTION_PARTS`; Xenos (same code) is the drift yardstick; final VP read alongside, because 074·076·077 had
charges and VP disagree.
geo-quartet, six new seeds (872741 873139 873664 873891 879269 882876), seat-swapped pairs, hard budget
(4 comparisons, 20 s), full 6 rounds, agentmaco, commit 0f76c21, 14:06 → 17:10 (3 h 04 min).
Result: lab/results/084-ships-vs-byfaction-full.md.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1735 vs 1722; A mean 12.39 s, median 18.20 s, p90 20.39 s, max 30.3 s; B mean 11.92 s,
median 16.29 s, p90 20.35 s, max 28.3 s (hard guard 60 s). Unsearched decisions 1359 vs 1364 (78% / 79%).

## Charges in rounds 1–3 (the verdict)

| Faction | Part on B | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005) |
|---|---|---:|---:|---:|---|---:|---|
| **Terrans** | track_income | 127.7 | 159.0 | **+31.3** | **[+8.2, +54.5]** | **6 / 6** | +9 · +35 · +59 · +2 · +47 · +38 |
| Geodens | former_use | 149.2 | 153.7 | +4.5 | [−16.4, +25.5] | 4 / 6 | +39 · +4 · −12 · +10 · +5 · −18 |
| Taklons | opening_budget + guard + release | 172.7 | 193.5 | +20.8 | [−46.6, +88.2] | 4 / 6 | −36 · +88 · +64 · −74 · +16 · +66 |
| Xenos | *(none — same code)* | 128.1 | 158.2 | +30.1 | [−26.4, +86.6] | 4 / 6 | +34 · −23 · +128 · +40 · +5 · −4 |
| **All (seat mean)** | | | | +21.7 | [−0.9, +44.2] | 5 / 6 | |

Posted watch replay: `pair-002/game-1-A12` seat 2 — Xenos A 123 vs Xenos B 251 in the other game of the pair; the
largest single-seat swing of the run and it is on the faction whose code is identical on both arms.

**Final VP (read alongside, not the verdict).**

| Faction | A mean | B mean | B−A | 95% CI | Pairs B > A | Per pair |
|---|---:|---:|---:|---|---:|---|
| Terrans | 71.2 | 91.5 | **+20.3** | [−16.1, +56.8] | 5 / 6 | +68 · +31 · +12 · +1 · +42 · −32 |
| Geodens | 68.0 | 61.0 | −7.0 | [−26.5, +12.5] | 2 / 6 (one tie) | −1 · −10 · +6 · −43 · 0 · +6 |
| Taklons | 77.5 | 75.0 | −2.5 | [−52.4, +47.4] | 2 / 6 | −16 · −43 · +4 · +89 · −32 · −17 |
| Xenos | 93.8 | 98.2 | +4.3 | [−33.2, +41.9] | 2 / 6 | +59 · −29 · −9 · −16 · +39 · −18 |
| All (seat mean) | 77.6 | 81.4 | +3.8 | [−13.0, +20.6] | | |

## What each part did (A → B, six seat-games per arm)

**Terrans, track_income.** The rule values Economy/Science track income again up to the guide step (Terrans: Economy 4).
Rounds 1–3 research (`research_counts.py`): Eco **5 → 12**, Sci 3 → 0, AI 10 → 12, TF 3 → 4, total 24 → 31. Round-1
academies 0 → 2 (`upgrade_counts.py`, new tool), rounds 1–3 Gaia formations 2 → 5 (4–6R 1 → 5), mines 9 → 9,
upgrades 29 → 31. End board (`game_profile.py`): research levels 14.0 → 16.3, tech tiles 5.7 → 7.2, Gaia planets
0.7 → 1.8, turns 38.3 → 45.3, mines 3.8 → 3.8. VP by move: pass 4.3 → 7.5, upgrade 5.3 → 9.0, end research
18.7 → 26.0, end mission 28.3 → 33.8; final 71.2 → 91.5. 074 and 076 saw the same shape on Terrans (AI → Economy, more
turns, pass and upgrade VP) with charges +27.4 / +2.7 and VP +23.8 / +10.2; this time charges and VP agree, every pair
is positive on charges and the CI excludes 0. Three cycles, 18 pairs, Terrans VP positive in 15 of them.

**Geodens, former_use.** Rounds 1–3: Gaia formation 0 → 1, asteroid mines 0 → 0, mines **10 → 6**, research AI 4 → 10,
Eco 9 → 5 (Gaia 12 → 11), ChargePower 35 → 42, round-1 academies 2 → 3. End: mines built 4.5 → 3.0, research levels
13.3 → 15.0, turns 36.2 → 36.3, end mission VP 27.2 → 19.0, final 68.0 → 61.0. The rule's intended footprint (formers
used instead of researching Gaia) does not appear: one formation in 36 seat-rounds, no asteroid mine. What moved is
the colony option set — transdim planets count as a mine option only while a former is on them, so the arm with the
rule builds fewer mines in rounds 1–3, the same footprint 079 put on **Terrans** (mines 10 → 6). 079's Geodens gain
(+20.7, mines 12 → 17) is not reproduced; pooled with 079 the part is +12.6 over 12 pairs, 8 of 12 positive, VP
≈ +0.9.

**Taklons, opening_budget + budget_guard + opening_release.** Round 1: upgrades 14 → 17 (TS 8 → 9, RL 6 → 7,
**AC 0 → 1**), mines 4 → 4. Rounds 1–3: AC 6 → 7, PI 1 → 1, power actions 9 → 16, ship explores 9 → 11, research
Nav 0 → 2, Gaia 3 → 6, total 25 → 31. End: research levels 14.5 → 15.2, feds 0.8 → 1.2, Gaia 0.2 → 0.8, final
77.5 → 75.0. The budget rule's target (round-1 academy finished) moved by one seat-game out of six; the charge swings
are ±36–88 per pair with the sign split 4:2, i.e. the 083 noise range. Pooled with 077 (+23.6, 4/6): +22.2 over
12 pairs, 8 of 12 positive, CI ≈ [−11, +55]; VP ≈ +1.9.

**Xenos, same code.** +30.1 charges (p002 +128), VP +4.3. In each game two seats are A and two are B, so the Xenos
"arm" only labels which opponents carry the faction parts; the swing is drift under the 20 s wall-clock cap (083
p000/p001) plus opponent interaction. It sets this run's yardstick: a per-faction difference of ≈ +30 with four of six
pairs positive is what the same code produces.

## Reading

Against the pre-registered rule, all three candidate parts come out positive on the point estimate — but only one
clears the run's own noise.

- **Terrans track_income: passes.** +31.3 [+8.2, +54.5], 6 of 6 pairs, VP +20.3 (5 of 6), and the footprint is the
  rule (Economy 5 → 12). Third cycle on this faction with the same direction (074 +27.4, 076 +2.7 charges; VP +23.8,
  +10.2, +20.3). Condition for `BASE_FACTION_PARTS` met.
- **Geodens former_use: not shown.** +4.5 with CI [−16, +26], VP −7.0 (3 of 6 negative, one −43), mines 10 → 6, the
  rule itself fired once. Smaller than the Xenos same-code drift.
- **Taklons opening budget: not shown.** +20.8 with CI ±67, 4:2, VP −2.5, round-1 academy 0 → 1. Also inside the
  same-code drift; pooled 12 pairs still through 0.

Decision on moving parts is the user's (the base `ships` factory is the D1 deployment teacher). Nothing was changed in
code; `upgrade_counts.py` (Upgrade moves by target building per arm and faction) was added to tools. 085 (quartet a,
hard vs byfaction) started at 17:10 as queued; 084 changes nothing in 085–087 (their B arm already carries the three
parts, their A arm is the live hard teacher).

## Proposal (user decision, nothing queued)

- (ㄱ) **Code, lab time 0**: move Terrans `track_income` from `CANDIDATE_FACTION_PARTS` to `BASE_FACTION_PARTS`
  (one table line in `teacher_patches.py`, plus the factory test and stack-parts.md D). Effect: the base `ships`
  factory — and so the D1 deployment teacher — plays Terrans with track_income; byfaction behaviour unchanged.
  Verification before commit: factory tests, `guide_values_smoke.py` on one geo-quartet seed for the other three
  factions unchanged.
- (ㄴ) **Geodens and Taklons: repeat 084 on six new geo-quartet seeds** (seeds.txt holds 32 unused after 882876,
  next six 883946 …), same A/B, 6R, ≈ 3 h; verdict on the 12-pair pool per faction (as 074 + 076). If (ㄱ) is done
  first, the repeat measures the same thing (Terrans then identical on both arms, a second same-code yardstick).
  Slot: after 087 (queue order 085 → 086 → 087, ≈ 4.5 h from 17:10).
- (ㄷ) **Close Geodens former_use and Taklons opening budget** now (both stay opt-in in `CANDIDATE_FACTION_PARTS`
  only if byfaction keeps them; otherwise remove from the candidate table): two cycles each, neither effect larger
  than the drift, Geodens VP negative twice (079 +8.7 was the exception), Taklons' target (round-1 AC) moved once.
- (ㄹ) Lab time 0, before (ㄴ): `explain_ab_decisions.py` on Geodens B mines — p003 game-0-A13 seat 0 (Geodens B 123,
  VP 39 vs 82) — whether former_use's "transdim only while forming" removed a mine the A arm built, i.e. whether the
  Geodens part is the 079 Terrans defect in a different seat.

Bot recommendation: (ㄱ) now, (ㄹ) now, (ㄴ) as the slot after 087 if the user wants Geodens/Taklons settled by
measurement; otherwise (ㄷ).
