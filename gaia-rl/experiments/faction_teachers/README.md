# Shared faction teachers

Opt-in **one search engine / 18 actual faction profiles / same-faction student
labels**. This does not replace the historical quartet, deploy in-game opponents,
or claim eighteen strong experts. Existing native rewards and all legal candidates
remain unchanged; the existing teacher conservation constraints still apply.

## What each teacher uses

- Native `factions.toml` supplies the actual home planet and starting pieces;
  native-generated income data supplies faction-specific income. Every eligible
  candidate is previewed through the real engine, including faction abilities,
  their costs, passive effects and follow-up decisions. No faction impersonation.
- The original four teachers retain their shallow rankings and source paths.
  Other factions share the existing native-preview value function, with no new
  faction score coefficients. Its soft estimates remain uncalibrated hypotheses.
- Original fourteen: BGG Part 2 R1 ending-inventory goals, with the approved
  select/keep/switch/fallback behavior. Source average scores are not win rates or
  extra rewards. R2 ends this semi-forced inventory guidance.
- Expansion four: **native-effect baseline only**, as approved by the user. No
  BGG row or dedicated opening guide is invented. Seven-color terraforming
  estimates are not applied to Asteroid/ProtoPlanet homes; their real paid
  construction effects remain in native previews. Tinkering tile decisions can
  enter the shared two-income search instead of comparing only tile IDs.
- Search retains 60-second soft / 300-second hard bounds and the existing
  two-income, 192-decision, bounded funding horizons. Actual opponents can differ
  from the shallow forecast. Unsearched paths are unknown, not impossible.

## Guide-to-code crosswalk

### Opt-in technology-plan preservation

With `GAIA_FACTION_TECH_PLANS=1` (default **OFF**), Terrans/Ambas technology
proposals have two continuations: the existing fallback route, followed by a
`preserve-plan:` alternative. Only the latter rejects its own actions that destroy
unfinished prerequisites, checked through native successors. Equivalent federations
that consume an Ambas swap mine are filtered together. Other legal alternatives,
prices and total time limits are unchanged; an incomplete comparison gets no
invented score. The pilot search uses matched progressive horizons described below. External invalidation still uses cancellation/fallback.
The `faction-tech-preserve` source marker is internal mode metadata, not a new guide.

The higher comparable value can win; plans are not globally mandatory. A saved
Ambas branch reaches PI construction and relocation under preservation, but its
target-site federation is still unfinished at the same horizon. This is a local
functional result, **not** a win-rate or expert-strength result.

From `gaia-rl/`, reproduce the bounded comparison (not a whole game):

```sh
PYTHONPATH=python:experiments .venv/bin/python tools/compare_plan_preservation.py \
  experiments/faction_teachers/fixtures/ambas-plan-cancellation.json --seconds 60
PYTHONPATH=python:experiments .venv/bin/python -m unittest faction_teachers.test_plan_preservation -v
```

Receipt: `research/strategy/cycles/011-plan-preservation-comparison-verified.json`.

### Native-valid federation preparation (2026-09-25)

In an Ambas preservation continuation, a pending target federation can now prepare
construction when its eligible building power is insufficient. Existing legal
formation actions still take precedence. The helper previews real native-paid
builds/upgrades, excludes conservation-blocked actions, and uses unchanged rankings.
If no direct construction is ready, at most 32 existing funding-action previews
can prove a same-actor follow-up construction. Opponent turns and missing resources
are never invented; this is not exhaustive multistep financing.

The saved failure also exposed an omitted legality prerequisite: a new Ambas
federation cannot contain a location touching its own old federation. Such pilot
goals now use the existing cancellation/fallback behavior, and preservation rejects
an own formation that would make its future target forbidden. Power preparation
counts neither old-federation buildings nor buildings adjacent to that federation.
Reaching seven power still does **not** complete a goal; the engine must actually
accept a formation including the target. These changes are confined to the pilot;
no engine rule, value bonus, total time budget or default OFF setting changes.

The earlier R5 target at `3,-2` touches old federation nodes `2,-2` and `3,-3`.
Its raw unfederated power was six, but only two could enter a separate federation.
The initial 6→8 construction result is retained as a diagnostic, not proof of a
usable target or strength improvement. See cycle014 receipts and STATUS.

### Matched-depth pilot search

The enabled Terrans/Ambas pilot now compares native-transition cutoffs
1, 2, 4, 8, 16, 32, 64, 128, then the original two-income horizon (192-transition
maximum). Game end or the original income boundary can finish a route earlier.
The first stage compares control and pilot legacy/preserved paths first; later
stages evaluate the previous incumbent and control before promising alternatives.
No candidate is discarded as inferior merely because time ran out.

