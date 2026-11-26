# Cycle 140b — prune factory check — the new teacher never picks a blocked candidate, 1R

No A/B. Command job (`lab/scratch_e362_prune_probe.py check`): the new factory
`guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier_prune` plays round 1 of geo-quartet-24 itself (easy budget,
`budget_teacher 0`) and counts decisions whose candidate list had blocked entries and decisions where a blocked
candidate was chosen. Queued 2026-11-26 from the debate 1/1 finding ② accepted in HANDOFF E362/E363 (140a only ran
`prune_indices` on saved snapshots, not through the factory).
Pre-registered: no verdict. Health criteria: exit code 0, FACTORY line printed, chose_blocked 0, with_blocked ≥ 1.
Next step if met: queue 140 (seed `e362-20388@factions=Firaks,Itars,BalTaks,Xenos`, 4-seat prune spec, 6R, 1 game).
Xenos/Taklons/Terrans/Geodens, 1 map, round 1 only, agentmaco, commit 4b85bf3,
2026-11-26 19:55 → 20:02 (7 min). Result: lab/results/140b-prune-factory-check.md.

**Health: clean.** Exit code 0, FACTORY line printed, no exception.

## Result (no verdict)

| Count (round 1, scratch_e362_prune_probe.py) | Value |
|---|---:|
| Decisions | 51 |
| Decisions with ≥ 1 blocked candidate | 9 (18%) |
| Decisions that chose a blocked candidate | **0** |

All four criteria met.

## Activation

The filter fired inside the factory on 9 of 51 round-1 decisions, and the search never returned a blocked move.
The job prints totals only: which rule blocked (tile track, P1, P2, P4, P5, F1/F2/F5) and how many candidates per
decision are not broken down here. 140a already showed federation rules 0 hits in 3R snapshots, so F1/F2/F5 are
still unverified. The 140 decision log's `prune_blocked` holds only a count (`tools/teacher_ab.py:452–456`), so the
per-kind count and the chosen-vs-blocked check need a replay of the recorded choices that recomputes `_prune_tile`,
`_prune_mine`, `_prune_feds` (F1/F2/F5 split) and `prune_indices` per decision (debate 1/1).

## Reading (HANDOFF 1 order)

- ② activation: confirmed for round 1 — the factory wiring works and blocked candidates are not chosen
  (root and rollout blocking as specified in E362).
- ③ scope: one map, one round, the fixed quartet, not the 140 lineup (Firaks/Itars/BalTaks/Xenos). Rounds 2–6
  and the federation rules are not exercised. This is a wiring check, not a strength or speed measurement.
- ⑤ window: no charges or VP measured, none intended.
- E364 principle (keep must-take faction tiles, gaia give-up by plan) is still unimplemented; 140 runs the current
  filter, as agreed in E364 (ㄴ).
- No result-page review section (command job).

No code or deployment change. Lab queue empty after this job.

## Proposal (user decision, nothing queued)

- (ㄱ) Queue 140 now, the one-game exception already agreed in E362/E363: seed `e362-20388@factions=Firaks,Itars,BalTaks,Xenos`,
  4 seats on the prune spec `tools/teacher-a-…-all-tier-prune-cap60-p2.json`, 6R, 1 game, ≈1–2 lab hours. Health:
  game ends, 0 errors/timeouts, chose_blocked 0 over all rounds.
- (ㄴ) At 140 review: replay the recorded choices, recompute the blocked set per decision by kind (F1/F2/F5 split),
  check the chosen index against it, count by round (Sonnet replay script + bot turn).
Bot recommendation: (ㄱ) → (ㄴ); other new experiments stay on hold (theory phase).
