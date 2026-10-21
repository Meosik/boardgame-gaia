# Cycle 096 — ships vs ships_endgame on the measured quartet, 6 rounds (round-6 stock at the final-scoring rates)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (deployment teacher).
B = `...-ships-endgame-cap20.json`: the same stack plus **endgame_prices** for every faction — when the valued state is
in round 6 (`horizon == 0`: a round-6 root decision, and the end of a round-5 rollout) the stock is priced at what the
final scoring pays (`scoring.rs`): 1 VP per 3 ore + credits + knowledge, **QIC and power 0**, 4 VP per research level
among 3–5; moves that turn stock into VP inside the round show their VP themselves. Queued by the user on 2026-10-20
(E34: "쓸 데가 없다는 것도 말이 안되고, 트와일라잇 들어갔으면 연방 능력 복사라도 하지" → "ㄱ은 먼저 해") after 090 p003 game-0
Terrans A held 9 QIC in round 6 while the Twilight token replay (3 QIC → 8 VP + 1 QIC) ranked −1.33 because a QIC was
still 7 charges; with the endgame spec the same decision 296 ranks the replay +8.00 first and selects it.
Pre-registered verdict: charges gained in rounds 1–3 (identity check — the part has no trigger before round 5). Read
alongside (pre-registered, not the verdict): final VP, round-6 replay / 2-QIC bonus / QIC→ore counts, QIC left at the
end, decision time, errors.
geo-quartet, six new seeds (925780 930239 931645 934257 940208 940261, the first of the 14 added in E62), seat-swapped
pairs, hard budget (4 comparisons, 20 s), full 6 rounds, agentmaco, commit 6d3c649, 06:15 → 09:13 (2 h 58 min).
Result: lab/results/096-ships-vs-endgame-full.md.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1753 vs 1887 (B plays more free actions); A mean 11.84 s, median 16.80 s, p90 20.32 s, max
25.6 s; B mean 11.18 s, median 13.16 s, p90 20.29 s, max 25.9 s. The round-6 price branch costs no time.

## Charges in rounds 1–3 (the verdict: identity check)

| Faction | A | B | B−A | 95% CI |
|---|---:|---:|---:|---|
| Geodens | 172.9 | 194.7 | +21.8 | [−27.6, +71.2] |
| Taklons | 171.4 | 182.5 | +11.1 | [−16.6, +38.8] |
| Terrans | 186.3 | 179.6 | −6.7 | [−19.9, +6.4] |
| Xenos | 150.3 | 131.8 | −18.5 | [−49.7, +12.7] |
| **All (seat mean)** | | | **+1.9** | [−9.2, +13.0] |

**Three of six pairs (p002, p003, p005) were move-for-move identical through round 4** — all four seats' round 1–3
charges are equal in both games — and split in round 5, where the part first acts (`shipmine_hits.py --first-split`):

| Pair | First split | Seat | Comparisons A / B | Moves (A game · B game) |
|---|---|---|---|---|
| p002 | step 211, R5 | Terrans | 4 / 4 | lab upgrade + tile 9 · lab upgrade + tile 5 |
| p003 | step 214, R5 | Taklons | 3 / 4 | ResearchAdvance AI · ResearchAdvance Economy |
| p005 | step 209, R5 | Terrans | 4 / 3 | lab upgrade + tile 8 · ResearchAdvance Navigation |

p002 split with both arms at 4 completed comparisons, i.e. the valuation itself (the round-5 rollout ends at the start
of round 6, which B prices at the final rates). The other three pairs split **before round 5, by comparison count at the
20 s cap**: p000 step 33 R1 Terrans (3 / 2), p001 step 94 R2 Xenos (3 / 2), p004 step 126 R3 Geodens (1 / 2) — the
same-code drift of 090 p004 and 095. Every non-zero charge number above comes from those three pairs. Verdict: **no
early harm, and the window cannot see the part** (as pre-registered).

Posted watch replay: `pair-000/game-0-A02` seat 0 — Geodens A 127 vs Geodens B 245 in the other game (a drift pair).

## Final VP (read alongside; this is where the part acts)

| Faction | A mean | B mean | B−A | 95% CI | Per pair (p000 … p005) |
|---|---:|---:|---:|---|---|
| Geodens | 79.7 | 91.5 | +11.8 | [−10.1, +33.8] | +34 · +1 · +11 · −23 · +30 · +18 |
| Taklons | 66.7 | 99.3 | **+32.7** | [+14.3, +51.0] | +64 · +41 · +26 · +15 · +23 · +27 |
| Terrans | 90.0 | 105.8 | +15.8 | [−6.1, +37.8] | −17 · +1 · +19 · +41 · +31 · +20 |
| Xenos | 99.3 | 98.3 | −1.0 | [−13.9, +11.9] | −14 · +7 · −10 · −12 · +14 · +9 |
| **All (seat mean)** | 83.9 | 98.8 | **+14.8** | **[+7.9, +21.8]** | +16.8 · +12.5 · +11.5 · +5.3 · +24.5 · +18.5 |

