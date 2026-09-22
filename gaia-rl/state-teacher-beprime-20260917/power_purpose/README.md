# Power-purpose teacher revision (local hypothesis, not a promoted model)

User-confirmed: burn principally to claim a useful shared action before opponents, or to
reduce an oversized, slow-cycling pool. Three ore per terraforming step and an isolated
six-credit trading station should be exceptions, not routine construction.

`PowerPurposeTeacher` extends frozen action-purpose stage 3. Stage 4's ship changes are
not included, so their effect is not conflated with this revision. Scope remains Xenos /
Hadsch Hallas; other factions, PPO weights, terminal rewards, and game rules are unchanged.

- Native previews must expose a newly legal **useful shared PowerAction**, including all
  mine costs for terraforming actions. Already affordable/taken slots do not justify burning.
- Burn → loose-resource conversion chains are disfavored; other conversion logic remains.
- Keep at least four circulating tokens before round 6. This is a teacher preference, not
  an engine legality restriction. No idle burn just because there are many tokens.
- Opponent readiness (not passed, bowl III covers printed cost) gives priority. This is
  conservative: it does not model opponents' burns, Taklons' brainstone, or Nevlas' PI.
- Congestion proxy: more than eight circulating tokens, at least four in bowl II, and
  bowl II at least as large as bowl I. It earns a bonus only with a verified immediate spend.
- Other purposeful burns remain possible at lower priority. Resource usefulness still uses
  coarse shortage thresholds; this is not a complete income/charge/opponent planner.
- Three-ore paid steps get an additional 24 teacher-score penalty per step; six-credit TS
  gets 18. These experimental weights can be outweighed by exceptional opportunities.
  They are not victory-point deductions and are not claimed tuned/optimal.

Run targeted checks with:
`PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest power_purpose.test_teacher`

The ongoing `action-purpose-v1` comparison is unchanged. This package is not automatically
selected by its runner. Compare separately against frozen stage 3 before training/promoting.

## Replay income

`tools/replay_log.py` now recovers exact income events from the saved round-transition
states via `gaia-engine/examples/replay_income.rs`. Build first:
`cargo build -p gaia-engine --release --example replay_income`.

The helper applies the recorded transition, including income-order decisions, and only
accepts it if **all resulting state fields** match. Incompatible historical transitions
fail closed; no income is guessed from net resource deltas. Existing actions/states/VP
remain unchanged. Recovered events describe current-rule replay of that matching transition,
not a claim to possess the historical engine's discarded original event stream.

Prepare old catalog copies with `tools/restore_replay_income.py --source DIR --output NEW_DIR`.
This never overwrites or publishes originals. Applying a prepared correction to production
needs separate authorization and backups; normal `publish_replays.py` intentionally rejects
same-ID changed-payload collisions. Rebuild the helper after engine source changes.
