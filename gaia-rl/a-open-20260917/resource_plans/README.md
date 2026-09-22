# Conditional Xenos resource plans

Approved 2026-09-12: fix missing resource preparation and paid follow-ups, **not a
fixed faction opening**. This opt-in candidate is evaluated on Xenos first.
`CurrentActionTeacher` and the Hadsch `ResearchPlanTeacher` remain unchanged
controls; no rules, PPO rewards/weights, UI or production defaults are changed.

## Comparison, not compulsory moves

- Planning runs at action-phase construction, conversion, ship and federation
  decisions, even before a research advance or Academy is affordable.
- Ordinary current play/expansion competes with research (including a preceding
  TS/lab), both Academies, actual available ship entry + use, and available advanced
  technology routes. No faction-wide order, mandatory Navigation2/Academy/Rebellion,
  credit:ore target ratio, or guide-compliance bonus is used.
- Each currently legal federation cargo/supply choice gets its own paid first
  action plus ordinary, Academy, and available Rebellion continuations. One shape
  per token retains the established ranking; **future multi-federation geometry
  and global optimal shape search are not implemented here**.
- Missing building/research resources can be supplied by native free actions
  (including burn -> ore), real resource actions, a TS/lab prerequisite, or a
  fundable next-income reservation. Passing is only a competing forecast, never a
  faction requirement. Existing construction-cost helpers include actual neighbor
  discounts. Xenos cannot invent Hadsch's credit conversions.
- Ship usage already taken by an opponent is not reserved or awarded. Forecast
  opponents play real legal turns, so entry can fail to yield the intended action.
  Acquired/covered tiles, actual cargo, green tokens, building supply and once-per-
  round actions continue to be enforced by the engine.

## Bounds and evidence

The common `research_plans.forecast` has optional continuation/acquisition hooks;
its default Hadsch path is preserved. All sampled sequences use native fork/step,
two actual income transitions (or real game end), a shared paid resource budget,
and the existing endpoint utility. No new leaf resource-price coefficients were
introduced. The first action alone executes; every real decision replans from its
new state. This can still change plans across turns and is not perfect foresight.

Funding search checks at most32 native forks per call and two free actions per
path. At a root, up to3 distinct verified funding first-actions are compared over
the full horizon. The main forecast limit remains192 native decisions. Limits are
recorded as unknown/unsearched, not proof that omitted routes are bad or illegal.
Incomplete forecasts have no numeric value; an incomplete ordinary control
preserves all existing ranks. Audits keep all sampled funding alternatives,
costs/incomes/end resources, node-limit hits and selected first actions.

Opponents use the inherited deterministic uniform-random forecast, **not a strong
opponent model**. Beyond the explicit horizon, income/stock/tech value is still the
existing heuristic. Credit spending, future leech, wider conversion chains and
plan stability remain imperfect. Adding this candidate is not a measured strength
improvement or permission to promote it automatically. More planning roots also
make this more expensive than the Hadsch research-only adapter.

```sh
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  resource_plans.test_teacher resource_plans.test_native resource_plans.test_evaluate \
  research_plans.test_teacher research_plans.test_native research_plans.test_evaluate

# When running a complete matched-game evaluation (automatically publishes replays):
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py resources \
  --specs /path/to/xenos-specs.json --output gaia-rl/runs/new-xenos-resource-comparison
```

Specs contain `seed`, `faction: "Xenos"`, and `seat`. Variants0/1 both use purpose
stage1: unchanged current teacher vs this resource-plan candidate. Native/source
and fixture snapshots, both outcomes, costs and replay audits are retained. Local
decision-prefix regression forecasts are not new completed games and do not
publish partial replays. The existing user-deferred naming deployment is separate.

### Conservation (2026-09-13)
Both current control and planner inherit the current-adapter conservation policy.
Funding paths and all forecast continuations honor it; an old high-utility plan
cannot re-enable forbidden liquidation. Earlier completed75/126/87 games are
historical outcomes, not results of this correction. Rerun matched arms before any
strength comparison. Native two-income horizons and existing search caps remain.