**All six pairs positive on the seat mean.** In the three pairs that were identical through round 4 (p002 · p003 ·
p005, so the whole difference is rounds 5–6) the seat mean is +11.5 · +5.3 · +18.5 (mean **+11.8**); Taklons 3 / 3
positive (+26 · +15 · +27), Terrans 3 / 3 (+19 · +41 · +20), Geodens 2 / 3 (+11 · −23 · +18), Xenos 1 / 3 (−10 · −12 ·
+9). The drift pairs read +16.8 · +12.5 · +24.5 (mean +17.9), the same sign and size. Taklons is the only faction whose
CI clears zero; the overall CI does too, the first 6-round VP result to do so (090 +7.0 [−9.7, +23.7], 089 and 084 wider).

## What the part did (replays of the 12 games)

**Stock at the last decision (`tools/endgame_stock.py`, new; per seat-game, A → B):**

| Faction | ore | credits | knowledge | **QIC** | bowl 3 | stock VP (⌊(ore+cr+kn)/3⌋) |
|---|---|---|---|---|---|---|
| Geodens | 6.8 → 2.2 | 20.5 → 14.3 | 1.2 → 0.5 | **2.5 → 0.0** | 1.3 → 0.0 | 9.3 → 5.5 |
| Taklons | 10.8 → 3.5 | 9.5 → 15.2 | 1.2 → 0.2 | **6.3 → 0.0** | 2.2 → 0.0 | 6.8 → 6.0 |
| Terrans | 9.8 → 2.2 | 20.7 → 15.5 | 1.3 → 0.5 | **1.7 → 0.0** | 0.5 → 0.0 | 10.5 → 5.8 |
| Xenos | 0.2 → 0.2 | 7.8 → 7.2 | 0.5 → 1.5 | 0.3 → 0.2 | 0.5 → 0.2 | 2.7 → 2.8 |
| Seat mean | 6.9 → 2.0 | 14.6 → 13.0 | 1.0 → 0.7 | **2.7 → 0.0** | 1.1 → 0.0 | 7.3 → 5.0 |

The deployment teacher ends a game holding **2.7 QIC a seat (Taklons 6.3)**, worth nothing; B ends with none, and
with less ore and a smaller unspent stock (7.3 → 5.0 VP) — the stock went into moves. Xenos holds almost nothing in
either arm (its Lost Fleet ore → bowl 3 conversion drains ore), so the part had nothing to reprice there: VP −1.0.

**Rounds 5–6 move counts (`action_counts.py`, 24 seat-games per arm, A → B):**

| | R5 A → B | R6 A → B |
|---|---|---|
| TwilightReplayFederationToken (the motivating move) | 1 → 2 | 2 → 1 |
| RebellionGainTechTile | 3 → 7 | 5 → 4 |
| EclipseResearchBoost / EclipsePlanetTypeBonus | 6 → 5 / 1 → 3 | 9 → 3 / 2 → 5 |
| RebellionCreditsAndQic | 6 → 3 | 8 → 3 |
| AcademyQicAction | 14 → 16 | 18 → 18 |
| **Build** | 11 → 16 | **12 → 23** |
| Upgrade | 18 → 18 | 19 → 18 |
| ResearchAdvance | 31 → 37 | 36 → 30 |
| **FormFederation** | 5 → 7 | **5 → 10** |
| GaiaFormation | 2 → 7 | 3 → 3 |
| **FreeAction** | **28 → 89** | 91 → 99 |

The Twilight replay that motivated the part is **unchanged in count** (3 → 3 over rounds 5–6; the 090 situation —
9 QIC and a legal replay — did not recur on these seeds). The gain came from the stock being spent: round-6 mines
12 → 23, federations 5 → 10 (Taklons A sat on 3.3 legal-federation decisions a seat-game in round 6 and formed 0.2;
B 0.5 / 0.5; Terrans 0.2 → 0.5, Xenos 0.3 → 0.5 formed), QIC → ore 15 → 21 over rounds 5–6, fewer Eclipse boosts
(15 → 8) and Rebellion credit+QIC actions (14 → 6). End state (`endgame_tech_counts.py`, seat mean A → B): Advanced
tiles 0.17 → 0.25, level 5 0.79 → 0.79, level 4+ 2.13 → 2.33, federation tokens 1.38 → 1.54, green left 0.42 → 0.50,
VP before final scoring 37.3 → 49.9 (so ≈ +12.6 of the +14.8 is scored inside the game, ≈ +2 in the final scoring).
Federations formed a seat-game (`federation_chances.py --by-arm`): Geodens 0.83 → 1.00, Taklons 0.83 → 1.33,
Terrans 1.00 → 1.33, Xenos 2.17 → 2.00.

