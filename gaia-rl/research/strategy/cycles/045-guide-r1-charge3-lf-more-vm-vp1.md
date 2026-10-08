# Cycle 045 — 1 VP = 1 charge + leech rule (vm_vp1)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-cap20.json` (043/044 B arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-vp1-cap20.json` — A + `install_vp1_leech`: `CHARGES_PER_VP` 1.0 everywhere
(LF01 says 1.5), and in ChargePower decline is blocked when the VP cost is ≤ 2 (charge ≤ 3), accept is blocked when it is ≥ 3.
Question: does valuing VP at 1 charge and taking cheap leech raise the charges gained in rounds 1–3?
Set before the run (user, 2026-10-08 "결과 보고 다음 단계에 전부 바꿔보던지"): judge by round 1–3 charges with held VP excluded
(`vp_rate 0`, so the two arms' VP rates do not bias the measure); the 1.5 table is reference only. After this run, the remaining frozen
formulas are to be replaced with guide values regardless.
6 fresh seeds (geo-quartet-500908 … 513365) × 2 seat-swapped games, agentmaco, commit 9579dde, stop_round 3.
Result: lab/results/045-guide-r1-charge3-lf-more-vm-vp1.md.

**Verdict measure: charges gained in rounds 1–3, held VP excluded** (`charge_rounds.py --vp-rate 0`).

| Faction | Pairs | A charges | B charges | B−A | 95% CI | at 1 VP = 1.5 |
|---|---:|---:|---:|---:|---|---:|
| Geodens | 6 | 170.4 | 148.1 | −22.3 | [−62.2, +17.7] | −24.0 |
| Taklons | 6 | 150.1 | 164.9 | +14.8 | [−10.1, +39.7] | +7.6 |
| Terrans | 6 | 160.7 | 160.7 | −0.0 | [−33.7, +33.6] | −7.0 |
| Xenos | 6 | 166.9 | 161.9 | −5.0 | [−61.5, +51.5] | −8.2 |
| **All** | 6 | | | **−3.1** | **[−19.7, +13.4]** | −7.9 [−18.7, +2.8] |

Not significant. Per-pair B−A from the game list (vp_rate 0):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −32 | −65 | 0 | +42 | −46 | −32 |
| Taklons | −13 | +16 | +13 | +12 | +58 | +3 |
| Terrans | −50 | −26 | +32 | +15 | +28 | +2 |
| Xenos | +61 | +4 | +15 | +6 | −103 | −12 |
| Pair mean | −8.5 | −17.8 | +15.0 | +18.8 | −15.8 | −9.8 |

Two of six pairs positive. Taklons is the only faction positive in 5 of 6 pairs; Geodens is negative in 4 of 6
(the faction value_max helped in 043/044). Xenos' mean is driven by p004 (A 257 in game 0, B 154 in game 1).

VP held at round 4 (not used for the verdict): −3.2 [−8.1, +1.7]; Taklons −4.8, Terrans −4.7 (both just short of
significance). With VP worth less, B spends or gives up more VP without gaining charges for it.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A lf_more_vm | 879 | 11.42 s | 15.36 s | 20.29 s | 24.1 s |
| B vm_vp1 | 823 | 12.07 s | 20.00 s | 20.29 s | 27.3 s |

No errors, timeouts or fallback decisions. B makes fewer decisions (823 vs 879) and its median hits the 20 s cap.
Unsearched decisions 622 vs 576.

No change to the live teacher. vp1 + leech rule shows no charge gain; proposed (pending user decision) to build the next step on lf_more_vm without vp1.
