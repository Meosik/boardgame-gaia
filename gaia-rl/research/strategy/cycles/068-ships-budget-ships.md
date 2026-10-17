# Cycle 068 — ships_budget re-run on the 064/066 seeds (same A/B and code as 067)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-budget-cap20.json` — A plus `opening_budget` with the ship
fix of 5e7a2bb (see cycle 067 for the rule). 068 was queued as "067 on the fixed code"; since 067 itself already ran on
ff5e54b (fixed code), 068 is an exact re-run: same six seeds (geo-quartet-699682 … 712850), same specs, same commit (lab
header says fcf9074, which only adds the 067 result files). agentmaco, stop_round 3, 1 h 34 min wall time.
Result: lab/results/068-ships-budget-ships.md.

Purpose set before reading: a second sample on these seeds, and a measurement of run-to-run drift of the time-capped search
(067 read a 12–16 charge difference between 066 A and 067 A as drift).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI | 067 B−A |
|---|---:|---:|---:|---:|---|---:|
| Geodens | 6 | 168.6 | 157.9 | −10.7 | [−38.8, +17.4] | −4.4 |
| Taklons | 6 | 148.4 | 144.6 | −3.8 | [−41.6, +34.1] | −8.5 |
| Terrans | 6 | 194.1 | 189.2 | −4.9 | [−47.8, +38.0] | −2.8 |
| Xenos | 6 | 159.4 | 140.5 | −18.9 | [−86.7, +48.9] | −24.8 |
| **All** | 6 | | | **−9.6** | [−29.6, +10.5] | **−10.1** |

Not significant for any row. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +29 | −52 | −22 | −3 | −3 | −14 |
| Taklons | +49 | −5 | +6 | −50 | −38 | +15 |
| Terrans | +13 | −81 | +21 | +34 | −2 | −15 |
| Xenos | −122 | −41 | −15 | +71 | +22 | −28 |
| Pair mean | −7.6 | −44.7 | −2.6 | +13.1 | −5.4 | −10.4 |

One pair positive (p003), five negative — the same pattern as 067 (p003 the only positive pair there too, p001 all four seats
negative in both runs, Xenos p000 the largest single loss in both: −138 then −122).

**How much the re-run moved (drift measurement).** Comparing the twelve game lines of 067 and 068 (same seeds, same code):
**8 of 12 games are identical to the charge in all four seats.** The four that differ:

| Game | Seat changes 067 → 068 |
|---|---|
| p000/game-0 | Xenos(B) 107 → 124, Taklons(B) 210 → 192, Terrans(A) 218 → 221, Geodens(A) 171 → 170 |
| p003/game-0 | Geodens(B) 186 → 159, Xenos(B) 107 → 157, Taklons(A) 136 → 133 |
| p005/game-0 | Taklons(A) 199 → 160, Xenos(B) 195 → 159, Terrans(B) 198 → 192, Geodens(A) 159 → 168 |
| p005/game-1 | Terrans(A) 202 → 206, Taklons(B) 171 → 175, Xenos(A) 191 → 186, Geodens(B) 156 → 154 |

So the time-capped search is deterministic in most games and, when one decision diverges, the rest of that game drifts by up
to ±40–50 charges per seat. This corrects the 067 reading: the 12–16 charge gap between 066 A and 067 A was not run-to-run
noise of the A arm — in 066 the B opponents played a different rule (ships_label), so every game diverged. The only game that
is identical across 066, 067 and 068 is p003/game-0 in 066 vs 067 (Geodens(B) 186, Terrans(A) 158, Xenos(B) 107, Taklons(A)
136), i.e. a game in which neither ships_label nor ships_budget changed any move; 068 then drifted on that game.
Consequence for pooling: 067 + 068 is not 12 independent pairs. Treat the two runs as one sample of 6 seeds read twice
(mean of the two: overall −9.9, Geodens −7.6, Taklons −6.2, Terrans −3.9, Xenos −21.9), not as a 12-pair confidence interval.

**Reference VP at the start of round 4** (not a verdict measure): **+2.0** [−1.8, +5.9]; Geodens +5.0 [−5.5, +15.5], Taklons
+1.2, Terrans +0.3, Xenos +1.7. The same shape as 067 (+1.6): B holds slightly more points and fewer charges at the end of round
3, the opposite of an academy-first opening that pays off in economy.

Counters A / B: decisions 866 / 860 (Geodens 184 / 210 — again the only faction with more decisions in B; Taklons 189 / 191,
Terrans 229 / 219, Xenos 264 / 240), unsearched decisions 602 / 592, errors 0, timeouts 0, fallback 0.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A | 866 | 12.35 s | 20.01 s | 20.27 s | 22.6 s |
| B | 860 | 11.73 s | 20.00 s | 20.27 s | **35.1 s** |

B's 35.1 s maximum is the same value as in 067 (within the 60 s server limit). The budget wrapper adds no time on average.

**Still not measured** (the bot cannot run python): Geodens round-1 academy count, Xenos and Terrans round 1–3 mines,
round-1 ore sources. Since 8 of 12 games are identical to 067, the counts on either run folder answer for both:

```sh
cd ~/projects/gaia-work/gaia-rl
.venv/bin/python tools/upgrade_targets.py ../../gaia-lab/gaia-rl/runs/lab-068-ships-budget-ships --rounds 1-1 --faction Geodens
.venv/bin/python tools/action_counts.py ../../gaia-lab/gaia-rl/runs/lab-068-ships-budget-ships --types Build Upgrade ExploreSpaceship --rounds 1-3
.venv/bin/python tools/ore_sources.py ../../gaia-lab/gaia-rl/runs/lab-068-ships-budget-ships --rounds 1-1
```

Reading: the re-run reproduces 067 almost move for move and lands on the same answer: overall −9.6 (067 −10.1), Xenos the
largest loss (−18.9, 067 −24.8), Geodens negative in both (−10.7, 067 −4.4), one positive pair out of six in both. Two
readings of the same six seeds agree that opening_budget does not gain charges on the seeds it was built for and costs the
mine-opening faction. The pre-set adoption condition (more Geodens academies, positive charges, no loss for the other
factions) fails on the two clauses that were measured; the academy count remains unmeasured. ships_budget is **not** proposed
for the base stack; the base stays vm_lf_ts_ships, the budget factory and spec remain opt-in, no code change, nothing to
deploy.

What was learned about the lab itself: an exact re-run of an A/B is cheap evidence of nothing new — most games replay
identically — so repeat samples must use new seeds, and the "drift" seen between cycles with different B arms is opponent
divergence, not search noise.

Candidate follow-ups (user decision pending, not queued): (a) run the three counts above on lab-068 (or lab-067) — if the
Geodens academy count did not rise, the rule is not reaching its goal and the next step is `explain_ab_decisions.py --arm B`
on pair-001/game-0-A23 (Geodens, −52 in both runs) and pair-000/game-0-A02 (Xenos, −138/−122), not more pairs; (b) if the
Xenos reading holds, the narrower version from 067 (c): keep the budget only when the label's first building is an academy or
planetary institute, leave lab-and-mines openings to the search — order and scope only, no numbers, no faction code — on
**new** seeds; (c) otherwise shelve the Geodens academy line (064–068: five runs, no charge gain) and return to the agreed
agenda (former_use on the ships base, then the "no federation" plan in the comparison set).
