# Cycle 072 — ships_fix vs ships_fix_label, full game, fresh seeds — null run (B arm played A's code)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-cap20.json` — ships_fix, the B arm of 071.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-label-cap20.json` — intended as A plus
label_value (the guide names the round-1 openings and their order; among the guide openings whose forecast
completes, the comparison value picks the one to follow; the guide order breaks ties, the remembered label is kept
only while no other guide opening forecasts higher, no plan outside the guide list is taken). Queued by the user
(2026-10-18 "제안대로 해봐") after 068 p001 Geodens kept the remembered 1AC+2M plan at 279.8 against the guide's
own PI opening at 339.7.
6 fresh seeds (geo-quartet-748492 … 756394) × 2 seat-swapped games, agentmaco, commit e85ebd4, all six rounds,
2 h 52 min wall time. Result: lab/results/072-ships-fix-label-full.md.

Adoption condition set before the run: charges positive → propose label_value as well (on top of a ships_fix
decision from 071, which failed its own condition).

**What the run measured: nothing.** The B factory `guide_r1_charge3_lf_more_vm_lf_ts_ships_fix_label` set
`_guide['label_value'] = True` but never called `install_opening_label()`, the function that puts
`guide_label_forecast` on `planning.select_forecast`. The flag is read only inside that hook, so with the hook
absent the B arm ran exactly the A arm's code. Checked three ways:

- Factory at runtime: `planning.select_forecast._opening_label` is False after building the B teacher, while
  `_guide['label_value']` is True.
- Round-1 upgrade targets (`upgrade_targets.py --rounds 1-1`): every faction's round-1 path (TS → RL → AC / PI,
  tiles, Economy placements) is the same in A and in B in all 12 games, pair by pair.
- Three of the six pairs (p000, p001, p004) are identical in all four seats through round 3 (charges equal to the
  decimal); in p003 the only round-1 difference is the order of two Terrans moves (power action 3 then Gaia
  forming vs the reverse, same inventory at the pass). That is the same drift seen in 068 (same code, same seeds,
  4 of 12 games moved ±5–50).

The numbers below are therefore the same code against itself and read as a second drift measurement, not as a
label_value result.

**Charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5)

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 156.4 | 160.3 | +4.0 | [−0.9, +8.9] |
| Taklons | 6 | 144.1 | 136.4 | −7.7 | [−18.8, +3.4] |
| Terrans | 6 | 163.4 | 166.1 | +2.8 | [−10.5, +16.1] |
| Xenos | 6 | 133.5 | 139.8 | +6.4 | [−10.5, +23.2] |
| **All** | 6 | | | **+1.3** | [−4.5, +7.2] |

Per pair B−A (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | 0 | 0 | +7 | +6 | 0 | +11 |
| Taklons | 0 | 0 | −11 | −9 | 0 | −27 |
| Terrans | 0 | 0 | +5 | +26 | 0 | −13 |
| Xenos | 0 | 0 | −14 | +27 | 0 | +25 |
| Pair mean | 0 | 0 | −3.1 | +12.4 | 0 | −1.3 |

**Final VP** (not the verdict measure): All +0.8 [−7.5, +9.0]; Geodens +3.8, Taklons +1.3, Xenos +3.0, Terrans
−5.2. Per pair: p000 and p004 all zero; p001 Terrans −3 (identical through round 3, so a round 4–6 drift);
p002 Tak −11 · Ter −16 · Geo +4 · Xen −15; p003 Geo +17 · Ter +17 · Tak +20 · Xen +6; p005 Ter −29 · Xen +27 ·
Geo +2 · Tak −1. Seat-average final VP A 80.0 → B 80.2.

Drift size from this run, for later reading of 6-pair results: with identical code a single seat can move up to
±27 charges in rounds 1–3 and ±29 VP at the end; a pair mean moved up to ±12 charges. The CIs of a 6-pair
A/B already contain this, but single-pair stories (one seat −80) should be read against it.

Rounds 1–3 research and action counts (`research_counts.py`, `action_counts.py`, six seats per arm) differ by at
most two per cell between arms (Geodens Nav 2 → 0, Taklons Economy 7 → 5, Xenos Build 14 → 12), as expected.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships_fix | 1602 | 12.22 s | 17.75 s | 20.43 s | 48.2 s |
| B (same code) | 1672 | 11.91 s | 17.08 s | 20.45 s | 47.2 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1246 vs 1290.

**Fix (this cycle, commit with this document).** `guide_r1_charge3_lf_more_vm_lf_ts_ships_fix_label` now calls
`install_opening_label()` before setting the flag, with a docstring note; a unit test builds the factory and asserts
the hook is on `planning.select_forecast` and the flag is set (`test_ships_fix_label_factory_installs_the_forecast_hook`).
The existing unit test for label_value called `guide_label_forecast` directly, which is why it passed without the
factory ever installing the hook. The `switched` count the queue note asked for cannot be read from the run folder
either: `decisions.jsonl.gz` carries step, seat, arm, timing and search counters, not the opening status.

Reading: 072 is void. label_value has not been measured; nothing changes in the base stack (vm_lf_ts_ships),
nothing to deploy. The proposal, pending the user's decision and not queued: rerun ships_fix vs ships_fix_label
with the fixed factory on fresh seeds (6 pairs, full game, same measures), once 073–075 have finished so the queue
order stands. Because the 071 decision kept ships_fix out of the base stack, the user may prefer to put
label_value on the base stack directly (ships vs ships + opening_label + label_value) — the 066 ships_label
comparison was the plain label rule without the value tie-break, so that would be the first measurement of
label_value anywhere.
