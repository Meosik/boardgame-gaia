# Cycle 071 — ships vs ships_fix, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-cap20.json` — A plus the ships_fix bundle built from
the 068 replays (user 2026-10-18 "지금 테스트 멈추고 고칠거 다 고친 후에 돌려야겠는데"): former_use + instant_forming (a
Transdim planet is a mine option only once it is being formed or can be formed at once), opening_budget with the first-step
fix and budget_guard (nothing is blocked when the chain cannot be paid from what is held now), opening_release (once the
target's upgrades are built the rest of round 1 goes back to the search), geodens_b14_tech (first standard tile 10 or 4 on
Economy, no Gaia advance before round 5) and academy_economy (a faction holding an academy, BalTaks excepted, researches
Economy to 2 in rounds 1–3 first). Order and scope only, no new number.
6 fresh seeds (geo-quartet-740367 … 745858) × 2 seat-swapped games, agentmaco, commit 6e9fa39, stop_round 0 (all six
rounds, user "앞으로 6라운드 끝까지 해서 점수비교도 하자"), 3 h 16 min wall time.
Result: lab/results/071-ships-fix-full.md.

Adoption condition set before the run: charges positive and final VP not lower → propose ships_fix for the base stack.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 149.7 | 162.5 | +12.8 | [−23.1, +48.7] |
| Taklons | 6 | 168.8 | 169.6 | +0.7 | [−53.6, +55.1] |
| Terrans | 6 | 191.1 | 145.8 | **−45.3** | [−88.1, −2.5] |
| Xenos | 6 | 128.1 | 148.7 | +20.6 | [−38.9, +80.2] |
| **All** | 6 | | | **−2.8** | [−34.0, +28.5] |

Overall flat; Terrans significantly negative. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +70 | +21 | +18 | −32 | −7 | +8 |
| Taklons | −15 | 0 | +29 | −61 | −36 | +87 |
| Terrans | −62 | −63 | −64 | −87 | −20 | +26 |
| Xenos | +63 | −84 | +8 | +53 | +18 | +66 |
| Pair mean | +14.0 | −31.5 | −2.3 | −31.8 | −11.3 | +46.8 |

Terrans lose in five of six pairs, four of them by 60–87 charges. Geodens are positive in four pairs, Xenos in five
(p001 −84 is the one large Xenos loss). Two pair means positive.

**Final VP (read together with the charges, per the user's request; not the verdict measure)**: All **+2.2** [−23.0,
+27.5]; Geodens +8.7 [−17.8, +35.1] (p004 +34, p005 +38), Xenos +13.7 [−21.3, +48.6] (five pairs positive), Taklons +0.7,
Terrans **−14.0** [−55.9, +27.9] (p000 −78, p001 −27, p003 −26). Seat-average final VP A 86.8 → B 89.0 (PPO start criterion
of about 110 still not reached). The Terrans loss carries from the charges into the final score; the Geodens and Xenos gains
carry too, Taklons are flat on both measures.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1749 | 12.22 s | 16.46 s | 20.43 s | **51.1 s** |
| B ships_fix | 1858 | 11.94 s | 15.56 s | 20.32 s | 43.7 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1376 vs 1466. The 51.1 s maximum is on the unchanged A
arm (the highest A maximum so far; 060 A 42.2 s), still under the 60 s server limit.

**Where the rules fired (counts from the run folder).**

Geodens round 1 (`upgrade_targets.py --rounds 1-1 --faction Geodens`), A → B per pair:

| Pair | A | B | Geodens B−A |
|---|---|---|---:|
| p000 | TS → RL (tile 2) | TS → RL (tile 4) → **AC** (tile 3 on Economy) | +70 |
| p001 | TS → RL (tile 2) | TS → RL (tile 10 on Economy) → TS | +21 |
| p002 | TS → RL (5) → AC (2) | TS → RL (tile 10 on Economy) → **AC** (2) | +18 |
| p003 | TS → RL (10) → AC (2) | TS → RL (5) → AC (3) | −32 |
| p004 | TS → RL (5) | TS → **PI** → TS | −7 |
| p005 | TS → RL (5 on Economy) | TS → **PI** | +8 |

Round-1 academies A 2/6 → B 3/6, plus two planetary institutes in B. geodens_b14_tech fires: B's first standard tile is 10
or 4 in three of the four lab seats (p003 took 5), and the Economy placement appears in three B seats against one in A.
Rounds 1–3 research Geodens A → B: Gaia 3 → 0, Economy 4 → 6, AI 9 → 14, Terraforming 0 → 2. Over six rounds Economy 7 →
13, Gaia 8 → 4. End board: mines 4.5 → 6.2, federations 0.7 → 1.2, final 64.7 → 73.3.

Rounds 1–3 action counts (`action_counts.py`, six seats per arm), A / B:

