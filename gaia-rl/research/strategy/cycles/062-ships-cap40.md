# Cycle 062 — vm_lf_ts_ships, 20 s cap vs 40 s cap

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (vm_lf_ts_ships, the base stack, 4
comparisons, 20 s cap — the hard setting).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap40.json` — the same teacher with a 40 s cap. No
rule or value differs; only the search time.
Question (user, 2026-10-16 "넣어"): in the 060 A arm, 67% of searched round 1–3 decisions hit the 20 s cap and on
average only 2.5 of the 4 comparisons completed (Fable count). Is search amount still a lever on this stack, as it was
for the original teacher (023 +13.1, 025 +21.1)?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges. Also look at decision time (B max must stay
under the hard server limit of 60 s) and the number of decisions with unsearched comparisons. If significantly
positive, propose a review of the live wait limit and parallel search (deployment is the user's call).
6 fresh seeds (geo-quartet-687549 … 698045) × 2 seat-swapped games, agentmaco, commit b98f762, stop_round 3 (ends at
the start of round 4). 2 h 14 min wall time.
Result: lab/results/062-ships-cap40.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 154.1 | 177.0 | +22.9 | [−50.7, +96.5] |
| Taklons | 6 | 194.5 | 194.9 | +0.4 | [−24.6, +25.3] |
| Terrans | 6 | 147.3 | 171.0 | +23.7 | [−21.5, +68.9] |
| Xenos | 6 | 140.4 | 139.5 | −0.9 | [−24.0, +22.2] |
| **All** | 6 | | | **+11.5** | [−4.7, +27.8] |

Not significant; direction positive. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +71 | +17 | +40 | +116 | −82 | −25 |
| Taklons | −11 | +1 | +21 | −15 | +35 | −29 |
| Terrans | +10 | +108 | +1 | −14 | +24 | +14 |
| Xenos | +6 | +2 | −25 | −6 | −19 | +37 |
| Pair mean | +18.8 | +32.0 | +9.2 | +20.4 | −10.6 | −0.8 |

Four of six pair means are positive. Geodens and Terrans each gain about 23 on average, but both rest on one or two
large pairs (Geodens p003 +116 against p004 −82; Terrans p001 +108). Taklons and Xenos are flat. The watch replay is
p003-g0, Geodens A 107 against 223 for the B arm in the other game.

Reference VP at the start of round 4: All −0.5 [−3.5, +2.4]; Xenos +3.2, Geodens −0.2, Terrans −1.8, Taklons −3.3.
Not the verdict.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A 20 s | 944 | 11.76 s | 20.00 s | 20.24 s | 23.7 s |
| B 40 s | 943 | 19.46 s | 19.02 s | 40.16 s | 43.7 s |

No errors, timeouts or fallback decisions. B is 1.65× slower on average; its max of 43.7 s stays under the hard
server limit of 60 s. About half of all decisions take 19–20 s or more in both arms (A median sits on the cap); under
the 40 s cap most of those finish between 20 and 40 s, and at least 10% still hit the 40 s cap (p90 = 40.2 s).
Decisions with unsearched comparisons: 645 (A) vs 663 (B) — unchanged, because that count is bounded by the
comparison budget of 4, not by time. The longer cap only lets the 4 comparisons complete more often.

Reading: on vm_lf_ts_ships, doubling the search time gives about +11 charges in rounds 1–3, the same direction as the
search-amount results on the original teacher (023, 025) but smaller and not resolved by 6 pairs. Geodens and
Terrans carry the gain, Taklons and Xenos show none. No deployment proposal from this run alone: the pre-set
condition (significant positive) is not met. Candidate follow-ups (user decision pending, not queued): repeat the same
A/B on 12 fresh seeds so that 062 + the repeat (18 pairs) can resolve an effect of this size; or move on to the next
item in the agreed order (former_use on the ships stack, then the "no federation" plan in the comparison set).
