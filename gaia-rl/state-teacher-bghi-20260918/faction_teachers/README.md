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
