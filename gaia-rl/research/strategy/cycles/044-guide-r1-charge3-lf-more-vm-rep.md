# Cycle 044 — repeat of 043 (value_max + ts_chain) on fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-cap20.json` (039/040 B arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-cap20.json` — A + `install_value_max` (value_max, ts_chain), unchanged from 043.
Question: does 043's +17.4 charge gain reproduce on fresh seeds?
Set before the run (user, 2026-10-08 "진행"): judge by round 1–3 charges; if the gain reproduces, propose hard vs lf_more_vm directly.
6 fresh seeds (geo-quartet-496607 … 500824) × 2 seat-swapped games, agentmaco, commit 95f9c7b, stop_round 3.
Result: lab/results/044-guide-r1-charge3-lf-more-vm-rep.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5 charges).

| Faction | Pairs | A charges | B charges | B−A | 95% CI | 043 B−A |
|---|---:|---:|---:|---:|---|---:|
| Geodens | 6 | 156.0 | 186.7 | +30.7 | [−22.8, +84.2] | +14.9 |
| Taklons | 6 | 155.8 | 152.0 | −3.8 | [−19.7, +12.0] | +12.7 |
| Terrans | 6 | 148.7 | 163.9 | +15.2 | [−30.4, +60.8] | +34.5 |
| Xenos | 6 | 155.6 | 134.2 | −21.3 | [−48.1, +5.4] | +7.4 |
| **All** | 6 | | | **+5.2** | **[−18.5, +28.8]** | +17.4 |

Not significant, and smaller than 043. Per-pair B−A from the game list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +76 | +16 | −28 | −21 | +44 | +97 |
| Taklons | +1 | +18 | −22 | +5 | −10 | −17 |
| Terrans | +82 | +56 | −9 | −31 | −2 | −4 |
| Xenos | −6 | −36 | +13 | −50 | −44 | −4 |
| Pair mean | +38.3 | +13.5 | −11.5 | −24.3 | −3.0 | +18.0 |

Three of six pairs positive. Geodens is the only faction positive in both runs (4 of 6 pairs each time) —
the target of the value_max fix (042 p004-g0 steps 18 and 54). Terrans' 043 gain (5 of 6 pairs) does not repeat
(2 of 6; the mean comes from p000 and p001). Xenos turns negative in 5 of 6 pairs.

043 + 044 pooled (12 pair means, no new run): about +11 [−7, +30], not significant.
By faction, averaging the two runs: Geodens ≈ +23, Terrans ≈ +25, Taklons ≈ +4, Xenos ≈ −7.

VP held at round 4 (not used for the verdict): −2.2 [−5.5, +1.1].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A lf_more | 868 | 11.01 s | 14.30 s | 20.13 s | 21.3 s |
| B lf_more_vm | 830 | 11.72 s | 16.96 s | 20.16 s | 21.2 s |

No errors, timeouts or fallback decisions. B's median is again higher (17.0 s vs 14.3 s). Unsearched decisions 609 vs 608.

No change to the live teacher. The 043 gain did not reproduce clearly: value_max + ts_chain is at best a small
gain over lf_more, concentrated in Geodens, and the pre-set condition for a direct hard vs lf_more_vm test is not met.
