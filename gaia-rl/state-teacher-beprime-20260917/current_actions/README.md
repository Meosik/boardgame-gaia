# Current-action adapter (2026-09-12)

`CurrentActionTeacher(stage=1..4)`, bound to the current native
environment with `.bind(env)`. Inherits the Xenos/Hadsch Hallas purpose teacher;
it is not a new trained PPO, a production bot promotion or all-faction support.

- Initial/pass booster12 selection now includes the best affordable one-step
  terraforming ore saving, using existing `resource_value` prices after known
  next income and its2credits. Full mine/remaining-step/range costs and mine
  supply are required. No usable saving means zero action value, not a forced
  tier bonus. Multiple targets never multiply the once-per-round benefit.
  Prior-round use resets; round6 pass has no future-booster value. Existing
  other-booster components and pass compression below3 stay unchanged.

- Booster12's build receives the existing mine/location/round/federation score,
  with only the existing ore-price credit for one free terraforming step. Mine
  payment, additional steps, range and natural-Gaia QIC remain in the cost.
- Same-kind conversion batches may qualify through an actual newly legal
  productive follow-up. Native resource changes and the old per-unit conversion
  penalties apply; batching itself receives no bonus. Xenos' old recovery
  exception remains for count1, not arbitrary-sized token purchases.
- Existing stage order, candidate order and 24-preview ceiling remain. Stage4
  reserves six previews for ships. More batch candidates can exhaust this budget;
  unexamined routes are not represented as bad or fully searched strategies.
- Historical teacher files, coefficients, checkpoints and replay records are
  untouched. This adapter does not add fixed booster tiers, mixed-kind conversion
  bundles, new chains or faction-specific strategies. Forecasts do not guarantee
  the target survives opponents' turns or plan future range origins/conversions.

Targeted verification:

```sh
PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python -m unittest \
  current_actions.test_teacher action_purpose.test_teacher -v
```

## Exact conversion-route scoring (2026-09-15)

For the exact `CurrentActionTeacher` class, conversion-route evaluation avoids
computing scores that its existing predicate immediately discards: passive actions
and productive actions that were already legal before the conversion. Their scores
are not reused from the old resource state. Every newly legal productive action is
still evaluated against the **complete after-snapshot candidate menu**, preserving
research/advanced-tile opportunity costs, original tie order, conversion penalties
and the inherited per-rank cache setup/cleanup. Normal root ranks remain complete.
Unknown subclasses retain full scoring because they may have mutable score effects.

This is not candidate pruning, new conversion logic or a shorter time allowance.
The native previews, preview budget, search horizon, conservation proofs and all
existing coefficients stay unchanged. Run `current_actions.test_route_scoring`
alongside the existing teacher/conservation suites. Fixed-work before/after evidence
must compare scores/reasons, commitments and native trajectories, not just the
number of decisions completed before a clock cutoff.

The standard `tools/simulate.py purpose` selects `current_actions.evaluate`.
Stage0 is `CurrentContextTeacher`; stages1..4 are `CurrentActionTeacher` with the
same cumulative purpose stages. All stages include the booster12 correction.
Stages1..4 also include the already implemented purposeful same-kind batches.
The runner preserves the old recorded-game format, audits booster12 ore/credit/QIC
debits, snapshots sources/versions and rejects source changes. Completed batches
follow the standard automatic public-replay path. Historical `action_purpose`
runners/results remain untouched; these stage numbers are not historical-score
equivalence. PPO/BC training is not started or modified by this connection.

## Conservation correction (2026-09-13)

Current adapters now block `OreToCredit` and `KnowledgeToCredit`, including
batches and QIC->ore->credit chains. `QicToOre` requires native proof that the
minimum missing ore immediately enables a paid PI/Academy, or an ore->power
conversion followed by a newly legal federation. Ordinary mine/station/lab or
speculative future-plan value is not an exception. After a chosen conversion,
only its verified continuation can be selected at the exact resulting snapshot;
other unchosen candidate proofs cannot match it. No fixed faction opening,
resource-price retuning, human-action ban, PPO change or historical-replay rewrite.

The finite blocked score is accompanied by an explicit policy marker. Planning,
funding and forecast selectors exclude that marker; a plan bonus cannot override
it. Proof needs the bound native environment; without proof QIC conversion remains
blocked. `PowerToCredit`, burning and the single-ore Xenos token-recovery exception
are otherwise preserved. Missing-resource proof is not proof of global optimality.

