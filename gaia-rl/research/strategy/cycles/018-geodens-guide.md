# Cycle 018 — Geodens guide as proposal order and look-ahead

## Change
`tools/teacher_patches.py` `geodens_guide` (spec `tools/teacher-a-search2-h1-geodens.json`),
on top of cycle 017's symmetric pass. From B14 (read in full; `../geodens-guide-b14.md`) and
B19, for Geodens only:

- proposal order: after the PI, Terraforming 3 and Navigation 2 first; new planet types
  cheapest first (terraform steps + QIC for range); from round 4, the next AI level;
- look-ahead: Geodens compares routes at the second income boundary, so the PI's
  3 knowledge per new type falls inside the comparison.

No value term, coefficient or prohibition is added; the order only decides which plan the
normal level (current choice + one proposal) examines.

## Smoke (2 seeds, normal, this container)
geo-quartet-340: Geodens 72 → 122 (8 planet types, terraforming 5, navigation 5);
geo-quartet-24: identical game (76) — the T3 proposal was examined but `potential` rejected
spending 4 knowledge (−0.7 to −5) and ore stayed at 0–3. Geodens thinking: mean 6.5–29 s.

## A/B (user run: A = symmetric pass, B = + Geodens guide; 12 seeds, 11 complete pairs)

| Faction | B−A | 95% CI |
|---|---:|---|
| Geodens | **+15.5** | **[+3.9, +27.2]** |
| Taklons | −3.5 | [−10.4, +3.3] |
| Terrans | −0.2 | [−4.7, +4.3] |
| Xenos | −3.5 | [−7.6, +0.7] |
| All seats | +2.1 | [−1.0, +5.2] |

Only Geodens' play changed; the small losses of its neighbours are consistent with a
stronger Geodens taking contested planets. Adopted for live AI seats (`tools/ai_worker.py`).
Live play keeps its 5 s cap, which may cut some two-income Geodens comparisons short; the
proposal order still applies.

## What remains
Seed 24 shows the open problem: resource prices in `potential` reject research and
building that the guide calls for. That is a judgment (coefficient) problem, left to the
learned value per the agreed scope.
