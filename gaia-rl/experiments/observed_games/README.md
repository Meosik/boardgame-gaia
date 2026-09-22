# observed_games — proposals from recorded human games

Opt-in candidates for the existing paid native search, drawn from games recorded
off uiqoo. **Not** rewards, price changes, forced openings or a default teacher.
An A/B match decides whether a proposal set is kept.

## OB01 (2026-09-16, one game)

Source and limits: [research/strategy/observed-uiqoo-20260916.md](../../research/strategy/observed-uiqoo-20260916.md).
One game of unknown player strength, so every proposal is a hypothesis.

| Faction | Proposal | Offered when |
|---|---|---|
| BalTaks | Gaiaformer→QIC, then Rebellion 3-QIC tech (Gaia project first if no former is back); T F Mars tech bonus | former in Gaia area or undeployed; ≥3 standard techs |
| Ivits | next Gaia track step; a Gaia project; Rebellion tech | Gaia < 5; undeployed former |
| Taklons | Planetary Institute in round 3 (rounds 1–2 already come from B10/PG21) | round 3, no PI |
| Firaks | research and PI-downgrade research on the two most advanced unfinished tracks | a track at 1–4; downgrade needs PI + Lab |

`TimedPreparationTeacher(observed_factions=...)` enables them per faction.
`faction_teachers.paths.action_matches` now also matches a `Type:Track` subtype so a
downgrade can target one track.

## A/B match

```sh
cd gaia-rl/experiments
../.venv/bin/python -m observed_games.ab_match --seeds ob01-2825 ob01-3750 ob01-7214 \
  --output ../runs/ob01-ab-<date> --preflight-only   # drop the flag to play
```

Each seed has exactly these four factions and runs two games: two factions use B
(OB01 on) in one game and A in the other, in identical seats. `ob01-2825` also has the
observed seat order. A game takes roughly 1–1.5 hours on the adaptive clock.
The run pins every `gaia-rl/experiments/*.py` hash, so editing any experiment file
while it runs stops it rather than mixing sources.

```sh
../.venv/bin/python -m unittest observed_games.test_ob01
```
