# Cycle 056 — every timing rule at once (when_all)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (vm_lf_ts_ships, the base stack).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-cap20.json` — A + every timing rule from the
guides, order only: 1b round 1 research track (as in cycle 055), 2 contested moves first, 3 per-ship entry timing,
4 leech (2 charges accepted to round 5, 3 charges to round 4, 4+ declined), 5 resource/income artifacts only in round 1
with three tokens left, 6 Academy type (rounds 1–3 knowledge, QIC after a Rebellion entry; rounds 5–6 QIC),
8 keep the last mine when an asteroid or protoplanet is in reach, 9 Taklons PI from round 4, Twilight range move
skipped when knowledge is a multiple of 4. Rules 7 (Research Lab even knowledge) and 10 (4 QIC) left out.
Question (user, 2026-10-14 "나머지 적용 안 한 거까지 한 번에 할걸" → "해보자"): do all the timing rules together gain
round 1–3 charges?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; compare with cycle 055 (1b alone); also look at
error games (first league run of rules 5–9), unsearched decisions, research tracks and replays (user: power problem).
6 fresh seeds (geo-quartet-612773 … 629784) × 2 seat-swapped games, agentmaco, commit d9aaafe, stop_round 3.
Result: lab/results/056-vm-lf-ts-ships-when-all.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 166.6 | 89.5 | **−77.1** | **[−134.0, −20.3]** |
| Taklons | 6 | 181.9 | 161.2 | −20.7 | [−60.9, +19.5] |
| Terrans | 6 | 159.7 | 183.7 | +24.1 | [−45.0, +93.1] |
| Xenos | 6 | 159.7 | 167.2 | +7.5 | [−27.2, +42.2] |
| **All** | 6 | | | **−16.6** | **[−34.7, +1.5]** |

Not significant overall (the interval just touches 0), but Geodens loses significantly. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −34 | −81 | −40 | −58 | −69 | −182 |
| Taklons | −81 | −32 | +7 | −23 | −28 | +32 |
| Terrans | +74 | −25 | −44 | +45 | +120 | −26 |
| Xenos | +38 | +14 | −40 | −20 | +7 | +45 |
| Pair mean | −0.8 | −31.0 | −29.3 | −14.0 | +7.5 | −32.8 |

Five of six pair means are negative. Geodens loses in all six pairs; in four of the six games Geodens on the B arm
gets 52–92 charges (A arm 114–234). The worst is p005-g1 (B 52 against A 234 in the other game), the auto-published
watch replay. Taklons lean negative (4 of 6); Terrans swing ±120 and Xenos is noise.

Against the earlier timing tests: 054 (rules 1–3) −20.7, 055 (1b alone) −4.6, 056 (1b + 2–6, 8, 9, Twilight) −16.6.
1b alone did not lose, and the Geodens loss is new here (055 Geodens −15.5, 054 −23.9), so the loss comes from rules
2–9; rules 2–3 were also in 054 and Geodens lost there too.

VP held at round 4 (reference only): All −1.2 [−6.7, +4.4]; Geodens −0.2, Taklons −6.3, Terrans +2.3, Xenos −0.5.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts_ships | 928 | 11.95 s | 18.87 s | 20.25 s | 28.9 s |
| B when_all | 967 | 11.53 s | 18.45 s | 20.23 s | 25.6 s |

No errors, timeouts or fallback decisions in the first league run of rules 5–9. Unsearched decisions 670 vs 684, so the
when stack did not starve the comparisons. B made 39 more decisions (Taklons 230 → 254).

Not measured: research tracks (`research_counts.py` was refused on the bot) and the replay check. To fill in:
`GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:tools .venv/bin/python tools/research_counts.py
~/projects/gaia-lab/gaia-rl/runs/lab-056-vm-lf-ts-ships-when-all --rounds 1-3` (from `gaia-rl`).

Not significant, loss direction. The bot proposed rejecting the bundle and splitting rules 2–9; the user decided
instead (2026-10-14 "일단 다 넣고, 리플레이 보면서 수정하는 게 나을 수도"): **the base stack becomes
vm_lf_ts_ships_when_all**, and the rules are fixed from replays (starting with p005-g1 B Geodens) rather than by
component A/B. No change to the live teacher.
