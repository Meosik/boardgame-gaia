# Cycle 126 — live AI worker decision times at the lab budget (new factory, 4 comparisons, 60 s cap, parallel 2) — command, no games, not a teacher verdict

Not a teacher A/B: no A and B specs, no charges. One tool, `tools/worker_times.py` play mode (lab commit bc9d0b9),
starts `tools/ai_worker.py` as a child process and times every request. Queued 2026-11-19 by E203 (user E202
「난이도 일단 정리하자. 나중에 결정하고 일단 전부 최선의 자원으로 최대한의 점수」, Codex clean): `ai_worker.py` (b8dbd7a)
gives every level the lab budget (`LAB_BUDGET`: 4 comparisons, one income ahead, 60 s cap) when `GAIA_AI_TEACHER` is
the new factory `guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier`; this run times that setting.
One cell: new factory × level name `hard` (the three levels are the same budget), `GAIA_AI_PARALLEL=2`,
`Environment('quartet-e-88365')` from the first setup decision, played with the worker's own choices, 80 decisions,
wall limit 5400 s, a decision over 180 s ends the cell as a timeout. One seed, one run.
Pre-registered reading: no pass / fail — evidence for the server guard `GAIA_AI_TIMEOUT_SECS` (default 30 s): the guard
has to be above the observed maximum, the value is the user's; a 180 s timeout or an error postpones the guard proposal.
Read next to 125's new-factory hard cell (20 s cap, no parallel) without attributing the difference to one cause.
Host agentmaco, 2026-11-19 15:57:42 → 16:40:18 (42 min 36 s). Result: `lab/results/126-worker-lab-budget-times.md`.

**Health: clean run, one worker defect found in the reading.** Exit code 0, 80 / 80 decisions, stopped by
`decisions`, reached round 2, errors 0, 180 s timeouts 0, wall total 2555.7 s. No review section (command job).

## Decision time (no charges table — not an A/B)

Wall clock per decision, `worker_times.py` metrics (`rows` recounted with a python one-liner on the result json):

| Slice | n | mean | median | p90 | max | > 30 s | > 60 s | cut at the cap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All | 80 | 31.94 | 31.82 | 58.29 | 120.03 | 44 | 4 | 4 |
| Setup (round 0) | 11 | 35.17 | 29.04 | — | 120.03 | 5 | 2 | 2 |
| Round 1 | 38 | 32.55 | 31.95 | — | 60.04 | — | 1 | 1 |
| Round 2 (cut at 80 decisions) | 31 | 30.06 | 35.57 | — | 60.05 | — | 1 | 1 |
| All without the 4 starting-booster picks | 76 | 30.90 | 31.55 | 58.15 | 60.05 | 41 | 3 | 3 |

Over 90 s: 1, at or over 120 s: 1 (the same decision). The three "> 60 s" outside the booster picks are 60.04–60.05 s
(the cap plus 0.05 s).

Setup, in order (seconds · completed comparisons / candidates):
start places 29.04 · 6/6, 31.96 · 6/6, 7.09 · 2/2, 23.78 · 5/5, 27.88 · 5/5, **60.04 · 12/13 (cut)**, 0.08 · 0/4
= 179.9 s; starting boosters 38.70 · 7/7, 33.08 · 6/6, **120.03 · 0/5 (cut at the doubled cap)**, 15.15 · 4/4 = 207.0 s.
Setup sum 386.8 s (6.4 min; the worst-case estimate was 15 min; 125 new hard 299 s, old hard 140 s).
Whole round 1 (38 decisions, four seats together) = 20.6 min; the 31 decisions of round 2 = 15.5 min.

After setup (69 decisions): 54 finished all 4 comparisons (19.7–58.7 s, mean 37.93, median 35.35), 2 were cut at
60 s (2/4 and 1/4 comparisons finished), 13 had no comparison (≤ 0.19 s; 12 of them with 2 candidates).

Next to 125's new-factory hard cell (cap 20 s, no parallel, 25 decisions): setup mean 27.16 → 35.17 s, max 40.15 →
120.03 s, round 1 mean 10.06 → 32.55 s. Cap and parallelism changed together; not read as one cause.

## Activation — is the worker playing the lab's teacher?

- **Starting-booster picks are not the lab's path.** In lab games of the same factory and budget
  (`runs/lab-123-all-tier-selfplay-18f-full-third`, 48 games, `decisions.jsonl.gz` read with a python one-liner) all
  192 starting-booster picks take 0.0 s with `selected` = `booster-tier-N`: the factory's `install_booster_tier_choose`
  (`teacher_patches.py:5407`, E117) answers the pick at once, no search. In 126 the worker searched all four picks
  (15–120 s, 7/7 · 6/6 · 0/5 · 4/4 comparisons).
