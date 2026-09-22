# First four-faction teacher / learning pilot

User approved **Xenos, Hadsch Hallas, Terrans, Taklons**, then explicitly delegated
Terrans/Taklons' detailed experimental preferences on 2026-09-13. This package is
opt-in, not a new game rule, reward, default opponent or promoted trained model.

## Decisions and source boundaries

| Faction | Policy | Conditional research / operation |
|---|---|---|
| Xenos | Unchanged `EconomyFirstTeacher` parent Xenos path | Existing expansion, federation and available-tech plans; no automatic AI-track priority. |
| Hadsch Hallas | Opt-in `EconomyFirstTeacher` | Contextual competing research plans; situational native-terminal Economy5 comparison. The approved 2026-09-14 correction removes unconditional Economy4 catch-up. |
| Terrans | New `NativeFactionTeacher` | Value reachable/fundable Gaia colonies, forming throughput and delayed token return; navigation/economy/science remain alternatives. No compulsory Gaia level or PI opening. |
| Taklons | New `NativeFactionTeacher` | Exact native Brainstone charge/spend outcomes, neighbor-dependent PI optionality, income deficits and still-available advanced technology. No forced research track/burn frequency. |

Source directions: curated `research/strategy/README.md` B04/B10 and
`research/strategy/paia-groject.md` PG18 (16:47–19:50, 76:34–80:15) / PG21
(16:42–20:00). These are qualified strategy opinions, not mandatory openings.
The recorded Terrans PDF path was unavailable when checked; this iteration uses
the existing curated notes and current native rules, not a claimed new full-PDF
or audio review. Lost Fleet ship competition remains relevant.

**Implementation choice:** dispatch by actual faction and maintain separate mutable
teachers per seat. Do not change historical guards, cost tables or scoring formulas,
monkeypatch module globals, or impersonate Xenos/HH to obtain another faction's score.
The new two-faction policy evaluates real `Environment.fork` outcomes. Costs,
Gaia conversion budget, Brainstone ordering and automatic transitions are native.
Existing native-generated income tables are reused from the sidebar data file;
the manifest pins them and the Rust generation parity test guards their accuracy.
This repository-local data dependency avoids another handwritten income rulebook.

## Explicit soft hypotheses (not PPO rewards)

`value.py` holds the coefficients for inspection. They are not tuned optimal values.

- Monotone concave resource potential: ore first5 at3 then1; credits first10
  at1.2 then.35; knowledge first8 at2 then.8; QIC first3 at2.5 then1.
  One global potential avoids a reversible conversion reward from price-threshold changes.
- Permanent gross income uses `.7 × remaining incomes`; a chosen booster contributes
  only its one known next income, not a presumed whole-game recurring booster.
- Power positions value ordinary tokens `.2/.6/1.4`, Brainstone `.5/1.5/4.2`.
  These are preferences; native previews determine actual token movement. Committed
  normal forming tokens retain delayed return value (Terrans AreaII / Taklons AreaI).
- Gaia opportunity checks actual range/QIC, normal tokens, available formers,
  next-income mine funding, mine inventory and unclaimed Transdim targets. It caps
  prospective colonies at2. Claimed unbuilt colonies retain value through forming.
  Per-colony option `6 + 2×horizon + 2(Terrans) + 2(Terrans PI)`; an unstarted
  opportunity gets65% of it. Future mine income is an estimate, not a paid colony.
- Income tracks at1 gain a soft level2 continuation option only if current stock
  plus projected permanent knowledge funds the next4knowledge advance. Advanced
  research optionality requires a green federation token, a coverable tile and a
  still-present advanced tile; higher levels improve proximity, not compulsory choices.
  Held advanced pass/action opportunities use current-board counters and explicit
  `.6` use estimates; event opportunities are coarse, not promised triggers.
- Ordinary final standings/research points guide the local potential. Round6
  resource salvage follows native ore/credits/knowledge scoring, not imaginary raw
  QIC VP. Once terminal, use the exact native final score.