A deeper stage replaces the published selection only after both anchors complete
at that depth. Selection, BGG opening arbitration and clock gaps use only that
stage's `plans`; `comparison_stages` retains the separate audit history. An
incomplete anchor retains the last valid shallower result. This pilot does not
apply the legacy three-comparison convergence shortcut between these stages;
fast verified reactions, full-horizon completion and the existing clock still stop
work. First-action resolution and completed full-horizon routes are reused without
reusing a shallow value as a deeper result. OFF and other factions keep the old search.

In the saved Ambas branch with no long thoughts left, the same 10-second budget
completed 115 routes each at depths 1 and 2, then three at depth 4. The previously
starved preservation routes were evaluated, but the chosen action stayed the same.
This establishes comparison coverage, not improved strength or a completed target
federation. See `research/strategy/cycles/013-progressive-search-probe.json`.

```sh
PYTHONPATH=python:experiments .venv/bin/python tools/probe_progressive_search.py \
  experiments/faction_teachers/fixtures/ambas-plan-cancellation.json \
  runs/tech-plan-pilot-20260924-shared-38/policy-checkpoint.json
PYTHONPATH=python:experiments .venv/bin/python -m unittest faction_teachers.test_progressive -v
```

These are conditional comparisons, not mandatory sequences or guide-completeness
claims. Original unavailable PDFs have **not** been reconstructed: this uses the
retained source summaries and supplied BGG PDFs. See
[source inventory](../../research/strategy/teacher-application.md) and
[faction summaries](../../research/strategy/README.md).

| Faction | Executable source-informed comparisons | Evidence |
|---|---|---|
| Terrans | Existing PI/Lab/Academy–Gaia/research alternatives | B04, PG18; existing quartet paths |
| Taklons | Existing Academy/research, two Labs, PI circulation | B10, PG21; existing quartet paths |
| Xenos | Existing Academy/range, Rebellion, two Labs, early federation | B15, PG15, LF04; existing quartet paths |
| HadschHallas | Existing Academy/economy and PI–Rebellion alternatives | B17, PG19; existing quartet paths |
| Ambas | PI relocation followed by federation | B06 |
| Gleens | Trading Station income then natural Gaia; direct Gaia alternative | B05 |
| Itars | PI, paid Gaia formation, Gaia-phase technology | B07 |
| Nevlas | Power-to-Gaia knowledge followed by research, with/without PI preparation | B08 |
| Firaks | PI/Lab prerequisite, actual downgrade, then rebuild the Lab | B09 |
| BalTaks | Gaiaformer-to-QIC followed by expansion | B11 |
| Ivits | Space Station then expansion or extending its single federation | B12 |
| Bescods | Lowest-track ability then expansion; correct alternate PI/Academy graph | B13 |
| Geodens | PI followed by a currently unowned, new planet type | B14 |
| Lantids | PI followed by a shared settlement on another player's planet | B16 |
| Tinkeroids, Moweyds, SpaceGiants, Darkanians | Common search and actual native ability effects; no fabricated guide sequence | Native rules; limited LF04 context, not dedicated faction guides |

`paths.py` adds ordered plans only in this shared lane. A later Firaks Lab rebuild
cannot be marked complete merely because the Lab existed before its downgrade.
Actual own actions advance special-action goals. Ordinary native roots remain
alternatives; proposing an ability does not make it free or guarantee success.

## Explicit local commands

```sh
export PYTHONPATH=gaia-rl/experiments
gaia-rl/.venv/bin/python -m faction_teachers profiles
# One potentially long four-teacher game; seed/setup is explicit, output must be new.
gaia-rl/.venv/bin/python -m faction_teachers record --seed YOUR_SEED --output /new/game
# Approved adaptive clock: ordinary target 10 s, up to six 120 s thoughts per seat.
gaia-rl/.venv/bin/python -m faction_teachers record --seed YOUR_SEED --output /new/game \
  --adaptive-clock
# Continue the exact board/history/plans in a NEW record, not a fresh simulation.
gaia-rl/.venv/bin/python -m faction_teachers record --seed ORIGINAL_SEED --output /new/continuation \
  --adaptive-clock --resume-checkpoint /old/game/policy-checkpoint.json
gaia-rl/.venv/bin/python -m faction_learning audit /new/game --faction Terrans --labels teacher
```

## Adaptive thinking time (approved 2026-09-15)

