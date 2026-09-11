# Source-route pilot (2026-09-11)

User approved the nine new Boardlife PDF findings and another comparison. This
candidate extends frozen `research_context`, scoped to Xenos/HadschHallas. Neither
PPO weights nor the reward/encoder, UI, published replay catalog or deployment are
changed. The engine fix applies to all factions, the teacher does not.

## Rules vs strategy

- Official `docs/GP_Exp_Rule_EN_V1_Web.pdf` p14: Eclipse6-credit asteroid mine needs
  no Gaiaformer and discards none. Normal asteroid Build still needs/discards one.
  Shared BuildOptions waives only that cost for this action; ore/credit, range/QIC,
  occupancy, supply, action exclusivity and scoring retain their ordinary paths.
- Fresh native build required; both arms run this corrected engine. Old checkpoints
  deliberately fail compatibility checks. Prior `.so`/versions retained under
  `runs/source-routes-native-before/`; original teacher sources remain immutable.

## Source mapping and preregistered hypotheses

Saved PDF page numbers, not rulebook claims:
- `초반에 게임 안망하는 법` pp3–8: Gaia research -> expend a former for an immediate
  asteroid mine. Evaluate one affordable target, printed marginal mine ore income,
  current-round scoring/final asteroid goal, QIC and mine/former supply. No power,
  ore or credit requirement for ordinary asteroid mining. The *same former* cannot
  promise both an asteroid and a delayed Gaia colony: use the better forecast.
- `고급 기술타일 기반 게임 운영법` pp9–13: compare actual advanced net (timing,
  covering lost income, green token opportunity) and joint prerequisites. At most
  two upgrade steps (TS->RL->AC to bootstrap a cover tile; Mine->TS->RL otherwise),
  shared ore/credit/knowledge budget through R3 (maximum2 incomes), then maximum1
  income later. A first standard tech must be available and grant aligned/flexible
  research. Respect piece supply. Green token already held or discounted local
  federation star proxy with4 circulating tokens retained. This is NOT exact
  legal federation/path search. Missing supply/resources/taken tile abandons route;
  a ready opponent discounts multi-action races. Target selected anew from state,
  not a hard faction opening or compulsory track4 pursuit.
- `종족 별 추천 빌드` p10 and Xenos/HH sections: early QIC academy receives a bounded
  bonus only for an explored, unused Rebellion action with2QIC and an available
  useful standard tech; knowledge academy retains its material/income valuation.
- `초반에 게임 안망하는 법` pp5–8: immediate1O1QIC /1O3K /type knowledge adds value
  only if *post-upgrade* balances enable another same-round mine or paid research /
  Rebellion3QIC action. No reinterpretation of resource-action advanced tiles as
  automatic income. Exact bonus free-mine joint routing remains approximate.
- `확장판 -함선에 관한 글-` pp4–11: corrected Eclipse former-independent suitability,
  actual tech-token12 cargo and bundled standard-tech/research follow-ups; real
  TFMars/Eclipse current counters replace the old round5 scoring switch. Rebellion
  conversion distinguished by a current3QIC funding path.

Numerical pilot hypotheses, not learned/canonical values: asteroid3 base +1.5 per
future ore income +actual round VP +2 goal, minus2.5/QIC; route net divided by
`1+.4*(steps-1)+delay`, readiness1/.5, ready-rival factor.35. Track support cap14
spread over remaining levels; matching upgrade/fed support cap10; actual advanced
net receives .5 weight capped12. Optional conversion opportunity penalty capped8
only with a currently legal advanced net>=8. Immediate funding+6 (research+4),
conditional QIC academy+10, Rebellion funding conversion+8/otherwise-8. No bans.
Coefficients are frozen before the paired games; no retuning on their outcomes.

## Deliberately not claimed solved

