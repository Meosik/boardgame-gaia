# Cycle 119 — 6R self-play collection, second batch (all_tier, 18 factions, 48 seeds × 1 game), command, no verdict

No A/B: one `command` job, `teacher_ab.py run --single` (one game per seed) with the same teacher in all four
seats — `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(`ships_menu1_all_tier`, cap60-p2, 4 comparisons), the 114 settings (`GAIA_ENGINE_FIXES_2=1`,
`GAIA_FEDERATION_ONE_ROUTE` off). Purpose: more behaviour-cloning / PPO initial-value data, 46 games → about 94
(E156 (ㄷ), released by the owner 2026-11-16 「추천 대로 해」, E157). Teacher-side changes since 114: 7cb307b (cap
passed before the search → root first choice, counted as a fallback timeout), 632b63f · f683e19 (decision log
`round`, `digest`, `timing`), engine 966e9ea (candidate list unchanged with the flag off, 115c).
Pre-registered verdict: none. Pre-registered checks: ① 48/48 games complete (failures, timeouts, fallback
timeouts; do the two re-run seeds finish) ② every decision row has `chosen` ③ maximum decision time, share over
60 s, count over 100 s (does the 110 s path of 115d appear with the flag off) ④ `bc_dataset.py index` → `stats`
for this run (strict replay, 6R games, decisions, engine build id; the 114 games on the same build) ⑤ reference
only: seat mean final VP, federations per seat, unflipped federation tokens against 114's 100.1 · 1.50 · 0.52.
18 factions, quartets geo 2 · a 10 · b 10 · c 9 · d 9 · e 8 with `@order` (current `faction_strength.py` order):
46 new seeds + the two seeds 114 lost to a crash (quartet-b-68171, quartet-d-75189, same order as in 114), one
game each, six rounds, agentmaco, commit 71e83b3, 2026-11-16 16:21 → 11-17 08:17 (15 h 56 min; estimate ≈ 16 h).
Result: lab/results/119-all-tier-selfplay-18f-full-more.md. No replay posted. No second-model review section
(command job).

**Health: 47/48 games complete, 1 error game, 9 fallback-timeout decisions.** Exit code 0. Timeouts 0,
federation candidate limit hits 0. Decision time over the 14,257 rows of the complete games (decision logs,
python count): mean 15.8 s · median 8.1 · p90 46.7 · p99 60.1 · max 138.3; over 60 s 894 rows (6.27 %; 114: 5.1 %),
over 80 s 6, over 100 s 2. Every row over 80 s is one of the 9 fallback rows. The A/B columns of the result page
are only `a_seats` labels of the same teacher and mean nothing here.

The error game: `pair-017/game-0-A03`, seed quartet-b-86715@order=3,1,2,0 (Bescods, Itars, BalTaks, Gleens), a
new seed, stopped at step 17 (round 1; 17 rows logged, the next mover by turn order is seat 2 BalTaks — the
failing decision itself is not in the log). `workers.log`: `ValueError: No eligible continuation; do not silently
pass` (`baseline-teacher-20260917/four_factions/preparation.py:555`), raised inside a rollout of `select_goal`
(`parallel_search.py:54` → `:215`) → worker exit code 1. Same message and same quartet as the 110 · 111 · 112 error
games; that path was closed for `gaia_asteroid_hold` in d5946bd · 61edf20 and passed the 112a2 regression on the
112 seed. Which filter left no candidate here is **not identified** (not replayed in this turn).

The 9 fallback-timeout decisions (`fallback_timeout` true, `completed_comparisons` 0, `time_capped` true; stage
times from the decision log `timing.stages`, python listing):

| Game | Seed | Step · round · faction | Seconds | Stage that took the time |
|---|---|---|---:|---|
| pair-001 | geo-quartet-1086706 | 91 · R2 · Xenos | 60.9 | `planned_tasks` 60.8 |
| pair-002 | quartet-a-89435 | 225 · R6 · Ivits | 138.3 | `planned_tasks` 137.1 |
| pair-014 | quartet-b-83174 | 179 · 184 · 189 (R5), 206 (R6) · Gleens | 88.4 · 89.6 · 90.6 · 89.0 | `root_rank` 88.3 – 90.5 |
| pair-021 | quartet-b-98306 | 229 · R6 · BalTaks | 107.0 | `root_rank` 106.8 |
| pair-025 | quartet-c-95821 | 204 · R5 · Ambas | 66.4 | `root_rank` 65.9 |
| pair-031 | quartet-d-75189 | 111 · R3 · Taklons | 60.8 | `planned_tasks` 60.3 |

## Charges in rounds 1–3 (the verdict)

None — no A/B, no pairs. Nothing is judged by this run.

Final VP (reference, `result.json` scores of the 47 complete games, 188 seat-games): seat mean **99.0** (114:
100.1; min 38, max 167), winner mean 122.5 (114: 124.1). By faction (seat-games): Xenos 119 (19) · SpaceGiants 111
(8) · Firaks 110 (10) · Taklons 106 (11) · Tinkeroids 105 (9) · Darkanians 103 (8) · Terrans 100 (19) · Bescods 97
(9) · Ivits 96 (10) · Ambas 95 (9) · Geodens 95 (11) · BalTaks 93 (9) · Lantids 92 (10) · Moweyds 91 (9) · Gleens 89
(9) · HadschHallas 88 (9) · Nevlas 88 (10) · Itars 84 (9). 8–19 seat-games per faction on different seeds and
tables: not a faction ranking.

## Activation (pre-registered checks)

- ① Completion: 47/48 (above). Not the pre-registered 48/48. Both re-run seeds finished: quartet-b-68171
  112 · 86 · 60 · 118 (no fallback row; the 114 crash at step 224 did not recur), quartet-d-75189 137 · 64 · 88 · 79
  (one fallback row at step 111 — the step where 114 crashed and where 115d logged its 110 s decision).
- ② `chosen`: 14,257 of 14,257 rows of the complete games carry `chosen` and `index` (python count over every
  `decisions.jsonl.gz`); the error game's 17 rows too.
- ③ Decision time: max 138.3 s, over 60 s 6.27 %, over 100 s 2 rows (138.3 s Ivits R6, 107.0 s BalTaks R6) — the
  100 s+ path does appear with the flag off, in the fallback rows only (table above).
- ④ `bc_dataset.py index <lab runs> --glob lab-119-all-tier-selfplay-18f-full-more` → `stats` (work tree, bot
  turn): **games 47, replay on this engine 47, 6-round 47, decisions 14,257**; engine `fc19671c4278` = current
  build, replay-checked on `fc19671c4278` for all 47 (strict replay, `chosen` compared per row). The 114 games:
  46/46 on the same build (E161, `runs/bc-114-fc19/manifest.jsonl`). Together 93 games, 28,098 decisions on one
  engine build. Seat-games: Xenos 19, Terrans 19, Taklons 11, Geodens 11, Ivits · Lantids · Firaks · Nevlas 10,
  Bescods · BalTaks · Itars · Gleens · Ambas · HadschHallas · Moweyds · Tinkeroids 9, Darkanians · SpaceGiants 8.
  (Manifest in the work tree's `runs/bc-119-fc19/manifest.jsonl`, not committed.)
- ⑤ Federations (reference): 286 `FormFederation` choices in 188 seat-games = **1.52 per seat** (114: 1.50) —
  counted from `chosen` in the decision logs, the same quantity as 114's action count, not with
  `federation_chances.py`; highest Xenos 2.63 and HadschHallas 2.11, lowest Geodens 1.09 and BalTaks · Gleens ·
  Tinkeroids 1.11. `endgame_tech_counts.py`: federation tokens held 1.59 per seat (114: 1.57), **unflipped (green)
  0.53** (114: 0.52), of those 0.46 with a level-5 step or Advanced tile still available (0.45); Advanced tiles
  0.36 per seat (32 % of seats; 114: 0.36), level-5 tracks 0.70 (67 %; 114: 0.69).
- Extra (the open item of E158 (나): the BC smoke against teacher games on the same two seeds, `charge_rounds.py
  --games`, charges gained in rounds 1–3 per seat). Teacher (119, four teacher seats) → BC (encoding 4, fold-0
  checkpoint of 118, four BC seats, `runs/smoke-policy-bc-114-v4b` · `-v4c`):
  quartet-b-68171 Bescods 302 → 126 · BalTaks 174 → 164 · Itars 132 → 46 · Gleens 147 → 176 (seat mean 188.8 → 128.0);
  quartet-d-75189 Taklons 237 → 149 · Moweyds 137 → 44 · Tinkeroids 184 → 68 · Geodens 180 → 92 (184.5 → 88.3).
  BC lower in 7 of 8 seats, mean −78.5 charges per seat.

## Reading (HANDOFF 1 order)

- Collection: 47 six-round games, 14,257 decisions, all replaying strictly on the current build — with 114, 93
  games and 28,098 decisions on one build, about twice the 114 set. The reference numbers sit on 114's (VP 99.0
  against 100.1, federations 1.52 against 1.50, green tokens 0.53 against 0.52, Advanced tiles 0.36 against 0.36):
  nothing in them speaks against pooling the two runs as one data set. They are means of different seeds, not a
  test of equality.
- Error game — ③ implementation, not noise: `No eligible continuation` is the quartet-b crash of 110 – 112 again,
  on a new seed, after the fix d5946bd · 61edf20. Either another filter than `gaia_asteroid_hold` can leave a
  rollout seat without a candidate, or the fix does not cover every state; 112a2 only showed that the 112 seed no
  longer crashed (its own stated limit: the fixed branch was not shown to run). In the two 48-game collections
  after the fix: 0/48 (114), 1/48 (119) games; other runs were not recounted. It is a crash path of the
  deployed-teacher family and costs a whole game each time.
- Fallback rows — the pre-search overrun of 114 · 115d now has a stage: `planned_tasks` (3 rows, 60.3 – 137.1 s) or
  `root_rank` (6 rows, 65.9 – 106.8 s), both inside `prefetch`. Neither stops at the cap (137 s against a 60 s
  cap), so 7cb307b turns the crash into a root-first move but does not shorten the decision. 115e could not show
  this (its `root_rank` maximum was 1.08 s, it stopped at round 4); seven of the nine rows here are in rounds
  5–6. For quartet-d-75189 the slow decision is at step 111 in 114 (crash), 115d (110 s) and 119 (`planned_tasks`
  60.3 s) — the same step number; that the three states are equal was not checked. Why the two stages take that
  long (candidate count, plan count) is not identified.
- For the data: 9 of 14,257 rows (0.06 %) carry the root ranking's first choice instead of a searched choice.
  They replay like any other row; whether the export keeps `fallback_timeout` was not checked. At this share they
  cannot move a BC accuracy number; the row count is recorded so a later, larger share is noticed.
- BC smoke against the teacher on the same seeds (extra item): −78.5 charges per seat over rounds 1–3, 7/8 seats,
  against a same-code drift of ±30 per faction and ±50 per pair (084/088). Two games, one checkpoint (fold 0, 114
  data only, old engine build), tables of four BC seats against tables of four teacher seats — not an A/B and not
  a strength verdict, but far outside drift → the E157 rule for (ㄹ) reads "wide apart → 12 pairs".
- Final VP and federations are references for the BC-vs-teacher comparison, not verdicts.

No code or deployment change. Lab queue after this cycle: 120-bc114-v4-rebuilt-engine (≈ 15–20 min).

## Proposal (user decision, nothing queued)

- (ㄱ) The pre-registered next step: export 114 + 119 with encoding 4 (93 games) and measure the data-volume
  effect again with the game-level cross-validation of 117 ③ / 118 (same width 256, 9 epochs, folds by game and
  quartet; train on about 18 / 37 / 74 games, paired by validation game). Lab command, ≈ 40 min; after 120 ✅ says
  the rebuilt engine leaves the encoding-4 rows unchanged (if 120 fails its row comparison, its cause comes
  first).
- (ㄴ) Diagnose the crash: replay `pair-017` to step 17 and find which filter leaves the rollout seat without a
  candidate; then a fix with a test and a regression run on quartet-b-86715. One or two bot turns + ≈ 40 min lab.
- (ㄷ) Pre-search overrun: make `planned_tasks` · `root_rank` respect the cap or find why they take 60–137 s (9
  decisions in 47 games, all handled by the fallback). Teacher tuning is paused (E128); only needed before the
  next long collection.
- (ㄹ) BC (encoding 4) vs teacher A/B: 12 pairs by the E157 rule (wide gap in the smoke), after (ㄱ) gives the
  full-data checkpoint; the lab venv torch install is an owner command.
Bot recommendation: (ㄱ) first (the lab is idle after 120), (ㄴ) in the bot turn after it, (ㄹ) once the full-data
checkpoint exists; (ㄷ) waits.
