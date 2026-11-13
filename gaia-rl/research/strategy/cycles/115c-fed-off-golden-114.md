# Cycle 115c — full candidate lists of the 114 games, old build vs the build after 966e9ea (flag off), command, no games

A = the engine that played 114 (build `36d2e007b6f9`, the bot work tree), used to dump the golden. B = the lab
engine rebuilt after 966e9ea (`gaia-engine/src/rules/ai_federation.rs`: a federation shape is validated once with
a plain token before its tokens and bonuses, both modes; HANDOFF E137). `GAIA_FEDERATION_ONE_ROUTE` is not set
(the queue file has no `env`), so this is the flag-off path every recorded game used. Queued 2026-11-13 by the
owner's 「진행해」 (E137) after debate 1/1: 115a ⑤ compared only counts and 115b only the chosen action, so the
claim "flag off leaves the candidate list unchanged" needed the whole list. No A/B, no games, no charge verdict.
Pre-registered pass criteria (queue note): `identical` true = 0 mismatched games, 14,176 decisions compared,
`final_free_checked` 56, and the engine build id differs from the golden's (a new build). Any mismatch = the
flag-off list changed → fix or revert the engine change.
Command: `golden_candidates.py compare --golden /home/sohegi/projects/gaia-work/gaia-rl/runs/golden-115c`
(golden outside git, 2.5 MB, dumped in the bot turn of E137 with `dump --final-free`, e9cd61c). For each of the
48 games of `lab-114-all-tier-selfplay-18f-full` the tool rebuilds the game from its seed, and at every recorded
decision compares `decision_id` and the full `candidates` JSON text with the golden string (`==` on the text,
`golden_candidates.py:115–124`), then steps the recorded index. After the last recorded decision it forks every
free-action candidate that the golden listed and compares candidate count and SHA-256 of the list after the fork
(`:126–139`). agentmaco, commit 00dca67, 2026-11-13 13:23:32 → 13:24:47 (75 s; tool 74.0 s).
Result: lab/results/115c-fed-off-golden-114.md.

**Health: clean.** Exit code 0, 48 `ok` lines, no `MISMATCH` line, no fork error. No games, so no decision
times, timeouts or fallbacks. The result page has no second-model review section (command job).

## Charges in rounds 1–3 (the verdict)

Not applicable: no games were played and nothing was pre-registered on charges. The pre-registered check is the
list comparison below.

| Pre-registered criterion | Expected | Measured (`metrics` of the result .json) | |
|---|---:|---:|---|
| `identical` / mismatched games | true / 0 | true / 0 of 48 | pass |
| decisions compared | 14,176 | 14,176 (sum of the 48 per-game counts) | pass |
| `final_free_checked` | 56 | 56 = pair-012 44 + pair-037 12 | pass |
| engine build id ≠ golden's | differs | golden `36d2e007b6f9` → now `fc19671c4278` | pass |

**Passed on all four.** `fc19671c4278` is the same id that ran the 115b replay check, and the bot recomputed it
from the work-tree HEAD source in the 115b turn (the id is the SHA-256 of the engine source,
`gaia-rl/build.rs:23–55`; last engine commit 966e9ea) — so the lists compared here come from the 966e9ea source.

## Activation (did the comparison reach the changed code?)

966e9ea changed only the federation candidate enumeration, so what matters is how many compared lists contain
federation candidates. Counted by the bot from the golden files (short python over
`gaia-rl/runs/golden-115c/*.jsonl.gz`, `"type":"FormFederation"` in the stored candidate text):

- 14,232 golden rows = 14,176 decisions + 56 final-free forks.
- **658 decisions in 48 of 48 games** list at least one `FormFederation` candidate: 54,244 federation candidates
  in total, median 30 per decision, largest 1,419. All of them are byte-identical on the new build, in the same
  order.
- The 56 final-free forks are stored as count + hash only (no text), list sizes 5 to **17,440** candidates; the
  44 forks from the pair-012 crash state (the lists with up to 17,318 federation candidates of 115/115a) are
  among them and every hash matches. The last state itself (after the final recorded step) is not compared as
  text, only through its forks.
- The other 13,518 decisions list no federation candidate. Whether the enumeration ran there and returned
  nothing (only illegal shapes) is not recorded; their lists match either way.

## Reading (HANDOFF 1 order)

- **Flag-off list identity — holds on this sample.** ① noise: none, the comparison is deterministic text
  equality. ② activation: the changed path produced 54,244 candidates over 658 decisions plus the large crash
  state, so the pass is not vacuous. ③ scope: the per-decision check compares the whole serialized list, so a
  changed candidate, a dropped one, an added one or a reordering would all fail; the final-free check uses
  count + SHA-256 of the same text, equivalent for this purpose. Together with 115a ⑤ (counts) and 115b (46
  games replay with `chosen` content), the three checks agree: with the flag off, 966e9ea changes speed only
  (flag-off fork sum 66.8 → 51.4 s, 115a), not the list.
- **Limits of the sample (not shown here).** (a) It is the 114 states only — 48 all_tier self-play games,
  one map setting, the lists reached along the recorded lines; identity on other states rests on the code
  argument of E137, not on this run. (b) E137 argues the exploration budget is charged the same for skipped
  shapes so the cut-off point is the same; this run does not record whether any of these states reached the
  budget cut-off, so that branch may be untested. (c) Final-free forks exist only for the two crashed games
  (finished games have no candidates at the end), so the very large lists are two states, one of them the
  17,440-candidate one. (d) The flag is not recorded in the metrics; it is off because the queue file sets no
  `env` — and a flag-on run could not have matched (17,318 → 476 candidates in the crash state, 115a).
- **What it unblocks.** The 114 data (46 games, 13,841 decisions) stays valid for BC export and as PPO initial
  data on the new engine: same lists, same indices, same chosen actions. The work-tree engine is still
  `36d2e007`; `bc-115b/manifest.jsonl` was checked by `fc19671c`, so `export`/`iter_samples` from the work
  tree are refused until the work tree is rebuilt (E131 rule).
- Health and timing: 74 s for 14,232 list builds; nothing to tune.

No code or deployment change. The flag stays default-off and no spec turns it on. Lab queue: empty after this
cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) New spec = all_tier with `GAIA_FEDERATION_ONE_ROUTE=1` in `env` (bot turn 1), then re-run the two crashed
  games of 114 (pair-012, pair-037, same seeds and seats, 6R, cap60) with that spec: pass = both finish, 0
  errors, max decision time under the cap-60 range (~80 s), fallback-timeout count reported. About 1–1.5 lab
  hours (114 averaged ~20 min per game). This is the first time the flag runs inside the teacher; 115/115a
  measured forks only.
- (ㄴ) Rebuild the work-tree engine — owner command
  `cd ~/projects/gaia-work/gaia-rl && .venv/bin/maturin develop --release` (a few minutes). After it the
  bc-115b manifest is the valid one and E128 (ㄴ) can go on: export of the 114 games + `tools/bc_train.py`
  (bot turns, tool test only).
- (ㄷ) Before any flag-on game is used for BC or PPO: the flag-on list is shorter than the 114 (flag-off)
  lists, so collection and play environments must use the same flag. Decide together with the next collection
  (E134 「ㄷ은 대기」 still holds).
- (ㄹ) Still open from E134 (나): whether the 38 rows "60 s, 0 comparisons" are dropped from BC.
Bot recommendation: (ㄱ) and (ㄴ) in parallel — (ㄱ) is lab time, (ㄴ) is one owner command; (ㄷ) with the next
collection.
