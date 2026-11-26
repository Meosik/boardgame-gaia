# Cycle 140 — prune spec × 4 seats — one observed game on a random map, 6R

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-prune-cap60-p2.json`
(ships_menu1_all_tier + E362 candidate pruning tables: off-track tiles, mine P1/P2/P4/P5, federations F1/F2/F5).
No A/B: the same teacher in all four seats. Queued 2026-11-26 by E366 (E365 (ㄱ), the agreed one-game exception to the
experiment hold, user E362 「일단 딱 한판 돌려볼래? 무작위 시드에서 젤 잘 풀릴거 같은 종족 4개 골라서」).
Pre-registered verdict: none (observation). Health: exit 0, game complete, 0 errors / timeouts, fallback count and
max decision time (≈ 80 s), 0 blocked candidates chosen in any round (by replay). To read: seat VP · federations ·
R1–3 charges (reference), blocked counts by round and kind (does F1/F2/F5 ever fire), candidates per decision.
Seed `e362-20388@factions=Firaks,Itars,BalTaks,Xenos` (140a PICK), 1 game, comparisons 4, cap60, 6R, agentmaco,
commit 8f6fa17, 2026-11-26 20:07 → 21:29 (1 h 22 min). Result: lab/results/140-prune-one-game.md.

**Health: clean.** 1/1 game complete, 291 teacher decisions (Firaks 75, Itars 63, BalTaks 55, Xenos 98), 0 errors,
0 timeouts, 0 fallback timeouts, 0 federation limit hits. Decision seconds (log): mean 16.9 · median 11.0 · p90 45.4 ·
max 60.0 (25 decisions above 55 s, all within the cap60 limit). prune_blocked logged on every row (0 None).

## Outcome (no verdict)

| Seat | Faction | Final VP | Federations formed (log, round) |
|---|---|---:|---|
| 0 | Firaks | 86 | 1 (R3) |
| 1 | Itars | 96 | 2 (R3, R6) |
| 2 | BalTaks | 83 | 1 (R6) |
| 3 | Xenos | **110** | 3 (R3, R5, R6) |

R1–3 charges: **not recomputed** — `charge_rounds.py` in the work tree stops with "candidate index 33 is out of
bounds" (see Activation: the work-tree engine build differs from the lab's).

## Activation (decision log `prune_blocked`, the lab's own engine)

| Round | Decisions | Candidates | Blocked | Decisions with blocked |
|---|---:|---:|---:|---:|
| 0 (setup) | 13 | 70 | 0 | 0 |
| 1 | 45 | 1143 | 91 | 9 |
| 2 | 28 | 549 | 46 | 4 |
| 3 | 48 | 2179 | 217 | 16 |
| 4 | 26 | 1382 | 140 | 9 |
| 5 | 40 | 3770 | 410 | 20 |
| 6 | 91 | 5073 | 1112 | 34 |
| **All** | 291 | 14166 | 2016 (14.2%) | 92 |

R1–3: 3871 candidates over 121 decisions (32.0 per decision), 354 blocked (9.1%) → 3517 left. 140a's probe
(1784 → 1509, −15.4%) was another game and seed; the rates are not comparable as savings (pre-registered caveat).
R6 has the highest blocked share (21.9%).

**Not done: blocked-choice check and per-kind tags.** `lab/scratch_140_replay.py` replays the logged choices and
recomputes `prune_indices` with a rule tag per blocked candidate, but in the work tree the replay leaves the log at
step 17 (round 1: 32 candidates here, 34 logged; digest differs from step 0). The work-tree `gaia_rl` build is not the
lab's build (same source commit). Up to step 17 the recomputed counts match the log (0 mismatches; 1 decision, 2 P1
mine candidates blocked, not chosen). So "0 blocked chosen" and "does F1/F2/F5 fire" stay open.

## Reading (HANDOFF 1 order)

- One game, one map, no comparison arm: no strength reading (① noise is total). Xenos 110 with 3 federations is the
  only seat to reach the PPO gate's ≥3 federations; Firaks and BalTaks formed one each.
- ② activation: the filter fires every round from R1 (92 decisions, 2016 candidates), rising to 22% in R6, where
  federation candidates are numerous — the first sign F rules may fire (140a · 140b saw 0 federation blocks), but
  the kind is unverified until the replay runs on the lab build.
- Health and timing clean; cap60 respected.

No code or deployment change. Lab queue: empty after this game; experiment hold (E362, theory phase 2026-11-26) stands.

## Proposal (user decision, nothing queued)

- (ㄱ) Rebuild the work-tree engine (owner command: `cd ~/projects/gaia-work/gaia-rl` then
  `VIRTUAL_ENV=$PWD/.venv .venv/bin/maturin develop --release`), then one bot turn runs `lab/scratch_140_replay.py`
  and `charge_rounds.py`: blocked-choice 0 check, F1/F2/F5 tags, R1–3 charges. Cost: a few minutes + one bot turn.
- (ㄴ) Publish the game's replay (Xenos seat) for the user to watch. Bot turn.
- Bot recommendation: (ㄱ) then (ㄴ); no new games while the theory phase holds.
