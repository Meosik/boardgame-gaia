# Soft three-federation pilot

User-approved test, 2026-09-11: Xenos / Hadsch Hallas aim for three or more efficient
federations, not a hard minimum. Existing-federation trading-station -> lab upgrades
remain neutral. Prefer new useful federation power outside existing federations;
retain income/technology/PI/round scoring exceptions through baseline scoring.

This is a **teacher-only** experiment, not PPO training or production deployment.
Existing economic/base teachers, engine, encoder, rewards and checkpoints are pinned
and untouched. New sibling folder preserves their source fingerprints.

## Preregistered hypothesis (before running)

- Below three formed federations: full preparation weight; after three:0.35.
- Satellite final goal:0.35 throughout (not a claim that fewer federations always win).
- Positive power inside an existing federation:-8 per additional power. Lab delta0
  receives exactly0 adjustment; income/technology rewards remain in the base score.
- New power outside:5–12 per power depending on nearby uncommitted buildings, +12
  crossing a local6/7-power proxy. Initial placement half weight. Radius3 uses board
  distances, not a validated federation route. No multi-round search/partition solver.
- New mines adjacent to own existing federation cannot count as new federation power.
- Formation: +12 goal weight, -3 per actual satellite in addition to baseline-2;
  before round6, -5 per circulating token below4 after payment, before token reward;
  -2 per excess committed building power. Conservative reserve proxy deliberately
  does not predict federation reward tokens or later income.
- Values are arbitrary fixed test hypotheses, not VP estimates. No candidate pruning
  or injected illegal actions, no hard minimum/terminal penalty. No retuning after
  observing the matched comparison.

Native structure power and XenosPI threshold mirrored for these two factions,
including active technology6. Count token ownership including gray minus Terraforming5
bonus; results independently count actual FormFederation decisions. Other factions,
notably Ivits, are out of scope. Research-before-build changes remain separate.

## Run

```sh
PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest federation.test_teacher
gaia-rl/.venv/bin/python gaia-rl/experiments/federation/evaluate.py \
  --output gaia-rl/runs/federation-teacher-v1
```

Eight matched pairs on the already-observed four seeds/two focal factions. Opponent
RNG identical to previous economic pilot, random policies; trajectories diverge after
a changed decision. Both arms rerun; control scores/steps/actions must exactly match
saved economic-teacher-v3. Source/native/runtime hashes checked before/after. Each
failure and each replay retained. Report means, completion,3+ rate, satellites,
power reserves and already-federated upgrade rates; do not judge just federation count.
Replays stay in run directory; UI publication/model promotion not automatic.
Pinned raw-Gaia and TF Mars cost discrepancies remain (see economy/README.md).

## First result — federation-teacher-v1 (no retuning / no promotion)

All16 games completed in104.88s. All8 controls exactly reproduced saved economic
pilot scores, steps and focal actions.21 tests passed (6 new +15 economic); all16
replay frame/log boundaries, metadata scores and per-frame inferred formation counts
matched actual FormFederation actions. Source/runtime/native fingerprints unchanged.

| Four paired games per faction | Xenos control → trial | Hadsch Hallas control → trial |
|---|---:|---:|
| Mean VP |84 →95|86 →81|
| Actual federations, total |6 →9|4 →5|
| Actual federations/game |1.50 →2.25|1.00 →1.25|
| Games with3+ |0 →1|0 →0|
| Satellites, total |32 →38|16 →18|
| Satellites/federation |5.33 →4.22|4.00 →3.60|
| Power-increasing upgrades inside existing federation |16 →2|5 →2|
| TS→RL inside existing federation (not penalized) |5 →3|4 →1|
| Builds absorbed into existing federation |5 →0|3 →1|
|6-credit paid TS / all paid TS |1/22 →1/22|1/23 →4/26|
| Post-formation tokens≤1 |5/6 →5/9|1/4 →2/5|

Paired VP (seed192,249,497,900): Xenos96→112,74→95,89→90,77→83;
HH78→92,103→75,86→88,77→69. Seed497 has satellite final objective in both
focal-faction cases. Thus3+ rate is1/8 overall, or1/6 non-satellite cases, not a
reliable three-federation policy. Combined satellites/formation4.8→4.0, but total
satellites48→56 as formations increased10→14. Do not describe this as lower total
satellite spending. More than one federation still often empties circulation.

Interpretation: the intended location/power preference changed and Xenos improved on
all four inspected maps; HH is mixed and mean VP regressed despite more formations.
HH900 explicitly made two instead of one while losing8VP. HH249 lost28VP with
unchanged formation count. More expensive TS builds are an observed competing cost,
not an isolated causal explanation. Fewer inside-lab upgrades occurred despite zero
explicit adjustment; changed trajectories and outside-upgrade priorities can still
indirectly change lab timing. No claim that the lab exception alone is fully optimized.

Existing TF Mars combined-cost underpayment increased from2 control occurrences to6
trial occurrences (Xenos1→3, HH1→3). Raw-Gaia discrepancy also persists. Results
are provisional under the pinned imperfect engine, not rules-complete strength proof.
No generalization from random opponents/eight already-observed setups; no PPO training
or baseline replacement. Full per-game actions/reasons, replays and paired_analysis.json
remain under the run directory. UI catalog unchanged.
