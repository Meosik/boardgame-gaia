# Cycle 095 — ships vs ships_shipmine, geo quartet, 4 rounds (mine next to the ship before a QIC-paying entry)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (the deployment teacher).
B = `...-ships-shipmine-cap20.json`: the same plus `ship_adjacent_mine` for every faction — when a plain ship
entry (`ExploreSpaceship`) has to pay range QIC and a mine on a home or one-step ring planet at hex distance 1
from that ship tile is legal for no more QIC, the best such mine takes the entry's rank (score swap, order only;
Gaia, Asteroid and Transdim planets excluded). The user's question (2026-10-20): "함선에 들어가기 위해 qic를 썼는데
함선 바로 인접한 곳에 모행성/1테라포밍 행성이 있는 경우 그냥 함선 들어가나?" → "진행해". The argument: a ship is
explored, not colonized, so later range is measured from the nearest own planet (expansion rulebook p.9) — the
QIC spent on the entry leaves no footprint, while a mine next to the ship makes the entry free next turn.
Pre-registered verdict: charges gained in rounds 1–3 per faction (1 VP = 1.5 charges); read alongside: how
often the part fired, ExploreSpaceship counts and rounds (`action_counts.py`), QIC use, decision time, errors.
geo-quartet, 6 new seeds (913365–924006) × seat swap = 6 pairs, hard budget (4 comparisons, 20 s), stop at the
start of round 4, agentmaco, commit 8118fb6, 01:24 → 02:57 (1 h 33 min). Result: lab/results/095-ships-vs-shipmine-4r.md.
(The queue file is still `_095-…` — the hold of E52 — yet lab ran it after 094 was stopped; nothing to do about that.)

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 922 vs 923; A mean 11.42 s, median 16.05 s, p90 20.28 s, max 22.1 s; B mean 11.80 s, median
18.22 s, p90 20.28 s, max 22.5 s. Unsearched 654 vs 658. The part costs no time.

## Charges in rounds 1–3 (the verdict)

| Faction | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005) |
|---|---:|---:|---:|---|---:|---|
| Geodens | 178.5 | 173.0 | −5.5 | [−27.4, +16.3] | 2 / 6 | **0** · +7.8 · −13.6 · +15.8 · −43.1 · **0** |
| Taklons | 176.9 | 170.8 | −6.0 | [−32.4, +20.4] | 1 / 6 | **0** · −27.6 · −25.2 · −22.0 · +38.7 · **0** |
| Terrans | 187.9 | 192.9 | +5.0 | [−31.3, +41.3] | 3 / 6 | **0** · +4.4 · −50.9 · +21.2 · +55.4 · **0** |
| Xenos | 131.8 | 151.9 | +20.1 | [−3.5, +43.7] | 4 / 6 | **0** · +60.6 · +16.7 · +27.2 · +16.0 · **0** |
| **All (seat mean)** | | | **+3.4** | [−9.7, +16.5] | | 6 pairs |

**Two of the six pairs (p000, p005) are identical in every seat through round 3** — in those seeds the part changed
nothing. The other four pairs swing ±50 per faction; the all-seat mean is flat. Xenos +20.1 (4 of 4 non-identical
pairs positive) is under 088's 25-charge line and, as the activation section shows, Xenos never faced a decision
the part can touch. VP at the start of round 4 (not the verdict): all −1.2 [−2.9, +0.5]; Terrans −3.5 (12.2 → 8.7).
Posted watch replay: `pair-001/game-1-A01` seat 0 — Xenos A 62 vs Xenos B 122 in the other game of the pair.

## Activation

**Moves, rounds 1–3** (`action_counts.py`, A → B): ExploreSpaceship 40 → 43 (Geodens 11 → 12, Taklons 7 → 6,
Terrans 9 → 11, Xenos 13 → 14), Build 43 → 42, Upgrade 116 → 112, FormFederation 15 → 14. Ship entries did not
move.

**Where the part's condition held** (new `tools/shipmine_hits.py`: replays the run and lists every action-phase
decision whose candidate list held both a QIC-paying plain entry and a legal home / one-step mine at distance 1 from
that ship tile, with what was played): 42 A decisions and 46 B decisions in rounds 1–3 — but in 84 of those 88 the
seat played neither the entry nor the adjacent mine (an upgrade, a power action, research …; the condition is
usually present as background while the seat does something else). The user's actual scenario — **the QIC entry
chosen while the adjacent cheap mine was legal — happened once in 922 A decisions**: `pair-004/game-0-A01` step
48, Taklons round 1 (9 VP), Eclipse for 2 QIC vs a home-planet mine at −1,−2. B never faced it (0 of 923): that
pair had already split at step 39 (below). Both arms played the same adjacent mine once (Xenos, p004 step 25).

**First split of each pair** (`shipmine_hits.py --first-split`: same seed, arms swapped, the first decision where
the two games differ):

| Pair | First split | game-0 | game-1 | Part involved? |
|---|---|---|---|---|
| p000 | none | — | — | identical |
| p001 | step 49 R1 Terrans (cmp 4 / 4) | Pass booster 10 | Pass booster 11 | no (pass choice) |
| p002 | step 45 R1 Xenos (cmp 1 / 2) | PowerAction 0,−4 | ExploreSpaceship Rebellion | no (no adjacent-mine condition at that decision; comparison counts differ) |
| p003 | step 76 R2 Geodens (cmp 2 / 1) | ResearchAdvance Economy | TwilightRangeExploreSpaceship | no (range-tile entry, outside the part) |
| p004 | step 39 R1 Terrans (cmp 2 / 2) | RoundBoosterRangeBuild −4,−2 | RoundBoosterRangeExploreSpaceship Eclipse | no (booster-range entry, outside the part) |
| p005 | none | — | — | identical |

