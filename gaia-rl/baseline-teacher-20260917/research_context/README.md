# Contextual research candidate (two factions, no fixed universal track order)

Approved2026-09-11: user asks to continue after noting that a wide resource engine
can favor Science, Navigation or Gaia depending on map/faction. Preserve the
completed integrated teacher/control and all historical data. New sibling owns
only research ranking refinements and its comparison; no rules/rewards/UI/PPO edits.

## Decisions / alternatives

- Reject a blanket Science penalty or randomized track balancing: diversity itself
  is not success. Replace Science's duplicate resource+research bonus with a single
  discounted usable-knowledge stream, remaining-track cap and material-capacity
  multiplier. Costs of paid4knowledge advances are separate from free tile advances.
- Science4->5 compares immediate9knowledge with lost recurring4knowledge through
  the same function. Existing printed track VP/actual advanced-tile preparation
  terms retained. This is an estimated opportunity value, not a claim all future
  research can be executed. No fixed stop at3/4 regardless of other conditions.
- Replace regular-only one-step construction estimate for Navigation/Terraforming
  with funded ordinary/Gaia destination cost savings, discounted second target.
  Navigation includes current ship suitability and Gaia reach. At0, look ahead to2
  only with enough current+one-income knowledge (4 when first advance comes from
  an upgrade, otherwise8); no unconditional rush to2.
- Gaia opportunity requires a free former (prospective unlock included), enough
  active tokens, reachable unreserved Transdim and mine stock/ore/credits. It uses
  following-round Gaia/mine bonus and Gaia final goal/active tech8. Temporary power
  scarcity and delay matter; no round6 promise of ordinary next-round conversion.
  Additional tokens/6->4 power cost change can make later Gaia steps useful.
- Last-green direct5th-level research considers currently legal advanced choices
  and covered tile loss, capped opportunity cost8; Terraforming5 replenishment
  exempt. No hard ban or automatic advanced acquisition. Free conversion funding
  and general advanced-vs-action priorities remain a separate unsolved problem.
- Faction differentiation uses actual Xenos/HH home type, mine/TS/RL/academy income,
  starting tracks and PI income through existing engine-matched helpers. Neither
  is assigned an invented fixed opening. Other16 factions' near-fixed strategies
  are NOT implemented or claimed validated in this scoped candidate.

Sources: supplied B03 science timing/knowledge/stop criteria, B15/B17/B19 faction
context, Lost Fleet LF03/LF04 map/ship alternative routes and latest user correction.
Engine research data loaded by existing helper; no external rule changes.

## Forecast limits

One-income affordability, discounted streams/at most two independent destinations,
not exact multi-turn funding or competition search. Resource caps, unknown leech,
free future tech advances, full Gaia-return/order timing are not simulated. Galaxy
and ship opportunities are proxies; only native candidates authorize real actions.
Base action-type preferences still exist: this change does not solve every failed
advanced-tech choice. Coefficients fixed before fresh-map outcomes, not optimized.

## Checks and preregistered fresh comparison

14new tests +56 preserved tests =70 passed before rollout. Tests include map-driven
Science/Navigation/Gaia preference changes, poor-vs-strong material engine, no late
income, excess knowledge/room, level5 lost income, funded Navigation2 preparation,
Gaia power/former/range/cost requirements, next-round goals, last-green opportunity,
paid vs free advances, deterministic rankings and unchanged snapshots.

Select first two seeds in `research-context-20260911-fresh-N` containing both Xenos
and HH by INITIAL SETUP METADATA ONLY (no policy game/score filtering): N10 and93.
Specs saved in fresh_specs.json. Four matched pairs (two maps x two focal factions),
other3players remain random. Control is unchanged IntegratedTeacher, NOT the older
economic teacher. Record all outcomes, no retuning/promotion during the comparison.

```sh
PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest research_context.test_teacher integrated.test_boosters integrated.test_teacher economy.test_teacher federation.test_teacher
gaia-rl/.venv/bin/python gaia-rl/experiments/research_context/evaluate.py \
  --specs gaia-rl/experiments/research_context/fresh_specs.json \
  --output gaia-rl/runs/research-context-v1
```

Historical integrated manifest source hashes/native/runtime pinned. New source
snapshot and exact map specs stored in run. Compare scores, completion, research
rounds/final tracks, advanced acquisition, federation/cost metrics. Small sample
and random opponents cannot validate general strength. No PPO training or public
replay publication occurs automatically.

## Result: research-context-v1 (not promoted)

8/8 complete in114.214s. Four paired focal scores: Xenos78→102,87→87;
HH58→75,119→103. Overall85.5→91.75 (2wins/1tie/1loss). Xenos mean82.5→94.5;
HH88.5→89. Advanced acquisition0→1;Nav2+0/4→2/4;formations7→8;6creditTS7→4;
3ore-stepbuilds3→4. No TF Mars underpayment observed here; known engine bug not fixed.

Mean final Science1.75→0.25,Nav0→1.5,Terraform3.25→3,AI1.25→2,Gaia0→0,
Economy3.75→3.25. Control Science concentration was ALREADY much lower on these
fresh maps than prior8-game sample. Candidate may now undervalue Science (no early
Science in4games) and loses16VP forHH93; no automatic strength/learning promotion.
Gaia opportunity is unit-tested but no actual Gaia track selection occurred in
these full games. Fixed18faction openings and conversion/advanced ranking remain
outside this research-only patch.

Audited8 replay scores/steps/event offsets,48 actual pass VP deltas and all
federation counts; pinned source/native/runtime guards pass.70 tests passed before
rollout. Post-run controlled resource-rich/Scienceadvanced20 fixture ranksScience
first (7.595 vsEconomy4.2), without changing weights; this rules out a hard ban,
not an assurance of proper Science choice in competitive full games.

Run contains manifest,source snapshots,8replays,full decision reasons,research
round diagnostics,report.json,paired_analysis.json,audit.py and
science_scenario_check.json. Follow-up should contrast Science/Gaia-favorable
scenarios and check common value scaling, not force equal track usage or retune
until these same two maps improve. No PPO training/replay publication/deployment.
