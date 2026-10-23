# Cycle 104a — ships vs ships_menu — comparison dedup smoke (install_task_dedup), stop at round 2 start

A = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap60-p2.json` (ships stack + `teacher_patches.install_task_dedup`).
B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu-cap60-p2.json`: A + plan_menu (103's B). Part under test
is not A vs B but the dedup itself (E90 (ㄱ), known-bad #10; 7057aa5 reverted because it changed FROZEN files, moved to
`install_task_dedup` in ce8c03f, `compared.spec` log key in 5a99400). Queued 2026-10-23 by the user ("그렇게 해", E90 (ㄱ)).
Pre-registered verdict: decisions in `decisions.jsonl.gz` whose `compared` list holds the same (goal, spec, first) twice —
**0 in both arms = pass** (103 by name: A 15 %, B 31 %). Read alongside: completed comparisons per decision, errors/timeouts,
max decision time, pair-003 Xenos B R1 academy.
Base quartet, 2 seeds (103 pair-003 and pair-016, the two worst pairs), seat-swapped pairs, comparisons 4, cap60-p2 both arms,
stop at round 2 start, agentmaco, commit b750b52, 12:49 → 13:19 (30 min). Result: lab/results/104a-dedup-smoke.md.

**Health: clean.** 4/4 games, errors 0, timeouts 0, fallback-timeout decisions 0/0. Decision time A/B mean 18.9 / 20.2 s,
median 18.0 / 17.6, p90 46.5 / 50.2, max 60.2 / 60.2 s. Decisions A 157, B 147.

## Charges in rounds 1–3 (the verdict)

Not applicable — the smoke stops at round 2 start (charge table empty by design). The verdict is the duplicate count:

| Arm | decisions with `compared` | exact duplicate (goal, spec, first) | duplicate by name | completed comparisons / decision |
|---|---:|---:|---:|---:|
| A | 98 | **0** | 0 | 3.888 |
| B | 88 | **19 (21.6 %)** | 19 | 3.864 |

(count: short python over `pair-*/game-*/decisions.jsonl.gz`, `compared` rows.) **Verdict: fail** (B ≠ 0).
Posted watch replay: none (smoke). VP at round 1 end (not used): A 7.4, B 9.2.

## Activation (round 1, A → B)

- Every one of the 186 decisions with a `compared` list is a round-1 decision whose first entry is a `BGG-R1-*` opening
  (A 98/98, B 88/88) — the stop at round 2 start means only the BGG-opening branch of search was exercised.
- All 19 B duplicates are in that branch and are `track-plan-*` goals (family `ordered`: Economy-2 ×6, Science-2, Science-4 …),
  shape `[BGG-R1-…, current-choice, track-plan-X, track-plan-X]`, the same track plan sitting in menu slot 2
  (`menu` = `[…, track-plan-X, …]`). This is the E90 case (menu slot 2 copy of a goal already in goals) surviving the dedup.
- Completed comparisons per decision 3.89 / 3.86 are round-1 only, not comparable to 103's 2.825 / 2.782 (all rounds).
- pair-003 Xenos B round-1 academy: not counted — `upgrade_counts.py --rounds 1-1` and `plan_labels.py --prefix BGG-R1-`
  printed no rows on these stop-at-R2 games (tool output empty; not investigated).

## Reading (HANDOFF 1 order)

- ① noise: no — a deterministic code property, 19 hits vs pre-registered 0.
- ② activation / ③ implementation: the dedup is installed (A 0, B down from 103's 31 % by name to 21.6 % in R1) but misses the
  BGG round-1 path in B. Lead (not verified this turn): in round 1 search builds its list from `bgg_openings.planning.goals`,
  which the three wrapped names (`goals_for`, `scoring_pairs`, roots `interleave_families`) do not cover, so the menu slot
  copy and the track_plans goal both reach the comparison order. A local unpushed WIP commit on the work tree
  (`wip: task dedup order (temporary)`, teacher_patches + tests) already wraps `bgg_openings.planning.goals` and rebuilds
  one round-robin order over all lists — it was not part of this run and is not reviewed or pushed.
- **Correction (2026-10-23, next bot turn): the BGG lead above is wrong.** Cause = two dedup layers: the ships factory
  installs `install_task_dedup`, plan_menu wraps it and installs it again; in the roots interleave call the inner layer
  consumes and clears the shared `_task_seen`, plan_menu then prepends slot 2, and the outer layer has nothing left to
  filter with. Not BGG-specific (R2+ would show it too); the WIP has the same flaw (inner layer pops `_task_build`).
  Fix 588c076 (each wrapper acts only while it is the module's outermost function); re-smoke 104b to round 3 start.
- ⑤ window / design gap: stopping at round 2 start tests only the BGG branch; the non-BGG path (rounds 2+, where 103's
  duplicates mostly were) was not exercised at all. The re-smoke should run to round 3 start.
- Health and timing clean; max 60.2 s both arms.
- Review section: none on the result page (no `## 검수`).

No code or deployment change in this record. Lab queue: empty after this; 097·100 held `_`.

## Proposal (user decision, nothing queued)

- (ㄱ) Code bot turn: finish the dedup for the BGG round-1 path (review/finish the WIP commit, add a test with a BGG opening
  list + menu slot 2 = a track plan already in goals), then re-smoke 104b with the same two seeds **to round 3 start**
  (both branches), pass = exact duplicates 0 in both arms (≈ 1 hour lab).
- (ㄴ) After (ㄱ) passes: E89 (ㄷ) B' (menu 1 slot) vs A on dedup code, 24 seeds 4R (≈ 8.5 hours).
Bot recommendation: (ㄱ) → (ㄴ).