- **Cause (code + a runtime check).** `ai_worker.py:140` calls `budget_teacher.install(...)` on every request, and
  `budget_teacher.install` sets `TimedPreparationTeacher.choose = _choose` unconditionally (`budget_teacher.py:207`).
  The factory wraps `choose` once, when the room's teacher is created (first request); the second request's install
  removes the wrapper and the cached teacher is never rebuilt. Check in the bot work tree (worker order: install →
  factory → install): `TimedPreparationTeacher.choose._booster_tier` is True after the factory and False after the
  second install (`choose is budget_teacher._choose` True). `teacher_ab.py:264` installs once per process, so the lab
  keeps the wrapper.
- Scope: `install_booster_tier_choose` is the only patch that replaces `choose` (grep over `teacher_patches.py`,
  `parallel_search.py`, `fast_teacher.py`), so the deployed default factory `…_ships` is not affected — nothing is
  wrong on the live server today. It affects the new factory in the worker: 125's three new-factory cells and 126.
- Start places match the lab: in lab-123, 45 of 359 round-0 non-booster decisions are at the 60 s cap (max 60.1 s);
  126 has 1 of 7 (60.04 s, 12/13).

## Reading (HANDOFF 1 order does not apply — a timing measurement)

- **Guard evidence, as pre-registered**: observed maximum 120.03 s, so the default 30 s guard cannot be used with
  this setting — 44 of 80 decisions are over 30 s (41 of 76 without the booster picks; the mean itself is 32 s).
  Outside the booster picks every decision stays at or under the 60 s cap (max 60.05 s).
- **The 120 s maximum comes from the defect above**, a path the lab teacher never runs: the worker searches the
  starting-booster pick (cap doubled to 120 s, `setup_booster_seconds`) where the lab teacher takes the tier pick in
  0 s. So the worker at this setting is not yet "the lab's teacher": the booster it takes can differ from the tier
  pick, and 207 of the 387 setup seconds are spent there. The guard proposal is postponed for this reason (not a
  180 s timeout or an error — the pre-registered trigger did not fire; this is a different, stated reason): the
  maximum has to be re-measured after the fix. Expected, not measured: max ≈ 60 s, setup ≈ 180 s.
- The 120.03 s pick finished 0 of 5 comparisons while its neighbours finished 7 and 6 in 33–39 s. Why that one
  position's rollouts did not finish is **not established** (rows do not record seat or choice); after the fix the
  worker no longer runs this path, so it is left unexplained rather than investigated.
- **125 correction (E200)**: its new-factory cells ran the same defect. "New hard: the four starting-booster picks take
  40 s (cap × 2), cannot be swapped as is" and option (ㄹ) "turn the booster cap × 2 off in the worker" describe the
  defect, not the teacher: with the wrapper kept the picks take 0 s. New hard's 4 decisions over 30 s were exactly
  those four picks. 125's start-place findings (easy: all places compared without a cap; normal: 0 comparisons
  finished in 5 s) are not touched. The E200 options stay on hold (E202) and need a re-read after the fix.
- **Waiting time is the practical number**: at this setting an AI decision averages 32 s; round 1 took 20.6 min for
  the four seats together (38 decisions). The 60 s cap bounds one decision, not a round.
- Limits (unchanged): one seed, one run, 80 decisions (setup to round 2), lab machine, one worker; rounds 3–6 by the
  replay mode (E199 · E201, size is the user's number); inside the live container (E196 (b)) separately.

Nothing changed in code or deployment in this turn. Lab queue empty.

## Proposal (nothing queued in this turn)

- (ㄱ) Fix the worker so the factory's `choose` wrapper survives the per-request budget install (worker side only, the
  lab path untouched), with a test that fixes the order install → factory → install; record `selected` in
  `worker_times.py` rows. Then re-run this cell as 126b (same seed, 80 decisions, parallel 2; lab command ≈ 45 min):
  the four booster picks must be `booster-tier-N` in ≈ 0 s, and the maximum is re-read for the guard.
- (ㄴ) Guard `GAIA_AI_TIMEOUT_SECS`: value is the user's, after 126b (above the observed maximum; today's evidence says
  above 60 s outside the booster picks).
- (ㄷ) Later, unchanged: replay-mode timing of rounds 3–6 (E199 · E201, size is the user's number), in-container
  timing (E196 (b)), `GAIA_AI_PARALLEL=2` and `GAIA_AI_TEACHER` settings and deployment (user commands).
Bot recommendation: (ㄱ) first — bot turn for the fix, then lab ≈ 45 min; (ㄴ) after its result.
