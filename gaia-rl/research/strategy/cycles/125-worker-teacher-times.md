# Cycle 125 — live AI worker decision times: old factory vs lab's current factory × easy / normal / hard — command, no games, not a teacher verdict

Not a teacher A/B: no A and B specs, no charges. One tool, `tools/worker_times.py` (lab commit d1d6757), starts
`tools/ai_worker.py` as a child process per cell and times every request. Queued 2026-11-19 by E195 (user 「바꾸고 한번에
배포하자」, E194 (ㄱ)): before the live teacher is swapped, measure what the swap does to decision time. In E194 the
new factory's easy level did not finish 40 decisions in 7 minutes and the old factory had never been timed.
Cells: 2 factories (old = `guide_r1_charge3_lf_more_vm_lf_ts_ships`, the worker's default = what the live server
runs; new = `guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier`, chosen with `GAIA_AI_TEACHER`) × 3 levels
(`ai_worker.py` `LEVELS` as they are: easy comparisons 0 · no cap, normal 2 · 5 s, hard 4 · 20 s) = 6 cells.
Each cell: `Environment('quartet-e-88365')` from the first setup decision, played with the worker's own choices,
stop at 80 decisions or 420 s of wall clock; a decision over 180 s ends the cell as a timeout. Cells diverge, so this
is a time distribution, not a same-position comparison. One seed, one run.
Pre-registered reading (queue note): a new-factory cell with 0 decisions over 30 s (the server guard
`GAIA_AI_TIMEOUT_SECS` default, `gaia-server/src/ai.rs:73` — past it the live server plays a fallback move),
0 timeouts and 0 errors = that level can be swapped without a cap change; any decision over 30 s = not as it is,
and the options and numbers are the user's. Narrowed in E196 (Codex debate, accepted): 125 is read **only as the
early-game latency check** — the swap also needs (a) late-round times (replay mode, E199) and (b) a measurement
inside the live container.
agentmaco, commit d1d6757, 2026-11-19 12:11:25 → 12:42:12 (30 min 47 s). Result: lab/results/125-worker-teacher-times.md.

**Health: clean.** Exit code 0, 6/6 cells ran, errors 0, 180-second timeouts 0. Three cells stopped on the
420-second wall limit, not on 80 decisions (old hard 42 decisions, new hard 25, new easy 8). `wall` equals the
worker's own `seconds` in every row checked (no transport overhead). No review section (command job).

## Decision time per cell (seconds; no charges — this is not a verdict on teacher strength)

| Factory | Level | Decisions | Stopped by | Last round | Mean | Median | p90 | Max | Over 30 s | Time-capped |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| old | easy | 80 | decisions | 2 | 0.06 | 0.05 | 0.13 | 0.26 | 0 | 0 |
| old | normal | 80 | decisions | 2 | 3.18 | 5.01 | 5.19 | 6.13 | 0 | 42 |
| old | hard | 42 | 420 s | 1 | 10.05 | 10.07 | 20.09 | 20.19 | 0 | 21 |
| **new** | **easy** | **8** | 420 s | **0** | **53.06** | 51.72 | 128.58 | **128.58** | **6** | 0 |
| new | normal | 80 | decisions | 2 | 3.76 | 5.05 | 5.56 | 10.17 | 0 | 54 |
| **new** | **hard** | 25 | 420 s | 1 | 17.59 | 20.04 | 40.07 | **40.15** | **4** | 17 |

By round (n · mean · max), from `metrics.cells[].by_round`:

| Factory | Level | Setup (round 0) | Round 1 | Round 2 |
|---|---|---|---|---|
| old | easy | 11 · 0.04 · 0.15 | 51 · 0.07 · 0.22 | 18 · 0.07 · 0.26 |
| old | normal | 11 · 3.26 · 5.20 | 47 · 3.03 · 6.13 | 22 · 3.44 · 5.19 |
| old | hard | 11 · 12.77 · 20.17 | 31 · 9.08 · 20.19 | — |
| new | easy | 8 · 53.06 · 128.58 | — (never left setup) | — |
| new | normal | 11 · 6.89 · 10.17 | 57 · 3.23 · 5.98 | 12 · 3.40 · 5.20 |
| new | hard | 11 · 27.16 · 40.15 | 14 · 10.06 · 20.22 | — |

Pre-registered reading, per level of the new factory: **normal passes** (0 over 30 s, 0 timeouts, 0 errors);
**easy fails** (6 of 8 decisions over 30 s, 13.6–128.6 s); **hard fails** (4 of 25 over 30 s, all four 40.0–40.1 s).

## Activation — where the slow decisions are (rows of the new factory, `metrics.cells[].rows`)

Every decision over 30 s is a **setup decision (round 0)**; after setup the new factory is inside the guard at
normal (max 5.98 s) and hard (max 20.22 s).

