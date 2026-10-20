# Cycle 095c — golden candidate compare of the reach memo on the lab engine (no A/B)

A lab `command` item, not an A/B. It re-runs the invariance check of E60's engine change on the lab machine's
own engine build: `tools/golden_candidates.py compare --golden runs/golden-candidates --metrics
runs/golden-candidates/metrics-lab.json` (HANDOFF E60, queued 2026-10-21 as the second half of the "reach memo"
verification; user had said "지금 시간 남는데 미리 작업해").

**The change under test (E60, E58 (ㄴ)).** Candidate generation used to run a fresh BFS over the whole board for
every range check (Build, GaiaFormation, booster range, Twilight, terraforming power action). Now one candidate
generation call memoizes one distance table per (start-hex set, range cap) — `MapEngine::distance_map` +
`ReachMemoScope` in `rules/engine.rs`, entered from `ai_decisions_with_diagnostics`. The claim is that the
candidate set and its order are byte-for-byte unchanged; the gain is speed (bot venv `bench_fork.py`, 092 p012
game-0-A02: fork 4R 14.4 ms → 3.1 ms, 1R 1006 → 336 µs, 2R 2426 → 996 µs).

**Golden.** 20 recorded games replayed by the engine alone, every decision's candidate list serialized as a JSON
string: 093 (16 games, pairs 000–015), 092 (3 games: p000 · p006 · p012 game-0-A02), 089 (1 game, p000 game-0-A02,
271 decisions) = **3022 decisions**. Dumped on the bot venv engine **before** the change (build id
`bfb65c38…`). E60 already compared it on the bot venv engine after the change (build `045232fa…`): 0 mismatches.

## Result (agentmaco, commit ade4a6d, 06:06:49 → 06:06:54, exit 0)

| | |
|---|---|
| golden engine (pre-memo, bot venv) | `bfb65c38cd3e…235d387a` |
| lab engine (HEAD + memo, auto-rebuilt by lab) | `045232fa8b9d…1a12283f4` |
| games / decisions compared | 20 / 3022 |
| mismatched games | **0** |
| `identical` | **true** |
| wall time | 3.4 s |

Every game line reads `ok … N decisions`; no `mismatch` field is set in any game.

## Reading

- **Candidate set and order are invariant on a second, independent build.** The lab's auto-rebuild (`maturin
  develop` from HEAD) produced **the same build id (`045232fa…`) as the bot venv's `maturin build --release`**
  of E60, so the bot venv engine and the lab engine are the same artifact; and both agree with the pre-change
  golden on all 3022 decisions. The three lineages (pre-memo bot venv → post-memo bot venv → post-memo lab) are
  one line. E60's caveat ("the golden might not be a HEAD build") is closed from the practical side: whatever
  the golden engine was, HEAD+memo reproduces its candidates exactly.
- Scope of the guarantee: this covers the paths the 20 games exercise (4R games from 092/093, one 6R game from
  089 with federations, Lost Fleet ships in every game). It is a replay of *recorded* decisions — the compare
  re-generates candidates for the recorded states, so it checks candidate generation, not the search's choice
  under a time cap. Recorded-game replay and `explain_*` tools are unaffected by construction.
- **What the speed-up does to real decisions is not measured here.** Under the 20 s cap the search spends the
  saved time on more comparisons, so decisions *can* change on both arms alike (E52 (c) spirit). 095a and 095b
  ran on the new engine (lab rebuilt before 095a): both clean (0 errors / timeouts / fallbacks), decision times
  the same shape as 093 (095b A mean 10.06 s, p90 20.12 s, max 22.9 s). The "unsearched decisions" column is
  not a speed metric (093 quartet a ≈ 23.5 per arm-pair, 095b ≈ 25) and should not be read as one.
- Still **pending for the user** (the bot cannot run cargo): `cargo test -p gaia-engine --test reach_memo`
  (two integration tests: `distance_map == shortest_distance` on 6 boards × caps 0–9, and real-board Build
  candidates == out-of-scope `validate_action`). File: `gaia-engine/tests/reach_memo.rs`.
- Not done, by decision (E60): E58 (ㄱ) removing the double validation stays on hold (`get_valid_actions`
  always inserts `Pass{None}` and `validate_pass` rejects it in rounds 1–5, so a plain skip changes the
  candidate set; after the memo the re-validation is cheap). E58 (ㄷ) planet-hex restriction is not planned.

Nothing changed in code, teacher stacks or deployment. The live server runs the same engine crate, so the
speed-up ships with D1 (3장) without any extra step.

## Proposal (user decision, nothing queued)

- (ㄱ) **Close the item**: user runs `cargo test -p gaia-engine --test reach_memo` once; if green, E58 (ㄴ) is
  done and the golden dump (`runs/golden-candidates`, 20 games) stays as the standing invariance fixture.
- (ㄴ) **Make the golden compare the standard gate for every engine change**: a reusable lab `command` template
  (same command as 095c) queued right after any engine commit, before the next A/B; re-dump the golden only when
  a change is *meant* to alter candidates (and say so in the cycle doc). Process only, no code.
- (ㄷ) **Next speed item, lab 0 first**: profile where the remaining 3.1 ms (4R fork) goes with `bench_fork.py`
  before touching E58 (ㄱ); only pursue it if a single hot spot shows. Not urgent — search quality (093/095b
  reads) matters more than another 2×.

Bot recommendation: (ㄱ) now (one user command), (ㄴ) as a rule in HANDOFF, (ㄷ) later.
