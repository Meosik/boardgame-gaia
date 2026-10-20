# Cycle 089 — ships vs ships_fed on the measured quartet, 6 rounds (federation compare + link cost)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (deployment teacher, Terrans
track_income included).
B = `...-ships-fed-cap20.json`: the same stack plus **fed_compare** (when a federation is legal, the best federation plan
goes first among the compared plans; the rollout decides) and **fed_cluster** as `_link_costs` (rounds 1–5 mines: the
minimum-spanning-tree satellite cost between my unfederated building groups, 0-1 BFS; when the cheapest-link site
(change ≤ 1) is cheaper than the top-scored site, the order is swapped). All factions. Queued by the user on 2026-10-20
("그렇게 해", 5a E25) on the 084 evidence: 3–8 federation-legal decisions per game, 0.7–2.0 formed, 28 passes while a
federation was legal (5 in round 6), the cheapest federation usually 6–11 satellites.
Pre-registered verdict: charges gained in rounds 1–3 (1 VP = 1.5 charges). Read alongside (not the verdict): federations
and satellites per game, end advanced tech / level 5, final VP, decision time.
geo-quartet, six new seeds, seat-swapped pairs, hard budget (4 comparisons, 20 s), full 6 rounds, agentmaco, commit
260833d, 07:41 → 10:52 (3 h 12 min). Result: lab/results/089-ships-vs-fed-full.md.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1633 vs 1643; A mean 12.61 s, median 20.01 s, max 33.3 s; B mean 12.39 s, median 19.34 s,
max 33.4 s. Unsearched decisions 1292 vs 1296. The extra federation plan and the link-cost BFS cost no time.

## Charges in rounds 1–3 (the verdict)

| Faction | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005) |
|---|---:|---:|---:|---|---:|---|
| Geodens | 162.1 | 177.4 | +15.3 | [−1.4, +32.0] | 4 / 6 | −1 · +42 · +15 · +23 · 0 · +13 |
| Taklons | 145.1 | 144.5 | −0.5 | [−21.7, +20.6] | 3 / 6 | 0 · −11 · +8 · +27 · +7 · −33 |
| Terrans | 167.2 | 183.0 | +15.9 | [−17.2, +48.9] | 3 / 6 | 0 · +37 · +13 · +68 · −4 · −19 |
| Xenos | 152.1 | 139.3 | −12.9 | [−44.4, +18.6] | 1 / 6 | 0 · −27 · −60 · −6 · −13 · +30 |
| **All (seat mean)** | | | **+4.4** | [−8.8, +17.7] | | |

**p000 played the same rounds 1–3 in both games** (charges 204/173/103/154 vs 204/173/103/155): on that seed neither
rule changed a move before round 4. The final scores of p000 differ (Geodens −6, Taklons +7, Terrans +6, Xenos −24), so
the arms split after round 3 — where fed_compare is meant to act.

Posted watch replay: `pair-003/game-1-A02` seat 2 — Terrans A 169 vs Terrans B 237 in the other game of the pair.
Largest negative seat: p002 Xenos B 69 vs A 129 (`pair-002/game-1-A12` seat 3).

**Final VP (read alongside).**

| Faction | A mean | B mean | B−A | 95% CI | Pairs B > A | Per pair |
|---|---:|---:|---:|---|---:|---|
| Geodens | 67.3 | 74.5 | +7.2 | [−16.9, +31.3] | 3 / 6 | −6 · −21 · +27 · +36 · −11 · +18 |
| Taklons | 70.3 | 67.5 | −2.8 | [−18.7, +13.0] | 3 / 6 | +7 · +18 · −20 · −20 · −4 · +2 |
| Terrans | 79.8 | 92.3 | +12.5 | [−9.3, +34.3] | 4 / 6 | +6 · +46 · −5 · +27 · +10 · −9 |
| Xenos | 106.2 | 99.2 | −7.0 | [−30.4, +16.4] | 2 / 6 | −24 · −35 · −4 · +5 · −12 · +28 |
| All (seat mean) | 80.9 | 83.4 | +2.5 | [−4.9, +9.8] | | |

## Not measured this turn

Federations formed per game, satellites per federation, federation-legal passes (`federation_chances.py`) and end
level 5 / advanced tech / unflipped green tokens (`endgame_tech_counts.py`) were not run: the Discord bot's tool list
refused the replay command. These are the numbers the change was built for (user's PPO gate: ≥ 3 federations per seat,
most tokens flipped), so the cycle is open on its main question.

