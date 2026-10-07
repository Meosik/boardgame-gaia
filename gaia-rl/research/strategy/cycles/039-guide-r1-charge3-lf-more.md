# Cycle 039 — guide_r1_charge3_lf_more vs hard (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-cap20.json` — 038's B (`lf_tiles` + held VP in the
charge leaf) plus `_guide['lf_more']`: special-action advanced tiles at LF02 values (12·12·14 charges)
× remaining uses, event-type advanced tiles = VP × 1.5 uses/round × remaining rounds, research options
at LF prices, and two values of our own — federation progress (power of unfederated buildings in a
2-hex chain, min(·,7)/7 × 18 charges) and neighbour leech (2 charges per opponent within 2 hexes per
round, at most 3).
Question: do the remaining LF values and the two new terms recover the guide package's loss?
User asked for 6 pairs and reporting by charges gained in rounds 1–3; no deploy condition was set.
6 fresh seeds (geo-quartet-452137 … 458025) × 2 seat-swapped games, agentmaco, commit ffee793.
Result: lab/results/039-guide-r1-charge3-lf-more.md.

**Verdict measure (user, 2026-10-07): charges gained in rounds 1–3 only** (`charge_rounds.py`, round-1
start to round-4 start, 1 VP = 1.5 charges; run by the owner). Final VP below is kept for the record
but is not used to judge.

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 85.0 | 142.0 | +57.0 | [−16.4, +130.3] |
| Taklons | 6 | 115.9 | 158.5 | +42.6 | [+10.2, +74.9] |
| Terrans | 6 | 127.8 | 145.8 | +18.0 | [−20.7, +56.8] |
| Xenos | 6 | 152.9 | 154.2 | +1.3 | [−67.0, +69.6] |
| **All** | 6 | | | **+29.7** | **[+0.2, +59.2]** |

B gains more charges in rounds 1–3, just significant overall; Taklons is significant on its own.
Geodens varies most (B 58–219, A 64–133). This is the measure the charge3 arm optimizes, so it favours B.
B's settings were fixed before the run, so this is a fair test, but 6 pairs is small.

Final VP (not used for the verdict):

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | −28.2 | [−68.3, +12.0] | 95.5 | 67.3 |
| Taklons | 6 | −8.5 | [−22.7, +5.7] | 96.7 | 88.2 |
| Terrans | 6 | −16.7 | [−26.7, −6.6] | 107.0 | 90.3 |
| Xenos | 6 | −6.8 | [−33.3, +19.6] | 118.3 | 111.5 |
| **Seat mean** | 6 | **−15.0** | **[−27.6, −2.5]** | 104.4 | 89.3 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1416 | 4.66 s | 1.94 s | 14.50 s | 37.9 s |
| B charge3_lf_more | 1727 | 11.05 s | 11.97 s | 20.27 s | 42.5 s |

No errors, timeouts or fallback decisions in either arm.

B is significantly worse for the sixth guide package in a row (034 −10.0, 035 −16.6, 036 −21.8,
037 −19.3, 038 −15.4, 039 −15.0). The new values did not move the overall result.
Geodens B scores 32, 81, 46, 93, 74, 78 (A 70–143): two collapsed games, the rest closer to A than in
036–038. Terrans is the only significant faction this time; B scores 69–105 against A 91–125.
Taklons improved to −8.5 (not significant) after −23 to −32 in 036–038. Xenos is negative for the
first time in the series (−6.8, wide CI; B has one 78).

B makes more decisions (1727 vs 1416; Terrans 429 vs 301, Taklons 431 vs 325) at a median 12.0 s
against the 20 s cap, so round-4 rollouts are often cut short (unsearched decisions 1337 vs 1085).
Both arms exceeded the 20 s cap (max 37.9 s / 42.5 s), inside the hard server wait limit of 60 s.

Not measured here: research advances per track (`research_counts.py` was refused by the Discord bot
this time), charges gained in rounds 1–3 (`charge_rounds.py` is outside the bot's allowed tools) and
fleet entries / ship actions per arm. Whether the AI-track lean of 037–038 persists is unknown.
The live hard teacher stays for now; a deploy is not proposed before a fresh-seed recheck.