## Bounded scoring cache

`experiments/scoring_cache.py` caches immutable-state geometry, costs and complete
research values only inside a ranking scope (4096 entries). Planning shares raw,
deterministic context scores by the **entire** snapshot/candidate order (128
entries, 8 MiB accounted payload bytes, not a process-RSS promise). Mutable values
are copied, scopes clear on exit/exceptions, and conservation commitments are
applied outside the shared score cache. `uncached()` is the diagnostic control.
Opt-in wrappers in the older economy helpers retain their old arithmetic outside
these scopes; no search limits, RNG, weights or timeout/fallback policy changed.

```sh
PYTHONPATH=gaia-rl/experiments:gaia-rl/tools gaia-rl/.venv/bin/python -m unittest \
  current_actions.test_conservation current_actions.test_conservation_native \
  current_actions.test_cache current_actions.test_teacher
```

## Four-faction state-delta A/B experiment

The following describes the initial v1 ablation. The current B policy additionally
includes the explicitly approved B19 slice below; old recordings remain unchanged.

`current_actions.ab_match` compares the existing A policies with B's paid native
`V(after) - V(before)` ranking for Xenos, HadschHallas, Terrans and Taklons. B uses
the **same existing faction-specific evaluator as its rollout leaf**, not newly
calibrated VP weights. Xenos/Hadsch action priors only order previews; Terrans/
Taklons no longer mix the free-action penalty/funding lookahead into this rank.
Setup local rankings, source-tagged plans, conservation/Brainstone proofs, BGG R1
goals, two-income horizon and search limits remain unchanged. This does not finish
the separate macro-payment/pass-cleanup/top-10 work. Historical defaults remain A.

Each native quartet seed produces two games with complementary two-A/two-B seats.
Native factions/seats/map stay fixed; the policy assignments swap. The three
possible partitions rotate across seeds. Scores are compared **within each
faction and seed**, then averaged. Both games must finish and pass independent
native replay before entering the report. Shared timeout fallback counts and
decision times are recorded in each game's `ab-audit.json`; these are not pure B
evaluations. Sources and versions are pinned; no training or automatic promotion.

```sh
# From gaia-rl. Validates one pair without running a game or creating files.
PYTHONPATH=experiments .venv/bin/python -m current_actions.ab_match \
  --seeds quartet-pilot-20260913-27703 \
  --output runs/state-delta-ab-pilot --preflight-only
# Remove --preflight-only to run. N distinct quartet seeds produce 2*N games.
```

The clock remains 10 seconds plus six optional 120-second decisions per seat.
Large batches can therefore be expensive. No completed strength benchmark is
implied by policy/runner tests. Remaining evaluator approximations (future asset
returns, phase boundaries, faction-specific prices) are intentionally not tuned
in this first ablation.

### B19 conditional track baseline (v2, 2026-09-16)

Explicit B selection (`delta_factions`) now also enables `four_factions/track_guidance.py`:

- Navigation/terraforming state value reflects fundable mine access and ore/QIC
  savings on actual unoccupied planets. Both ranking and rollout use that value.
  Existing expansion prices/discounts are reused, not fitted or claimed as VP.
- Navigation1's continuation estimate needs knowledge for Navigation2 and a real
  destination. Ordinary Gaia pays its entry QIC. Mine supply, next permanent income
  caps and a shared budget for at most two estimated colonies are respected.
- B19 pp.10–11 proposes ordered Navigation2→mine, existing affordable expansion,
  Terraforming3→mine from levels1/2, and Economy2→expansion only if the former
  expansion options are blocked and Economy2 actually funds a destination.
  A taken target invalidates the plan, even before the research is finished.
- These proposals precede other goal families, but keep the baseline comparison,
  all ordinary/faction-specific alternatives, native payments and conservation.
  Terrans/Taklons retain their Gaia terms; their former expansion term is replaced,
  not added twice. A/defaults and local setup rankings are unchanged.

This is **not** a full guide implementation: advanced-tech/track-top races, AI/ship
and science preferences, Gaia future-value completion, income utilization, tempo,
macro financing and top10/round-end search remain separate work. No economy penalty
or universal Navigation2 mandate. Pairwise conditions are regression tests, not
yet a ranking-training dataset; no coefficient fitting/self-play training/promotion.
The runner labels this `current-action-table-vs-guide-state-delta-v2` and timed
receipts identify `B19-expansion-v1` separately from control/quick fallback.
