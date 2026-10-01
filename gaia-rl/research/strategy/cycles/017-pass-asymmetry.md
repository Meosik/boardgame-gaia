# Cycle 017 — Pass asymmetry in `potential` and the Geodens diagnosis

## Question
Why does the shared teacher (notably Geodens) pass with unspent resources?

## Method
`tools/diagnose_passes.py` plays one teacher self-play game and records every Pass with
resources and the best candidate of each action type. Lineup Xenos/Taklons/Terrans/Geodens
(seeds `geo-quartet-*`, found with `examples/faction_lineups ... Xenos,Taklons,Terrans,Geodens`).

## Finding 1 — fact-level bug (all 16 `potential`-based factions)
`four_factions/value.py::potential` adds the booster's next income (`.7 x` its value) only
when the player has *already* passed, and the held booster's pass VP appears only after the
pass. An unpassed player collects both when passing later this round, so every Pass scored
+2 to +7 over any other action. Seed geo-quartet-340, easy: the Geodens Pass score equalled
exactly that booster term in rounds 2, 3 and 5 (2.66, 2.10, 2.52); rounds 1 and 4 added the
booster-6 pass VP (3 per unspent Gaiaformer).

Fix (opt-in, frozen tree untouched): `tools/teacher_patches.py` `symmetric_pass` adds the held
booster's pass VP and the best pool booster's income term to unpassed action-phase states.
`booster_pass_vp` matches the engine on 292 of 293 native passes over three games (the one
difference, Xenos +1, is a pass effect other than the booster). Tests: `tools/test_teacher_patches.py`.

Easy level, 4 seeds, all seats patched vs none (self-play, not a paired A/B):

| Faction | VP base → patched | Leftover ore+credits/3+knowledge | Structures |
|---|---|---|---|
| Terrans | 61.0 → 69.2 | 25.8 → 21.7 | 4.5 → 6.0 |
| Taklons | 52.0 → 60.2 | 20.9 → 17.2 | 5.0 → 6.0 |
| Geodens | 51.8 → 50.2 | 23.8 → 24.0 | 5.8 → 5.5 |
| Xenos (other evaluator) | 89.8 → 100.2 | 4.6 → 5.5 | 13.0 → 13.2 |

Strength must be judged by the paired 12-seed A/B below, at the normal level.

## Finding 2 — Geodens: judgment, left to learning
With the bias removed Geodens still builds little: Build/Upgrade previews score −2 to −11
because `materials` prices ore at 3 VP (first 5) and Geodens' expansion needs multi-step
terraforming ore. That is a coefficient question (resource price vs. structure value), outside
the fact-only scope agreed for teacher fixes; it is left to the learned value.

## Pending A/B (run by the user)
```sh
cd gaia-rl
GAIA_ENGINE_FIXES_2=1 .venv/bin/python tools/teacher_ab.py run \
  --teacher-a tools/teacher-a-search2-h1.json --teacher-b tools/teacher-a-search2-h1-sympass.json \
  --games 24 --seeds geo-quartet-24 geo-quartet-340 geo-quartet-2090 geo-quartet-2683 geo-quartet-4321 \
    geo-quartet-4513 geo-quartet-5088 geo-quartet-7532 geo-quartet-7597 geo-quartet-7615 geo-quartet-9108 geo-quartet-9718 \
  --comparisons 2 --jobs 4 --fast-copy --output runs/ab-sympass-geo-quartet
```
