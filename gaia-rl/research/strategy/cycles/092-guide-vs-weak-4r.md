# Cycle 092 — ships_byfaction_guide vs ships_byfaction_guide_weak, quartets a · b · c, 4 rounds (the three low-charge factions' parts alone)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-guide-cap20.json` (091's B arm:
deployment stack + `CANDIDATE_FACTION_PARTS` + `GUIDE_FACTION_PARTS`).
B = `...-ships-byfaction-guide-weak-cap20.json`: the same plus `WEAK_FACTION_PARTS` (research/strategy/conflicts/
weak-factions.md) — **opening_only** for HadschHallas (catalog cut to 1AC+2M · 1RL+4M · 1AC+1M · 1RL+5M: no institute,
no lab with 2–3 mines), Itars (1AC+1M · 1AC+2M · 1PI+2M · 1PI+1M: no lab-only opening) and Firaks (1PI+1TS ·
1RL+1TS+2M · 1RL+1TS+1M), and **building_limits** for HadschHallas (no institute in rounds 1–2). The other nine
factions run the same code on both arms and are the drift yardstick.
Queued by the user on 2026-10-20 ("제안 순서대로 진행해" → ④ 측정 after the read-through and conflict tables).
Pre-registered verdict: charges gained in rounds 1–3 for the three factions (1 VP = 1.5 charges); read alongside:
activation (round-1 buildings from upgrade_counts, the round-1 plan labels), decision time, errors; if bad,
HANDOFF 1's order (noise → activation → implementation → conflicts → measure → conditions → source).
quartet-a (Firaks) × 6 new seeds + quartet-b (Itars) × 6 + quartet-c (HadschHallas) × 6 = 18 seat-swapped pairs,
hard budget (4 comparisons, 20 s), stop at the start of round 4, agentmaco, commit 2dd4d3a, 17:06 → 21:12
(4 h 05 min). Result: lab/results/092-guide-vs-weak-4r.md.

**Health: clean.** 36 of 36 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 2688 vs 2607; A mean 10.78 s, median 13.67 s, max 44.4 s; B mean 11.00 s, median 14.35 s,
max 44.8 s (both arms over the 20 s cap on a few setup decisions, as in 033; inside the 60 s guard). Unsearched
1822 vs 1751. The parts cost no time.

## Charges in rounds 1–3 (the verdict)

| Faction | B parts in 092 | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| **Firaks** | opening_only (1PI+1TS · 1RL+1TS+2M · 1RL+1TS+1M) | 149.0 | 129.2 | **−19.8** | [−43.6, +4.0] | 1 / 6 | −11 · **0** · −16 · −56 · −38 · +2 |
| **HadschHallas** | opening_only (1AC+2M · 1RL+4M · 1AC+1M · 1RL+5M), building_limits (PI ≥ R3) | 142.7 | 131.0 | −11.7 | [−31.0, +7.6] | 0 / 6 | −8 · **0** · **0** · −47 · −15 · **0** |
| **Itars** | opening_only (1AC+1M · 1AC+2M · 1PI+2M · 1PI+1M) | 148.6 | 151.4 | +2.8 | [−56.8, +62.4] | 3 / 6 | **0** · −61 · −52 · +90 · +40 · +1 |
| Ambas (same code) | — | 129.6 | 130.7 | +1.1 | [−6.0, +8.3] | | |
| BalTaks (same code) | — | 186.7 | 184.2 | −2.5 | [−28.8, +23.8] | | |
| Bescods (same code) | — | 194.8 | 194.0 | −0.8 | [−24.3, +22.7] | | |
| Gleens (same code) | — | 169.8 | 160.2 | −9.6 | [−24.5, +5.3] | | |
| Ivits (same code) | — | 172.2 | 162.3 | −9.9 | [−27.9, +8.2] | | |
| Lantids (same code) | — | 167.5 | 161.3 | −6.1 | [−26.5, +14.2] | | |
| Nevlas (same code) | — | 152.8 | 147.8 | −4.9 | [−38.6, +28.8] | | |
| Terrans (same code) | — | 186.8 | 181.5 | −5.3 | [−13.3, +2.7] | | |
| Xenos (same code) | — | 158.1 | 153.7 | −4.4 | [−23.0, +14.2] | | |
| **All (seat mean)** | | | | **−5.9** | [−11.9, +0.1] | | 18 pairs |

