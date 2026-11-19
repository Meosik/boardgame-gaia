# Cycle 126b — live AI worker decision times at the lab budget after the booster-tier fix (new factory, 4 comparisons, 60 s cap, parallel 2) — command, no games, not a teacher verdict

Not a teacher A/B: no A and B specs, no charges. Re-measurement of 126 with the same command (`tools/worker_times.py`
play mode, which starts `tools/ai_worker.py` as a child process and times every request). Queued 2026-11-19 by E205
(E204 (ㄱ), Codex clean, user standing order 2026-11-13). What changed since 126: the worker fix 9170cd7
(`ai_worker.install_budget` puts the factory's `choose` wrapper back after every per-request `budget_teacher.install`,
so the new factory's instant booster-tier choice survives the second request of a room; lab path untouched) and the
`selected` field in the rows of `worker_times.py`.
One cell: new factory `guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier` × level name `hard` (at lab commit
24da3f7 that name still meant the lab budget: 4 comparisons, one income ahead, 60 s cap), `GAIA_AI_PARALLEL=2`,
`Environment('quartet-e-88365')` from the first setup decision, played with the worker's own choices, 80 decisions,
wall limit 5400 s, a decision over 180 s ends the cell as a timeout. One seed, one run; same seed as 126 because it is
the same design re-measured, not a paired comparison per decision (the positions diverge once a choice differs).
Pre-registered reading: no pass / fail. ② the four starting-booster decisions must all be `booster-tier-N`, under 1 s,
0 comparisons — otherwise the fix failed and the guard proposal waits. If ② holds, the observed maximum is written down
as evidence for the server guard `GAIA_AI_TIMEOUT_SECS` (default 30 s): only "the guard has to be above it", the value
is the user's. A 180 s timeout or an error postpones the guard proposal. 1R / 2R time differences from 126 are not read
as an effect of the fix.
Host agentmaco, 2026-11-19 16:55:24 → 17:36:10 (40 min 46 s). Result: `lab/results/126b-worker-lab-budget-times-fixed.md`.

**Health: clean.** Exit code 0, 80 / 80 decisions, stopped by `decisions`, reached round 3, errors 0, 180 s timeouts 0.
No second-model review section (command job). Decision wall time mean 30.57 · median 31.83 · p90 60.04 · max 60.07 s;
wall total 2446.1 s.

## Charges in rounds 1–3 (the verdict)

None — no games, no arms. The pre-registered readings are below.

## Activation (did the fix fire?) — `metrics.cells[0].rows` of the result json

Starting-booster decisions (rows 8–11, candidates 7 · 6 · 5 · 4):

| Row | Candidates | 126 wall (comparisons) | 126b wall | 126b comparisons | 126b selected |
|---:|---:|---|---:|---:|---|
| 8 | 7 | 38.70 s (7/7) | 0.004 s | 0 | `booster-tier-2` |
| 9 | 6 | 33.08 s (6/6) | 0.002 s | 0 | `booster-tier-12` |
| 10 | 5 | 120.03 s (0/5) | 0.002 s | 0 | `booster-tier-13` |
| 11 | 4 | 15.15 s (4/4) | 0.003 s | 0 | `booster-tier-10` |
| Sum | | 207.0 s | 0.012 s | | |

**② confirmed: 4 / 4 are `booster-tier-N`, under 1 s, 0 comparisons** — the worker now takes the same path as the lab
teacher (`lab-123`: 192 / 192 booster decisions at 0.0 s, `booster-tier-N`). The 120 s decision of 126 is gone with the
path that produced it.

Starting places (rows 1–7) are the same shape as 126: 5 decisions compare every candidate (7.2–32.1 s; 6/6, 6/6, 2/2,
5/5, 5/5), one is cut at 60.04 s with 12 / 13 compared, one has no comparison (0.08 s). Sum 180.5 s (126: 179.9 s).

## Times (reference for the cap-60 setting)

| | n | mean | max | sum | 126 |
|---|---:|---:|---:|---:|---|
| Setup (0R) | 11 | 16.41 | 60.04 | 180.5 s | 386.8 s (places 179.9 + boosters 207.0) |
| 1R | 41 | 40.46 | 60.07 | 27.65 min | 38 decisions, mean 32.55, 20.6 min |
| 2R | 24 | 20.99 | 60.04 | 8.4 min | 31 decisions, mean 30.06 |
| 3R (start) | 4 | 25.70 | 39.82 | 1.7 min | not reached |
| All | 80 | 30.57 | 60.07 | 40.8 min | mean 31.94, max 120.03 |

Thresholds: over 30 s 41 / 80, over 60 s 12 / 80 (all 12 are the `time_capped` decisions, 60.00–60.07 s), over 90 s 0,
over 120 s 0. `time_capped` 12 (126: 4): one starting place (12 / 13), ten in 1R (2–3 of 4 comparisons), one in 2R (2 / 4).
After setup, 69 decisions: 45 finish all 4 comparisons (18.4–59.1 s, mean 35.65), 11 are cut at 60 s, 13 have no
comparison (≤ 0.54 s, `local-baseline`).

## Reading

- **Fix (②): confirmed.** The worker defect found in 126 (E204) is closed by 9170cd7 in a real worker run; the E208
  bot-turn measurement at the 20 s level saw the same (4 booster decisions at 0.0 s). Setup falls from 386.8 s to
  180.5 s and all of the difference is the booster path (places 179.9 → 180.5 s).
- **Guard (pre-registered, ② holds, no timeout, no error):** observed maximum 60.07 s — the cap plus under 0.1 s. For
  this setting a guard has to sit above 60.1 s; the default 30 s cannot be used with it (41 / 80 decisions over 30 s,
  mean 30.6 s). **But this setting no longer exists in the code**: the per-factory level table was removed in f9f9deb
  (E207, user 「난이도 관련 코드 하나도 건들지마」), so `hard` is again 4 comparisons · 20 s without parallel. The number
  is a reference for a cap-60 worker, not a proposal to change the guard now; the deployed level is timed by 127.
- **1R is longer than in 126 (27.65 min / 41 decisions vs 20.6 min / 38) and 12 decisions hit the cap instead of 4** —
  not read as an effect of the fix (pre-registered: the booster choices may differ and the positions diverge; 126 rows
  have no `selected` to check). A second uncontrolled cause: bot turns ran on the same machine during this run (worker
  tests for E206 / E207 at about 17:00–17:12, the E208 timing run of 181 s ending 17:17), overlapping decisions about
  18–41. So the 1R numbers here are an upper-side reading of the cap-60 setting; the booster rows and the maximum
  (bounded by the cap) are not affected.
- Waiting at cap 60 stays what 126 showed: about 30 s per decision and 20–28 min for one round of four AI seats — the
  reason E207 dropped this budget for the user-vs-AI path.
- Limits as in 126: one seed, one run, 80 decisions (setup–start of 3R), lab machine, one worker; rounds 3–6 (replay
  mode, E199 / E201) and inside the live container (E196 (b)) are not measured.

No code or deployment change. Lab queue after this cycle: `127-worker-new-teacher-hard-times` (E207; new factory at
the deployed hard level, 4 comparisons · 20 s, no parallel, same seed, 80 decisions) runs next on its own.

## Proposal (user decision, nothing queued)

- (ㄱ) Nothing new to queue: 127 is the measurement that decides the switch (pre-registered: over-30 s count 0, errors
  0, booster decisions `booster-tier-N` → `GAIA_AI_TEACHER` one line, no difficulty or guard change). Its result opens
  the next review turn.
- (ㄴ) Guard `GAIA_AI_TIMEOUT_SECS`: no change proposed (the cap-60 setting is out of the code). If a cap-60 worker
  ever returns, the guard has to be above 60.1 s — the value is the user's.
- (ㄷ) Unchanged, user commands or user numbers: deployment and `.env` (E208 command bundle), late-round replay timing
  (E199 / E201, size is the user's), in-container timing (E196 (b)).
Bot recommendation: (ㄱ) — wait for 127.
