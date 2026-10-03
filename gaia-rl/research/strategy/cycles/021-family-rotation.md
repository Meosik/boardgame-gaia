# Cycle 021 — The one examined plan was always an upgrade or a research step

## Fast playout measurement (option 2, measurement only)
`examples/simulate` with a uniformly random policy: 3 games, 400 decisions in 0.54 s
(746 decisions/s, ~0.18 s per game, this container). The engine is fast enough for large-scale
self-play; a useful policy costs one native preview per candidate and will be far slower.

## Finding
Normal level = current choice + the first proposal (cycle 016 budget). `goals_for` lists
Academy/PI upgrades, then research, then colonies; families are interleaved, so the first
proposal is always from the first family. Replaying one game (smoke-sympass, rounds 2+), the
most frequent first proposals were:

| Faction | Most frequent first proposals |
|---|---|
| Terrans | Qic Academy 10, PI 5, Terraforming-5 5, Science Academy 2 |
| Taklons | PI 8, Navigation-2 8, Terraforming-3 6, Science Academy 5 |
| Xenos | Qic Academy 19, Terraforming-5 19, Terraforming-4 12, Terraforming-3 10 |

Expansion plans were never examined first. Games show the result: Terrans and Taklons end with
PI + two Academies and 1–4 mines, against B19 (Terrans: PI start is a trap, Academy for
4-charge + Gaia tech, many mines; Taklons: research lab + 5 mines, cover the map with tier-1/2
buildings).

## Change (opt-in)
`teacher_patches.family_rotation` (spec `teacher-a-search2-h1-rotation.json`): the first
proposal family rotates with the decision's step number. Neutral — no family is preferred,
nothing is added or removed. Geodens keeps its cycle-018 guide order.

## Pending A/B: A = geodens_guide (live), B = family_rotation

## A/B result (user run; A = geodens_guide live, B = family_rotation; 12 seeds, 12 pairs)

| Faction | B−A | 95% CI |
|---|---:|---|
| Geodens (unchanged; control) | −3.2 | [−10.7, +4.2] |
| Taklons | −2.5 | [−14.6, +9.6] |
| Terrans | −12.1 | [−24.5, +0.3] |
| Xenos | **+10.2** | **[+1.3, +19.1]** |
| All seats | −1.9 | [−7.6, +3.8] |

Not adopted as a whole. Xenos ranks with its own evaluator (`endpoint_value`) and gains from
examining expansion plans; Terrans and Taklons rank with `potential`, which prices building
low, and do not. Restricting the rotation to Xenos was chosen after seeing this table, so it
is confirmed separately on 12 seeds not used here (`teacher-a-search2-h1-xenos-rotation.json`).