All root candidates not already prohibited get a native preview. Up to24 additional
native previews sample newly legal main actions after free conversions. The sample
is not exhaustive; unsampled continuations retain their actual one-step valuation.
Free conversions have a `.25/unit` preference overhead, not an engine cost.
There is no invented future income transition, wall-clock fallback or automatic pass.

### Standing constraints

- No teacher ore/knowledge-to-credit liquidation, including batches.
- QIC->ore only for the exact missing ore of a newly native-legal paid PI/Academy,
  or the existing immediate ore->power->new-federation exception. The exact resulting
  state binds the critical continuation; no replan into an ordinary mine/station.
- No newly allowed Brainstone Gaia commitment (including ship entry). This is a
  **teacher** restriction: game legality and the student's native PPO action mask stay
  unchanged. Student violations are measured rather than silently hidden.

## Evaluation/training boundary

1. `setup.py`: native roster-only seed discovery. The small Rust prefilter uses the
   native RNG, serialized faction order and `SetupPolicy`; verify every accepted
   lineup again through a full `Environment`. No map/score selection. Evaluation
   uses4 different maps, each faction occupying each seat once, NOT map rotations.
2. `games.py`:6 quartet-teacher demonstration games +2 validation games. Per-seat
   planners retain their own commitments. Write full incremental traces and verify
   every decision/state/terminal score independently before using labels.
3. `train.py`: fresh matched initialization; BC4epochs, baseline PPO and BC+PPO each
   4×256 configured native steps, CPU2threads. Same rewards/encodings/optimizer settings
   as the prior pilot. Extra BC compute is **not** matched total compute.
4. Evaluate BC-only / baseline PPO / BC+PPO / teacher separately, each focal faction
   vs3 uniform-random opponents on the held-out pool. Record all failures and report
   by faction, not just a global average. No automatic promotion or publication.

The legacy two-income teachers can make data collection much slower than the PPO
updates. Small step budgets do not imply a short wall-clock run. Source changes fail
closed; old trained weights are untouched. Generated weights are inference-only,
not resumable optimizer checkpoints. No strength guarantee is implied.

```sh
cargo test --manifest-path gaia-rl/Cargo.toml --release --example faction_lineups
cargo build --manifest-path gaia-rl/Cargo.toml --release --example faction_lineups
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  four_factions.test_teacher four_factions.test_training -v
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m four_factions.train \
  --setups /path/to/validated-setups.json --output gaia-rl/runs/new-quartet-run
```

`coverage.py` steers diagnostic native games to PI/Gaia/charging branches. Those
forced diagnostic actions are **not** production strategy, BC data or score evidence.
Full-game smoke scores are small training-map diagnostics, not held-out improvement.

## Opt-in preparation-path competition (2026-09-14)

The next competitive validation uses `compete.py`, **all four teacher seats**,
not the historical focal-teacher-versus-three-random evaluation above. It does not
train, promote a model, publish recordings, or replace the historical control.

```sh
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  four_factions.test_audit four_factions.test_preparation four_factions.test_outcomes \
  four_factions.test_provenance -v
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m four_factions.compete \
  --output gaia-rl/runs/new-preparation-competition
```

Use a fresh output directory. The runner verifies the actual quartet, pins source
hashes and copies the source snapshot, and independently replays the completed
native trace. Do not edit pinned sources during a game. `training/0` is only the
existing live-spectator directory layout, not permission to consume data for
learning. Attach the existing local `watch_ai_game.py` spectator when running an
observed game; this command does not start a viewer server itself.
The shared `provenance.py` guard does not import Torch or training code; historical
training imports the same helpers, with unchanged source/version checks.

### What changes

- `preparation.py` compares paid native continuations through the same two-income
  horizon (or actual terminal), rather than awarding a bonus for merely intending
  to build. Starting-placement alternatives also run forward through that horizon.
- Proposals include both Academy types at each eligible site, research milestones,
  every available Gaia/Transdim target, ships, advanced tiles and separate-core
  federation planning. Existing leaf prices are reused without new coefficients
  or a mandatory faction opening. A goal is a comparison, not a required action.
- Root action families and preparation/scoring-tile pairs are interleaved. A
  currently legal scoring-tile acquisition can be compared with compatible
  intended expansion, upgrades, research or federation. Native subsequent actions
  award the points; the planner does not pay hypothetical triggers itself.
