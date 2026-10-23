# Cycle 104b — ships vs ships_menu — comparison dedup re-smoke (588c076, outermost-layer dedup), stop at round 3 start

A = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap60-p2.json` (ships stack + `install_task_dedup`).
B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu-cap60-p2.json`: A + plan_menu. Part under test is
the dedup fix 588c076 (each dedup wrapper acts only while it is the module's outermost function; 104a cause = two layers, E92),
not A vs B. Queued 2026-10-23 by the user ("그렇게 해", E91 (ㄱ)).
Pre-registered verdict: decisions in `decisions.jsonl.gz` whose `compared` list holds the same (goal, spec, first) twice —
**0 in both arms and both branches (R1 BGG, R2) = pass**. Read alongside: errors/timeouts, max decision time, completed
comparisons per decision by branch, duplicates by name.
Base quartet, 2 seeds (103 pair-003 and pair-016), seat-swapped pairs, comparisons 4, cap60-p2 both arms, stop at round 3 start
(`stop_round` 2), agentmaco, commit 0e35043, 20:55 → 21:39 (44 min). Result: lab/results/104b-dedup-smoke.md.

**Health: clean.** 4/4 games, errors 0, timeouts 0, fallback-timeout decisions 0/0. Decision time A/B mean 18.3 / 19.0 s,
median 17.4 / 16.6, p90 40.2 / 46.9, max 60.3 / 60.7 s. Decisions A 226, B 209.

## Charges in rounds 1–3 (the verdict)

Not applicable — the smoke stops at round 3 start (charge table empty by design). The verdict is the duplicate count:

| Arm | branch | decisions with `compared` | exact duplicate (goal, spec, first) | duplicate by name | completed comparisons / decision |
|---|---|---:|---:|---:|---:|
| A | R1 BGG | 95 | **0** | 0 | 3.95 |
| A | R2 | 57 | **0** | 0 | 3.91 |
| B | R1 BGG | 89 | **0** | 0 | 3.94 |
| B | R2 | 43 | **0** | 0 | 4.00 |

(count: short python over `pair-*/game-*/decisions.jsonl.gz`, `compared` rows; branch = first `compared` goal starts with
`BGG-R1-`.) **Verdict: pass** (104a B 19/88 → 0/132).

## Activation

- The menu fired: B has a non-empty `menu` on 113 of its 132 decisions with `compared`, and in all 113 at least one menu goal
  reached `compared` (A 0 — no menu). So the case that failed in 104a (menu slot copy of a goal already in goals) was exercised
  and filtered, not avoided.
- Both branches exercised this time (R2 decisions A 57, B 43), which 104a's round-2-start stop could not test.
- Completed comparisons per decision ≈ 3.9–4.0 in both arms: removing the copies did not leave empty slots (the next distinct
  plan fills in).

## Reading (HANDOFF 1 order)

- ① noise: not applicable — a deterministic property, 0 vs pre-registered 0 on 284 decisions.
- ② activation / ③ implementation: the fix works on the path that failed (B menu, R1 BGG) and on the R2 path.
  588c076's unit test (`test_teacher_patches.py`) has still not been run by a bot turn (E92); this smoke is the runtime evidence.
- ⑤ window: two seeds, rounds 1–2 only; rounds 3+ paths (late plan lists) not exercised. Duplicates are a code property, not
  a game-state one, so this is enough to unblock the A/B; the next run's logs can re-check it for free.
- Note: the dedup is in the ships factory, so the A arm and the deployed teacher line change too (as said in E90); no deployment
  in this record.
- Review section: none on the result page (no `## 검수`).

No code or deployment change in this record. Lab queue: empty after this; 097·100 held `_`.

## Proposal (user decision, nothing queued)

- (ㄱ) E89 (ㄷ) B' (menu front 1 slot) vs A on the dedup code, the 103 24 seeds 4R cap60-p2 (≈ 8.5 hours), budget criteria as
  E89 (ㄷ), plus the duplicate count 0 as a health check. Needs a code bot turn first to build B' (menu 1 slot spec).
- (ㄴ) Optional: re-run 103's design (B = full menu) on dedup code to see whether the 103 loss shrinks (≈ 8.5 hours).
Bot recommendation: (ㄱ) — B' code turn, then queue.