**Side effect to check (③/④): the round-5 free-action surge.** B plays 89 free actions in round 5 against A's 28
(Taklons 7 → 41, Geodens 2 → 23); the kinds are OreToPower 2 → 26, OreToCredit 4 → 15, PowerToCredit 4 → 13,
QicToOre 1 → 8, KnowledgeToCredit 4 → 7. A round-5 rollout ends at the start of round 6, where B prices knowledge,
credits and ore alike (⅓ VP) and power and QIC at 0 — so inside round 5 the search already sees knowledge → credit
as free and ore → power as −⅓ VP, and ties fall to the default order. Ore → power (26) cannot be paid for by any
round-6 use the valuation sees; it is either a tie-break artefact or a chain the explain would show (power action in
round 6). It did not cost the sign (every clean pair positive), but it is the one place the part changes play where
the user did not ask it to. Decision ids for an explain: the first R5 split of p002 (step 211) and a B Taklons
round-5 OreToPower decision.

## Reading

- **Verdict (pre-registered, rounds 1–3 charges): identity confirmed** — +1.9 [−9.2, +13.0], three pairs identical
  through round 4, the other three split at the cap before the part can act. No early harm; the window cannot
  measure the part (same situation as 089 / 090, 090 (ㄱ) still pending).
- **Effect (pre-registered alongside metric): final VP +14.8 [+7.9, +21.8], 6 / 6 pairs, 3 / 3 clean pairs
  (+11.8).** The strongest 6-round VP result on the quartet so far and the first whose CI clears zero. Taklons
  +32.7 CI above zero; Terrans and Geodens positive with CIs through zero; Xenos nothing to reprice.
- **Mechanism is not the Twilight replay** but the general one the user named ("쓸 데가 없다는 것도 말이 안 되고"):
  QIC 2.7 → 0.0 left, ore 6.9 → 2.0, more round-6 mines and federations. The 7-charge QIC and the ore / knowledge
  prices made the deployment teacher hoard in round 6; at the final-scoring rates it spends.
- **One implementation wrinkle**: the price switch keys on the valued state's round, so round-5 rollouts also end at
  the final rates; that shifts round-5 play (free actions 28 → 89, lab-tile and research choices at the first splits).
  Net positive here, but a root-round-6-only variant would isolate the intended effect from this one.
- PPO gate: federations 1.38 → 1.54 a seat (still far from 3), tokens 0.42 → 0.50 green left. The ceiling is
  placement (089), unchanged.

Nothing changed in code or deployment; `endgame_prices` stays an opt-in part (`..._ships_endgame` factory). New tool
`tools/endgame_stock.py` (end stock per arm and faction + late FreeAction kinds). Lab queue after 096: 098 → 099 → 101.

## Proposal (user decision, nothing queued)

- (ㄱ) **Adopt `endgame_prices` into the deployment stack** (`ships` → base factory flag on for every faction; D1 deploy
  path as usual). Evidence: 6 / 6 pairs, +14.8 [+7.9, +21.8], clean pairs +11.8, 0 early harm, same decision time.
  The rules-correct valuation (QIC is worth 0 at the end) is the part, not a tuned number. If the user wants 12-pair
  evidence first: six more geo seeds, same design (≈ 3 h), pooled with 096.
- (ㄴ) **Root-round-6-only variant** `endgame_prices_r6` (flag read at the root decision, round-5 rollouts keep the
  guide prices; one bot turn, no new number) measured **ships_endgame vs ships_endgame_r6**, six new geo seeds, 6
  rounds (≈ 3 h): tells whether the round-5 shift helps or hurts. Only worth it after (ㄱ), since both arms carry
  the part.
- (ㄷ) **Lab 0, bot turn: explain two B decisions** — p002 step 211 (first R5 split, 4 / 4 comparisons: why tile 5
  over tile 9) and one Taklons B round-5 OreToPower — with `explain_ab_decisions.py`, to name the round-5 side effect
  before (ㄴ) is designed.
- (ㄹ) **Re-ask the Twilight question on the 090 seeds** (not new seeds): the 096 seeds never produced the "9 QIC and
  a legal replay" state; a 6-round rerun of 090 p003 with the endgame spec would show the replay being played in a
  game, not just at decision 296. Lower priority — the gain is already measured without it.

Bot recommendation: (ㄷ) now (lab 0), (ㄱ) as the user's decision, (ㄴ) after (ㄱ).