- Hypothetical opponents use purposeful faction-aware **shallow** continuations.
  They are not random, recursively full-depth teachers, or guaranteed optimal.
  All four seats in the actual game use the same timed search infrastructure.
- Existing conservation commitments are transported by exact native state. No
  teacher liquidation, relaxed QIC exception, Brainstone Gaia commitment, native
  rules, faction IDs, student action mask or frontend behavior changes.

### Exact reuse within one decision

`preparation_cache.py` reuses faction-policy ranks only for the identical full
native snapshot (including candidate order) and incoming actor commitment map.
It restores the resulting commitment map as well as the scores; a cached QIC
conversion cannot lose its verified follow-up restriction. Serialized entries
give each caller detached values. Storage is bounded to 128 entries / 8 MiB of
accounted payload and entry overhead; a full cache simply computes normally.

The cache belongs to one search root and its native branches, not multiple games
or environments with different step limits. It is never persisted into the next
real decision. `policy_cache` in the audit reports hits, misses and storage limits.
Only ranking work is reused: no distinct goal is dropped, no leaf price/depth or
candidate order is changed. Actual private rollouts retain the first root fork
and then step their own branch rather than cloning it before every later action.
Search deadlines may still affect how many complete comparisons fit in a turn;
an optimization does not establish whole-game strength or latency guarantees.

### Time and diagnostic contracts

`timed.py` owns a separate search subprocess for each decision. It reconstructs
the exact seed/action prefix and validates the snapshot hash. It publishes a
completed eligible baseline first, then completed comparisons atomically. The
mean target is 60 seconds per seat, with a 60-second ordinary soft allocation.
It is not a debt bank: long placement choices do not erase subsequent investment
comparison budgets. Easy response phases finish early and actual means are measured.
After 60 seconds no new comparison starts, including during starting placement,
federation and advanced-technology choices. Only a comparison already in progress
may finish, within the 300-second maximum including a cleanup reserve. A completed
comparison can still replace the incumbent after the soft cutoff. This is not a
guarantee that the observed mean will be 60 seconds.

At the deadline the supervisor stops only its own process and returns the best
completed eligible incumbent. Unknown, interrupted or horizon-capped routes are
not labeled inferior. A missing incumbent or a known worker error fails explicitly,
without inventing a pass. OS scheduling/suspend delays are not a real-time guarantee;
actual mean/max, deadline flags and any decision above 300 seconds are recorded.

`teacher_audit` retains compared routes, paid action/resource traces, coverage and
timing. `outcomes.py` separately checks whether selected predicted milestones
actually happened by the corresponding horizon; this is agreement, not causality.
The final report includes first Academy rounds, federation rounds, original Gaia
occupancy, and original Transdim formation **separately** from colonization.

### Known limits and evidence

- This is a bounded comparison set, not exhaustive optimal play. Budget exhaustion
  can leave opening choices, colony routes and federation geometries unsearched.
  Funding preparation tests at most 32 single-step funding previews; multiple
  prerequisite actions and all future tile/ship combinations are not enumerated.
- Existing leaf estimates, including stock/income optionality, still matter. A
  two-income forecast does not establish a whole-game three-federation result or
  guaranteed late-game Gaia coverage. Every real turn replans; predicted opponents
  can differ from the full-search actual opponents.
- Native regression on the previously recorded Terrans R1 premature-pass root:
  control leaf 136.85 versus paid Science Academy path 166.62 at the same R3
  horizon; the latter pays for TS, Lab and a R2 Academy without injected resources.
  These are existing heuristic leaf values, **not final VP or a completed match**.
- A supervised 35-second target / 40-second diagnostic returned that path's first
  TS action in 37.1 seconds. Hung-process, no-incumbent and worker-error tests cover
  termination/failure separately. A new complete four-teacher strength result is
  still required; no improvement or model-promotion claim follows from this probe.

## 2026-09-15: source-backed preparation sequences (competitive variant v3)

