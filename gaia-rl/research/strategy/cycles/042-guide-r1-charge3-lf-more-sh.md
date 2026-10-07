# Cycle 042 — sheden_r1 on top of guide_r1_charge3_lf_more (20 s cap, games stop at round 4)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-cap20.json` (039/040 B arm, 041 A arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-sh-cap20.json` — A + `_guide['sheden_r1']`: round-1 openings
are tried in the sheden #4 order (`SHEDEN_OPENINGS`, Geodens included), and when a round-1 academy goal makes no
progress for lack of ore, terraforming 0→1 research (2 ore) is tried first. No academy_r1. Order only, no new values.
Question: do the sheden #4 openings raise charges gained in rounds 1–3?
Set before the run (user, 2026-10-07 "진행해"): judge by round 1–3 charges; also count round-1 buildings.
6 fresh seeds (geo-quartet-475169 … 488133) × 2 seat-swapped games, agentmaco, commit 6f00112, stop_round 3.
Result: lab/results/042-guide-r1-charge3-lf-more-sh.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5 charges).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 136.9 | 113.7 | −23.2 | [−85.5, +39.0] |
| Taklons | 6 | 147.1 | 153.1 | +6.0 | [−22.2, +34.2] |
| Terrans | 6 | 169.7 | 146.8 | −22.9 | [−54.4, +8.7] |
| Xenos | 6 | 136.2 | 129.3 | −7.0 | [−33.0, +19.0] |
| **All** | 6 | | | **−11.8** | **[−37.1, +13.6]** |

Not significant. Unlike 041, the arms play differently in every pair (no identical pairs).
Per-pair B−A from the game list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −3 | −34 | +11 | +14 | **−139** | +12 |
| Taklons | +10 | −46 | +26 | +8 | +10 | +27 |
| Terrans | +29 | −31 | −7 | −30 | −44 | −55 |
| Xenos | −27 | −2 | +34 | −18 | −33 | +4 |

Geodens' mean comes from one seat (pair-004/game-0-A01, B 68 vs A 207); the other five pairs average about 0.
Terrans lose in 5 of 6 pairs — the most consistent signal, though the interval still covers 0.
Taklons gain in 5 of 6 pairs (sheden #4 recommends the round-1 academy only for Taklons among the four).

Round-1 buildings (`academy_rounds.py`) were not counted: the tool is outside the Discord bot's permissions.

VP held at round 4 (not used for the verdict): −1.2 [−3.9, +1.5]; Terrans −4.7 [−8.2, −1.1].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A lf_more | 781 | 12.05 s | 17.75 s | 20.25 s | 27.4 s |
| B lf_more_sh | 785 | 11.96 s | 17.30 s | 20.26 s | 27.7 s |

No errors, timeouts or fallback decisions. Same cost per decision in both arms.

No change to the live teacher; sheden_r1 shows no charge gain, with a possible Terrans loss.