The explicit `--adaptive-clock` lane leaves the historical 60/300-second control
available. It allocates **10 seconds normally**, up to **1 second for a forced
choice** and **3 seconds for reactions or verified resource follow-ups**. These
are budgets, not artificial waits: an evaluated forced choice or the unique
evaluated next step of a remembered plan returns as soon as ready.

At the basic deadline, an unresolved important comparison or a blocked old plan
may use one of **six long thoughts per actual seat per game**. A long thought has
a **120-second total cap from the start of that decision**, not 120 extra seconds.
Uses do not reset each round, and no round has a mandatory quota. With fewer uses
than remaining rounds, the close-comparison threshold tightens. Unknown critical
plans can still warrant spending a use; the system does not guarantee an even
distribution or require spending all six.

The parent supervises the process deadline. The worker can continue the same
search after an extension without throwing away its first ten seconds of work.
Stable selection across three completed distinct first actions, a completed
control forecast and a sufficient value gap can end thinking early; unresolved
BGG fallback and unexamined alternatives are not reported as exhaustive success.
The 3% normalized gap and its remaining-game adjustment are **uncalibrated time
allocation heuristics**, not changes to action scores, win probabilities or
evidence that a shorter teacher is equally strong. All native costs, candidate
legality, conservation constraints and BGG selection rules remain in force.

`teacher-audit.jsonl` records the basic budget, extension reason, remaining uses
and actual elapsed time. `policy-checkpoint.json` atomically records the exact
native prefix/state and teacher memory, including spent long thoughts. Resume
independently verifies every old native transition and creates a new full record
whose provenance identifies the old-policy prefix separately from the new policy.
It does not silently re-label the imported moves or reset an existing adaptive
allowance. Source/hash mismatch, missing evaluated choices and failed workers
remain explicit failures; there is no automatic pass to hide them.

For adaptive records, use `timing.long_think_*`,
`timing.total_decision_cap_seconds` and `stop_reason` for allocation evidence.
The raw search's older `extension_policy`/`extended_reason` labels still describe
the legacy soft-deadline loop and are not authoritative for adaptive allocation.

Adaptive v2 prepares a small **native one-step reserve** before the normal root
ranking, inside the same decision budget (target up to 0.5 s, checked between
indivisible native previews; at least one eligible action is evaluated). If no
normal ranking is published on time, it chooses the best evaluated reserve
action instead of ending the game. Normal on-time rankings still take priority.
This is not an automatic pass, extra long-think allowance or a full search:
`timing.quick_fallback_used`, `quick_reserve_seconds`, and the `quick_*_indices`
audit fields distinguish evaluated, excluded and still-unknown candidates.
The reserve reuses the existing native state potential, samples action families,
keeps verified follow-up obligations and resource/Brainstone constraints, and
does not attempt new QIC-to-ore funding proofs. Pass can only win by evaluation,
never as an exception handler. Actual state/source/worker errors are not masked.
Legacy non-adaptive control behavior remains unchanged.

The recorder keeps a named/source-pinned teacher receipt and a full append-only
native trace. It checks a second native environment during execution; offline
audit independently replays the complete trace again. Only terminal, compatible,
consistent records can supply labels. Human, teacher and PPO/other AI controllers
are distinct; caller declarations are **not authentication or proof of expertise**.

To branch a student from explicitly selected same-faction teacher games:

```sh
# Creates independent untrained models, not eighteen completed PPO learners.
gaia-rl/.venv/bin/python -m faction_learning init --output /new/models
gaia-rl/.venv/bin/python -m faction_learning bc --source /new/models --output /new/bc-branch \
  --faction Terrans --labels teacher --training-game /teacher/train-game \
  --validation-game /teacher/validation-game --epochs 1
```

BC requires an explicit epoch budget and separate games; duplicate/leaked games,
wrong faction/role and divergent native records are rejected. Only the selected
faction's weights change, in a **new** catalog. Existing PPO model/optimizer/RNG
checkpoints remain untouched. BC does not automatically continue PPO, mix human
and teacher data, update a live game, or promote the branch.

## Verification boundary

Native previews cover all eighteen real factions. Tests cover guide proposals,
Bescods topology, Ivits federation handling, ordered Firaks rebuilding, controller
ownership, independent native replay, split leakage rejection and same-faction BC
weight isolation. The tiny end-to-end BC fixtures use diagnostic moves, **not
expert demonstrations or score-improvement evidence**. Full teacher-game quality,
all late-game ability interactions and student strength still need evaluation.