`compete` now uses `preparation-paths-v3-source-sequences`. The earlier table's
`QuartetTeacher`/legacy policies are retained as controls; actual timed competition
uses `preparation.Policies` plus paid two-income search for every real faction.
See [source/application/remaining-gap crosswalk](../../research/strategy/teacher-application.md).

- `source_paths.py` proposes contextual faction cores, +1/+2 paid colonies before
  or after the core, ship payoffs, range/Gaia-to-colony and early-federation-to-tech.
  Unplaced free starting mines do not count as new paid expansion.
- Sequences can select native Lab/Academy/ship tech variants that also advance the
  intended next track. Paid ship-assisted station/Lab upgrades are valid alternatives.
- Plans persist as *comparison proposals*, not saved candidate indices or compulsory
  moves. Completed work is removed using actual own actions/states; lost planet/tile
  targets and impossible duplicate buildings invalidate the remaining proposal.
- Main resource actions can fund an upcoming milestone even when they end the turn.
  The forecast still executes opponents before spending; resource gains alone do not
  establish successful construction. Native-aligned shared quartet upgrade costs guide
  these proposals; the old HH/Xenos-only estimator/guards remain unchanged.
- Seventh Lost Fleet advanced tile access is considered separately from the six
  research-track tiles. Existing native green-token/cover/access requirements apply.
- Forecast outcomes include remaining work; actual-outcome accounting distinguishes
  own ship use from someone else's shared-slot use. No intent/guide bonus is added.
- All old root alternatives remain eligible, with unchanged60s soft/300s hard bounds.
  Incomplete/unsearched alternatives are unknown, not evidence of inferiority. Initial
  baseline may still consume the whole budget on expensive native branch generation.

This is not a full verified opening book or proof of3federations/R2Academy/lateGaia
coverage. Other14factions, missing original articles, full video reconstruction,
background pondering and remote/distributed compute have not been implemented.

## Opt-in BGG round-one inventory goals (2026-09-15)

Subsequent opt-in 18-faction shared teachers and same-faction teacher BC are documented
in [faction_teachers](../faction_teachers/README.md). The quartet command below still
keeps its historical four-faction roster and defaults.

Add `--bgg-openings` to the `four_factions.compete` command above to select
`preparation-paths-v4-bgg-r1`. Without the flag, the historical v3 behavior remains.
Programmatic callers use `TimedPreparationTeacher(seed, bgg_openings=True)`.
This is connected to the existing **Xenos / HadschHallas / Terrans / Taklons**
teachers only, not fourteen or eighteen complete faction teachers.

- [BGG Part 2 data](../../research/strategy/bgg-openings-part2.csv) preserves all
  222 rows for the fourteen original factions. These are usage counts and average
  final scores, **not win rates** or verified Lost Fleet opening statistics.
- A goal is the exact inventory remaining at the end of R1, including starting
  mines; it is not a fixed action sequence or a count of new mines. Academy types
  are combined as in the source. Coordinates, funding and order use native actions.
- Optimistic building topology proposes routes but cannot certify affordability
  or map access. Paid native forecasts must cross the actual R1 boundary and finish
  the existing two-income horizon before they can justify preferring a BGG result.
- Among those forecasts, keep the remembered target if a matching route is found;
  otherwise choose another source combination using the existing teacher leaf
  value. Printed source order orders proposals; source averages are not extra
  heuristic/PPO rewards. Matching goals take precedence over unmatched forecasts.
- When no matching complete forecast is available, use the existing teacher
  incumbent. This means **no verified route found within the budget**, not proof
  that every opening is impossible. No fabricated pass or relaxed conservation.
- Guidance ends after R1. `bgg_opening` records target selection/retention/switching
  or fallback; `bgg_r1_observed` separately records the real R1 ending inventories
  and target agreement. A forecast is never marked as an observed completion.

The CSV is included in pinned source receipts. The existing 60-second soft and
300-second hard decision bounds remain. This change does not train PPO, promote a
model, deploy in-game AI, or establish improved full-game scores. A native regression
at the recorded Terrans premature-pass root reaches `1RL+1M` through paid upgrades
and independently replays exactly; it is a constrained R1 example, not a strength
benchmark.
