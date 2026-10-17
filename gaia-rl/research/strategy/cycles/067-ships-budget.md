# Cycle 067 — ships_budget (opening_budget) on the 064/066 seeds (vm_lf_ts_ships base)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-budget-cap20.json` — A plus `opening_budget`
(`teacher_patches.opening_budget_scores`): while the round-1 opening target still has an unbuilt upgrade (chain costs TS 2/6,
RL 3/5, PI 4/6, AC 6/6, nearest path, mines not counted), any move that is not one of those upgrades is blocked when the ore +
QIC (1 → 1 ore) + bowl-III power (3 → 1 ore, 1 → 1 credit) left after the native fork can no longer pay the remaining upgrade
cost. Chain upgrades, moves that spend nothing (research, charge, pass) and moves that leave the budget intact are untouched;
the missing ore is left to the frozen funding search (QIC → ore, power → ore, power action 3). B14 §4 and IR01 "academy first,
mine only with what is left", engine costs and rulebook exchange rates only, common to all 14 factions with a guide order.
Includes the ship fix of 5e7a2bb: ship entries (`…ExploreSpaceship`, VP + range QIC) are exempt from the budget check, ship
upgrade actions (Twilight free research lab, Rebellion free trading station) count as chain steps by building count after the
fork, the remaining cost is recomputed after the move.

Question (user, 2026-10-17 "1번 ㄱㄱ"): on the seeds where the unmodified stack stalls the Geodens 1AC+2M opening at the
research lab (064: 5 of 6, 066: 4 of 6), does reserving the academy's ore finish the academy and gain charges in rounds 1–3,
without hurting the other three factions that share the rule? Set before the run: judge by round 1–3 charges at 1 VP = 1.5
charges, read the Geodens row first, then the other three; count Geodens round-1 academies (`upgrade_targets.py`), Xenos and
Terrans round 1–3 mines (`action_counts.py`), round-1 ore sources (`ore_sources.py`), errors, unsearched. Adoption condition set
in advance: more Geodens academies, positive charges, no loss for the other factions.

**Which code ran.** The lab started 067 at 15:51 on the first-version code (41bcef6). The user restarted the lab at 16:09:57 to
drop it; the restarted lab re-pulled and picked 067 up again at 16:09:58 at commit ff5e54b — which already contains the ship
fix (5e7a2bb, 16:02) — before the queue deletion (413df1f, 16:11) reached it. The 15:51 partial run was discarded
(`lab-067-ships-budget.partial-…`). So this result **is** the fixed-code test that 068 was queued to be; 068 (started 17:44:35,
same A/B, same six seeds, same code) is an exact re-run and will serve as a second sample.

The 064 seeds reused (geo-quartet-699682 … 712850) × 2 seat-swapped games, agentmaco, commit ff5e54b, stop_round 3 (ends at
the start of round 4). 1 h 35 min wall time. Result: lab/results/067-ships-budget.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 167.4 | 163.1 | −4.4 | [−35.8, +27.0] |
| Taklons | 6 | 155.3 | 146.8 | −8.5 | [−53.1, +36.1] |
| Terrans | 6 | 193.0 | 190.2 | −2.8 | [−45.6, +40.0] |
| Xenos | 6 | 160.1 | 135.4 | −24.8 | [−88.0, +38.5] |
| **All** | 6 | | | **−10.1** | [−28.7, +8.5] |

Not significant for any row. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +28 | −52 | −21 | +25 | −4 | −3 |
| Taklons | +67 | −4 | +6 | −53 | −39 | −28 |
| Terrans | +16 | −80 | +21 | +34 | −2 | −4 |
| Xenos | −138 | −41 | −15 | +20 | +22 | +4 |
| Pair mean | −6.8 | −44.3 | −2.3 | +6.5 | −5.8 | −7.8 |

One pair positive, five negative. The two large losses are **Xenos in pair-000** (B 107 vs A 245 in the mirror seat; this is the
published replay, pair-000/game-0-A02 seat 1) and **pair-001, where all four B seats lose** (Terrans −80, Geodens −52). Geodens
is split 2:4 with ±25 swings on the three seeds that move, and is flat (−3, −4) on p004 and p005 — unlike 066, pair-004 is not
identical in the two arms this time (Taklons −39, Xenos +22), so either the rule fires on that seed or the arms drifted.

