# Cycle 115 — engine flag `GAIA_FEDERATION_ONE_ROUTE=1` check (one satellite route per federation building set), command, no games

A = flag off (the engine as every recorded game used it). B = flag on: `gaia-engine/src/rules/ai_federation.rs`
(a81072f) keeps, per federation building set, only the first satellite route that yields a legal action in the AI
candidate list; the validator and human play are unchanged. Part proposed in HANDOFF E134 (가), written in E135.
Queued 2026-11-13 by the owner's 「가 진행하고」. No A/B, no games, no charge verdict.
Pre-registered pass criteria (queue note): ① engine rebuild succeeds ② invariant violations 0 — (a) every on-candidate
is an off-candidate (b) non-federation candidates identical in order (c) same (building set, token, bonus) key set
(d) one candidate per key with the flag on ③ fork errors 0 and `flag_effective` ④ free-action fork total at the
pair-012 crash state: off ≈ 66 s → **on under 10 s** (`final_free_fork_seconds_on`).
Tool `tools/federation_one_route_check.py` replays lab 114 pair-012 (crash game, 224 decisions) and pair-001
(324 decisions) and forks each recorded move with the flag off and on. Host agentmaco, commit **fa5e8e3**,
2026-11-13 12:50:20 → 12:51:45 (1 min 25 s). Result: lab/results/115-federation-one-route-check.md.

**Health: clean run, exit code 0, no review section (command job).** The lab started from fa5e8e3, before the debate
fix 73262aa: the queue line it ran had no `--max-final-free-seconds-on 10` and the tool it ran did not test ④
(its output has no `speed_failures=` field). **The printed `PASS` therefore covers ②③ only.**

## Charges in rounds 1–3 (the verdict)

Not applicable (no games). The pre-registered criteria instead:

| Criterion | Number | Result |
|---|---|---|
| ① rebuild | flag changes the candidate list (`flag_effective` true) | pass |
| ② (a)(b)(c)(d) | 0 / 0 / 0 / 0 over 548 decisions (224 + 324) | pass |
| ③ fork errors | 0 | pass |
| ④ crash-state free-action forks (44 free actions) | off 66.8 s → on **15.0 s** (limit: under 10 s), not truncated | **fail** |

**Overall: not passed as pre-registered (④ misses, 15.0 s vs 10 s).** The current tool (73262aa, line 204:
`final_free_fork_seconds_on >= limit`) returns FAIL on these numbers.

## Activation (tool output, metrics in the result page)

- Crash state (pair-012 after step 224), largest federation list behind one free action: **17,318 → 476**
  (the 34 building sets × 14 token choices predicted in E135).
- Recorded line of play: pair-012 has 8 decisions with federation candidates, largest list 204 → 34 (step 160),
  total 340 → 114; pair-001 has 5, largest 12 → 8, total 46 → 34. Fork time summed over the whole recorded line is
  0.22 / 0.20 s and 0.18 / 0.18 s (off / on): on the played line the enumeration costs nothing; the cost is in the
  free-action forks that convert ore to power tokens first.
- pair-001 ends with no free actions (0 / 0 s), so ④ rests on pair-012 alone.

## Reading (HANDOFF 1 order)

- Correctness (②③): the flag does what was written. It removes only extra routes of a building set, leaves every
  other candidate in place and in order, and loses no (building set, token, bonus) choice. Two games, 13 decisions
  with federation candidates plus 44 crash-state forks; no Ivits game (growth federations) in the sample.
- Speed (④): ③ scope/implementation. The list shrank 36× (17,318 → 476) but the time only 4.5× (66.8 → 15.0 s).
  If time followed the list size, on would be ≈ 1.8 s; about 13 s does not depend on how many candidates are
  kept. Code reading: with the flag on, `graph.routes` (ai_federation.rs:271) still enumerates every minimum route
  of every building set and all 1,237 shapes are still built; the flag only skips validation after the first legal
  route (:288). The split between route enumeration and the remaining validations (free-mine tokens validate one
  action per board hex) is **not measured**.
- What 15 s means for the teacher: at the crash decision the root ranking was 69 s against a 60 s cap (E134);
  with the flag it would be about 18 s, so the cap-before-search path would not fire there, but a quarter of the
  cap still goes to the root ranking and every rollout step in such a state pays the same enumeration.
  7cb307b (play the root ranking instead of crashing) stays the safety net either way.
- The 10 s limit was the bot's own estimate, not a source claim; missing it is a statement about the
  implementation, not about the idea.

No code or deployment change in this cycle. The flag stays default off; no spec turns it on. Lab queue is empty.

## Proposal (user decision, nothing queued)

- (ㄱ) Finish the speed part in the engine: under the flag stop the route enumeration at the first route per
  building set (fall back to the full enumeration when that route fails validation, so criterion (c) holds), then
  re-run this check as 115a with the limit enforced (queue file already carries it). One bot turn + lab ≈ 2 min.
  The bot cannot run cargo, so a compile error comes back as a failed 115a.
- (ㄴ) Accept 15 s: add an all_tier spec with the flag in `env` for new collections now, leave the engine as is.
  The pre-registered ④ stays recorded as missed.
- (ㄷ) Leave the flag unused; rely on 7cb307b only.
Bot recommendation: (ㄱ), then the spec of (ㄴ) once 115a passes; E133 (ㄴ) bc_train continues in parallel.
