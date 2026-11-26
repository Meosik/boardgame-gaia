# Cycle 140a — prune probe — candidate counts under the pruning filter (E362) + random-map 4-faction pick, 3R snapshot

A = none (command job, no A/B). Part under test: the candidate-pruning filter `teacher_patches.prune_indices`
(E362: 1.1 off-track basic tiles, P1, P2 gaia-only exception, P4, P5 Gleens, F1, F2, F5 1–5R), applied to the
easy teacher's 3R decisions on `geo-quartet-24`; plus a random map seed and a fit score for the 14 base factions
(home-type planets within 3 hexes at terraform step 0–1, gaia-track factions +1 per gaia · +0.5 per transdim,
Gleens step 0 + gaia only) picking 4 factions with no shared board colour.
Queued 2026-11-26 by the user's 「일단 딱 한판 돌려볼래? 무작위 시드에서 젤 잘 풀릴거 같은 종족 4개 골라서」
(one-game exception to the 11-26 experiment hold), debate 1/1 two fixes, Codex clean (HANDOFF E362).
Pre-registered verdict: none. Health = exit 0, PROBE and PICK lines printed, no exception.
agentmaco, commit cc7886b, 2026-11-26 19:50:10 → 19:50:13 (3 s). Result: lab/results/140a-prune-probe.md.

**Health: clean.** Exit 0, both PICK and PROBE lines printed, no exception. 3 s because the probe calls
`prune_indices` on saved decision snapshots; it plays no game and runs no search.

## Candidate counts (no charges — not an A/B)

| Measure | Value |
|---|---:|
| Decisions probed (3R, 4 seats) | 38 |
| Candidates before → after | 1784 → 1509 (−275, −15.4%) |
| Cut: tech tiles | 245 (89% of cuts) |
| Cut: mines | 30 |
| Cut: federations | 0 |

Largest decisions (before → after, round, faction): Xenos 138 → 121 (R1), Taklons 113 → 83 (R3),
Terrans 108 → 77 (R3), Xenos 102 → 90 (R1), Geodens 88 → 58 (R2).

Pick on map `e362-20388`: Firaks 7.0, Itars 6.0, BalTaks 6.0, Xenos 5.5 (next Bescods 5.0 — same board as
Firaks, so skipped by the colour rule anyway; last Gleens 2.5, Lantids 2.0).
Seed arg for 140: `e362-20388@factions=Firaks,Itars,BalTaks,Xenos`.

## Activation

- Tile rules (1.1 off-track tiles) fire on most decisions: 245 cuts.
- Mine rules (P1/P2/P4/P5) fire rarely: 30 cuts in 38 decisions.
- Federation rules (F1/F2/F5) fired **0 times** — the easy teacher's 3R snapshots hold few or no federation
  candidates, so this probe does not test F1/F2/F5 at all.

## Reading (HANDOFF 1 order)

- ① noise: n/a (one fixed set of snapshots, deterministic filter).
- ② activation: tiles yes, mines a little, federations not exercised — F rules stay untested until a 6R game
  (140) logs `prune_blocked` on federation decisions.
- ③ scope: −15% is a **candidate count**, not compute saved — blocked candidates are still scored before the
  filter drops them (140b note). Speed gain, if any, comes only from the search not expanding them.
- ③ scope: the probe called the filter directly on the easy teacher's snapshots; whether the new factory
  `…_ships_menu1_all_tier_prune` really never picks a blocked candidate in play is 140b (queued, debate 1/1).
- ⑥ condition: the fit score is a home-area proxy (no ship range, no Lost Fleet, no round/final tiles), so
  "best four" means "best starting land on this map", not a measured strength.
- No second-model review section on this page (command job); the debate 1/1 findings were already taken in 140b.

No code or deploy change in this record. Lab queue: `140b-prune-factory-check` → in its review turn, if
`chose_blocked 0` and `with_blocked ≥ 1`, queue `140` (prune spec, 4 seats same teacher, 6R, 1 game, the seed arg above).

## Proposal (user decision, nothing queued)

- (ㄱ) After 140b passes, run 140 as already agreed (6R 1 game, ≈1–2 lab hours at cap60) — the user's
  one-game exception; no new experiment beyond it while the theory hold stands.
- (ㄴ) In 140's review, count `prune_blocked` by kind per round to see whether F1/F2/F5 ever fire (bot turn).
Bot recommendation: (ㄱ) via 140b's review turn, then (ㄴ) in the 140 record.
