# Cycle 082 — live normal vs vm_lf_ts_ships at the normal search budget (063 follow-up ⓑ)

A: `teacher-a-search2-h1-geodens-cap5.json` (geodens_guide, 2 comparisons, 5 s cap — the live normal teacher).
B: `teacher-a-search2-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap5.json` (vm_lf_ts_ships, the teacher D1 would
deploy, same 2 comparisons and 5 s cap; new spec file for this cycle).
Queued by the user on 2026-10-18 13:45 ("배포 다 하고 실험 다 시작하면 안되나", E4ⓑ). Background: the teacher swap in
`tools/ai_worker.py` is one factory shared by easy, normal and hard, but every hard-vs-stack measurement (052, 063, 081)
used the hard budget (4 comparisons, 20 s), where the stack's median decision is about 16 s. Normal is the live default
level, and at a 5 s cap most of B's decisions would be cut off by the cap. Question: does B still gain more round 1–3
charges than A when both run at the normal budget? Pre-set fork: positive → the swap is justified for normal too;
negative → propose keeping geodens_guide on normal (a per-level factory).
6 fresh geo-quartet seeds (geo-quartet-862133 … 870632) × 2 seat-swapped games, stop at the start of round 4,
agentmaco, commit e26386c, 16 min wall time. Result: lab/results/082-normal-hard-vs-ships.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 63.3 | 196.3 | **+133.0** | [+72.1, +193.9] |
| Taklons | 6 | 112.2 | 152.9 | **+40.7** | [+9.9, +71.5] |
| Terrans | 6 | 79.6 | 138.3 | **+58.7** | [+27.5, +89.9] |
| Xenos | 6 | 147.3 | 90.2 | **−57.1** | [−125.6, +11.4] |
| **All** | 6 | | | **+43.8** | **[+17.8, +69.9]** |

Per-pair B−A from the seat list (rounded):

| | p000 | p001 | p002 | p003 | p004 | p005 | mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Geodens | +145 | +146 | +126 | +29 | +145 | **+207** | +133.0 |
| Taklons | +52 | +90 | +28 | +40 | +34 | +1 | +40.7 |
| Terrans | +75 | +84 | +23 | +42 | +95 | +33 | +58.7 |
| Xenos | −25 | −14 | +13 | −84 | **−170** | −62 | −57.1 |
| Pair mean | +61.7 | +76.2 | +47.7 | +6.6 | +26.1 | +44.7 | +43.8 |

Significant and positive: all six pair means are positive, and Geodens, Taklons and Terrans are each positive in all
six pairs with CIs clear of 0. The size matches the hard-budget measurements on the same lineup (052 +50.5 at 4
comparisons / 20 s; 063 +52.2 on the live lineup): Geodens +133.0 (052 +121.1), Taklons +40.7 (052 +29.7), Terrans
+58.7 (052 +29.0). The one difference is **Xenos −57.1**, five of six pairs negative, CI touching 0: 052 had Xenos
+22.1 and 063 +42.7 at the hard budget. p004 (geo-quartet-866833) carries a third of it: A Xenos 225 charges in
game-0-A01 against B Xenos 55 in game-1-A23. The posted watch replay is pair-005/game-1-A03 seat 0, Geodens on the
A arm with 21 charges against 228 for the B-arm Geodens in the other game — the A teacher's own home faction is where
the stack gains most at this budget, as in 052.

**Where the charges come from (rounds 1–3 move counts, `action_counts.py` / `research_counts.py`, 12 seats per arm,
A → B).**

| | Build | Upgrade | Research | Gaia-forming | Ship explore | Power action | Charge power | Research tracks A → B |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Geodens | 16 → 4 | 13 → 25 | 13 → 22 | 2 → 0 | 3 → 11 | 6 → 3 | 42 → 36 | TF 4·Gaia 4·Eco 5 → **AI 15**·Eco 6·Gaia 5·Sci 4·Nav 3 |
| Taklons | 7 → 10 | 25 → 23 | 12 → 15 | 0 → 0 | 0 → 5 | 16 → 14 | 46 → 39 | **Eco 13**·Sci 6 → AI 7·Gaia 6·Eco 4·TF 4·Sci 3 |
| Terrans | 12 → 7 | 21 → 27 | 8 → 17 | 8 → 2 | 0 → 11 | 6 → 4 | 55 → 43 | Gaia 7·Eco 6 → AI 7·Eco 5·Sci 5·TF 5·Gaia 3 |
| Xenos | 8 → 10 | 31 → 24 | 12 → 7 | 0 → 0 | 15 → 14 | 16 → 11 | 55 → 36 | **Eco 10**·Nav 7 → Nav 8·Eco 3 |

