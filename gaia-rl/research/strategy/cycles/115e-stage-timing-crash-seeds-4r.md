# Cycle 115e — stage timing in the decision log, the 2 crashed 114 seeds, to the start of round 4, command, no verdict

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(`ships_menu1_all_tier`, four seats the same teacher, `teacher_ab.py run --single`, comparisons 4, cap60-p2,
`GAIA_FEDERATION_ONE_ROUTE=1` at the head of the command `env`) = the 115d command plus `--stop-round 3`. The part
under test is the instrumentation 632b63f (HANDOFF E143): every decision-log row carries `round`, `digest` and
`timing{choose, search, cap, published_at, stages{…}, time_capped, budget_stopped, expired_before_search,
audit_fresh}`; it records time only and does not change a decision. Queued 2026-11-14 by the standing order
(E142 (ㄱ), Codex clean) to find the slow stage of the 115d decision (pair-001 step 111, Taklons, 110.65 s, 0 completed
comparisons, no fallback flag — the step and seat where 114 pair-037 crashed).
No A/B, no charge verdict (n = 2, same teacher). Pre-registered reading (queue note): ① instrumentation — 2/2 games
reach the start of round 4 with no failures, every row has `round`·`digest`·`timing`, rows with `audit_fresh` true
have `stages` (otherwise fix the instrumentation) ② a slow decision = 100 s or more, or 30 s or more with 0 completed
comparisons; if one appears, name its longest stage = the next fix target (that decision's stage only, not the cause
of 114 pair-037) ③ if none appears the cause stays open — a failed reproduction is not read as a fix. Report only:
maximum decision time, decisions of 60 s or more and their stages, fallbacks, how long the d seed follows the 115d line.
Seeds `quartet-b-68171@order=0,2,3,1` (pair-000, A02: 매드 안드로이드·발타크·아이타·글린) and
`quartet-d-75189@order=1,2,0,3` (pair-001, A01: 타클론·모웨이드·팅커로이드·기오덴), agentmaco, commit 1bd83d5, lab engine
build fc19671c4278 (run manifest), 2026-11-14 16:56:09 → 17:29:24 (33 min), exit code 0. Result:
lab/results/115e-stage-timing-crash-seeds-4r.md (no review section: command job).

