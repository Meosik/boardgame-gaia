# Cycle 064 — Geodens B14 opening order vs the prior 1PI+4M rule (vm_lf_ts_ships, only Geodens differs)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-geodens-prior-cap20.json` — vm_lf_ts_ships with
`_guide['geodens_b14'] = False`: the Geodens opening as it was before 2026-10-16 (guide_r1 rule 5, conditional
1PI+4M first from BGG-O2, no B14 opening order).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current vm_lf_ts_ships: Geodens
opening candidates in the uiqoo B14 order (1AC+2M → 1RL+1TS+2M → 1PI+1TS+2M), the 1PI+4M priority off
(user, 2026-10-16 "기오덴 빼줘. 자료 대로"). The other three factions share all code.
Question (user, "테스트 굴려봐"): does following the B14 article for Geodens, instead of the hand-picked 1PI+4M rule,
gain charges in rounds 1–3? Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges, read the Geodens
row first; also look at whether the round-1 academy gets finished, and errors/unsearched decisions.
6 new seeds (geo-quartet-699682 … 712850, seeds.txt extended with 710953–730948) × 2 seat-swapped games, agentmaco,
commit a6de55d, stop_round 3 (ends at the start of round 4). 1 h 33 min wall time.
Result: lab/results/064-ships-geodens-b14.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 143.4 | 158.1 | +14.7 | [−37.9, +67.4] |
| Taklons | 6 | 160.9 | 159.7 | −1.2 | [−11.9, +9.5] |
| Terrans | 6 | 171.0 | 180.9 | +9.8 | [−4.8, +24.5] |
| Xenos | 6 | 155.3 | 161.4 | +6.1 | [−44.7, +57.0] |
| **All** | 6 | | | **+7.4** | [−6.9, +21.6] |

Not significant for any row. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −66 | +44 | +47 | +63 | −26 | +27 |
| Taklons | +7 | −11 | +15 | −5 | −9 | −4 |
| Terrans | +21 | +5 | −11 | +29 | +9 | +6 |
| Xenos | +39 | −39 | −17 | +44 | +62 | −53 |
| Pair mean | +0.3 | 0.0 | +8.5 | +32.5 | +9.1 | −6.1 |

Geodens is positive in 4 of 6 pairs but swings ±66, so the +14.7 mean sits inside a ±52 interval. Taklons, which
share no changed code, are flat (−1.2 [−11.9, +9.5]); Terrans and Xenos move only through the table.

**Round-1 Geodens buildings** (`tools/upgrade_targets.py`, new in this cycle; one Upgrade list per game):

| Arm | Games | Round-1 upgrade path | Academy finished |
|---|---:|---|---:|
| A (1PI+4M first) | 6 | TS → PI in 5 games; TS → RL (Economy tile) in p000 | 0 |
| B (B14 order) | 6 | TS → RL in all 6; a second RL in p001; TS → RL → AC (Science, tile 2 AI) in p003 | 1 |

B follows the 1AC+2M target in every game but completes the academy once (p003/game-0, the pair with the largest
Geodens gain, +63). The other five stop at the research lab, which is the 1RL+1TS+2M shape with the second trading
station missing. A reaches the planetary institute in round 1 in five of six games.

Round 1–3 move counts for Geodens (`action_counts.py`, 6 games per arm): Build 18 → 10, Upgrade 17 → 19,
ResearchAdvance 24 → 17, ExploreSpaceship 8 → 9, FormFederation 5 → 2. Decisions 224 (A) vs 198 (B). B builds fewer
mines and forms fewer early federations, yet ends rounds 1–3 with more charges on average; the reference VP at the
start of round 4 is −4.0 [−11.7, +3.7] for Geodens (A 12.7, B 8.7).

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A | 888 | 12.12 s | 20.01 s | 20.24 s | 21.5 s |
| B | 847 | 12.07 s | 19.63 s | 20.24 s | 21.7 s |

No errors, timeouts or fallback decisions. Unsearched decisions 622 (A) vs 600 (B), Geodens 148 vs 140.

Reading: the B14 order is not worse than the 1PI+4M rule in rounds 1–3 and leans positive for Geodens (+14.7, 4 of 6
pairs), but six pairs cannot resolve a difference of this size against ±66 swings. The B14 first choice (1AC+2M)
is mostly not reached in round 1 — Geodens finish the lab and run out before the academy — so what B actually plays
is a lab opening, not an academy opening. The user's rule "자료대로" stands: B (the current stack) stays as the base;
no code change from this cycle, and nothing to deploy.

Candidate follow-ups (user decision pending, not queued): (a) re-run the same A/B on 12 new seeds to settle the
Geodens row (18 pairs would resolve about ±30); (b) look at why 1AC+2M stalls at the lab — one replay
(p000/game-1 seat 0, published as the watch replay, B 150 vs A 216) shows the losing shape and p003/game-0 the
finished academy — before deciding whether the B14 first choice should be gated on affordable ore; (c) move on to
the queued agenda (former_use A/B, then the "no federation" plan in the comparison set), since 063 already met the
deployment condition for the stack as a whole.
