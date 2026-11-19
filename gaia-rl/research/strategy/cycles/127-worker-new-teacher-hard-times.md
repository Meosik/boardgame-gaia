# Cycle 127 — live AI worker decision times: new factory at the deployed hard level (4 comparisons, 20 s cap, no parallel) — command, no games, not a teacher verdict

Not a teacher A/B: no A and B specs, no charges. One timing cell of `tools/worker_times.py` (play mode: it starts
`tools/ai_worker.py` as a child process and times every request). Queued 2026-11-19 by E207 (user: 「난이도 관련 코드
하나도 건들지마. 최상의 어려움 교사도 지금 나보다 못하는데. 실시간으로 나랑 겨루는 교사 셋 만들어와」): the per-factory
level table was removed (f9f9deb), so the worker's `LEVELS` are the deployed values whatever the factory, and the only
switch left is `GAIA_AI_TEACHER`. This cell times that switch: new factory
`guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier` × `hard` (4 comparisons, one income ahead, 20 s cap = the live
server's values), `GAIA_AI_PARALLEL=0` (compose default), `Environment('quartet-e-88365')` from the first setup
decision, played with the worker's own choices, 80 decisions, wall limit 2400 s, a decision over 180 s ends the cell as
a timeout. One seed, one run; same seed as 125 / 126 / 126b (same design re-measured). It replaces the new-factory hard
cell of 125 (25 decisions, 4 over the guard), whose over-guard decisions were the worker defect fixed in 9170cd7 (E204).
Pre-registered reading: 0 decisions over 30 s (server guard `GAIA_AI_TIMEOUT_SECS`, default 30), 0 errors, 0 timeouts
over 180 s and ② all four starting-booster decisions `booster-tier-N`, under 1 s, 0 comparisons → 「for the first 80
decisions the switch needs no difficulty-code or guard change, one line `GAIA_AI_TEACHER`」; any decision over 30 s is
reported separately and the switch proposal waits. The distribution of completed comparisons is reference only.
Host agentmaco (lab machine), lab commit bb39ab4, 2026-11-19 17:41:15 → 17:58:56 (17 min 41 s; cell wall 1060.5 s).
Result: lab/results/127-worker-new-teacher-hard-times.md.

**Health: clean.** Exit code 0, 80 / 80 decisions, stopped by `decisions`, reached round 2, 0 errors, 0 timeouts over
180 s. No second-model review section (command job). Decision wall time: mean 13.25 · median 20.04 · p90 20.35 ·
max 20.53 s.

## Charges in rounds 1–3 (the verdict)

None — no games, no arms. The pre-registered reading is the timing below.

## Timing (rows of `results/127-worker-new-teacher-hard-times.json`, `metrics.cells[0].rows`)

| | n | mean s | max s | sum |
|---|---:|---:|---:|---:|
| Setup (round 0) | 11 | 12.57 | 20.10 | 138.3 s |
| Round 1 | 56 | 12.98 | 20.53 | 726.6 s (12.1 min, four seats) |
| Round 2 (first 13) | 13 | 15.03 | 20.39 | 195.4 s |
| **All** | 80 | 13.25 | 20.53 | 1060.5 s |

- ④ Over the 30 s guard: **0 / 80**. Over 20.5 s: 1 (decision 42, round 1, 20.53 s). Over 21 s: 0. Cut by the cap
  (`time_capped`): 51 / 80, all between 20.01 and 20.53 s — the cap overshoot is at most 0.53 s, 9.5 s under the guard.
- ② Starting boosters: decisions 8–11 (candidates 7 · 6 · 5 · 4) are `booster-tier-2 · 12 · 13 · 10`, 0.002–0.003 s,
  0 comparisons, sum 0.009 s. **Confirmed 4 / 4** (125 before the fix: 40.0–40.1 s each, the four over-guard decisions).
- Setup: the seven starting-place decisions take 138.3 s (six cut at 20 s with 1–3 comparisons done out of 4–13
  candidates, one finished 2 / 2 in 17.9 s). 125 new-factory hard cell: about 299 s; E208 bot-turn preview: about 141 s.
- ⑤ Completed comparisons (reference): 53 decisions searched — 51 cut by the cap with 1 / 2 / 3 comparisons done in
  10 / 29 / 12 decisions, 2 finished under the cap (2 of 2 candidates in setup; 4 of 4 in 13.6 s in round 2). Mean 2.08
  of 4 per searched decision. Searched but cut with 0 comparisons: **0**. The other 27 decisions did not search:
  4 booster-tier picks and 23 `local-baseline` decisions (2 candidates, ≤ 0.03 s; 20 in round 1, 3 in round 2).
- After setup (69 decisions): 46 searched (45 cut at 20 s: 1 / 2 / 3 done in 8 / 26 / 11; one finished 4 / 4), 23 instant.
  126b at the lab budget (60 s cap, parallel 2) finished all four comparisons in 45 of 69 — at the deployed hard level
  the new teacher searches about half as deep per decision.
- `selected` of the 51 capped decisions: 15 are `current-choice` (all with 1–3 comparisons done).

## Activation

The part under test is the worker path itself: the booster-tier wrapper survives the per-request budget install
(4 / 4, above), and the worker reports its searches as capped at 20 s as `LEVELS['hard']` says. Nothing else to count.

## Reading (HANDOFF 1 order does not apply — timing, not a part)

- **Pre-registered reading met:** 0 over 30 s, 0 errors, 0 timeouts, ② 4 / 4 → for the first 80 decisions (setup to
  early round 2) the new teacher can replace the old one with the one line `GAIA_AI_TEACHER`, no difficulty-code and no
  guard change. The margin is the cap: every searched decision ends within 0.53 s of 20 s.
- What a player waits: setup about 2.3 min for four seats, round 1 about 12 min of AI thinking over four seats (56
  decisions, 13 s mean; three AI seats in a 「AI 3명」 room take their share of that). 125's old factory at the same level:
  mean 10.05 s, max 20.19 s over 42 decisions — the same ceiling, the new teacher sits at it more often.
- Reference, not a verdict: the 20 s cap leaves room for about 2 of 4 comparisons, so this is a weaker searcher than
  the lab's cap60-p2 teacher that produced the A/B results; whether that costs play strength was not measured here
  (user E207: no difficulty-code changes).
- Not controlled: other load on the lab machine during the run (the Codex round of the 126b review turn may have
  overlapped; not checked). The maximum is bound by the cap, so the reading does not depend on it.
- Limits: one seed, one run, 80 decisions (setup to round 2), lab machine, one worker. Rounds 3–6 were not timed
  (replay mode, E199 / E201); lab cap-20 specs have shown single decisions near 35 s in full games, so the 30 s guard is
  not established for the late game — there the server plays its fallback move. Inside the live container: not measured
  (E196 (b)).

- Scope of the switch (Codex debate 1/1, both findings accepted): `GAIA_AI_TEACHER` picks the factory for the whole
  worker (`tools/ai_worker.py:77`); the level arrives per request (`:139`). 127 timed `hard` only. With the same line an
  easy room also runs the new factory, and 125 measured that cell: 6 of 8 setup decisions over 30 s, max 128.6 s
  (starting places compared in full, `teacher_patches.setup_places_budget`, no cap at easy). That reading was not the
  booster defect (126 correction) and 9170cd7 does not change it. Normal passed in 125 (max 10.17 s, 0 over the guard).
  So this cycle supports 「hard, first 80 decisions」 and nothing wider: not the late game, not the container, not easy.

- **Correction (same day, user question 「왜 옛 교사로?」): the guard for `hard` is not 30 s.** `gaia-server/src/ai.rs:150`
  `guard_timeout` gives the hard level at least 60 s (68d242e, 2026-10-04, after cycle 025's 33 s maximum); 30 s is the
  guard of easy and normal. The queue note, the limits bullet above and the debate both used 30 s for hard. Against the
  real guard: 0 / 80 over 60 s here, and the lab's cap-20 maximum (about 35 s) is inside it, so the late-game worry for a
  hard room is much smaller than written. Unchanged: rounds 3–6 and the container were not timed with this factory, and
  easy rooms (30 s guard) pass it in setup.

No code or deployment change. Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

Corrected after the debate: the first version recommended switching now; that went past what was measured.

- (ㄱ) Keep the E196 order: deploy with the old teacher (the E208 commands without the `GAIA_AI_TEACHER` line) → (ㄴ) and
  (ㄷ) → switch by adding the line and `up -d` (no rebuild). The fixed-map 「AI 3명」 room works from the first step.
- (ㄴ) Late-game timing by replay (`worker_times.py --replay`, E199 / E201): rounds 3–6 of recorded 123 games at the hard
  level, to see whether any decision passes 30 s. Scale is the user's number; bot suggestion 2 games × default sampling
  (every 8th decision + the 5 slowest per round) ≈ 100 positions, lab ≈ 35–40 min.
- (ㄷ) In-container timing after the deploy (E196 (b)) — user commands.
- (ㄹ) Easy path before the switch (user; E207 froze the difficulty code): accept that easy rooms pass the guard in
  setup and get the server's fallback move, or hold the switch, or reopen the easy setup budget.
- The one-step switch of E208 (user 「빨리」) stays the user's choice, with those three unmeasured risks.
Bot recommendation: (ㄱ) → (ㄴ) once the user gives the scale → (ㄷ) → (ㄹ) → switch.