Full multi-turn optimal plan/search, rival turn/funding prediction, guaranteed
federation legality for future builds, broad18faction opening profiles, strategic
booster early-pass races, exact federation piece composition and all public/private
resource-action comparisons remain outside this bounded four-priority batch.
Source route can still be out-ranked by fixed legacy action preferences. The route
forecast does not simulate free-mine tech rewards, future leech or arbitrary
conversion chains; native candidates alone decide legality.

## Comparison

```
PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest \
  source_routes.test_teacher research_context.test_teacher integrated.test_teacher \
  integrated.test_boosters economy.test_teacher federation.test_teacher

gaia-rl/.venv/bin/python gaia-rl/experiments/source_routes/evaluate.py \
  --output gaia-rl/runs/source-routes-v1
```

Four paired games per arm (two existing setup-only-selected maps x two factions),
ContextResearchTeacher vs SourceRouteTeacher, identical corrected native build,
seed/seat/opponent RNG streams. These maps are now previously observed, opponents
random: no independent generalization or PPO improvement claim. Persist all
failures, source/native snapshots, choices/replays, pass/formation and score audits.
No automatic promotion or historical score-equality assertion across rule versions.

## Result — do not promote

`runs/source-routes-v1`:8/8 complete,192.452s,4 equal-initial-state pairs on the
corrected engine. Control -> candidate:

| Faction | Map10 | Map93 | Mean |
|---|---:|---:|---:|
| Xenos |120 ->74|87 ->82|103.5 ->78|
| HadschHallas |92 ->137|95 ->84|93.5 ->110.5|
| Combined | | |98.5 ->94.25|

1paired win/3losses. Not overall improvement. Gaia final mean0 ->2, ordinary
asteroid mines0 ->4; Eclipse mines1 ->1; formations8 ->9; advanced acquisitions
2 ->1 (candidate only HH map10,R6,tile6). Six-credit trading stations4 ->7,
three-ore-step builds2 ->3. No Science advance in the candidate's four games.
These changes were bundled; neither the faction gain nor loss isolates one cause.

Read-only route diagnostics (no extra games) find prospective route frames:
Xenos10=8 startingR4;Xenos93=0;HH10=13 startingR4;HH93=19 startingR3. Thus the
bounded route planner did NOT establish earlyR2/3 advanced acquisition in this
sample. Gaia/asteroid valuation changes opening choices but alone do not preserve
research/income tempo. Full route action selection and cross-track opportunity
cost remain needed; don't tune on these same maps and claim generalization.

Important confound: already-known TF Mars cost validation bug recurred3times in
candidate HH games (map10 R3 5expected/3paid,R5 5/4;map93 R4 5/4), zero controls.
The137-point HH game therefore includes discounted illegal-under-rules costs.
Not repaired here (outside the approved Eclipse rule fix), not hidden as success.
No claim the HH score gain is reliable evidence of better strategy.

Verification:498 engine tests,85 teacher tests (15new+70prior),4 native environment
bridge tests pass;6 Eclipse regressions rerun after strengthening once-per-round
fixture to rule out wrong-turn/occupied-target false positives. Native50-step
smoke20focal rankings finite,immutable,accepted. Clippy passes with3 pre-existing
warnings only in unchanged ai_federation.rs; compileall/diffcheck pass. Native
source snapshot digests, all6 policy-source groups, all8 replay score/steps/event
offsets,48 pass VP deltas, all formation counts and Eclipse cost/former effects
audited.4 matched initial states and faction identities checked. Current native
binary +hash and old native binary retained. Old checkpoints intentionally reject
new engine build; no bypass/retroactive version relabeling.

Files:engine.rs +lost_fleet_spaceships.rs;new source_routes/{planning,teacher,
test_teacher,evaluate,audit}.py and thisREADME; existing plan/session records.
No PPO learning/model promotion, server/mini-PC deployment, replay publication or
other faction policy expansion. Early-pass races/full conversion planning remain
pending, not claimed part of the delivered prototype.
