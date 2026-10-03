# Cycle 022 — B19 proposal order for Terrans and Taklons

## Why
Cycle 021: Terrans and Taklons (both ranked by `potential`) end with PI + two Academies and
1–4 mines, the opposite of B19. Neutral rotation of the examined family did not help them
(Terrans −12.1, Taklons −2.5). As for Geodens (cycle 018, +15.5), the guide may decide the
ORDER of proposals — which plan the normal level examines — without adding values or bans.

## Change (opt-in, `teacher_patches.quartet_guide`, spec `teacher-a-search2-h1-quartet-guide.json`)
- Terrans (B19): Academy path first ("아광": 4-charge + Gaia 3 VP tiles), then the Gaia track,
  Gaia/Transdim colonies, ordinary expansion; PI proposals last ("PI start is a trap").
- Taklons (B19): an expansion plan first ("연5광", tier-1/2 buildings everywhere), then the
  existing two-labs path.
- Xenos and Geodens unchanged (Xenos: control; Geodens: cycle 018 order).

Smoke (geo-quartet-9840, normal, to round 3): Taklons selected `one-new-colony`, Terrans
`Terrans-academy-Gaia`; no errors.

## Pending A/B: A = geodens_guide (live), B = quartet_guide, 12 fresh seeds
geo-quartet-62074 geo-quartet-62555 geo-quartet-62634 geo-quartet-63239 geo-quartet-63574 geo-quartet-65849 geo-quartet-68390 geo-quartet-68609 geo-quartet-71365 geo-quartet-75708 geo-quartet-82639 geo-quartet-83878

## A/B result (user run; 12 fresh seeds, 12 pairs)

| Faction | B−A | 95% CI |
|---|---:|---|
| Geodens (unchanged) | +2.4 | [−2.6, +7.5] |
| Taklons | **−9.0** | **[−14.9, −3.1]** |
| Terrans | −3.5 | [−11.2, +4.2] |
| Xenos (unchanged) | −4.6 | [−12.8, +3.7] |
| All seats | **−3.7** | **[−6.1, −1.3]** |

Not adopted. Expansion-first hurt Taklons (rotation gave −2.5 in the same direction). For
`potential`-ranked factions, changing *which* plan is examined does not help while the
evaluation itself prices building low; the Geodens gain (cycle 018) may owe more to its
two-income look-ahead than to the order. Next: more search with the same evaluation
(cycle 023, 4 comparisons instead of 2).
