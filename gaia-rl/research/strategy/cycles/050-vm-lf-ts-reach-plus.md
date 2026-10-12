# Cycle 050 — range +1 alone (vm_lf_ts_reach_plus)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (047 B arm, same A as 048 and 049).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-plus-cap20.json` — A + part C of `install_reach` only:
expansion value also counts planets reached at the next navigation range step, and booster 5 keeps its table value only
when a free gaiaformer reaches a transdim planet at that range.
Question (user, 2026-10-12 "부품 분리해서 원인 파악해"): part split 2 of 3 — does range +1 carry any of the 048 loss?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges.
Same 6 seeds as 048 (geo-quartet-534437 … 536873) × 2 seat-swapped games, agentmaco, commit dd9dce5, stop_round 3.
This is a cause-separation run on seeds already used, not a fresh-seed confirmation.
Result: lab/results/050-vm-lf-ts-reach-plus.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 144.3 | 133.6 | −10.8 | [−45.4, +23.8] |
| Taklons | 6 | 150.5 | 161.4 | +10.9 | [−37.2, +59.1] |
| Terrans | 6 | 169.1 | 165.7 | −3.4 | [−36.1, +29.3] |
| Xenos | 6 | 159.5 | 147.4 | −12.0 | [−44.7, +20.6] |
| **All** | 6 | | | **−3.8** | **[−27.3, +19.7]** |

Not significant, close to zero. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −41 | −60 | +28 | −1 | +0 | +8 |
| Taklons | +22 | +31 | −18 | −65 | +66 | +30 |
| Terrans | +3 | −37 | −1 | −43 | +26 | +32 |
| Xenos | −9 | +23 | −61 | −37 | +6 | +5 |
| Pair mean | −6.1 | −10.7 | −12.7 | −36.5 | +24.6 | +18.6 |

Two pair means are positive, four negative. No faction has a consistent sign: Taklons is positive in 4 of 6 pairs,
Terrans and Geodens in 3 of 6, Xenos in 3 of 6. p003 is the only pair where the loss is large (Taklons B 100 vs A 166,
Terrans B 147 vs A 191, Xenos B 99 vs A 136). p004 Geodens is low in both arms again (A 86, B 87).

Compared with 048 and 049 on the same seeds:

| Run | B parts | All | Taklons | Terrans | Geodens | Xenos |
|---|---|---:|---:|---:|---:|---:|
| 048 | setup + range +1 + focus (nav bug) | −10.9 | −24.8 | −38.4 | +17.7 | +2.0 |
| 049 | focus only (fixed) | −20.9 | −19.3 | −22.3 | −35.0 | −6.8 |
| 050 | range +1 only | −3.8 | +10.9 | −3.4 | −10.8 | −12.0 |

The Taklons and Terrans loss seen in 048 and 049 is absent here: range +1 does not reproduce it, which fits 049's finding
that the research reorder (part D) is its source. The 048 negative pairs p001–p003 are negative here too, but p001 and
p002 are small (−11, −13) and split across factions. As in 049 the A arm means move between runs on the same seeds
(Terrans 159.0 → 169.1, Geodens 162.3 → 144.3), so the pair-by-pair comparison across runs is loose.

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 6 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 0 | 2 | 15 | 1 | 6 | 4 | 28 |
| A | Taklons | 4 | 0 | 16 | 3 | 1 | 5 | 29 |
| A | Terrans | 4 | 1 | 15 | 1 | 3 | 5 | 29 |
| A | Xenos | 4 | 14 | 3 | 0 | 6 | 0 | 27 |
| B | Geodens | 0 | 0 | 15 | 2 | 2 | 3 | 22 |
| B | Taklons | 6 | 4 | 14 | 1 | 2 | 3 | 30 |
| B | Terrans | 4 | 4 | 14 | 0 | 4 | 4 | 30 |
| B | Xenos | 3 | 15 | 3 | 0 | 5 | 0 | 26 |

Range +1 moves research only a little: Taklons and Terrans take navigation 4 times each over 6 seats (A 0 and 1), without
giving up AI (16 → 14, 15 → 14). That is the mild shift the part was meant to allow, unlike 048 B (Nav 18 and 13) and
049 B (AI 15 → 4 for Terrans). Geodens B researches less in total (28 → 22, mostly Eco 6 → 2) and takes no navigation;
why is not known. `academy_rounds.py` and `action_counts.py` are outside the bot's allowed tools, so buildings and
action counts were not checked.

VP held at round 4 (not used for the verdict): −0.9 [−6.0, +4.1].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts | 864 | 11.90 s | 18.42 s | 20.22 s | 27.6 s |
| B vm_lf_ts_reach_plus | 872 | 12.61 s | 20.02 s | 20.25 s | 22.5 s |

No errors, timeouts or fallback decisions. Unsearched decisions 611 vs 625. Watch-replay publishing picked
pair-004/game-0-A01 and failed again for the same reason as 048 and 049 (no `replay_income` example binary in the lab
checkout).

No change to the live teacher. Range +1 (part C) shows no effect either way at 6 pairs: it is not what cost Taklons and
Terrans in 048, and it is not shown to help. It stays out of the base stack, which remains vm_lf_ts. 051 (setup parts)
on the same seeds is the last part; 052 (hard vs vm_lf_ts, 12 fresh pairs) follows.