**Arm-A drift.** The A arm is the same stack and seeds as 066 A (and 064 B). 066 reported the round-1 Geodens paths reproducing
exactly, but the charge totals do not: 066 A → 067 A is Geodens 172.7 → 167.4, Taklons 152.9 → 155.3, **Terrans 176.9 → 193.0**,
Xenos 172.4 → 160.1. The time-capped search is not deterministic run to run, and a same-code same-seed drift of 12–16 charges
per faction row is the size of most of the differences above. 068 (an exact re-run of this A/B) will show the same drift for
both arms and, combined with 067, gives 12 pairs on these seeds.

**Not measured in this cycle** (the bot cannot run python): Geodens round-1 academy count, Xenos and Terrans round 1–3 mines,
round-1 ore sources. The adoption condition's first clause (more academies) is therefore unchecked. Commands for the user:

```sh
cd ~/projects/gaia-work/gaia-rl
.venv/bin/python tools/upgrade_targets.py ../../gaia-lab/gaia-rl/runs/lab-067-ships-budget --rounds 1-1 --faction Geodens
.venv/bin/python tools/action_counts.py ../../gaia-lab/gaia-rl/runs/lab-067-ships-budget --types Build Upgrade ExploreSpaceship --rounds 1-3
.venv/bin/python tools/ore_sources.py ../../gaia-lab/gaia-rl/runs/lab-067-ships-budget --rounds 1-1
```

Counters from the result file, A / B: decisions 879 / 866 (Geodens 188 / 209, the only faction with more decisions in B;
Taklons 195 / 191, Terrans 233 / 227, Xenos 263 / 239), unsearched decisions 619 / 593 (Geodens 128 / 143, Xenos 196 / 174). Reference VP at the start
of round 4 (not a verdict measure): **+1.6** [−1.4, +4.5], all four rows slightly positive (Geodens +2.3, Taklons +2.3, Terrans
+0.7, Xenos +1.0) while the charges are negative — B converts a little more into points by the end of round 3 and holds less
economy, the opposite of what an academy-first opening should show if it had worked.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A | 879 | 12.34 s | 20.01 s | 20.30 s | 22.8 s |
| B | 866 | 11.65 s | 19.44 s | 20.26 s | **35.1 s** |

No errors, timeouts or fallback decisions. One B decision at 35.1 s is above the 20 s cap (within the 60 s server limit); the
budget wrapper itself does not add time (B mean and median are lower than A).

Reading: the budget rule does not pay off in charges on the seeds it was built for: overall −10.1 [−28.7, +8.5], Geodens −4.4,
and the faction with the most mine-heavy opening, Xenos, loses the most (−24.8, one seed −138). The mechanism fits: for a
1RL+5M-type target the rule withholds ore for TS + RL (5 ore) from every mine until the lab is built, which is the reverse of
the guide's order for that faction, and in pair-000 the Xenos B seat ends round 3 with less than half the mirror seat's charges.
Whether the Geodens academy count rose is unknown until the counts above are run; the charge row says that if it did, it did
not gain anything by the start of round 4. Of the pre-set adoption condition, "positive charges" fails and "no loss for the other
factions" fails for Xenos (not significant, but large). ships_budget is **not** proposed as the base stack; the base stays
vm_lf_ts_ships, the budget factory/spec remain opt-in, no code change, nothing to deploy.

Candidate follow-ups (user decision pending, not queued): (a) let 068 finish (same A/B, same seeds, same code — a second sample
and a drift measurement; about 1.5 h), then read 067+068 as 12 pairs; if the user prefers not to spend it, stop it with
`systemctl --user restart gaia-lab` after deleting `lab/queue/068-ships-budget-ships.json`; (b) run the three counts above on
lab-067 first: if Geodens academies did not increase, the rule is not reaching its goal and the next step is a mechanism check
(`explain_ab_decisions.py --arm B` on pair-001/game-0-A23 Geodens, or on pair-000/game-0-A02 Xenos for the −138), not more
pairs; (c) if the Xenos reading holds, a narrower version that reserves the budget only for a big-building target (academy or
planetary institute first in the label, the order the guide already gives), leaving lab-and-mines openings to the search — order
and scope only, no numbers, no faction code; (d) otherwise shelve the Geodens academy line (064–067: four runs, no charge gain)
and return to the agreed agenda (former_use on the ships base, then the "no federation" plan in the comparison set).
