# Cycle 114 — 6R self-play collection on the current engine (all_tier, 18 factions, 48 seeds × 1 game), command, no verdict

No A/B: one `command` job, `teacher_ab.py run --single` (8d20dc3, one game per seed) with the same teacher in all
four seats — `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(`ships_menu1_all_tier`, cap60-p2, 4 comparisons). Purpose: behaviour-cloning / PPO initial-value data on the
current engine with the chosen candidate recorded per row (E128 ①, E131 (ㄴ), E132). Queued 2026-11-12 by the owner
「ㄱ 대로 해」 (052af15; the first 24-seed × seat-swap design was held because A = B replays the same start twice).
Pre-registered verdict: none. Pre-registered checks: ① 48/48 games complete (failures, fallback timeouts) ② every
decision row has `chosen` ③ `bc_dataset.py index` → `stats` for this run: strict replay passes, 6R games, decisions,
engine build id ④ reference only: seat mean final VP, federations per seat (`federation_chances.py`), unflipped
federation tokens (`endgame_tech_counts.py`).
18 factions, 48 new seeds with `@order` (current `faction_strength.py` order): quartets geo 2 · a 10 · b 10 · c 9 ·
d 9 · e 8, one game each (no seat swap, no pairs), six rounds, agentmaco, commit 630c068,
2026-11-12 15:31 → 11-13 07:14 (15 h 43 min; estimate was 1–1.5 days). Result: lab/results/114-all-tier-selfplay-18f-full.md.
No replay posted. No second-model review section (command job).

**Health: 46/48 games complete, 2 error games, otherwise clean.** Exit code 0. Timeouts 0, fallback-timeout
decisions 0, federation candidate limit hits 0. Decision time over all 14,176 logged rows (decision logs, python
count): mean 15.2 s · median 8.2 · p90 43.0 · p99 60.1 · max 80.4; over 60 s 725 rows (5.1 %), over 80 s 1, over 100 s
0 — inside the cap60 norm (~80 s). The 100 s+ decisions of 102 (148 rows, max 757 s) did not appear in this run.
Unsearched comparisons in 10,755 rows (expected with 4 comparisons). The A/B columns of the result page are only
`a_seats` labels of the same teacher and mean nothing here.

The two error games (same traceback in both `workers.log`):

| Game | Seed | Factions | Stopped at step |
|---|---|---|---:|
| pair-012/game-0-A02 | quartet-b-68171@order=0,2,3,1 | Bescods, BalTaks, Itars, Gleens | 224 |
| pair-037/game-0-A01 | quartet-d-75189@order=1,2,0,3 | Taklons, Moweyds, Tinkeroids, Geodens | 111 |

`SearchExpired: No more search time` raised by the entry check of the frozen search
(`baseline-teacher-20260917/four_factions/preparation.py:574`, `check_time(hard_deadline)` before the root ranking)
→ nothing was published yet, so `budget_teacher._choose` re-raises (`budget_teacher.py:87–89`) → worker exit code 1.
The cap clock starts at the top of `_choose` (`:56`, `:78`), so the 60 s were spent before the frozen search
started: wall time minus logged search time is 85.6 s (pair-012) and 61.7 s (pair-037) against ≈4 s in complete
games. Which pre-search stage was slow is **not identified** (candidates: `parallel_search._prefetch` at
`parallel_search.py:243`, `forget_unaffordable_plan` at `teacher_patches.py:4598`, the `choose` wrapper at `:5418`);
the failing decision itself is not in the log. Rate: 2 of 14,178 decisions, but each one loses a whole game.

## Charges in rounds 1–3 (the verdict)

None — no A/B, no pairs. Nothing is judged by this run.

Final VP (reference, `result.json` scores of the 46 complete games, 184 seat-games): seat mean **100.1**
(min 49, max 171), winner mean 124.1. By faction (seat-games): Xenos 124 (19) · Firaks 112 (10) · Tinkeroids 112 (8) ·
Taklons 107 (10) · SpaceGiants 105 (8) · Ivits 102 (10) · Darkanians 100 (8) · Terrans 99 (19) · HadschHallas 97 (9) ·
BalTaks 96 (9) · Geodens 95 (10) · Lantids 95 (10) · Ambas 94 (9) · Moweyds 94 (8) · Bescods 92 (9) · Gleens 90 (9) ·
Itars 86 (9) · Nevlas 80 (10). 8–19 seat-games per faction, different seeds and tables per faction: not a faction
ranking.

## Activation (pre-registered checks)

- ① Completion: 46/48 (above). Not the pre-registered 48/48.
- ② `chosen`: 14,176 of 14,176 logged rows carry `chosen` (python count over every `decisions.jsonl.gz`, the two
  error games included).
- ③ `bc_dataset.py index <lab runs> --glob lab-114-all-tier-selfplay-18f-full` → `stats` (work tree, bot turn):
  **games 46, replay on this engine 46, 6-round 46, decisions 13,841**; engine `36d2e007b6f9` = current engine build,
  replay-checked on `36d2e007b6f9` for all 46. These are the first games whose replay check also compares the chosen
  candidate's content per row (rows recorded from 2026-11-12). Seat-games: Xenos 19, Terrans 19, Taklons · Geodens ·
  Lantids · Firaks · Nevlas · Ivits 10, BalTaks · Bescods · Gleens · Itars · Ambas · HadschHallas 9, Tinkeroids ·
  Moweyds · SpaceGiants · Darkanians 8. (Manifest written to the work tree's `runs/bc-114/manifest.jsonl`, not
  committed.)
- ④ Federations (reference): `federation_chances.py` — 276 FormFederation actions in 184 seat-games = **1.50 per
  seat**; highest Xenos 45/19 = 2.37 and Ivits 22/10 = 2.20, lowest Nevlas 10/10 = 1.00 and Ambas 10/9 = 1.11; one
  Nevlas seat never had a legal federation. `endgame_tech_counts.py` — federation tokens held 1.57 per seat (higher
  than the action count; the difference is presumably tokens from other sources, not checked), **unflipped (green)
  0.52**, of those 0.45 with a level-5 step or Advanced tile still available; Advanced tiles 0.36 per seat (35 % of
  seats hold one), level-5 tracks 0.69 (65 %).

## Reading (HANDOFF 1 order)

- Collection: 46 six-round games, 13,841 decisions, all replaying on the current engine with the chosen candidate
  compared — the first data set that meets the E129 trust standard (same build and `chosen`) with complete games.
  Before this run that standard gave 70 games and no 6R game. Size is small next to the 395-game equivalence bundle
  (51,574 decisions, 57 six-round games, no `chosen`): about a quarter of its decisions.
- Two error games — ③ implementation, not noise: an uncaught time-cap exit before the first published result. The
  cap comment in `budget_teacher.py:73–74` says the root ranking always completes; the frozen search's entry check
  breaks that when the stages before it use up the cap. It is a crash path of the teacher itself (the same factory
  is the deployed-teacher family), so it should be closed before more collection. Not reproduced in a bot turn.
- Decision time: no 100 s+ decision in 14,176 rows. This says the 102 long-decision path did not occur with this
  stack and these seeds; it does not identify or fix that path (E108 cause still open).
- Federations 1.50 per seat against the owner's former PPO gate of 3 per seat (now an evaluation metric, E128):
  the teacher is at about half; this is the baseline a learned policy is compared with, nothing to fix here.
- Final VP 100.1 seat mean is a reference for the BC-vs-teacher comparison, not a verdict.

No code or deployment change. Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Close the crash path: when the cap is passed before the first result, play the root ranking's first choice
  and count it as a fallback timeout instead of exiting (`budget_teacher._choose`), with a test; first find which
  pre-search stage took the 60 s (replay the two games to the failing step). One or two bot turns.
- (ㄴ) E128 ②: export the 114 manifest, write `tools/bc_train.py` and the policy-teacher factory (bot turns), then
  ③ BC policy vs teacher A/B on the lab (the actual BC verdict).
- (ㄷ) More collection: another 48 new seeds with the same command (≈ 16 h of lab time; add the two failed seeds),
  after (ㄱ). The lab is idle while (ㄴ) is written.
Bot recommendation: (ㄱ) first, then queue (ㄷ) and do (ㄴ) while it runs.
