# Source-informed strategy integration (candidate, not trained/deployed)

User approval2026-09-11: select useful advice from supplied material and implement it
before the next comparison. Scope remains Xenos/Hadsch Hallas. Existing teachers,
models, environment/rewards and replay UI are preserved. This is not an18-faction
strategy implementation and does not claim the supplied articles are wholly encoded.

## Source → implementation

| Advice | Implementation | Limits |
|---|---|---|
| B03 technology timing / LF02–04 first advanced tile | All21 available advanced IDs mapped to immediate counters, pass scoring, event scoring or resource actions; prospective upgrade board used for counters. Actual aligned tile informs research toward4. | Not a fixed tier list; future event counts are funded growth estimates. ID18 absent in engine, rejected rather than invented. |
| B03/B19 even knowledge income | Permanent income from labs, Science academy, Science track, active tile5 and artifact3; budget realizable advances using current knowledge+up to2incomes minus selected knowledge spending. | No blind even-number reward. Unknown next booster excluded except selected pass booster. No stochastic income forecast. |
| Covering standard technology / first advanced tile | Lost future income/retained effect, knowledge-budget loss, green-token opportunity cost. Spent immediate rewards have no cover penalty. | Scalar token opportunity cost; no exact race simulation. |
| Research before construction / LF expansion alternatives | Terraforming/Navigation compare costs and availability of up to2funded regular-color targets at next level. Science/Economy compare income; level5 stops recurring income and grants immediate printed resource reward. Terraforming5 values the reserved base token; Gaia5 counts printed VP; Navigation5 uses a free-colony proxy. | One-step research + one-income affordability proxy, not full multi-turn planning; Gaia/asteroid target planning remains limited. |
| Building upgrades / user correction | InsideTS→RL federation adjustment stays0; neutral economic teacher reused with half-strength local federation preparation after HH regression. Science academy income early vsQIC late. | Prototype penalties are not hard bans or optimized weights. |
| Federation timing / B06/B19 | Compare current route with one funded new mine or upgrade and local star-route estimate; account for investment, scarce token/current round scoring, no waiting penalty inround6. | Hypothetical star routes are not validated federation routes. No exhaustive future-state search or guaranteed savings. |
| B02/LF01 power circulation | Soft reserve6early/4later acrossI/II/III for satellite/artifact/BurnPower/Gaia moves; returned federation token13 power counted; ordinary bowlIII spending recycles rather than discards. | Future Gaia returns/optional token recovery not fully forecast; terminal rounds may spend reserve. |
| Charge VP / LF exploration | Actual movable/affordable power vsVP paid, heavier scrutiny at3+VP; retain early ship-entry VP. | Two supported factions only, no brainstone/Itars/Nevlas rules. |
| Knowledge ship spending | Rebellion2knowledge action compares lost realizable advances with2credits+QIC. Xenos token recovery gets urgency below4. | Full free-action conversion-chain search remains deferred. |

Rule IDs/counters mirrored from engine.rs: tech2494–3308; income8965–9194;
research data/research_tracks.toml (loaded, not duplicated); faction scope checked.
Space/deep-space counters use engine radius2 / rotated3-hex footprint. Known raw-Gaia
and TF Mars underpayment are not changed. Numerical coefficients are explicit
heuristic hypotheses, **not VP rewards** and not proof of playing strength.

No weights have been fitted to new rollout outcomes. Half-strength federation
preparation is an explicit revision motivated by the already-observed HH regression;
future reuse of the old8evaluation setups remains non-independent evidence.

## Verification and next comparison

```sh
PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest integrated.test_teacher
# Separate next full-game comparison (not automatically run by unit tests):
gaia-rl/.venv/bin/python gaia-rl/experiments/integrated/evaluate.py \
  --output gaia-rl/runs/integrated-teacher-v1
```

The next runner explicitly selects IntegratedTeacher, not a stale baseline class;
reruns8economic controls with exact historic score/step/action equality guards,
then compares8candidate games and stores replays, technology holdings, research and
knowledge-income diagnostics. Fingerprints guard original/economic/federation/new
sources and native/runtime versions. No model promotion, PPO training or replay-list
publication happens automatically. Fresh-map/stronger-opponent validation is still
needed before learning expansion or strength claims.