- New easy, the 8 setup decisions (wall s · completed comparisons / candidates): 52.1 · 6/6, 57.4 · 6/6, 13.6 · 2/2,
  41.4 · 5/5, 51.4 · 5/5, 128.6 · 13/13, 0.0 · 0/4, 80.0 · 7/7. Comparisons = candidates, about 7–11 s per
  comparison: the level's "comparisons 0" does not hold at setup.
- Cause in code: `teacher_patches.setup_places_budget` returns `max(budget, places [+1 at the booster pick])` for a
  player with the `mj01` part (`ships_menu1_all` and above; commits 13067d5 and 8aaecde, lab 108c/108d, user
  2026-10-25 "every starting booster is compared once") — every start place and every starting booster gets its own
  rollout whatever the level's budget is. Lab runs it under cap60; the easy level has no cap, so it runs to the end.
- New hard, setup: 7 start places at 18.0–20.1 s (cap 20 s, 1–3 comparisons done), then the 4 booster picks
  (7·6·5·4 candidates) at **40.0–40.1 s each** with 3–4 comparisons done — the booster pick's cap is doubled
  (8aaecde, HANDOFF row 108d "부스터 상한 ×2"; normal shows the same 2 × 5 s), 2 × 20 s = 40 s > the 30 s guard.
- New normal, setup: 7 start places at 5.0–5.1 s and 4 booster picks at 10.0–10.2 s (2 × 5 s), **0 comparisons
  completed in all 11** (`time_capped` 11/11): one setup rollout takes longer than the 5 s cap, so normal spends
  about 76 s on setup and still decides by the default order.
- Old factory, setup: easy 0.04 s mean, normal 3.26 s, hard 12.77 s (max 20.17 s) — no setup-all-compare part.

## Reading

- Not a strength result; ①–⑦ of HANDOFF 1 do not apply. One seed, one run, one machine (lab host, not the live
  container), one worker without `GAIA_AI_PARALLEL` — the numbers are sizes, not distributions with intervals. The
  two guard overruns are not noise, though: both follow from code (uncapped all-compare at easy; 2 × cap at the
  booster pick at hard) and would repeat on any seed.
- E194 explained: the easy test did not hang and the new teacher is not slower in general — the new factory's easy
  level spends about 53 s per setup decision (7 of 8 decisions compared every candidate), so 40 decisions cannot
  finish in 7 minutes. On the live server each of those would pass the 30 s guard and be replaced by a fallback move.
- Hard: only the 4 starting-booster picks pass the guard (40 s). Start places are at the 20 s cap. Whole setup
  in a 4-AI room: about 299 s (11 × 27.16) against 140 s with the old factory.
- Normal: inside the guard, but the setup comparisons never complete — the swap changes nothing at normal's setup
  except about 40 s more waiting (76 s against 36 s).
- Not measured: the new factory's easy level after setup (the cell never left round 0); hard beyond round 1 in
  either factory (420 s limit); rounds 3–6 at any level (E196 (a): replay mode, built in E199, run size is the
  user's number); the live container (E196 (b)).

No code or deployment change. The teacher swap stays uncommitted (E194). Lab queue empty.

## Proposal (user decision, nothing queued)

Per the pre-registration the options and the numbers are the user's:

- Easy (must change before a swap): (ㄱ) the worker's easy level keeps budget 0 at setup too (no setup-all-compare
  at easy — easy means "no comparisons"; setup then costs what it costs now, about 0.04 s) (ㄴ) an easy cap of N
  seconds (start places then take N s and booster picks 2N s; a cap shorter than one setup rollout, about 7–11 s,
  completes no comparison — normal's 5 s shows it — so a short cap is (ㄱ) plus waiting) (ㄷ) easy stays on the old
  teacher.
- Hard (must change before a swap): (ㄹ) no doubled cap at the booster pick in the worker (20 s, inside the guard)
  (ㅁ) raise the guard `GAIA_AI_TIMEOUT_SECS` above 40 s (user command at deployment; value is the user's)
  (ㅂ) hard stays on the old teacher.
- Normal: can be swapped as it is; optional (ㅅ) skip the setup-all-compare when the cap is shorter than one setup
  rollout (saves about 40 s of setup; the decisions should not change since 0 comparisons complete now — to be
  confirmed by the change's test, not shown here).
- After the choice: one bot turn for the worker change (engine untouched), then a re-run of this queue
  (lab command, about 30 min) to show 0 over 30 s in all three new cells and to time easy after setup; then the
  late-round replay run (E199) and the in-container measurement (E196).

Bot recommendation: (ㄱ) + (ㄹ) + (ㅅ), then the re-run. They need no number, keep the guard where it is, and leave
the lab's cap60 behaviour untouched (the change is in what the worker asks for, not in the factory).
