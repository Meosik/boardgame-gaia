# Cycle 123 — 6R self-play collection, third batch (all_tier, 18 factions, 48 seeds × 1 game), command, no verdict

No A/B: one `command` job, `teacher_ab.py run --single` (one game per seed) with the same teacher in all four
seats — `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(`ships_menu1_all_tier`, cap60-p2, 4 comparisons), the 114 · 119 settings (`GAIA_ENGINE_FIXES_2=1`,
`GAIA_FEDERATION_ONE_ROUTE` off). Purpose: behaviour-cloning / PPO initial-value data from 93 games to about 141 —
the pre-registered consequence of 121a ① (about 74 against 37 training games at equal steps: +2.32 pt
[+1.68, +2.96], above 0 = the number of games is still one of the limits). Queued 2026-11-18 by the owner's
「추천대로 해」 (E166 (ㄴ), E168); 48 games = the value of the two earlier collections. No engine, teacher or
`teacher_ab` change since 119; the known 119 crash (`No eligible continuation`) and the pre-search overrun were
left unfixed on purpose so the collecting teacher stays the one of 114 · 119.
Pre-registered verdict: none. Pre-registered checks: ① 48/48 games complete (failures, timeouts, fallback
timeouts) ② every decision row has `chosen` ③ maximum decision time, share over 60 s, count over 100 s, the
`timing.stages` of fallback rows ④ `bc_dataset.py index` → `stats` (strict replay, 6R games, decisions, engine
build id = fc19671c4278 as in 114 · 119, largest candidate count) ⑤ reference only: seat mean final VP,
federations per seat, unflipped federation tokens against 114's 100.1 · 1.50 · 0.52 and 119's 99.0 · 1.52 · 0.53.
18 factions, quartets geo 2 · a 10 · b 10 · c 9 · d 9 · e 8 with `@order` (current `faction_strength.py` order), 48
new seeds, one game each, six rounds, agentmaco, commit f624307, 2026-11-18 15:33 → 11-19 06:44 (15 h 11 min;
estimate ≈ 16 h). Result: lab/results/123-all-tier-selfplay-18f-full-third.md. No replay posted. No second-model
review section (command job).

**Health: clean — 48/48 games complete, 0 error games, 3 fallback-timeout decisions.** Exit code 0,
`games_complete` 48, `failures` empty, timeouts 0, federation candidate limit hits 0. Decision time over the
14,050 rows (decision logs, `lab/scratch_123_stats.py`): mean 15.3 s · median 8.2 · p90 43.9 · p99 60.1 · max 69.8;
over 60 s 725 rows (5.16 %; 114: 5.1 %, 119: 6.27 %), over 80 s 0, over 100 s 0 (119: 6 and 2). The A/B columns of
the result page are only `a_seats` labels of the same teacher and mean nothing here.

The 3 fallback-timeout decisions (`fallback_timeout` true, `completed_comparisons` 0, `time_capped` true,
`selected` `local-baseline`) are one game and one seat in a row: `pair-023`, seed quartet-c-107925@order=0,1,2,3,
Terrans, round 4, steps 196 · 197 · 199 (68.7 · 69.4 · 69.8 s). Stage times (`timing.stages`): `planned_tasks`
67.7 · 68.5 · 69.0 s, `root_rank` 0.9 · 0.9 · 0.8 s — all three are the `planned_tasks` path inside `prefetch`.

## Charges in rounds 1–3 (the verdict)

None — no A/B, no pairs. Nothing is judged by this run.

Final VP (reference, `result.json` scores, 192 seat-games): seat mean **99.1** (114: 100.1, 119: 99.0; min 47,
max 162), winner mean 121.6 (124.1, 122.5). By faction (seat-games): Xenos 115 (19) · Firaks 114 (10) · Tinkeroids
105 (9) · SpaceGiants 104 (8) · Terrans 103 (19) · Moweyds 101 (9) · Taklons 101 (11) · BalTaks 100 (10) · Bescods 99
(10) · Darkanians 98 (8) · Gleens 97 (10) · Geodens 97 (11) · Itars 92 (10) · Ivits 92 (10) · Nevlas 90 (10) · Ambas
89 (9) · HadschHallas 86 (9) · Lantids 84 (10). 8–19 seat-games per faction on different seeds and tables: not a
faction ranking.

## Activation (pre-registered checks)

- ① Completion: **48/48**, the pre-registered value (114: 46/48, 119: 47/48). The quartet-b crash of 119
  (`No eligible continuation`) did not occur in the 10 quartet-b games.
- ② `chosen`: 14,050 of 14,050 rows carry `chosen` and `index` (python count over every `decisions.jsonl.gz`;
  the sum of `steps` in the 48 `result.json` files is also 14,050).
- ③ Decision time: max 69.8 s, over 60 s 5.16 %, over 100 s 0. The only rows that passed the cap before the
  search are the three `planned_tasks` rows above.
- ④ `bc_dataset.py index <lab runs> --glob lab-123-all-tier-selfplay-18f-full-third` → `stats` (work tree, bot
  turn): **games 48, replay on this engine 48, 6-round 48, decisions 14,050**; engine `fc19671c4278` = current
  build = the build of 114 · 119, replay-checked on `fc19671c4278` for all 48 (strict replay, `chosen` compared
  per row). Together with 114 (46 games, 13,841) and 119 (47, 14,257): **141 games, 42,148 decisions on one
  engine build.** Seat-games: Terrans 19, Xenos 19, Taklons 11, Geodens 11, Firaks · Lantids · Ivits · Nevlas ·
  BalTaks · Bescods · Gleens · Itars 10, Ambas · HadschHallas · Tinkeroids · Moweyds 9, SpaceGiants · Darkanians 8.
  Largest candidate count (`lab/scratch_capacity_119.py 123`, replay without encoding): **2,417** — one decision
  over the encoder capacity 2048 (quartet-c-123829, round 5, Terrans, step 189: 2,324 of the candidates are
  `FormFederation` routes, and a federation was the chosen move); 7 decisions over 1,024, p99 327. (Manifest in
  the work tree's `runs/bc-123-fc19/manifest.jsonl`, not committed.)
- ⑤ Federations (reference): 283 `FormFederation` choices in 192 seat-games = **1.47 per seat** (114: 1.50, 119:
  1.52; counted from `chosen` in the decision logs as in 119). Highest Xenos 2.32, HadschHallas 2.00, Bescods ·
  Ivits 1.90; lowest BalTaks · Moweyds 1.00, Firaks · Nevlas 1.10. Seats by number of federations formed: 0 → 1,
  1 → 107, 2 → 76, 3 → 8 (Xenos 7, Bescods 1); games in which every seat formed at least two: 1 of 48, at least
  three: 0. `endgame_tech_counts.py`: federation tokens held 1.54 per seat (114: 1.57, 119: 1.59), **unflipped
  (green) 0.51** (0.52, 0.53), of those 0.39 with a level-5 step or Advanced tile still available (0.45, 0.46);
  Advanced tiles 0.34 per seat (33 % of seats; 0.36, 0.36), level-5 tracks 0.70 (66 %; 0.69, 0.70).

## Reading (HANDOFF 1 order)

- Collection: all four pre-registered checks pass. 48 six-round games, 14,050 decisions, every one replaying
  strictly on the build of 114 · 119 → the BC / PPO initial-value set is 141 games and 42,148 decisions on one
  engine build, half as large again as the 93 games that 121a · 122 measured.
- Reference numbers sit where 114 and 119 sit (VP 99.1 against 100.1 · 99.0, federations 1.47 against 1.50 · 1.52,
  green tokens 0.51 against 0.52 · 0.53, Advanced tiles 0.34 against 0.36 · 0.36, level-5 tracks 0.70 against
  0.69 · 0.70): nothing in them speaks against pooling the three runs. They are means over different seeds, not
  a test of equality.
- The same numbers are also the current teacher's level on the owner's federation question (E173 – E181): a
  third federation in 8 of 192 seats (7 of them Xenos), no game with three federations in every seat, one game
  with two in every seat. This is a third sample of the picture of E174 · E175 (93 games: every seat ≥ 2 in 3
  games, ≥ 3 in 0), not new information, and no cause is measured here.
- Crash: 0 of 48 here. Over the three 48-game collections after the fix d5946bd · 61edf20 the
  `No eligible continuation` crash is 0/48 · 1/48 · 0/48 games. The cause of the 119 game is still not
  identified; one clean run does not show it is gone.
- Fallback rows — ③ implementation, same path as 119: `planned_tasks` runs past the 60 s cap (67.7 – 69.0 s) and
  7cb307b plays the root ranking's first choice. Three consecutive Terrans decisions of one round in one game;
  why `planned_tasks` takes that long in that state is not identified (not replayed). 119 also had `root_rank`
  rows and decisions up to 138 s; this run has neither, which is a difference of seeds, not of code.
- For the data: 3 of 14,050 rows (0.02 %; pooled 12 of 42,148, 0.03 %) carry an unsearched root-first choice as
  the label. Whether the export keeps `fallback_timeout` is still not checked (open since 119); at this share
  they cannot move a BC accuracy number.
- Capacity: one decision lists 2,417 candidates (119 had one with 2,257). The export needs `--capacity 4096` as
  in 121a; play and PPO use the run-time capacity 4096 of db997d9 (E172).
- Final VP and federations are references, not verdicts.

No code or deployment change (the manifest and the scratch script are outside git). Lab queue after this cycle:
empty.

## Proposal (user decision, nothing queued)

- (ㄱ) The step the queue note named: export 114 + 119 + 123 with encoding 4 (`--capacity 4096`, 141 games,
  42,148 decisions) and measure the data amount one step further on the game-level, quartet-stratified 5 folds of
  121a · 122 — the `all` arm (about 113 training games) against a two-thirds arm (about 75 games) stopped at the
  same number of steps, paired by validation game — with the 18-epoch curve of 122, plus a full-data training
  that saves a checkpoint per epoch (checkpoint epoch = fold-mean validation-loss minimum, the 122 rule). Lab
  command, about 1.5 – 2 h (121a ≈ 60 min and 122 38 min on 93 games); the script is committed before the queue
  file. It runs in the work tree on build fc19671c4278, so it goes before (ㄴ).
- (ㄴ) The owner's ladder order (E177 · E180 · E181): implement the seed suffixes `@factions=` · `@tiles=` in
  `gaia-rl/src/env.rs` and push → rebuild (owner command) → baseline 12 games on quartet-e-88365 with the fixed
  faction list (≈ 4 h). Bot turn; it changes the engine build id, so after the rebuild the three manifests are
  re-indexed and the full-data checkpoint of (ㄱ) is trained again (≈ 20 min of lab, as 120 did for 114) — the
  data-amount measurement of (ㄱ) stays valid.
- (ㄷ) Waiting as before: checkpoint epoch choice E171 (ㄱ), BC against teacher A/B of 12 pairs (lab venv torch is
  an owner command), E179 fix choice (ㄱ)(ㄴ)(ㄷ), E177 dispute, E170 (ㄱ)(ㄴ)(ㄷ), the 119 crash cause, the
  `planned_tasks` overrun.
Bot recommendation: (ㄱ) now while the lab is idle and the build id is unchanged, then (ㄴ) in the turn after its
result.
