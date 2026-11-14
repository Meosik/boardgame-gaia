# Cycle 115d — `GAIA_FEDERATION_ONE_ROUTE=1` inside the teacher, the 2 crashed 114 seeds, 6R, command, no verdict

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(`ships_menu1_all_tier`, four seats the same teacher, the 114 command: `teacher_ab.py run --single`, comparisons 4,
cap60-p2). The only change is `GAIA_FEDERATION_ONE_ROUTE=1` at the head of the command `env` (HANDOFF E141: a spec
`env` reaches only the teacher workers, `teacher_ab.py:348`; the runner's `Environment`, `:397`, would stay flag-off
and the snapshots would diverge). Engine after 966e9ea (one satellite route per building set, restore stops at the
first route; 115–115c). Queued 2026-11-13 by the owner's 「진행해」 (E140 (ㄱ), E141): the first run of the flag
inside the teacher to the end of round 6. No A/B, no charge verdict (n = 2; time-budget search does not follow the
114 line, so 114 numbers are a reference only).
Pre-registered pass criteria (queue note): ① 2/2 games finish round 6, no failures (a `worker native state diverged
from runner` or `teacher returned a decision for another state` error would mean runner and worker disagree on the
flag) ② maximum decision time under 100 s (114: 80.4 s over 46 finished games) ③ worker timeouts 0. Report only:
fallback-timeout decisions, decisions of 60 s or more, `federation_limit_hits`, federations per seat, final VP.
Activation: flag-on strict replay and one-candidate-per-set count if the work tree engine is rebuilt, otherwise
"not confirmed". Warning written before the run: after 7cb307b a cap passed before the search plays the root
choice instead of crashing, so finishing alone says nothing about the flag.
Seeds = the two 114 crashes with the same seat split: `quartet-b-68171@order=0,2,3,1` (114 pair-012, here pair-000,
seats A02: Bescods, BalTaks, Itars, Gleens) and `quartet-d-75189@order=1,2,0,3` (114 pair-037, here pair-001, seats
A01: Taklons, Moweyds, Tinkeroids, Geodens). agentmaco, commit 3e3c29f, lab engine build `fc19671c4278`
(run manifest), 2026-11-13 14:24:59 → 15:22:55 (58 min). Result: lab/results/115d-fed-on-crash-seeds-full.md.

**Health: both games finished, but pre-registered ② fails.** 2/2 games complete, `failures` empty, error games 0,
worker timeouts 0, fallback-timeout decisions 0, `federation_limit_hits` 0, no divergence error (① and ③ pass).
Decision time over 580 decisions (run folder `decisions.jsonl.gz`, python one-liner): mean 11.8 · median 7.1 ·
p90 28.5 · **max 110.65 s** (≥ 100 s: 1 decision → ② fails); 60 s or more: 14 (2.4 %; 114: 5.1 %) = 13 at the cap
(60.0 s, pair-000, 1–5 comparisons finished) + the one 110.65 s decision. `chosen` recorded on 580/580 rows.

## Charges in rounds 1–3 (the verdict)

None — same teacher in all seats, 2 single games, no verdict pre-registered. Reference only (not a result):
final VP pair-000 Bescods 136 · BalTaks 101 · Itars 85 · Gleens 74, pair-001 Taklons 135 · Tinkeroids 107 ·
Geodens 73 · Moweyds 60; seat mean 96.4 (114: 100.1 over 46 games). Federations formed, counted from the recorded
`chosen` rows with type `FormFederation` (`lab/scratch_115d.py`; `federation_chances.py` cannot replay, see
Activation): pair-000 6 (Bescods 2, Gleens 2, Itars 1, BalTaks 1), pair-001 5 (Taklons 2, Tinkeroids 1, Moweyds 1,
Geodens 1) = **1.38 per seat** (114: 1.50). With n = 2 this neither shows nor excludes an effect of the shorter
federation list on play.

## Activation

- **Flag in the runner: indirect evidence, yes.** The work tree engine is still `36d2e007b6f9` (not rebuilt), which
  115c showed has the same flag-off lists as the lab build. Replaying the recorded indices on it
  (`lab/scratch_115d.py`, compares `candidates[index]` with the recorded `chosen`) follows the recorded line until
  the **first decision that has federation candidates** and leaves it exactly there in both games: pair-000 step 105
  (flag-off list 37 with 12 federation candidates; the recorded choice is at flag-off index 31, recorded index 25),
  pair-001 step 50 (list 20 with 12; flag-off index 19, recorded 13). In both the recorded index is 6 lower = the
  recorded list had 6 fewer candidates ahead of the choice, i.e. 12 federation candidates → 6. No decision before
  those had a federation candidate. So the lists the lab recorded were not flag-off lists from the first federation
  on, and runner and workers agreed (no divergence error in 580 decisions).
