# Paia-informed conditional teacher candidate

User authorization 2026-09-13: improve the unfinished current teacher and test it.
Scope remains **Xenos / Hadsch Hallas**, not all18factions, trained PPO or production bot promotion.
Sources/conditions: [curated Paia notes](../../research/strategy/paia-groject.md).
Historical teachers remain controls, without modified weights or rules.

## Added competing paths

- Site-specific PI preparation, PI then repeated available Rebellion tech actions,
  and (when the distance goal exists) PI/Academy pairs in both orders.
- Gaia colony completion means an actual paid mine, not simply deploying a former.
  Separate immediate-only paths include an ordinary asteroid Build afterward;
  low Gaia1 access is considered without automatically climbing to2. Native legality
  pays range, mine costs, power and the former's actual use/discard. No Eclipse
  credit-action substitution in this specific former-discard chain.
- A minimum-three-federation planning candidate keeps large cores separate; PI
  preparation is also compared. Only actual native federation candidates certify
  completed groups. Upgrades/expansion between them are still sampled preparation:
  **not exhaustive future geometry, guaranteed three federations or a hard ban on
  using two Academies together**. The unrestricted control can win a technology race.
- A selected goal is continued within the current round using live native costs
  and legal actions, not frozen action indices. Actual income, goal completion or
  a lost target triggers a new comparison. Unmet targets remain alternatives in
  that comparison instead of silently moving after each research bump. This is
  an intentional planning-policy change, not decision-preserving caching; no
  faction-wide compulsory opener or unconditional whole-game route is imposed.
- Existing conservation masks apply to roots, funding and continuations. No new
  resource exchange ratios, fixed opener or fictitious future rewards.

## Computation and limitations

`PaiaPlanTeacher` evaluates goal continuations together. Identical **full action
prefixes** share native state generation and contextual ranks. Different histories,
opponent RNG streams, goal-completion flags and conversion commitments are not
merged. Same two-income horizon, same192decision cap, same existing endpoint utility;
incomplete branches have no numeric value. Native independent/shared parity is tested.
No persistent database or cross-game cache. If every sampled route starts with the
same action, skip forecasts that cannot change this action; do not claim their
future was evaluated or achieved.
Continued decisions log their original forecast root and do not claim a new
forecast utility. This avoids recomputing all long plans after each small action.
Reactions to unrelated newly available opportunities within a round are not
exhaustively replanned; evaluate this tradeoff in actual games before promotion.

`PaiaReplanTeacher` is the matched control: the same candidates, funding,
conservation, exact prefix sharing and forecast horizon, but it reconsiders plans
at every actual action. Select it with `--planning-mode per-action`; the existing
default remains `--planning-mode goal-continuation`. Records use distinct policy
identities and manifests record the mode. Neither is promoted automatically.

`OpeningPlanTeacher` (`--planning-mode opening`) is a separate opt-in candidate.
It keeps `PaiaReplanTeacher` main-action behavior but compares **every legal starting
mine** by native continuation through R1 play and R2 income. It reuses the existing
two-income horizon,192decision cap, deterministic-random opponent forecast,
context policy and endpoint utility. No recursive full-plan search during that
forecast, fixed preferred sector, new income multiplier or mine-count quota.
Equal forecast utilities retain the prior local placement preference. Incomplete
forecasts have no numeric value; an incomplete control preserves old ranks.

Opening audit records distinguish new R1 board colonies from remaining mines
after upgrades, preserve actual reconstructed R1/R2 income and list which starting
sites gained neighbors in the sampled setup. These diagnostics add no score.
Opponent placements/charging are native hypothetical actions, not promised help
or adversarial isolation testing. This is **one sampled early continuation**, not
the best possible opening, two full played rounds, or predicted final VP. Actual
main-action replanning may choose a different continuation after placement.

`EconomyFirstTeacher` (`--planning-mode economy-first`) retains its opt-in mode
name from the113VP review, but no longer forces Hadsch to catch up to Economy4.
The 2026-09-14 spectator review supersedes that unconditional priority: research
must compete in the current position, including when another track is already
developed or the final round has no further income. Below4 it now uses the same
contextual competing plans as `OpeningPlanTeacher`, without a new round cutoff,
track penalty or forced Gaia/AI response. Economy routes remain eligible and may
still win. Opening comparison, native conservation and other factions are unchanged.

When that parent would take Economy5 before R6, compare taking it now, after the
next income and after R6 income. These alternatives use **native terminal VP on
both sides**, common deterministic-random opponent streams and the unchanged192
decision cap. An incomplete control preserves the original action; an incomplete
alternative is unknown. Equal terminal scores prefer later income. Early5 may
still win through actual payout use or a race; Science5/other tracks are not
delayed by this filter. Forecast continuations are contextual, not recursively
replanned, so a sampled terminal score is not a guaranteed result. No new credit
surplus definition, resource prices, default promotion or training is included.

This is adapted from the previously isolated `HadschPlanTeacher` staging, with
current cache/conservation and new paths. The legacy staged files are preserved.
`HadschPlanTeacher` retains its Hadsch-only compatibility surface; the new Paia
class supports both existing target factions.

A first Xenos140 root99 probe (before the later candidate-fallback correction)
selected the same first federation and took92.416s. Shared steps1069 vs1603
independent equivalent prefix steps. **This is not proof of improvement or
completion.** A subsequent600s diagnostic cutoff interrupted a game; that budget
was not an approved teacher performance criterion or a completed quality test.
The evaluator itself has no wall-clock cutoff. Full-game performance and the
three-federation outcome must be measured; do not train/promote based on unit tests.

## Verification / local evaluation

```sh
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  conditional_plans.test_teacher conditional_plans.test_paia \
  conditional_plans.test_forecast conditional_plans.test_native test_live_replays -v

PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  conditional_plans.test_economy_first conditional_plans.test_economy_first_native -v

PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m conditional_plans.evaluate \
  --specs /path/to/specs.json --output gaia-rl/runs/new-paia-evaluation
```

The evaluator freezes source hashes and records real actions. Same setup/seat and
opponent seeds as prior runs enable paired comparisons. No policy learning occurs.
Each actual action produces an immutable, local compressed prefix plus atomic
`live-N/index.json`. Running/failed prefixes omit final scores and cannot pass the
completed replay validator. This local recording does **not** mean browser live
viewing or public transport has been implemented/deployed. Playback-follow choice
is pending user input; preserve completed publication validators and existing UI.
Completed batches can be passed to the existing `simulate.py publish --run ...`
path after validation; the evaluator itself does not deploy or restart services.