The nine same-code factions average **−4.7** (−9.9 … +1.1), the same lean as 088's self-play drift (−4.3), so the
"all" −5.9 is mostly drift. **Five of the 18 pairs are identical through round 3 in every seat** (pair-001 in
quartet a, pair-006 in b, pairs 013 · 014 · 017 in c): on those seeds the parts changed nothing before round 4.
Against 088's rule (a faction difference under 25 cannot be read) and the per-pair swing (±50 … ±90): **Firaks
−19.8 (4 of 6 negative, one identical) leans negative, unconfirmed**; **HadschHallas −11.7 is inside drift** (three
identical pairs, the rest −8 · −47 · −15); **Itars +2.8 is unreadable** (±60, pairs −61 · −52 · +90 · +40).

Posted watch replay: `pair-009/game-0-A13` seat 1 — Itars **A** 82 vs Itars B 172 in the other game of the pair
(the pair that swung +90 for B; the low game is the A arm, so it says nothing about the weak parts).

VP at the start of round 4 (not the verdict): all −1.0 [−2.7, +0.6]; Terrans −8.2 (14.7 → 6.5, p016 29 → 0 and
p017 5 → 0 — same code), Itars −7.2 (16.0 → 8.8), Lantids −3.2, HadschHallas +2.5 (9.0 → 11.5), Firaks −0.8.

## Activation (round 1 and rounds 1–3, A → B, 6 seat-games per arm)

**Round-1 plan labels selected** (`decisions.jsonl.gz` `selected`, the "via" plan; whole run):

| Faction | A | B |
|---|---|---|
| HadschHallas | 1RL+1TS+2M ×18 · 1RL+1TS+1M ×5 · 1RL+3M ×5 · 1RL+4M ×4 (**42 BGG picks**) + HH-academy-economy ×4 | **no BGG plan ever selected (0)** — current-choice 106 · local-baseline 69 · HH-academy-economy 19 · value-max 1RL+4M 2 · HH-PI-Rebellion 2 |
| Itars | 1RL+3M ×19 · 1PI+1TS+1M ×11 · 1RL+2M ×9 · 1AC+2M ×3 · 1PI+1TS+2M · 1RL+1TS+2M | **1AC+1M ×21 · 1AC+2M ×5** (26 of 26 BGG picks are the academy) + Itars-PI Gaia-tech ×3 |
| Firaks | **1PI+1TS ×23** · 1RL+2M ×9 · 1PI+2M ×6 · 1RL+1M ×2 + lab-cycle / downgrade-rebuild ×9 | **1PI+1TS ×26** · 1RL+1TS+1M ×3 + downgrade-rebuild ×5 |

**Upgrades** (`upgrade_counts.py`, TS / RL / PI / AC):

| Faction | Round 1, A → B | Rounds 1–3, A → B |
|---|---|---|
| HadschHallas | 12 / 6 / **0** / **0** → 13 / 6 / **0** / **0** | 15 / 12 / **0** / 6 → 17 / 13 / **0** / 5 |
| Itars | 8 / 4 / 1 / **1** → 7 / 6 / 0 / **4** | 11 / 9 / 1 / 4 → 11 / 11 / **0** / **6** |
| Firaks | 10 / 3 / **3** / 0 → 9 / 2 / **4** / 0 | 11 / 13 / 5 / 1 → 12 / 10 / 4 / 1 |

**Research** (`research_counts.py --rounds 1-3`, TF / Nav / AI / Gaia / Eco / Sci): HadschHallas 6 / 6 / 2 / 3 / 13 / 1
= 31 → 9 / 7 / 1 / 1 / 12 / 1 = 31 (unchanged); Itars 2 / 4 / 3 / 6 / 2 / 2 = 19 → 4 / 5 / 3 / 6 / **6** / 3 = **27**
(academy start: Economy 2 → 6); Firaks 1 / 2 / 3 / 1 / 13 / 1 = 21 → 1 / 0 / 1 / 0 / **16** / 0 = 18 (Economy only,
Navigation 2 → 0, AI 3 → 1). Same-code factions move by up to 5 steps (Ivits Eco 9 → 13, AI 1 → 4) — drift alone.

## Reading (HANDOFF 1 order)