**Added later the same day (owner ran `federation_chances.py`, both arms pooled, 12 seat-games per faction):**
federations formed per seat-game Geodens 0.92, Taklons 0.83, Terrans 0.92, Xenos 2.08 — the 084 range (0.7–1.0,
0.8–1.2, 0.8–1.0, 1.8–2.0). Satellites per formed federation 3.2 / 3.3 / 4.3 / 5.4 (084: 3.6 / 4.1 / 3.4 / 5.9). Legal
but not formed: **Terrans 3.6 decisions per seat-game in round 6, 0.1 formed**; the cheapest legal Terrans federation
was 7 satellites at 70 of 119 decisions; the move played instead was mostly a FreeAction (40). Federation-legal passes:
Geodens 4, Taklons 4, Terrans 9. With both arms pooled, a B-only gain shows at half size. No sign of a large rise.
`federation_chances.py --by-arm` was added to split A and B.

**End state by arm (`endgame_tech_counts.py`, owner run, 6 seat-games per cell; A → B):** federations Geodens
0.83 → 1.00, Taklons 0.83 → 1.00, Terrans 0.83 → 1.00, Xenos 2.33 → 2.33 — **one extra federation per six seat-games**
on three factions, none on Xenos. Advanced tiles Terrans 0 → 0.33, Xenos 0.17 → 0.33, Geodens 0.17 → 0; level 5
unchanged (0.50–1.00); green tokens left Geodens 0.17 → 0.50, Taklons 0 → 0.33, Terrans 0.33 → 0.17, Xenos 1.17 → 1.00.


**Federation chances by arm (`federation_chances.py --by-arm`, owner run; legal decisions / formed per seat-game,
summed over rounds, A → B):** Geodens 4.0 / 0.9 → 2.1 / 1.1, Taklons 4.0 / 0.9 → 3.5 / 0.9, **Terrans 15.8 / 0.9 →
4.0 / 1.0** (A round 6 7.2 / 0.2 → B 0 / 0; A's cheapest legal federation was 7 satellites at 69 decisions), Xenos
3.1 / 2.0 → 3.2 / 2.2. Satellites per formed federation: Geodens 3.2 → 3.2, Taklons 3.8 → 2.8, Terrans 3.4 → 5.0,
Xenos 4.8 → 5.8. Reading: **fed_compare does its job — B forms when a federation is legal instead of sitting on it**
(Terrans' wasted round-6 chances vanish, at the price of more satellites), but the number of federation chances per game
is small on both arms (≈ 1–2 distinct groups reach power 7). The ceiling is the number of buildable groups, i.e.
placement.

The rules work in the intended direction but at a size far from the user's PPO gate (≥ 3 per seat): placement, not the
compare order, holds federations down (cheapest legal federation 7+ satellites most of the time).

## Reading

- **Verdict (pre-registered, rounds 1–3 charges): not shown.** +4.4 with CI [−8.8, +17.7]; no faction's CI excludes 0.
  The 084 same-code yardstick was ±30 per faction, every faction here is inside it.
- Direction matches the design: fed_cluster acts in rounds 1–5 and moves mines toward my own groups, which can cost
  charges (084 decision 129: rollout 245 vs 254); fed_compare acts mostly in rounds 3–6, outside the verdict window.
  Rounds 1–3 coming out flat (p000 identical) is the expected "no early harm" result, not evidence of a gain.
- **Xenos is the only consistent negative**: charges −12.9 (1 of 6 pairs positive), VP −7.0 (4 of 6 negative). Xenos
  already formed the most federations (084: 1.8–2.0 per game); a rule that clusters mines and adds federation plans
  may pull it away from the spread-out mines that bring charges. Not significant; worth one explain before a repeat.
- Geodens +15.3 (CI just touching 0) and Terrans +15.9 with VP +7.2 / +12.5 lean positive.
- Final VP +2.5 [−4.9, +9.8]: flat.

Nothing changed in code or deployment. 090 (ships vs ships_tokens) starts next as queued; its A arm is plain `ships`,
so 089 does not alter it.

## Proposal (user decision, nothing queued)

- (ㄱ) **Lab time ≈ 0, first**: federation and endgame counts on the 089 folder, owner runs from `~/projects/gaia-work`:
  `GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/tools gaia-rl/.venv/bin/python gaia-rl/tools/federation_chances.py ~/projects/gaia-lab/gaia-rl/runs/lab-089-ships-vs-fed-full`
  and `... endgame_tech_counts.py ~/projects/gaia-lab/gaia-rl/runs --glob 'lab-089-*'` (or as a lab `command` job).
  This decides whether the rules did what they were for (feds per seat, satellites, round-6 federation passes).
- (ㄴ) If federations per seat rose: repeat 089 on six new geo-quartet seeds (12-pair pool, ≈ 3 h) before any move to the
  deployment stack; if they did not: explain the round-6 federation-legal passes on B to see why fed_compare's plan lost.
- (ㄷ) Lab time 0: `explain_ab_decisions.py` on p002 `game-1-A12` Xenos B (charges 69) — which rule moved its round 1–3
  mines.

Bot recommendation: (ㄱ) now, then (ㄴ) or the explain depending on the federation count.