**None of the four splits is at a decision the part can act on**: two have different completed-comparison counts
(20 s wall clock, host load), the other two are ties the search broke differently. 095 measured search timing
noise, not `ship_adjacent_mine`.

## The three real situations, re-asked (③ implementation, lab 0)

`explain_decision.py --spec` on every recorded QIC-entry-with-adjacent-mine decision found in 095 and in 090 (six
6-round games per arm, same code both arms, `shipmine_hits.py --rounds 1-6`: **two such situations in 12 games**).
Plan values are the rollout's one-income forecasts, comparable across the two specs (same state, same values,
only the order differs):

| Situation | Entry | Adjacent mine | Entry plan (ships spec) | Mine-first plan (shipmine spec) | What the shipmine spec chooses |
|---|---|---|---:|---:|---|
| 095 p004 g0 step 48, Taklons R1, 9 VP | Eclipse, 2 QIC | home planet −1,−2 | **263.19** | 232.73 | Rebellion entry 254.28 — the Eclipse entry fell to −9.93 (the mine's old score) and was not compared |
| 090 p005 g0 step 54, Taklons R1, 12 VP | Eclipse, 1 QIC | home planet −1,4 | 267.84 | **278.75** | trading-station upgrade 282.61 on both specs (the recorded entry came from plan memory) |
| 090 p002 g0 step 119, Geodens R3, 10 VP | Twilight, 1 QIC | one-step planet −7,1 | **253.94** | 243.68 | the mine 243.68 — the Twilight entry fell to −13.60 and was not compared |

The swap itself works (the mine takes rank 0 with the reason text). But two things follow:

- **"Order only, the rollout decides" is not what happens.** The entry inherits the mine's one-step score (−2.5 …
  −13.6) and drops out of the 4-comparison window, so the rollout never compares entry against mine-first; the B
  arm plays the mine (or another ship) without the entry plan ever being valued. That is exclusion, the same shape
  as 092 Firaks / 093 Lantids (plans deleted by a list), not an ordering.
- **Within one income the rollout prefers the QIC entry in 2 of 3 situations** (+30.5, +10.3) and the mine-first
  plan in 1 (+10.9). The user's gain — the QIC kept for later, the entry free next turn — lies beyond the one-income
  horizon by construction, so neither the rollout nor the 1–3R charge verdict can see it (⑤).

## Reading (HANDOFF 1 order)

- ① Noise: all +3.4 [−9.7, +16.5], VP −1.2; two identical pairs, four pairs split by timing. Nothing to read.
- ② Activation: **the scenario is rare** — 1 in 922 decisions in 4R games, 2 situations in 12 six-round games.
  A 6-seed A/B cannot measure a rule that fires once; the per-decision explain is the instrument.
- ③ Implementation: the swap removes the entry from the comparison instead of ordering it; must be fixed before
  any re-measure.
- ⑤ Measurement: the claimed benefit is next-turn and later; a one-income rollout and 1–3R charges do not see it.
- Nothing is adopted; `ships_shipmine` stays opt-in and off the lab plan.

Code added: `tools/shipmine_hits.py` (opportunity list and `--first-split`). No teacher, spec or deployment change.

## Proposal (user decision, nothing queued)

- (ㄱ) **Make the part order-only in effect**: instead of swapping scores, add the adjacent mine to the compared
  set beside the entry (the entry keeps its score; the mine is compared first — the plan_menu "compare first" slot
  or a `root-N` candidate), so the rollout values both. Bot turn, tests, no new values. Do this only if (ㄴ) shows
  the mine-first plan winning somewhere.
- (ㄴ) **Measure by decision, not by A/B (lab 0)**: run `shipmine_hits.py --rounds 1-6` over the recorded 6R runs
  (076 · 079 · 081 · 089 · 090 · 096 when done), collect every QIC-entry-with-adjacent-mine decision (expect
  about two per six seeds), explain each under both specs, and count how often the mine-first plan beats the entry
  plan. Two of three so far say the entry; if that holds, the part has no job at this horizon.
- (ㄷ) **Ask the user about the 095 case** (standing rule: turn the question back with the facts): Taklons, round
  1, 9 VP, Eclipse entry for 2 QIC vs a mine on the home planet next to the ship — the rollout prefers the entry by
  30 within this round. Would the user build the mine first there, and what are the 2 QIC for later (a planet out of
  range, a Gaia planet, the 3-QIC action, a QIC academy)? If the answer is "the QIC itself", the fix is a
  two-income rollout for this plan only (the `geodens_two_incomes` precedent), not an ordering rule.
- (ㄹ) Drop the part and the question; keep `shipmine_hits.py` as a diagnostic.

Bot recommendation: (ㄴ) + (ㄷ) now (no lab time), (ㄱ) only on evidence from (ㄴ). Lab plan unchanged: 095a
(running) → 095b → 095c → 096 → 098 → 099 → 101.
