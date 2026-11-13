# Cycle 115a — re-check of engine flag `GAIA_FEDERATION_ONE_ROUTE=1` after engine 966e9ea (shape tested once, one-route mode stops at the first route), command, no games

A = flag off (the engine as every recorded game used it). B = flag on. Engine change under test:
`gaia-engine/src/rules/ai_federation.rs` 966e9ea (HANDOFF E137) — ① both modes: a federation shape (buildings +
satellites) is validated once with a plain token before any token or bonus is tried; an illegal shape skips all
its tokens, the search budget is still charged for the skipped tries ② flag on: the route reconstruction stops at
the first route per building set; if that shape is illegal it falls back to the full enumeration (a81072f
behaviour). Proposed in E136 (ㄱ) after 115 missed its speed criterion (15.0 s vs 10 s). Queued 2026-11-13 by the
owner's 「진행해」. No A/B, no games, no charge verdict.
Pre-registered pass criteria (queue note; the tool must print PASS): ① engine rebuild succeeds and `flag_effective`
② invariant violations (a)(b)(c)(d) = 0 over the 548 recorded decisions **and** the 44 free-action forks of the
pair-012 crash state (`final_free checked = n`) ③ fork errors 0 ④ pair-012 free-action fork total with the flag on
under 10 s, not truncated ⑤ flag-off candidate counts equal to 115: crash state max 17,318; recorded line pair-012
max 204 · total 340; pair-001 max 12 · total 46. Watched, not criteria: flag-off fork total (115: 66.8 s), flag-on
candidate max (115: 476).
Tool `tools/federation_one_route_check.py` (with 73262aa speed check and 917d4f5 invariant compare on the crash-state
forks), lab 114 pair-012 (crash game, 224 decisions) and pair-001 (324 decisions). Host agentmaco, commit
**419898a** (contains 966e9ea), 2026-11-13 13:12:07 → 13:13:05 (58 s). Result:
lab/results/115a-federation-one-route-check.md.

**Health: clean run, exit code 0, tool printed `PASS`, no review section (command job).** This time the tool that
ran does test ④ (output has `speed_failures=0`) and compares the crash-state forks (`checked=44` of `n=44`).

## Charges in rounds 1–3 (the verdict)

Not applicable (no games). The pre-registered criteria instead:

| Criterion | Number | Result |
|---|---|---|
| ① rebuild, `flag_effective` | the engine compiled (966e9ea had not been compiled before the run); `flag_effective=True` | pass |
| ② (a)(b)(c)(d) | 0 / 0 / 0 / 0 over 548 recorded decisions (224 + 324) and 44 / 44 crash-state free-action forks | pass |
| ③ fork errors | 0 | pass |
| ④ crash-state free-action forks, flag on | **2.1 s** (limit: under 10 s; 115: 15.0 s), `truncated=False` | pass |
| ⑤ flag-off candidate counts vs 115 | crash state max 17,318 = 17,318; pair-012 max 204 · total 340 = 204 · 340; pair-001 max 12 · total 46 = 12 · 46 | pass |

**Overall: passed as pre-registered (①–⑤).**

Watched numbers (not criteria): flag-off fork total at the crash state **66.8 s (115) → 51.4 s**; flag-on candidate
max 476 = 476 (115); on the recorded line the flag-on counts are also those of 115 (pair-012 max 34 · total 114,
pair-001 max 8 · total 34); recorded-line fork totals 0.22 / 0.20 s and 0.18 / 0.18 s (off / on), as in 115.

## Activation

- The flag fires: crash-state federation candidates 17,318 → 476 (same as 115, = 34 building sets × 14 tokens),
  recorded line pair-012 340 → 114, pair-001 46 → 34 (tool metrics, results page).
- The new engine code ran: the same tool on the same two games gives different times than 115 (on 15.0 → 2.1 s, off
  66.8 → 51.4 s) with identical candidate counts. This is indirect evidence of the rebuild; the page carries no
  engine build id. 115c (queued) compares build ids directly.

## Reading

- **Correctness (②③)**: now also holds on the large lists — at the crash state every flag-on candidate is a flag-off
  candidate, the non-federation candidates are identical, the (building set, token, bonus) key set is the same and
  there is one candidate per key, for all 44 free-action forks (115 had left these uncompared). The route kept per
  building set may differ from a81072f (first reconstructed route instead of first legal route in JSON order); no
  recorded game used the flag, so nothing depends on which route it is. Sample limits unchanged from 115: two games,
  13 recorded decisions with federation candidates, one crash state, no Itars growing-federation game.
- **Speed (④)**: 15.0 s → 2.1 s, a 5× margin under the 10 s line; one run, one state (pair-001 has no free action
  at its last state). Candidate-proportional time would have been ≈ 1.8 s (115 reading), so the ≈ 13 s that did
  not scale with the candidate count is gone. Which of the two changes removed it is **not measured**: flag-off
  gained 15.4 s from the shape pre-check alone (66.8 → 51.4 s, single runs on the lab host, load not controlled),
  which is about the size of the flag-on gain (12.9 s), so the pre-check may account for most of it — a guess from
  two timings, not a profile.
- **Flag off is not a fix by itself**: 51.4 s of free-action forks at that state remains. Estimated root ranking of
  the crash decision (E136 arithmetic, 69.2 s measured with 66.8 s of forks): flag off ≈ 54 s, flag on ≈ 4.5 s
  against the 60 s cap. Estimates, not re-measured in the teacher.
- **Flag-off list identity (⑤)**: the counts equal 115. Equal counts do not prove equal contents (debate 1/1, E137);
  that rests on 115c (full candidate lists, old build vs new, byte compare) and replay compatibility on 115b (114's
  46 games, strict replay). Both are queued and not finished at the time of writing — until they pass, "flag off
  unchanged" is supported by counts only.
- The 10 s line is the bot's own expectation, not a source claim.

No code or deployment change in this cycle. The flag stays off by default and no spec turns it on. Lab queue after
this: 115b-fed-off-replay-114, 115c-fed-off-golden-114 (each 2–5 min).

## Proposal (user decision, nothing queued)

- (ㄱ) Wait for 115b · 115c (already queued, no decision needed). A mismatch in either means the flag-off list or
  replay changed → fix or revert 966e9ea in a bot turn.
- (ㄴ) After both pass: add an all_tier spec with `GAIA_FEDERATION_ONE_ROUTE=1` in its `env` (bot turn; used for
  the next collection or A/B — further collection itself is on hold, E134 「ㄷ은 대기」).
- (ㄷ) Work-tree engine rebuild (owner command `cd ~/projects/gaia-work/gaia-rl && .venv/bin/maturin develop --release`,
  a few minutes), then re-index the manifest (the build id changes). Only needed when bot-turn tools must run the
  new engine; the 115c golden files are already saved.
- (ㄹ) To settle before flag-on games feed BC/PPO: flag-on candidate lists are shorter than those in the 114 data
  (flag off), so training data and the policy's play environment should use the same setting.
Bot recommendation: (ㄱ) → (ㄴ); (ㄷ) when a bot-turn tool needs it; (ㄹ) decided together with the next collection.
