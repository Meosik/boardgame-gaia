# Cycle 137 — teacher early upgrades — R1–2 upgrade decisions of the 141 finished 6R games, command, no verdict — **failed (invalid counts)**

No A/B. Read-only replay of the current teacher's finished 6R games (114 · 119 · 123 = 141 games, played on engine build
`fc19671c4278`) with `lab/scratch_e339_upgrades.py`: every R1–2 main-turn decision classed selected / prep_selected /
lost_compare / menu_only / not_in_menu / not_legal, by faction and by legal target building. Queued 2026-11-26 by the
user's question 「점수 비교 유지에서 초반에 업그레이드를 잘 안하진 않나?」 (HANDOFF E339, Codex clean, queue commit 73a4997).
Pre-registered: no verdict; read ① compared-field share ② classes and first upgrade round by faction ③ lost_compare
value gap ④ engine = fc19671c ⑤ error_count. Expected ≈ 15 min, limit 1 h. agentmaco, lab commit 73a4997,
2026-11-26 01:47:31 → 01:47:57 (26 s). Result: lab/results/137-teacher-early-upgrades.md.

**Health: failed — the counts are not usable.** Exit code 0, but:
- **engine** printed `49318fef…` (the current lab build, same as 133), not `fc19671c` (check ④ fails).
- **error_count 123 / 141**: every error is `IndexError('list index out of range')` at
  `cands[row['index']]` — the logged candidate index does not exist in the lab build's candidate list, i.e. the replay
  parts from the logged game. Only **18 games** finished (seat-games: Xenos 16, Terrans 16, Ambas 9, HadschHallas 9,
  Darkanians/SpaceGiants/Taklons/Geodens 4, six factions 1) — mostly one quartet, not the 18-faction sample.
- **wrong script version**: the lab pulled 73a4997 and started at 01:47:31; the debate fix 27b6b87 (prep_selected class,
  per-target judgement, merge a game only after its whole replay) was pushed at 01:47:40. The run used the old script,
  which adds counts decision by decision, so the 123 failed games also left their counts up to the failing step:
  `main_decisions` 5,349 is far more than 18 games' R1–2 main turns. There is no `prep_selected` column.
- Runtime 26 s against ≈ 15 min expected = most games stopped early.

## Counts (not the verdict — invalid, recorded only for the shape)

ALL selected 1,143 · lost_compare 14 · menu_only 457 · not_in_menu 993 · not_legal 2,742; `has_compared_field`
5,349/5,349 (every decision row carries `compared`, so lost_compare and menu_only can be told apart once the replay is
right). lost_compare value gap n = 14, median 4.11 (p25 0, p75 16.75). Terrans and Xenos hold 418/457 menu_only.
None of these numbers is read: they mix 18 whole games with partial prefixes of 123 diverged games on a different build.

## Activation

Not applicable (no teacher part). The replay itself did not run as designed (see Health).

## Reading (HANDOFF 1 order)

- ① noise — not reached. ③ implementation — the cause: the replay ran on a build that does not reproduce the logged
  games. E201 already found that snapshots embed `engine_build_id` and that other builds part from the log; E303 (133)
  and cycle 129 used the lab build only for games it played itself. The 141 games were played on `fc19671c`; the lab
  has since been rebuilt to `49318fef`. My queue note assumed the lab still replays them (E337 counted "strict replay
  141/141" on the fc19671c index, not on today's build) — design mistake.
- Second cause: the queue went in before the debate fix, and the lab picked the old script 9 s before the fix landed.
- The script also replays all six rounds although only R1–2 are counted (`continue` instead of `break` past round 2),
  so a divergence in R3–6 also drops a game.
- No review section (command job).

No code, engine or deploy change. Lab queue empty.

## Proposal (user decision, nothing queued)

- (ㄱ) Fix and re-run (Sonnet edit + lab ≈ 5 min): in `scratch_e339_upgrades.py` stop each replay after round 2, check
  every step that the candidate at `row['index']` equals the logged `chosen` action and drop the game at the first
  mismatch, recording the round of the divergence; print the build. If most games still part inside R1–2 on
  `49318fef`, go to (ㄴ).
- (ㄴ) Replay on an `fc19671c` build (an extra venv built at that engine commit — user command, ≈ 10 min build), then
  the same script on all 141 games.
- (ㄷ) Without replay, from the log only: `chosen` upgrades per seat in R1–2 and the first upgrade round (no legality,
  so no not_in_menu / not_legal) — bot turn, answers half of the question.
Bot recommendation: (ㄱ) first; it also tells how far the two builds agree.
