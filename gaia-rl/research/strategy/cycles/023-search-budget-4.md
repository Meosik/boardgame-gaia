# Cycle 023 — Four comparisons per decision instead of two

The largest gain so far came from search volume (cycle 016: root-only → 2 comparisons,
+19 to +22 VP/seat). The live normal level compares the current choice with ONE proposal.
B = the live teacher (geodens_guide) with 4 completed comparisons (current choice + three
proposals); nothing else changes, no value or order is added. Decision time is the cost and
is measured with the score (per-decision seconds in each game's decisions.jsonl.gz).

Spec: `tools/teacher-a-search4-h1-geodens.json`. Seeds (fresh): geo-quartet-85000 geo-quartet-85804 geo-quartet-91730 geo-quartet-92689 geo-quartet-93213 geo-quartet-93479 geo-quartet-98077 geo-quartet-99908 geo-quartet-100559 geo-quartet-100601 geo-quartet-101294 geo-quartet-101565

## A/B result (user run; A = live teacher, 2 comparisons; B = 4 comparisons; 12 fresh seeds, 12 pairs)

| Faction | B−A | 95% CI |
|---|---:|---|
| Geodens | **+22.3** | **[+9.6, +35.1]** |
| Taklons | **+12.1** | **[+4.8, +19.4]** |
| Terrans | **+18.7** | **[+9.0, +28.3]** |
| Xenos | −0.7 | [−18.0, +16.7] |
| All seats | **+13.1** | **[+5.6, +20.6]** |

Decision time (all decisions of the run, user's laptop, 4 games in parallel):

| Arm | Decisions | Mean | Median | p90 | Max |
|---|---:|---:|---:|---:|---:|
| A, 2 comparisons | 2,669 | 3.36 s | 0.89 s | 8.58 s | 103.0 s |
| B, 4 comparisons | 2,646 | 6.29 s | 1.75 s | 18.30 s | 117.4 s |

The largest gain since cycle 016, and it again comes from search volume, not from values or
guides: every `potential`-ranked faction gains 12–22 VP; Xenos (own evaluator) does not move.
Cost: ~1.9× decision time. Live play caps a decision at 5 s, which would cut many of the extra
comparisons, so adoption needs either (a) proof that the gain survives the cap, or (b) the
extra comparisons run in parallel processes (same decisions, less wall time).

## Under the live 5 s cap (user run; A = 2 comparisons + cap, B = 4 comparisons + cap; 12 fresh seeds)

| Faction | B−A | 95% CI |
|---|---:|---|
| Geodens | +3.2 | [−9.8, +16.1] |
| Taklons | +8.8 | [−2.5, +20.0] |
| Terrans | −7.4 | [−19.7, +4.9] |
| Xenos | +5.8 | [−12.8, +24.5] |
| All seats | +2.6 | [−6.3, +11.4] |

Time: A mean 1.98 s, median 0.81, p90 5.10, max 65.5; B mean 2.67, median 1.64, p90 5.16,
max 215.1 (the cap starts after the root ranking, which alone is long for 300–400 candidates).
The uncapped +13.1 mostly disappears under the cap: the extra comparisons that matter are in the
long decisions the cap cuts. Normal stays at 2 comparisons; `hard` (4, 20 s cap) keeps them;
parallel processes (live: GAIA_AI_PARALLEL=3) finish more comparisons within the same cap — this
A/B ran without them.
