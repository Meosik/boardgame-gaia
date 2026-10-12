# Cycle 048 — distinct setup comparisons, soft adjacency, range +1, research focus (vm_lf_ts_reach)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (047 B arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-cap20.json` — A + `install_reach`: setup decisions compare
up to 4 distinct places/boosters (setup only, 50 s), opponent-adjacent places ranked first instead of the others being
blocked, expansion value and booster 5 count planets reached at the next navigation range step, research moves reordered
(highest track at level 2+ first, otherwise navigation below 2 first).
Question: do these four fixes from the 047 p000-g1 analysis raise the charges gained in rounds 1–3?
Set before the run (user, 2026-10-12 "진행해"): judge by round 1–3 charges at 1 VP = 1.5 charges.
6 fresh seeds (geo-quartet-534437 … 536873) × 2 seat-swapped games, agentmaco, commit fe5d895, stop_round 3.
Result: lab/results/048-guide-r1-charge3-lf-more-vm-lf-ts-reach.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 165.2 | 182.9 | +17.7 | [−44.2, +79.5] |
| Taklons | 6 | 157.4 | 132.6 | −24.8 | [−52.3, +2.7] |
| Terrans | 6 | 179.5 | 141.1 | −38.4 | [−89.4, +12.6] |
| Xenos | 6 | 125.6 | 127.7 | +2.0 | [−57.0, +61.1] |
| **All** | 6 | | | **−10.9** | **[−57.0, +35.2]** |

Not significant. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +55 | −4 | −44 | −42 | +34 | +106 |
| Taklons | +2 | −6 | −72 | −31 | −28 | −14 |
| Terrans | +28 | −78 | −84 | −72 | −36 | +13 |
| Xenos | +88 | +2 | −75 | −38 | +2 | +32 |
| Pair mean | +43.2 | −21.3 | −68.8 | −45.8 | −6.8 | +34.2 |

Two of six pairs positive. Taklons is negative in 5 of 6 pairs (CI just reaches zero) and Terrans in 4 of 6, three of them
by −72 to −84; these are the two factions where the sign is consistent. Geodens (+17.7) and Xenos (+2.0) swing ±40–106 per
pair, so their means are noise. p002 is negative for all four factions.

VP held at round 4 (not used for the verdict): +0.3 [−2.9, +3.5].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts | 872 | 12.28 s | 20.01 s | 20.27 s | 24.0 s |
| B vm_lf_ts_reach | 847 | 16.05 s | 20.04 s | 22.84 s | 57.3 s |

No errors, timeouts or fallback decisions; the reach code ran cleanly in all 12 games. B is 1.31× slower on average and its
longest decision is 57.3 s — the 50 s setup budget overshoots and sits 2.7 s under the live hard server wait limit (60 s).
Unsearched decisions 645 vs 651.

Automatic watch-replay publishing (first run) picked pair-005/game-1-A03 (Geodens, the largest arm gap) but failed: the lab
checkout has no `target/release/examples/replay_income` binary. The experiment itself was unaffected.

No change to the live teacher. The package does not raise round 1–3 charges, and the direction for Taklons and Terrans is
down. The four parts were bundled, so this run cannot say which one costs them; the research reorder and the range +1 value
act on every round and are the first suspects, the setup comparisons act only on the first few decisions.