**Health: clean.** 2/2 games reached the start of round 4, failures 0, error games 0, timeout games 0, fallback-timeout
decisions 0, `federation_limit_hits` 0, `expired_before_search` 0. Decisions 279 (pair-000 134, pair-001 145; counts
from the run folder's `decisions.jsonl.gz`, `lab/scratch_115e.py`): pair-000 mean 14.1 · median 13.4 · p90 30.4 ·
max 60.02 s, pair-001 mean 13.7 · median 11.5 · p90 29.3 · max 48.22 s.

## Charges in rounds 1–3 (the verdict)

No verdict: one teacher on all four seats, 2 games, the result table has 0 pairs. VP at the start of round 4 (not a
verdict): pair-000 매드 안드로이드 23 · 발타크 4 · 아이타 21 · 글린 5, pair-001 타클론 16 · 모웨이드 12 · 팅커로이드 22 ·
기오덴 17.

## Pre-registered reading

| | Criterion | Observed (`lab/scratch_115e.py`) | |
|---|---|---|---|
| ① | 2/2 games to round 4, no failures; every row has `round`·`digest`·`timing`; `audit_fresh` rows have `stages` | 2/2, failures 0; rows missing a field 0/279; `audit_fresh` true 279/279; `stages` is `null` in 8 rows (4 per game) | pass except the 8 rows |
| ② | a decision of 100 s or more, or 30 s or more with 0 completed comparisons | 0 in both games | none appeared |
| ③ | if none appears, the cause stays open | applies | **cause still open** |

The 8 rows without `stages` are the four starting-booster decisions of each game (`selected` `booster-tier-N`, round 0,
0.001–0.002 s, `search` 0.0): the booster-tier immediate return goes through `budget_teacher` (so `audit_fresh` is
true) but returns before any stage is recorded, and `decision_timing` (`tools/teacher_ab.py:358`) copies the missing
`stages` as `null`. No time is lost there, but the letter of ① ("otherwise fix the instrumentation") asks for a
uniform shape — a one-line fix (`stages` → `{}`), proposed below.

## Report only

- **Maximum decision time** 60.02 s (pair-000 step 19, 글린, round 1, 2 completed comparisons, `time_capped`);
  pair-001 maximum 48.22 s (step 4, 팅커로이드, setup, 10 completed, `budget_stopped`).
- **Decisions of 60 s or more: 2 of 279** (0.7%; 115d 2.4%, 114 5.1% — those are 6R games), both pair-000 글린
  (steps 2 and 19, 60.02 s, completed 5 and 2). Longest stage in both = the frozen search itself
  (`parallel_search − prefetch − drop_unfinished` 59.7–59.9 s); first result published at 0.07–0.18 s.
- **Where the time goes over all 279 rows**: `seconds − choose` (runner·IPC) at most 0.003 s, `choose − search`
  (choose wrapper) 0.00 s, `bind_check`·`state_check` 0.001 s, `root_rank` at most 0.38 s (pair-000) / 1.08 s
  (pair-001). The only stage before the search that is not negligible is **`planned_tasks`**: pair-000 at most 0.69 s
  of prefetch, pair-001 six decisions of 2 s or more — step 21 타클론 2.2 s, 31 기오덴 3.1 s, 87 팅커로이드 2.6 s,
  **90 타클론 8.8 s** (round 2, 1,485 unsearched comparisons, first publish at 8.97 s, decision 36.3 s), 100 모웨이드
  3.8 s, 124 타클론 5.1 s; all six have 816–1,485 unsearched comparisons.
- **Fallbacks** 0 (fallback-timeout 0, `expired_before_search` 0).
- **Same line as 115d**: the d seed for the first 69 decisions (the 115d slow decision was step 111), the b seed for
  the first 92. Step 111 of this pair-001 is a different state: 기오덴 seat 3, 5.47 s, 4 completed comparisons.

## Reading (HANDOFF 1 order)

- **The slow decision did not come back (pre-registered ③).** The d seed left the 115d line at decision 70, so the
  state of the 110.65 s decision was never reached; no decision in either game passed 60.02 s and none had 0 completed
  comparisons at 30 s or more. The cause of the 115d decision and of 114 pair-037 stays open; this run is not
  evidence that the delay is gone (279 decisions to round 4, against 1/580 in 115d over six rounds).
- **The instrumentation works** (② activation): 279/279 rows carry the fields, `seconds`, `choose` and `search`
  agree to within 0.005 s, and the 60 s rows show the expected picture (cap reached inside the search, results published throughout).
  Whenever a slow decision appears in a later run, its row will name the stage without another experiment.
- **A lead, not a cause**: `planned_tasks` is the one pre-search stage that grows with the size of the decision
  (2.2–8.8 s at 816–1,485 unsearched comparisons, 타클론 three of six). The 115d decision had 4,476 unsearched
  comparisons, so a long `planned_tasks` there is possible — but the root ranking is published only after prefetch
  (first publish 8.971 s = prefetch 8.97 s at step 90), and 115d's `fallback_timeout` was false, which says something
  was published inside the 60 s cap. The two do not fit together without the missing measurement; untested.
- Health and timing: clean, 33 minutes (estimate 35–45).

No code or deployment change. The flag stays off by default, no spec turns it on. These two flag-on games are not
mixed with the 114 (flag-off) BC data. Lab queue empty. Per E144 the 115 side track (115–115e) ends here: the crash
became a finished game after 7cb307b, what remains is a rare slow decision, and the timing fields now stay in every
decision log.

## Proposal (user decision, nothing queued)

- (ㄱ) Close the side track as E144 decided; the main line (E128 ②) waits for the owner's command
  `cd ~/projects/gaia-work/gaia-rl && .venv/bin/pip install "ray[rllib]==2.58.0" "torch==2.14.0"` (the work tree venv
  still has neither, checked this turn), then the bot turn of E144 (bc_train tool test → 114 export and training →
  policy teacher factory → BC vs teacher A/B).
- (ㄴ) The pre-registered instrumentation fix: `decision_timing` writes `stages` as `{}` when the audit has none
  (booster-tier immediate return), plus a test line in `test_teacher_ab` — one bot turn, a Sonnet edit, no lab time.
- (ㄷ) Not proposed: another reproduction run. Time-budget search leaves the old line (69 of 111 decisions here), so
  a rerun reaches the same state only by luck; the timing fields will catch the next slow decision in the main-line
  runs for free.
Bot recommendation: (ㄱ) and (ㄴ); (ㄴ) is the only step the bot can take now.
