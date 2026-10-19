# Cycle 080 — 062 repeat: vm_lf_ts_ships, 20 s cap vs 40 s cap, 12 fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the base stack vm_lf_ts_ships (4
comparisons, 20 s cap — the hard setting).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap40.json` — the same teacher with a 40 s cap. No rule
or value differs; only the search time.
Queued by the user on 2026-10-18 13:45 ("배포 다 하고 실험 다 시작하면 안되나", E5) as the repeat of 062, which was
+11.5 [−4.7, +27.8] on 6 pairs (Geodens and Terrans positive, four pairs positive, B mean 19.5 s, max 43.7 s). The plan
set before the run: 12 fresh seeds so that 062 + 080 (18 pairs) can resolve an effect of about +11; judge by round 1–3
charges at 1 VP = 1.5 charges; also read decision time (B max under the hard server limit of 60 s, p90) and the number
of decisions with unsearched comparisons; if the 18-pair sum is significantly positive, propose a review of the live
hard wait limit and parallel search (`GAIA_AI_PARALLEL`), deployment being the user's call.
12 fresh seeds (geo-quartet-841643 … 859726) × 2 seat-swapped games, agentmaco, commit d92a650, stop_round 3 (ends at the
start of round 4), 4 h 19 min wall time. Result: lab/results/080-ships-cap40-rep.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 12 | 169.4 | 176.9 | +7.4 | [−10.3, +25.2] |
| Taklons | 12 | 179.4 | 177.3 | −2.1 | [−27.2, +23.0] |
| Terrans | 12 | 169.1 | 191.1 | **+21.9** | [−7.4, +51.2] |
| Xenos | 12 | 141.0 | 163.9 | **+22.8** | [−4.2, +49.8] |
| **All** | 12 | | | **+12.5** | **[+1.7, +23.3]** |

**Significant on its own** (the CI excludes 0). Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 | p006 | p007 | p008 | p009 | p010 | p011 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | +21 | −11 | −16 | +30 | −26 | **+72** | +19 | +2 | +11 | −19 | +23 | −16 |
| Taklons | −8 | −47 | +12 | +40 | +1 | **−70** | +9 | +27 | +3 | **+73** | −41 | −24 |
| Terrans | +32 | **+95** | +31 | −8 | −1 | **+75** | +38 | −4 | +15 | **+83** | −41 | −50 |
| Xenos | +11 | +1 | +58 | −31 | −35 | +26 | +5 | +67 | **+100** | +5 | −4 | +72 |
| Pair mean | +13.9 | +9.2 | +21.1 | +7.8 | −15.5 | +25.8 | +17.5 | +23.3 | +32.1 | +35.3 | −15.6 | −4.5 |

Nine of twelve pair means are positive; the three negative pairs (p004, p010, p011) are −4 to −16, the positive ones go
up to +35. Per faction: Terrans positive in 7 pairs with four large gains (+75 to +95) against two losses of −41 and −50;
Xenos positive in 9 pairs (p008 +100 is the posted replay `pair-008/game-1-A12` seat 2, Xenos A 75 against B 175 in the
other game; p011 +72 is Xenos A 70 against B 142); Geodens 7 positive, mostly small; Taklons 7 positive but the large
seats cancel (p009 +73 against p005 −70, p001 −47, p010 −41). Unlike 062, where Geodens and Terrans carried the gain,
here Terrans and Xenos do; Geodens drop from +22.9 to +7.4 and Xenos rise from −0.9 to +22.8, so the faction split in
either run is noise around a general effect.

**062 + 080 pooled, 18 pairs** (pair means from both seat lists; same method as the per-run CI): All **+12.2**
**[+4.2, +20.2]**, 15 of 18 pair means positive. Per faction (pair-weighted): Terrans +22.5, Xenos +14.9, Geodens +12.6,
Taklons −1.3. The pre-set condition (18-pair sum significantly positive) is met.

Reference VP at the start of round 4: All +2.4 [−1.6, +6.3]; Taklons +4.5, Xenos +3.9, Geodens +1.2, Terrans 0.0. Not
the verdict, but the same direction as the charges.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A 20 s | 1816 | 11.98 s | 20.01 s | 20.27 s | 24.4 s |
| B 40 s | 1886 | 19.59 s | 20.07 s | 40.16 s | **46.6 s** |

No errors, timeouts or fallback decisions. B is 1.63× slower on average (062: 1.65×); its max of 46.6 s (062: 43.7 s)
stays under the hard server guard of 60 s with about 13 s to spare. Both medians sit at 20 s: half of all decisions take
the full 20 s in A, and under the 40 s cap the median is still 20 s while p90 moves to 40.2 s — so about half the
decisions finish inside 20 s either way, and the other half use the extra time, with at least 10% hitting 40 s. Decisions
with unsearched comparisons 1284 (A) vs 1342 (B) — unchanged in proportion (71% of decisions in both arms), because that
count is bounded by the comparison budget of 4, not by time. Decisions per faction A / B: Geodens 389 / 423, Taklons
466 / 476, Terrans 460 / 469, Xenos 501 / 518.

The 079 question (both arms had one decision above 100 s, attributed to the 078 `explain_ab_decisions.py` runs
overlapping on the same host) is answered by this run: with nothing else running, A max 24.4 s and B max 46.6 s — the
same as 062 (23.7 s / 43.7 s). The 079 outliers were host load, not the teacher.

Reading. Search time is still a lever on this stack: doubling the cap from 20 s to 40 s gains about +12 charges in
rounds 1–3 (≈ 8 VP at 1.5 charges per VP), significant on 12 fresh pairs alone and on the 18-pair pool, in the same
direction as 023 (+13.1) and 025 (+21.1) on the original teacher but smaller. It is a pure time change — no rule, no
value, no code path differs — so there is nothing to adopt into the stack; the lever is the live hard level setting.

**Proposal (user decision, nothing changed, nothing deployed)**: raise the live hard cap from 20 s to 40 s. What it
touches: `tools/ai_worker.py` `LEVELS['hard']['max_seconds']` 20 → 40 (one number, the measured B setting); the server
guard `gaia-server/src/ai.rs guard_timeout` already gives hard at least 60 s, which the measured max of 46.6 s stays
under, so it can stay — raising it to 90 s (`GAIA_AI_TIMEOUT_SECS=90` in `.env`, no code change) would widen the margin
from 13 s to 43 s at the cost of a slower recovery from a genuinely hung worker. The cost to players is the wait: the
hard AI's median turn stays 20 s but its slowest 10% go from 20 s to 40 s, and a 4-AI room would feel it on every
round. Parallel search (`GAIA_AI_PARALLEL=N`, 024: 1.55× faster, identical decisions) is the way to buy the extra search
without the extra wait — with N=2 a 40 s cap would finish in roughly the time the 20 s cap takes now — but whether
`.env` sets it on the live host is not known to the bot (key name only; `grep -c GAIA_AI_PARALLEL ~/gaia-live/.env`),
and the live host also runs the lab at lowest CPU priority, so the 4 lab jobs would then contend with up to N×rooms AI
processes. This proposal rides on the pending D1 teacher deployment (the hard setting is in the same `ai_worker.py`).

Candidate follow-ups (user decision pending, not queued): (a) adopt the 40 s cap in the next deployment together with
D1, with or without `GAIA_AI_PARALLEL`; (b) measure the next step first — 40 s vs 60 s on the same stack (6 pairs,
stop_round 3; needs a `...-ships-cap60.json` spec and a server guard above 60 s if it were ever deployed), to see whether
the gain keeps growing or saturates; (c) measure parallel search on this stack (cap 40 s, `GAIA_AI_PARALLEL=2` vs 1):
decisions should be identical by 024, so this is a timing check, not an A/B — it tells whether the 40 s cap can be
deployed with no extra wait. The bot's recommendation is (a) for the setting and (c) as a cheap timing check before the
deployment, with (b) only if the user wants to know where the lever stops; the next rule experiment slot stays with
E9 (b) geodens_b14_tech alone or E7 (ships_land_safe).
