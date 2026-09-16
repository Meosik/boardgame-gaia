# Hadsch Hallas: two-income research plans

User-approved scope (2026-09-12): compare research -> expansion -> advanced
technology through the next **two income phases**, with a long-term estimate
afterward. This is a separate `ResearchPlanTeacher`, not a changed game rule,
PPO checkpoint, universal faction opening, or automatic policy promotion.
`CurrentActionTeacher` is preserved as the paired control. Xenos ranks are unchanged.

## What is actually compared

- Current action choice remains a candidate. Alternative plans try Navigation2,
  Economy2/4, Science income, Gaia2 and both Gaia/range orders, Terraforming and
  AI research when the root has a corresponding legal research/technology choice.
- Gaia plans include an actual Gaia-project action, not just a free former value.
  A range/QIC plan attempts an actual Rebellion entry and3QIC technology action.
- The two highest current-valued remaining regular advanced tiles are candidate
  targets. Track4, a legal acquisition, a cover tile and a green token must
  actually coexist. A native legal federation may fund the token; its satellites
  are paid. If a rival takes the tile, that target is abandoned.
  Already legal advanced acquisitions, including Lost Fleet advanced technology,
  also have a direct acquisition plan rather than relying on the old category priority.
- A separate plan withholds Economy/Science4->5 until the next income, including
  free tile-granted advances. Immediate entry is still a candidate. This is NOT
  an unconditional late-five rule, and the hold does not apply in round6.

Every continuation runs on `Environment.fork` and subsequent native `step` calls.
Knowledge, ore, credits, QIC, power, building supply, Gaia returns, range origins,
tile covering, token flipping, once-per-round actions and income/caps are **one
shared engine state**, not additive independent budgets. No future action is
executed in the real game: only the selected first native candidate is returned.
The parent environment and snapshot remain unchanged.
Income audit uses the existing `tools/replay_income.py` exact-state/action
reconstruction and current `target/release/examples/replay_income` helper;
offline native snapshots do not append returned income events to their log.

## Forecast assumptions and bounds

- Opponents use deterministic uniform-random forecast streams, common to the
  candidate branches at a root. They consume tiles/planets/actions and receive
  income normally, but this is NOT a skilled-opponent model or a guaranteed race.
- Focal continuation uses the existing cheaper `CurrentContextTeacher`, with a
  candidate goal directing legal research, funding, acquisition or QIC actions.
  It does not recursively run this planner or the expensive conversion preview
  loop. Thus the continuation is an estimate, not the actual future policy.
- Maximum192 native decisions per branch. Stop at the action phase after the
  second income, or actual game end if fewer incomes remain. Incomplete branches
  get **no numeric value**. If even the control misses the horizon, preserve all
  current ranks. Unexamined/incomplete paths are not asserted to be inferior.
- Tail utility reuses existing material/QIC prices (fixed at the root), the
  contextual teacher's single usable-knowledge stream,0.7 material-income
  discount,0.8 charge valuation, reserve shortfall and retained technology
  estimates. Current-board final-goal standings and research-level VP are added;
  the metric implementation is checked against the36-value Rust/TS fixture.
  Economy VP-side income is included. Immediate tech rewards already earned are
  not valued twice. Actual terminal states use engine final scores only.
- Utility is NOT on the legacy action-score scale and is not a prediction in VP.
  The highest complete sampled plan selects its first candidate explicitly;
  legacy ranking breaks ties. Its displayed selection score is just an ordering
  adapter. Evaluation records retain every plan's utility, payments, incomes,
  own-action sequence, endpoint resources/tracks and selected goal.

These are source-informed candidate paths, not an implementation of every supplied
article. Full optimal sequencing, arbitrary future federation layout, expert
opponent prediction, other16faction strategies and learned PPO remain unsolved.

## Verification and comparison

```sh
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  research_plans.test_teacher research_plans.test_native research_plans.test_evaluate

gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py research \
  --specs /path/to/hadsch-specs.json --output gaia-rl/runs/new-research-comparison
```

Specs have `seed`, `faction: "HadschHallas"`, `seat`. Comparison variants0/1
both use purpose stage1 (booster12 + purposeful batches);0 is the unchanged
current teacher,1 adds research plans. The export-compatible `stage` field names
the comparison variant, with `purpose_stage: 1` saved separately. This is not an
old purpose-stage ablation. Both arms preserve native/source manifests, exact
booster debit audits, decisions and replays. Completed batches use the existing
automatic public-replay pipeline; no learning or game-server restart is invoked.

## Result: research-plans-20260912.q6I0Swor

Four games completed on the frozen current native engine in2532.029s. Each pair
has identical initial state/seat and opponent RNG initialization. No outcome-based
retuning, policy promotion or PPO training was performed.

| Map | Current -> plan VP | Federations | Advanced tiles | Unfederated buildings / total |
|---|---:|---:|---:|---:|
| Previously observed HH90 |90 ->135|1 ->2|0 ->2|8/12 ->4/13|
| First HH setup in fresh namespace |92 ->106|2 ->1|0 ->0|5/13 ->4/8|

Mean91 ->120.5 is encouraging but only two maps against random opponents, not
evidence of human-level strength or generalization. The original90-point control
reproduces every saved frame/event exactly. The135-point game acquires tiles21
and10 only in rounds5 and6, keeps Economy4, and still ends at Navigation0. The
106-point game also stays Navigation0, takes Economy5 in round5, forms only one
federation and acquires no advanced tile. Thus better research/expansion sequencing,
early advanced acquisition and multi-federation planning are NOT solved.

All337 sampled forecasts at30 real planning decisions reached the common horizon;
21 first actions changed from the contemporaneous current-choice control. Audit
checks actual selected actions, exact expected income rounds, all four completed
replays, source snapshots and native/runtime identity. Comparison utilities are
still heuristic and plans can change between actual turns. The42-minute batch
also makes this an expensive offline experiment, not a production-latency claim.

Verification:179-test regression pass, affected final-revision24-test rerun,
one additional early two-income native test and final22-test ranking/export rerun
(overlapping counts, not a combined distinct-test total). No engine/frontend source
changes required by this experiment. Evidence includes comparison-audit.json,
plans-{0,1}.json, regression/native logs and frozen source manifests in the run.

Automatic replay publication completed without restarting the game service:
`eval-3d3fad9ddba52bf4-{0,1,2,3}` = current90, plan135, current92, plan106.
Both candidate games are listed as `ResearchPlanTeacher` at
https://shgaia.com/?aiReplay=1. Existing models and historical replay payloads are
preserved. These are new teacher evaluations, not newly trained PPO checkpoints.
