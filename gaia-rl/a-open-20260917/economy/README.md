# Economic teacher trial (Xenos / Hadsch Hallas)

User-approved first step: improve construction economics, starting placement and
neighbor/fleet opportunities, then compare eight games. **No BC/PPO training**, rule,
reward, encoder, production AI or replay UI changes. Federation lookahead is the next
separate step, not implemented here.

The original top-level experiment files, models and 24 replay records are preserved.
This nested directory does not change the original pilot's top-level Python-file hash.
New artifacts receive their own source fingerprint and a new output directory.

## Run

From the repository root:

```sh
PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest discover \
  -s gaia-rl/experiments/economy -p 'test_teacher.py' -v
gaia-rl/.venv/bin/python gaia-rl/experiments/economy/evaluate.py \
  --output gaia-rl/runs/economy-teacher-new
```

Output must not exist. Runtime/engine fingerprints must match the original pilot.
Baseline diagnostics are extracted from its verified teacher replays, checked against
saved metadata. Revised games use the exact same seeds/focal seats and independent
per-opponent RNG streams. Different focal actions can still change opponents' legal
choices and game lengths; this is matched setup, not identical opponent trajectories.
Failures remain in reports and invalidate claims based only on completed games.

## Changes and interpretation

- Supported construction cost estimates distinguish 3/6-credit trading stations,
  normal mine/terraform costs, research cost per step, navigation/active range tile,
  booster/Twilight range, power-action free steps, TF Mars activation, Eclipse asteroid
  activation, and the actual activation costs of free trading station/research lab actions.
- Costs subtract experimental scarcity-sensitive ranking penalties; actions stay legal
  candidates and expensive moves are not categorically banned. Resource/VP rewards and
  the original teacher's technology/round scoring priorities remain unchanged.
- Starting placement rewards **marginal** accessible home/one-step planets at board-path
  distance 1–3, rather than recounting opportunities covered by an earlier mine. Board
  paths use the pinned engine's board-only BFS, not straight-line shortcuts through gaps.
- Neighbor evaluation distinguishes own and opponent structures, distinct rival owners,
  possible future upgrades, circulating tokens and remaining rounds. It is potential,
  not a promise of future charging (opponents may pass or build elsewhere).
- Fleet proximity is conditioned on faction, available slots, VP/QIC access and useful
  resource/planet paths. Xenos/Rebellion and Hadsch Hallas/TF Mars or Eclipse are
  source-informed tendencies, not mandatory openings. Poor funding discounts future
  possibilities; this is not a full multi-turn affordability planner.
- Expansion opportunities currently focus on home/one-step colored planets. Gaia and
  asteroid construction still have cost estimates but no new equivalent opportunity
  bonus. Pass timing, full advanced technology valuation, strategic federation cluster
  planning and neural input features remain outside this iteration.
- Weights are hypotheses, not calibrated strength claims. The four maps were already
  observed, and opponents are random; results are not independent generalization evidence.
  No repeated weight tuning on these games.

## Diagnostics

Each `game-N.json` records selected focal decisions, estimated costs and reasons,
starting-placement neighborhoods, expensive trading/terraform frequencies, construction
neighbor presence and federation satellites/power before/after. `report.json` aggregates
by faction and retains completion counts. Post-federation power includes token rewards.
Direct resource debits are compared against snapshots for unambiguous construction
(no tech acquisition rewards). Metrics count actions, not guaranteed income or VP value.
Replays are retained in the run directory; not automatically published to the UI.

## Existing engine discrepancies exposed by debit checks

These were **not changed** in this experiment:

1. A raw `Gaia` planet with `is_gaia_formed=false` does not pay the entry QIC in the
   current engine; formed Gaia does, except owned former-converted Transdim. The cost
   estimator mirrors this pinned behavior rather than silently changing rules.
   Observed original teacher game 0, decision 15, Build (-6,2): one range QIC, no entry QIC.
2. TF Mars validates the 3-credit activation and the 2-credit mine independently. With
   only 3–4 credits, application saturates to zero instead of rejecting the combined
   5-credit cost. Ranking retains nominal 5-credit cost, while diagnostics explicitly
   record underpayment in `engine_cost_anomaly`. Unknown debit mismatches still fail.

`economy-teacher-v1/failure.log` and `v2/failure.log` retain the baseline audit failures
that identified these mismatches. Neither reached revised-game evaluation. Regression
coverage distinguishes these discrepancies from intentional discounts/free actions.

## First completed result — `runs/economy-teacher-v3`

15 targeted tests pass. All eight revised games completed in ~56 seconds after the
baseline audit, without training. Source fingerprints at start/end match. Eight saved
replays' frame/log boundaries and scores were independently checked after export.

| Metric (4 games per faction) | Xenos original → revised | Hadsch Hallas original → revised |
|---|---:|---:|
| Mean VP | 76.50 → 84.00 | 79.25 → 86.00 |
| 6-credit trading stations / all paid TS upgrades | 1/15 → 1/22 | 7/24 → 1/23 |
| Builds paying 3 ore per terraforming step | 13 → 2 | 10 → 3 |
| Construction actions with opponent neighbor | 40/55 → 56/80 | 46/69 → 56/76 |
| Starting mines with existing opponent neighbor | 5/12 → 5/12 | 3/8 → 4/8 |
| Federations | 4 → 6 | 6 → 4 |
| Satellites per federation (aggregate mean) | 5.00 → 5.33 | 3.67 → 4.00 |
| Post-federation circulating tokens ≤1 | 4/4 → 5/6 | 2/6 → 1/4 |

This is a positive **economic teacher** result, not proof of better PPO learning.
Total constructions increased, so report rates as well as raw counts. Neighbor rate
did not improve for Xenos (72.7% → 70.0%); the improvement is not universal. Seven
individual games improved, while Hadsch Hallas seed900 fell 86 → 77 VP. All paid
terraform builds in this small set still used 3-ore steps; the change reduced their
frequency, not the research cost per step.

Federation planning is **not fixed**: aggregate satellites per federation rose from
4.2 to 4.8, and six of ten federations still left at most one circulating token after
rewards. Total federations stayed at ten, redistributed between factions. Upgrade/
cluster preparation and waiting-versus-forming remain the next isolated experiment.

The known TF Mars underpayment occurred once in original and twice in revised games.
Raw-Gaia entry behavior is also unchanged. Interpret both arms under this same pinned
engine, not as verified rules-complete play. Fixing either engine issue requires a
versioned rebuild and a fresh baseline rather than merging incompatible results.
No policy was retuned after seeing these scores; no new model was trained or deployed.