| Faction | GaiaFormation | Build | Upgrade | Asteroid mine | Ship entries | ResearchAdvance |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | 0 / 0 | 12 / 9 | 25 / 24 | 4 / 6 | 8 / 9 | 15 / 19 |
| Taklons | 0 / 1 | 11 / 13 | 29 / 28 | 4 / 1 | 8 / 7 | 17 / 20 |
| Terrans | 1 / **4** | **11 / 2** | 30 / 29 | 1 / 0 | 12 / 8 | 21 / 18 |
| Xenos | 0 / 0 | 14 / 14 | 27 / 28 | 1 / 3 | 14 / 13 | 13 / 11 |

Rounds 1–3 research (`research_counts.py`), A → B: Terrans AI **19 → 4**, Economy **3 → 10**, Science 2 → 4; Taklons
Economy 4 → 8, AI 9 → 6; Xenos Economy 1 → 4. academy_economy fires for every academy faction and moves the early research
from AI to Economy. Round-1 ore sources (`ore_sources.py --rounds 1-1`): Terrans Terraforming research 6 → 2, QIC → ore
4 → 2, power action 3 ore 4 → 6; Taklons 32 → 23 (power action 4 → 2, no pass ore); Xenos 34 → 27.

**The Terrans loss.** B Terrans build two mines in rounds 1–3 against eleven (both arms build the same three round-1
academies: A p000-g1, p001-g1, p003-g1; B p000-g0, p002-g0, p004-g1). They catch up in rounds 4–6 (Build 6 → 10) but
end with fewer turns (45.8 → 40.8), fewer labs on the board (1.0 → 0.2), fewer ship actions (6.7 → 3.7) and a lower end
mission score (27.0 → 18.8). The posted replay, pair-003/game-0-A13 seat 2 (Terrans B 139 against A 226 in the mirror
game), shows the shape (`list_decisions.py --rounds 1-3 --seat 2`, both games):

| Round | A (game-1) | B (game-0) |
|---|---|---|
| 1 | TS → RL (5) → Eclipse → **Terraforming research** → QIC → ore → **AC** (2) → **mine** → Twilight → pass | TS → RL (2) → Eclipse → burn 2 power → Eclipse boost AI → **GaiaFormation** → pass (no AC, no mine) |
| 2 | TS → Twilight free RL (10) → AI → Twilight range build → **federation** → Rebellion → pass | AC (5) → **Economy research** → Twilight → artifact → pass |
| 3 | AI → TS → Twilight range build → tile 10 action → free RL (13, AI) → AI → token replay → pass | Terraforming research → Twilight range build → TS → RL (10) → tile 10 action → pass |

Two candidate causes, not separated by this run: (1) academy_economy — once the academy stands, Economy research is
ranked first among research moves, and the Terrans AI line (A: three AI advances by round 3, QIC into mines and
federations) disappears; (2) former_use / instant_forming with the budget — in round 1 the B Terrans form a planet and pass
instead of researching Terraforming for the academy's ore, so the academy slips to round 2 and the round-1 mine is lost
(budget blocks the mine while the academy is owed; research and forming are never blocked; the forming is the preferred
move for an idle former). Which rule ranks the round-1 forming over the Terraforming research needs `explain_decision`
at step 47 of pair-003/game-0-A13 (B spec); the bot cannot run it (the command needs the `PYTHONPATH` prefix, refused):

```sh
cd ~/projects/gaia-work/gaia-rl
GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools .venv/bin/python tools/explain_decision.py \
  ~/projects/gaia-lab/gaia-rl/runs/lab-071-ships-fix-full/pair-003/game-0-A13 --step 47 --top 8
```

Reading: as a bundle, ships_fix is flat on the verdict measure (−2.8) and flat on final VP (+2.2). The Geodens part works
as designed (first tile on Economy, no early Gaia, more round-1 big buildings, +12.8 charges, +8.7 VP, more mines and
federations by the end) and Xenos gain on both measures, but Terrans lose 45 charges in rounds 1–3 (five of six pairs) and
14 VP at the end, because B Terrans stop building mines in rounds 1–3 and research Economy instead of AI. The pre-set
condition (charges positive, VP not lower) fails on the charges, so ships_fix is **not** proposed for the base stack; the
base stays vm_lf_ts_ships, ships_fix stays opt-in, no code change, nothing to deploy. 072 (ships_fix vs ships_fix_label,
queued by the user) runs on the ships_fix base and reads label_value on its own.

Candidate follow-ups (user decision pending, not queued): (a) split the Terrans cost — ships vs ships_fix without
academy_economy (the only rule that acts in rounds 2–3 for every academy faction; Terrans AI 19 → 4 is its clearest
footprint), fresh seeds, 6 pairs, full game, judged by Terrans and overall charges; (b) the other half — ships vs ships_fix
without former_use/instant_forming, same design; (c) the explain_decision above first, then only the half it points to.
The bot's recommendation is (a), because the Geodens and Xenos gains come from rules that do not touch rounds 2–3, and
academy_economy is the one rule the user asked for by hand (01:45) whose faction-wide effect was never measured alone.
