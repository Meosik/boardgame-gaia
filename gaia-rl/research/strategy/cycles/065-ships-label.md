# Cycle 065 — ships_label: remember the guide's round-1 opening under its own label (vm_lf_ts_ships base)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-label-cap20.json` — A plus `opening_label`
(`teacher_patches.guide_label_forecast`): when a guide-ordered bgg-opening plan (UIQOO/SHEDEN order) was compared,
`select_forecast` remembers that plan's own label (e.g. 1AC+2M) instead of the catalog row matching the inventory its
rollout reached (e.g. 1RL+2M). The 064 replays showed every B-arm Geodens game renaming 1AC+2M to 1RL+2M at decision 0
and never proposing the academy again. The rule is common to all 14 factions with a guide order; order only, no new numbers.
Question (user, 2026-10-17 "일단 고쳐봐" → "넣어"): does keeping the label get the Geodens academy finished in round 1 and
gain charges in rounds 1–3? Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges, read the Geodens row
first but also the other three (shared rule); count Geodens round-1 academies (`upgrade_targets.py`), errors, unsearched.
6 new seeds (geo-quartet-713070 … 730948) × 2 seat-swapped games, agentmaco, commit 9c34c94, stop_round 3 (ends at the
start of round 4). 1 h 40 min wall time. Result: lab/results/065-ships-label.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 186.0 | 177.1 | −8.9 | [−46.4, +28.5] |
| Taklons | 6 | 151.2 | 167.5 | +16.3 | [−6.9, +39.5] |
| Terrans | 6 | 172.0 | 179.5 | +7.4 | [−13.5, +28.4] |
| Xenos | 6 | 164.9 | 119.6 | **−45.3** | [−92.8, +2.2] |
| **All** | 6 | | | **−7.6** | [−29.7, +14.5] |

Not significant for any row; Xenos touches zero. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +1 | −39 | −41 | −12 | −19 | +56 |
| Taklons | +38 | −10 | +15 | +40 | +24 | −9 |
| Terrans | +2 | −27 | +14 | +14 | +9 | +33 |
| Xenos | −10 | −58 | **−128** | −44 | −2 | −29 |
| Pair mean | +7.8 | −33.5 | −35.0 | −0.5 | +3.0 | +12.8 |

Xenos is negative in all six pairs; Taklons positive in four, Terrans in five, Geodens in two.

**Round-1 Geodens upgrade path** (`tools/upgrade_targets.py --rounds 1-1 --faction Geodens`), A / B per pair:

| Pair | A | B |
|---|---|---|
| p000 | TS → RL (Eco, tile 10) → AC Science (tile 5) | same |
| p001 | TS → RL (Gaia, tile 5) → TS | TS → RL (Gaia, tile 5) |
| p002 | TS → RL (Gaia, tile 5) → TS | same |
| p003 | TS → RL (Gaia, tile 2) → AC Science (tile 3, AI) | same |
| p004 | TS → RL (Eco, tile 10) → TS → RL (AI, tile 11) | TS → RL (Eco, tile 10) → TS |
| p005 | TS → RL (Eco, tile 10) → AC Science (tile 5) | same |

Academies finished in round 1: **A 3 of 6, B 3 of 6, the same three pairs**. The fix targets the game where the 1AC+2M
rollout stalls at the lab and the academy is forgotten; on these six seeds the unmodified A arm already finishes the
academy in half the games (064's A arm, on other seeds, did so in 1 of 6), and where it stalls (p001, p002, p004) B stalls
too. The label rule changed nothing visible in the Geodens round-1 path; its −8.9 is seed noise (p005 +56 with an identical
path).

**Xenos**: round-1 upgrade paths are also near-identical (TS → RL in every game, a second TS in two or three games per arm),
but B builds half the mines: Build in rounds 1–3 A 19 → B 9 (R1 7 → 5, R2 5 → 2, R3 7 → 2), Upgrade 26 → 29. In the
published game pair-002/game-0-A03 (seat 1, Xenos B 94 vs A 221 in the mirrored game) both arms play identically through
frame 50 (TS, RL with tile 10, mines at −9,5 and 3,1, tile-10 action, power → ore); at frame 51 B upgrades 3,1 to a second
trading station while A researches Navigation, and in round 2 A builds two mines plus an asteroid mine and forms a
federation while B builds none. Xenos' guide order starts with 1RL+5M (three more mines); the label logic was written for an
upgrade target that the rollout stops short of, not for a mine-count target, and what the remembered label did at frame 51
has not been checked yet (`explain_ab_decisions.py --arm B --steps 50` on that game — about 50 decisions × up to 20 s,
longer than one bot turn).

Round 1–3 move counts (`action_counts.py`, 6 games per arm, A / B): Geodens Build 9 / 9, Upgrade 29 / 26, Research 25 / 21;
Taklons Upgrade 33 / 29, Research 17 / 18; Terrans Research 19 / 21, GaiaFormation 3 / 5. Decisions 964 (A) vs 895 (B).
Reference VP at the start of round 4 (not a verdict measure): −1.8 [−11.0, +7.4]; Geodens −4.0, Taklons −4.0, Terrans +4.2,
Xenos −3.3.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A | 964 | 11.68 s | 17.69 s | 20.25 s | 25.8 s |
| B | 895 | 12.45 s | 20.00 s | 20.25 s | 23.4 s |

No errors, timeouts or fallback decisions. Unsearched decisions 693 (A) vs 643 (B).

Reading: the pre-set adoption condition (Geodens positive and more round-1 academies) is not met — Geodens −8.9 and the
academy count is unchanged at 3/6 — so ships_label is **not** proposed as the base stack; the base stays vm_lf_ts_ships and
the label factory/spec remain opt-in. The one real behaviour change is on Xenos (−45.3, 6 of 6 pairs, mines halved), a
faction whose first guide label is a mine count rather than an upgrade, which the rule was not written for. Nothing to deploy.

Candidate follow-ups (user decision pending, not queued): (a) find out what the remembered Xenos label did at frame 51 of
pair-002/game-0-A03 (one `explain_ab_decisions.py` run, user-side because of the bot turn limit) before deciding whether the
rule should apply only when the guide label differs from the reached inventory by an upgrade step (AC/PI not reached) and not
by mine count — an order/scope change, no new number, no faction code; (b) re-run A = ships vs B = ships_label on the 064
seeds (699682 … 712850), where the unmodified stack stalled at the lab in 5 of 6 games, so the fix is tested where its
trigger actually fires; (c) shelve ships_label and move on to the agreed agenda (former_use A/B, then the "no federation"
plan in the comparison set).