Verification2026-09-11:
- Integrated23 + preserved economic15 + federation6 =44 targeted tests passed.
- Native partial smoke:40 decisions each on seed192, focal Xenos12 rankings / max49
  candidates and Hadsch Hallas9 / max50; finite rankings, unchanged snapshots and
  all selected native steps accepted. These are not completed games.
- Original/economic experiment fingerprints match the pinned historical manifest;
  all four experiment source groups unchanged across smoke; native/runtime guards pass.
- New comparison runner `--help` imports successfully; no full comparison, PPO
  training, model promotion, replay publication or engine edits performed.
- Regression checks include the future Xenos PI's reduced federation threshold,
  immediate token13 circulation recovery, actual remaining research room, and
  Terraforming/Gaia terminal rewards. Hypothetical waiting routes remain estimates.

## Booster follow-up (approved before comparison)

`boosters.py` now evaluates all14 current engine boosters, for initial selection
and next-round pass selection. B03 pp12–16 motivates early income/late scoring,
knowledge budgets, scarce circulating tokens and usable range destinations. IDs
come from current engine income/pass/special functions, NOT old base-game article
numbering: current booster5 is immediate Gaia,8 is range+3,12 only2credits in engine.

Components are logged in each selected decision reason: resource scarcity after
known income, marginal realizable research, usable charge/new-token reserve,
current-board next-pass points, one funded build/upgrade's pass/next-round-goal
synergy, best usable special action. Range retains terraforming cost, is not stacked
with a shovel action, and counts only one use (build/Gaia/ship). Immediate Gaia
requires a free former and reachable unreserved Transdim, not power payment.
Starting selection uses round1; a round5 pass values round6, a round6 pass no new
booster. Pass scores monotonically compress below3 to avoid comparing future
booster VP as if immediately gained against productive main actions.

Limits: one-action growth estimate, no full opening sequence, exact income-order/
resource-cap/cleanup-Gaia-return/opponent competition forecast, or strategic early
pass timing. Ordinary upgrades are resource/stock projections, not native-validated
future tech choices. Future passive leech is unknown. Only two factions supported.
56 tests passed before full comparison (12 new booster cases); see task/session
record for run authorization. Existing44-test evidence above is the earlier stage.

## Still deferred

- Other16factions and their individual resource/ability strategies.
- Exact future-state federation route/competition/charge/gaia-return search.
- Complete free-action multi-conversion funding chains, map preemption value and
  final-ranking marginalVP; full ship/artifact/standard-tech strategy audit (including
  detailed standard-tile charge valuation). Navigation5 placement is only a colony proxy.
- Faction-only replay filter: interpretation and UI not approved; no frontend changes.
- The separately remembered tier-list image has not been uniquely identified. Supplied
  B03 tile-by-tile analysis was used; no invented tier mapping or all-PDF coverage claim.

## First full comparison: integrated-teacher-v1

2026-09-11 approved comparison:16/16 complete,162.922seconds;8 unchanged economic
controls reproduce historical all-player scores,steps,focal actions exactly.
Xenos mean84→107;HH86→101.75;7/8 pairs improve (HH249103→97). No retuning occurred.
These are observed maps/random opponents and teacher policies, NOT trained PPO.

Booster special uses2→12;unused owned action-booster rounds4→0;booster-only pass
VP108→100. All96 passes reconcile actual VP deltas against old-booster/advanced
pass/economy income; new-booster selections validated. No isolated booster causal
claim: research/federation/other strategy terms also changed. Formations10→15,
satellites per formation4.8→3.867 (total48→58);3+formations0/8. Nonfinal low-reserve
formations9/12 remain. Inside-power upgrades21→3;6-creditTS2→5;3-ore-step builds5→2.
Known TF Mars underpayment2→2 unchanged, provisional results.

Advanced acquisitions1→0. Native reproduction of the8 stored integrated games
finds73 legal advanced-choice decision points across7games, but other choices win
ranking (23free conversions,13standard-tech actions,8upgrades,8research,6power,
15others). Availability is not the bottleneck in those7games; relative action
priorities and acquisition funding/green-token opportunity planning remain weak.
This is NOT proof every available advanced choice should have been taken. Blind
advanced bonuses/retuning to these maps would be misleading. No model promotion.

Full decisions,16replays,replay/pass checks and advanced availability/ranks are in
`runs/integrated-teacher-v1/{report,paired_analysis,advanced_analysis}.json`.
Audit scripts and all four source groups are archived in the run; source-snapshot
hashes match manifest, so subsequent revisions need not erase this experiment.
