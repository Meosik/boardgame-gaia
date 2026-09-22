# bgs_records — recorded boardgamers.space games as training data

Mirrors finished Gaia Project games from [boardgamers.space](https://www.boardgamers.space),
normalises each one into rounds, seats and attributed resource changes, and emits either
decision rows for learning or counted observations for a teacher to consult.

Everything is derived from the site's own move log. Nothing here runs the rules.

## What a log can and cannot tell you

Measured against the final board of every mirrored game, not assumed:

| | |
|---|---|
| **Exact** | victory points, every structure on the map, research levels the seat advanced, QICs, each round's turn order |
| **Close but wrong sometimes** | credits, ore, knowledge — about 1% of seats drift, so they are **not** emitted |
| **Unavailable** | the power bowls; their tokens move between areas the log never names |
| **Unavailable** | the legal-move list — no engine, so no "what else could they have played" |

`state.verify` re-checks the rebuild against each game's own recorded final board, and a
game that fails contributes no rows at all. That check is what stops an upstream notation
change from quietly producing plausible, wrong training data.

## Before you rely on this corpus

Every one of the site's 51,572 finished games was counted on 2026-09-16 — a full census,
not a sample. `python -m bgs_records census` repeats it without downloading any game.

| setup | games |
|---|---|
| finished, uncancelled Gaia Project games | **40,213** |
| 2 players, base game | 20,005 |
| **4 players, base game** | **14,434** |
| 3 players, base game | 5,468 |
| any player count, `frontiers` | 276 |
| any player count, `spaceships` | 28 (not usable — see below) |
| any player count, `lost-fleet` | **1** |

Read those carefully:

- **The archive holds one Lost Fleet game.** Not "few" — one, and it is two-player. Four
  players with the expansion does not exist here, which is why the selection widens to
  four-player base game by default. Base-game play is evidence about shared mechanics; it
  is not evidence about the expansion, and rows from it should not be treated as such.
  For the expansion itself, self-play is the only source.
- **The 28 games tagged `spaceships` are not Lost Fleet records.** The name looks like an
  early one for the same expansion, and some are literally called `playtest-spaceships-N`,
  but their gameplay records carry no expansion at all: no `expansions`, no engine
  version, no spaceship tiles, and — in a 467-move game — not one spaceship move. They
  are abandoned playtests from before the expansion existed, and they never finished, so
  the pipeline refuses them on the `ended` check regardless.
- **Four-player base game is abundant**, so nothing about the fallback path is constrained
  by corpus size.
- **The newest games are not representative.** Gaia Project is 36-48% of the most recent
  pages but 75-90% deeper in, so `fetch --start` matters when crawling for volume.
- **A listing entry marked `ended` may be an abandoned game**, and part of the older
  archive keeps final data for only some seats. Both are refused; see the pitfalls below.
- **`frontiers` games are refused, not mislabelled.** That expansion adds colony ships,
  customs posts and trade ships this package does not read and the engine does not model.
- Faction variants differ (`standard`, `more-balanced`, `beta`, and unrecorded on older
  games), as do auction modes and engine versions. Every row carries all of them in
  `setup`, and the report counts an unrecorded variant in its own bucket.
- These are recorded human games. A frequent move is a popular move, not a correct one.

## What gets selected

`report` and `build` both apply one policy, and print what it dropped:

1. **Four players with Lost Fleet.** That is the target setup.
2. **Widen to four-player base game if fewer than 30 such games exist**, with a loud note
   on the output. The expansion is rare enough that this is the normal outcome; base-game
   rows are evidence about shared mechanics, not about the expansion. `--strict-expansion`
   refuses to widen and returns whatever Lost Fleet games there are, however few.
3. **Learn only from seats rated 120+ going in** — seat by seat, not game by game. A
   strong player's moves are a strong player's moves even with a beginner at the table,
   so a mixed game contributes the seats that clear the floor and drops the ones that do
   not. A game where nobody clears it is dropped entirely. The rating used is the one
   carried *into* the game, never the post-game one, which already knows the result.

Every row carries `setup.table_elo`, the whole table's starting ratings, so a consumer
can still weigh a move played against three equals differently from one played against a
beginner. `--all-seats-rated` restores the stricter reading — only games where everyone
cleared the floor — for a consumer that wants it.

Ratings live only in the listing endpoint. A seat with no rating never qualifies, and a
game mirrored without its listing record has no ratings at all; `backfill` fetches the
missing records.

`--min-elo` tunes the floor (`0` disables it). Measured over 644 mirrored seats: the
median is 190, the 10th percentile is 100, and there is a floor cluster of new or
barely-rated accounts below 100. Over 3,109 mirrored games the per-seat rule keeps 2,982
four-player games and 9,904 of their 12,008 seats; 20 games are dropped outright because
no seat cleared the floor.

## Use

```sh
cd gaia-rl/experiments

# Mirror games. Resumable: a second run re-downloads nothing.
# --start matters: Gaia Project is a much smaller share of the newest games.
python -m bgs_records fetch --wanted 500 --start 30000

# Fill in listing records (ratings) for anything mirrored without one.
python -m bgs_records backfill

# Counted observations, on the terminal and optionally as JSON.
python -m bgs_records report --json /tmp/catalog.json

# Decision rows for learning, one JSON object per line.
# A '.gz' suffix compresses about thirtyfold — the whole four-player corpus is
# gigabytes as plain JSONL, and a few hundred megabytes gzipped.
python -m bgs_records build --out /tmp/decisions.jsonl.gz --min-elo 150
```

The mirror defaults to `gaia-rl/research/bgs-records` and is gitignored: it is
re-fetchable, unlike `research/strategy`, which holds source documents.

## Row shape

Line 1 is a schema header; every later line is one decision.

```jsonc
{
  "game_id": "Amphibian-mint-2421", "move_index": 11, "round": 1, "phase": "roundMove",
  "seat": 0, "player": "b4e7dac7ae6ddcce", "faction": "terrans", "engine_faction": "Terrans",
  "action":   { "command": "build",
                "clauses": [{"command": "build", "args": ["lab", "3A1"]},
                            {"command": "tech", "args": ["nav"]},
                            {"command": "up",   "args": ["nav"]}],
                "raw": "terrans build lab 3A1. tech nav. up nav (0 ⇒ 1)." },
  "features": { "turn_order": [2, 0, 3, 1], "turn_position": 1,
                "victory_points": 10, "vp_behind_leader": 0, "buildings": {"ts": 1, "…": 0},
                "colonised": 2, "research": {}, "tech_tiles": [], "booster": "booster6",
                "federations": [], "round_scoring": "score3", "final_scorings": ["gaia"],
                "opponents": [{"seat": 1, "faction": "xenos", "victory_points": 9,
                               "colonised": 2, "buildings": {"m": 2, "…": 0},
                               "research": {}, "federations": 0}] },
  "outcome":  { "final_victory_points": 121, "victory_points_still_to_come": 111,
                "placement": 2, "won": false, "margin": -110, "elo_initial": 145 },
  "setup":    { "nb_players": 4, "expansions": [], "faction_variant": "standard",
                "table_elo": [212, 145, 260, 98], "table_min_elo": 98,
                "auction": null, "engine_version": "4.8.51", "factions": ["terrans", "…"] }
}
```

`turn_order` is that round's seat order, derived from who passed first the round before
(round 1 uses the setup order). It is checked against the order seats actually acted in,
and matches on every round of every mirrored game. With four players it moves a lot, so
it is a feature rather than a constant. It is `null` on the pre-round-1 placement moves,
which follow the setup snake rather than a round order.

`player` is a stable hash of the account, not the name. **Split train and test by it.** A
handful of regulars play a large share of the archive — across 569,741 rows from 2,981
games the ten most frequent of 414 accounts hold 25% of them — so a random row-level split
puts the same player's style on both sides and flatters the result.

`features` is the position **before** the move. `outcome` looks forward from it, so a row
supports imitation (copy the action) and outcome weighting (prefer actions from seats that
went on to score). Reactions — charge, decline, income, brainstone, burn — are left out
unless `--include-reactions` asks for them, since they are bookkeeping, not choices.

## Modules

| | |
|---|---|
| `source.py` | the four public endpoints, paced and retried; transport injected for tests |
| `corpus.py` | resumable on-disk mirror with a digest and fetch time per game |
| `notation.py` | the move notation. Unknown tokens raise rather than being skipped |
| `timeline.py` | joins `moveHistory` with `advancedLog` into rounds, seats and effects |
| `state.py` | rebuilds the position before each move, and verifies the rebuild |
| `census.py` | counts what setups the archive holds, from the listing alone |
| `selection.py` | the target setup, the widening rule and the per-seat rating floor |
| `dataset.py` | decision rows as JSONL |
| `catalog.py` | counted observations, each with its sample size |

Opening labels use the same notation and token order as `bgg_openings` (`1PI+2M`,
biggest building first), so the observed openings and that article's tables compare
directly. Across 9,904 four-player seats, 9,350 (94%) opened with a shape the article
also lists — an independent check on both the rebuild and the source table.

## Things that will bite

Each of these was found by the archive rather than anticipated, and each fails quietly.
All are covered by tests, which is why they are written down rather than fixed silently.

**`advancedLog` move numbers are 0-based offsets into `moveHistory`, not 1-based.**
`moveHistory[0]` is the `init` line and has no log entry. Off by one and every resource
change lands on the wrong move and the wrong player, while every total still looks fine.

**A log entry can carry both `move` and `changes`.** Most do. Handling the move and moving
on drops about 85% of the resource data, and nothing downstream complains.

**A listing entry marked `ended` may be a game somebody abandoned in round two.** Only the
gameplay record's own `ended` flag distinguishes a finished game from a resigned one.

**Older records omit `version`, `factionVariant` and sometimes `layout`.** Requiring them
throws away the older part of the archive, which is most of it. They are carried as
unknown, and an unrecorded variant is counted in its own bucket rather than as `standard`.

**Older records omit the `(from X)` annotation on Ambas's `swap-PI`.** Depending on that
annotation silently leaves the institute on its old hex; the origin comes from the
position being rebuilt instead, which knows it either way.

**Some games keep final data for only part of the table.** A seat that left is dropped
from `players` while staying in `setup` and in the log. Without that seat's score, whether
anyone else won is a guess, so those games are refused.

## Tests

```sh
cd gaia-rl/experiments
python -m unittest discover -s bgs_records -t . -p 'test_*.py'
```

`test_mirror.py` runs against the real mirror and skips when none has been fetched. It is
the drift detector: if the site changes its notation, it fails there first. It checks an
evenly strided sample so the suite stays seconds rather than minutes; `BGS_MIRROR_FULL=1`
sweeps every mirrored game.

It allows up to 1% of games to fail verification rather than demanding zero. Dropping the
occasional record the log cannot explain is the design, not a defect — at 3,109 mirrored
games exactly one does (a research level that advances with no move to account for it) —
while a real notation change would push that share far past the ceiling.