The stack plays the same shape it played at the hard budget: fewer mines and more upgrades and research for Geodens
and Terrans (Geodens Build 16 → 4, Research 13 → 22 with AI 0 → 15; Terrans Research 8 → 17, Gaia-forming 8 → 2),
ships entered on every faction (Explore 18 → 41 in total), and A normal's Economy-first research (Taklons 13 of 21,
Xenos 10 of 22) replaced by AI and mixed tracks. Xenos is the faction where B does less of everything that earns
charge: Research 12 → 7 (Economy 10 → 3, no AI), ChargePower 55 → 36, PowerAction 16 → 11, Upgrade 31 → 24, while
A normal's Xenos is the busiest seat in the run (252 decisions against B's 215) and takes Economy 10. Whether this is
the 5 s cap cutting B's Xenos plans short, or the same Xenos weakness the stack has shown in other cycles (030 −12.8,
033 −11.8, 044 −21.3, 065 −45.3), cannot be told from 6 pairs; the pair-level sign (5 of 6) is the flag.

**Reference VP at the start of round 4 (not the verdict): All −7.7 [−11.2, −4.1]**, Terrans −13.0, Geodens −11.2,
Taklons −5.2, Xenos −1.3. Same direction and size as 052 (−6.8) and 063 (−8.6): the stack holds charge and research
instead of banking early VP, and 081 is the only full-game reading of what that becomes by round 6 (level, −2.5).

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A normal (geodens_guide, 2 cmp, 5 s) | 759 | 1.28 s | 0.31 s | 4.18 s | 6.6 s |
| B vm_lf_ts_ships (2 cmp, 5 s) | 770 | 3.47 s | **5.02 s** | 5.29 s | 7.0 s |

B's median decision is the cap itself: at least half of its decisions run to 5 s (the cap is checked between
comparisons, so the overrun is small — p90 5.29 s, max 7.0 s, inside the normal server guard of 30 s). A normal
finishes most decisions in well under a second (median 0.31 s). Unsearched comparisons: A 515 of 759 (68%), B 597 of
770 (78%) — B leaves ten points more of its comparison budget unsearched because the cap cuts it, and still wins on
charges. No errors, timeouts or fallback decisions on either arm. Decisions 759 vs 770 (Geodens 160 → 182, Xenos
252 → 215).

**Reading.** On the pre-set fork the answer is "positive": at the normal budget, with most of its decisions cut at the
5 s cap, the stack still gains +43.8 charges per seat in rounds 1–3 against the live normal teacher, significant, six
of six pairs, three of four factions individually significant. The hard-budget results (052, 063) therefore carry
over to the live default level, and the shared factory in `ai_worker.py` does not need a per-level split: D1 now has
a measurement for normal as well as hard. The one open flag is Xenos (−57.1, 5 of 6 pairs, CI touching 0), which was
positive at the hard budget on both lineups; it is not large enough to move the overall verdict, but it is the first
hard-vs-stack cycle where a faction loses charge at the pair level, and it is the faction with the most decisions per
game. Time cost on the live server: normal AI turns go from a median of 0.3 s to 5 s (the cap), the same change hard
users saw in 063 (median 15.9 s at the 20 s cap).

**Proposal (user decision, nothing queued, no code change, no deployment).**

- D1 (teacher swap): 082 removes the "normal unmeasured" caveat — one factory for all levels is supported by
  052 + 063 + 082 (30 pairs, all pair means positive). The per-level factory alternative is not needed. Deployment
  timing stays the user's call (081 reported level final VP on the live lineup).
- (ㄱ) **Lab time 0, bot work**: `explain_ab_decisions.py` on B Xenos in p004 game-1-A23 seat 0 (55 charges vs 225
  for A Xenos in game-0-A01) and p003 game-1-A02 seat 1 (67 vs 151) — whether the 5 s cap leaves the Xenos plan
  unsearched (first comparison only) or the stack's Xenos ordering is the cause. Names the Xenos flag before any
  rule is considered.
- (ㄴ) **ships cap5 vs ships cap10 at normal** (new spec `...-ships-cap10.json`, 2 comparisons, 6 fresh geo-quartet
  seeds, 4R stop, ≈ 20 min): does the normal cap lever still pay for the new stack (027 found +18.7 for 4 cmp / 10 s
  with the old teacher, D3 has been waiting since 10-13), and does Xenos recover with more time. This is the
  normal-level counterpart of 080 and would decide D3 with the teacher that will actually run.
- (ㄷ) **082 repeat on 6 fresh geo-quartet seeds** (13 unused in `lab/seeds.txt`): pool to 12 pairs; tells whether
  Xenos −57.1 is real. Lower priority than (ㄴ) because the overall verdict is already significant.

Bot recommendation: (ㄱ) now, (ㄴ) as the next lab slot if D3 (normal setting) is to be decided with D1, otherwise
E13 (ㄱ) 081 repeat keeps the slot. The rule-experiment slots E9 (ㄴ) geodens_b14_tech alone and E7 ships_land_safe
are unchanged.