- **Not confirmed (pre-registered as such without a rebuild):** flag-on strict replay of the two games, and that
  every building set has exactly one candidate (12 → 6 is consistent with it, the number of sets was not counted).
- **The slow decision:** pair-001 step 111, seat 0 Taklons, 110.65 s, 0 comparisons finished, `selected`
  `local-baseline`, 4,476 unsearched comparisons, `fallback_timeout` false; the move played is the root choice
  (upgrade to the Science academy at −11,6 with standard tile 9). It is the only decision of 30 s or more with
  no finished comparison. **114 pair-037 crashed at the same step 111, same seat** (the two games play the same
  moves up to decision 86 and differ from 87 on, so the states are not identical). The neighbours are normal
  (steps 108–110 and 112–113: 4.3–9.0 s). 7cb307b flags a decision as fallback only when the cap passes before
  anything is published (`budget_teacher.py:112–120`, `parallel_search.py:246–256`); the flag is false here, so
  either the root ranking was published inside the cap and the time went elsewhere (one uninterruptible call in the
  first comparison, or worker time outside `_choose`), or the count misses a path. Which stage took the time is not
  recorded — the decision log has only the total.

## Reading (HANDOFF 1 order)

- ① noise: E134 could not reproduce 114 pair-037 step 111 alone (3.8 s). The delay was observed again at the same
  seed, step number and seat (110.65 s), but the two games differ from decision 87 on, so the states are not the
  same, and the slow stage was measured in neither run. Observation only: **a delay re-observed at the same seed and
  seat, cause not established** — chance (for example machine load) is not excluded with n = 2 runs, and the round
  and state of the 115d decision were not recorded (debate 1/1).
- ② activation: the flag was on in runner and workers (indirect, above). It did not remove this slow decision, and
  pair-000 (the 17,318-candidate seed) never came near the cap before the search (max 60.03 s) — but that game
  follows another line than 114, so, as pre-registered, this is not evidence that the flag fixed pair-012.
- ③ scope/implementation: hypotheses, not findings (debate 1/1). (a) Whether the delay lies outside federation
  enumeration is unknown: it happened with the flag on, but the stage is unmeasured, so a federation-related stage
  is not excluded. (b) Whether 7cb307b is what kept this game alive is unknown: its path sets
  `expired_before_search` (`budget_teacher.py:112–120`, `parallel_search.py:246–256`) and the row has
  `fallback_timeout` false, so that path did not run in this decision — it may have ended through the normal path
  (a time-capped search with no finished comparison, or time outside `_choose`). Observed only: 0 fallbacks
  reported next to a 110 s decision with 0 finished comparisons.
- ④ interaction: none measured. ⑤–⑦ do not apply (no claim under test).
- Health and timing: apart from the one decision the run is inside cap60 (max 60.03 s, 2.4 % at the cap, 114
  5.1 %). The two games are flag-on data and stay out of the 114 (flag-off) BC set (E140 (ㄷ)).

Result against the pre-registration: **① pass, ② fail (110.65 s ≥ 100 s), ③ pass.** No code or deployment change;
the flag stays off by default and no spec turns it on. Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Find the stage behind step 111: record per-stage seconds in the decision log (worker time before the search,
  root ranking / prefetch, comparisons, `time_capped`, `expired_before_search`; small change in
  `budget_teacher.py` · `teacher_ab.py`, bot turn) and re-run only `quartet-d-75189@order=1,2,0,3` with the flag,
  stopped at the start of round 4 (step 111 was round 3 in 114; lab ≈ 30 min). Also record the round and a state
  digest of every decision over the cap. Pre-registered reading: if a decision of 100 s or more (or 30 s or more
  with 0 comparisons) appears, the per-stage seconds name the stage; if none appears (time-budget search may take
  another line), the cause stays not established and the run only shows that the timing fields work.
- (ㄴ) Accept the single 110 s decision (the game finishes, 1/580) and go on with flag-on collection — leaves a
  0-comparison root move that is not counted as a fallback in BC data (same question as E134 (나), 38 rows).
- (ㄷ) Work tree engine rebuild (owner command `cd ~/projects/gaia-work/gaia-rl && .venv/bin/maturin develop --release`)
  → flag-on strict replay of these two games + 114 export and `tools/bc_train.py` (E128 (ㄴ)). Independent of (ㄱ).
- (ㄹ) Still open: flags must match between collection and play when flag-on games feed BC/PPO (E140 (ㄷ)).
Bot recommendation: (ㄱ), with (ㄷ) whenever the owner runs the command; not (ㄴ) before the stage is known.