- **HadschHallas: ② not activated.** The cut catalog (academy or lab + 4–5 mines) left the B arm with **no
  completed opening forecast in any of the 6 seat-games** (A selected a BGG plan 42 times, B 0). The 20 s search
  completes about one forecast a decision, and an academy or a 4–5 mine forecast rarely finishes — exactly what the
  `opening_only` note in `teacher_patches.py` records for BalTaks before `fixed_academy` + the budget tools were
  added ("opening_only alone left BalTaks at the research lab, local-baseline picks"). B's round 1 was therefore the
  search's own picks: buildings unchanged (TS 13, RL 6, **academies 0 of 6, institute 0**), research unchanged, three
  seeds identical. Neither "RL + 4 mines" nor "AC + 2 mines" was played. **building_limits had nothing to forbid**:
  A never built the institute in rounds 1–3 either (0 / 0), so 088's "no early institute" explanation for the lowest
  charges does not hold — the guide stack already avoids it. The HadschHallas charge question (088) stays open; the
  part as written is a no-op minus the planner.
- **Firaks: fired weakly, leans negative, unconfirmed.** Both arms already open 1PI+1TS (A 23, B 26 selections);
  the part only removed A's secondary plans (1PI+2M 6, 1RL+2M 9) and let 1RL+1TS+1M in (3). Round-1 institutes 3 →
  4 of 6. Charges −19.8, 4 of 6 pairs negative (p003 −56, p004 −38), below the 25-charge line and inside a single
  pair's swing, but the largest negative in the run against a −4.7 same-code lean. ① needs the two big pairs
  explained before any re-run (why B at pair-003 123 vs A 179 with the same primary opening). ③ candidate: the
  guide (B09-S10, SH04-S39) keeps the lab-and-mines fallback for when ore 11 is not reachable; the part dropped it.
- **Itars: fired as written, unreadable.** Every B BGG pick is the academy (26 / 26), round-1 academies 1 → 4 of 6,
  institute 1 → 0, research 19 → 27 (Economy 2 → 6). Charges +2.8 with pairs −61 · −52 · +90 · +40. Both arms carry
  091's tile_prefs scope error (tiles 6 / 8 on every standard tile choice), and an academy start takes **more**
  standard tiles early, so the error interacts with the part here rather than cancelling. Re-measure only after
  098 (the scope fix) and with the fixed guide as the A arm.
- ⑤ measure: all three parts are round-1 openings, so rounds 1–3 charges is the right window; no mismatch.
- The run's "all −5.9 [−11.9, +0.1]" is drift (nine same-code factions −4.7); nothing to act on.

Nothing changed in code or deployment. 093 (`guide vs src`) is still in the queue (the user's `git mv` hold from
E52 is pending) and **carries the same risk**: its `opening_only` lists for Ambas (RL+4–6M, AC+2M), Bescods
(RL+4–5M, 2RL+1M), Gleens (RL+4M, 6M, 7M), Nevlas (PI+RL…), Lantids (PI+3–6M) are big-mine or two-building
forecasts that the 20 s search rarely completes — 093 may measure "no opening planner" instead of the sources.

## Proposal (user decision, nothing queued)

- (ㄱ) **HadschHallas: make the opening playable before measuring again.** Give HadschHallas the BalTaks treatment —
  `fixed_academy` (Science academy, PG19-S23 지식 아카데미) + the budget tools when the academy forecast does not
  complete — and/or run the weak spec on a **cap60** teacher (E52 (c): comparisons complete, forecasts finish) so
  1RL+4M / 1RL+5M can actually be chosen. Then weak vs guide, quartet c, the same six seeds, 4R (≈ 1 h 20 min for
  one quartet). building_limits can stay (harmless, never fires on this stack).
- (ㄴ) **Firaks: explain first, lab 0.** `explain_ab_decisions.py` on pair-003 (`game-0-A13` B seat, 123 vs 179) and
  pair-004 (`game-1-A23`, 206 vs 244): if the loss is the missing lab + mines fallback, restore 1RL+2M to the Firaks
  list (B09-S10's ore-11 condition is the guide's own branch); if it is unrelated to round 1, the part is a no-op and
  can be dropped or folded into plan_menu's Firaks row (E54).
- (ㄷ) **Itars: wait for 098** (tile_prefs scope fix on quartet b), then weak vs fixed guide, quartet b, 6 seeds.
- (ㄹ) **093 hold stays recommended** (E52) — and before it runs at all, check the same forecast-completion problem
  for its five opening_only factions (one smoke seat-game per faction on cap60, lab command ≈ 10 min), or move 093
  to cap60 specs.

Bot recommendation: (ㄴ) now as a bot turn (no lab time), (ㄱ) as code + one quartet-c re-run, (ㄹ) before 093 runs.
