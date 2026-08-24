# Gaia Rebuild Rule and Source Evidence Audit

**Date:** 2026-08-14  
**Mode:** planning-only, read-only audit of implementation sources  
**Scope:** four-player browser implementation of the base game plus *The Lost Fleet*  
**Primary specification:** `.omx/specs/deep-interview-gaia-lost-fleet-core.md`

## 1. Executive finding

The rebuild must treat the two official PDFs as the rule authority and must not seed a new rules engine from the current TOML files, legacy business rules, faction identifiers, final-scoring enum, or most current rule tests. Those materials contain confirmed contradictions with the official books, not merely incomplete coverage.

The safest reusable core is narrow: hex-coordinate mathematics, generic deterministic-PRNG mechanics after correcting and locking the seed contract, serialization-test patterns, and some Rust domain-shape ideas. All game facts must be re-transcribed into a versioned component/rule catalog and verified against the PDFs before implementation.

## 2. Evidence hierarchy and frozen source versions

The clarified specification explicitly orders sources as official rulebooks, explicit product decisions, verified data/tests, then legacy material (`.omx/specs/deep-interview-gaia-lost-fleet-core.md:7-14`). It requires exactly four guest players, base plus Lost Fleet, deterministic setup, all six rounds, durable recovery, and pause-until-reconnect (`.omx/specs/deep-interview-gaia-lost-fleet-core.md:16-29`). AI, spectator/replay UI, auth/matchmaking, and production operations are excluded (`.omx/specs/deep-interview-gaia-lost-fleet-core.md:31-40`).

Audited official files:

| Source | PDF pages | SHA-256 | Authority |
|---|---:|---|---|
| `docs/EN_Gaia_rulebook_lo.pdf` | 24 | `195f8db89bea4189e018ccf45d9ccf7fd5663d76c5c2cd0eec9335dad49f9185` | Base-game rules |
| `docs/GP_Exp_Rule_EN_V1_Web.pdf` | 16 | `c8e6509e3106041df3c514b5eeb10c307c26c43599329fc04b3035dd46a5fc22` | Lost Fleet changes and additions |

Page references below are 1-indexed PDF pages. The expansion rule applies the base rules except where it changes or supplements them (Lost Fleet PDF p.3).

## 3. Authoritative rule surfaces

### 3.1 Base game

| Surface | Official location | Required engine responsibility |
|---|---|---|
| Components, setup pools, scoring board | Base pp.2-5 | Component inventory, random selection, supply counts |
| Faction setup and initial resources | Base p.6 | Faction-board-derived stocks, power bowls, initial research, special pieces |
| Initial structures and first booster | Base p.7; advanced setup p.19 | Coordinate choices, staged placement, reverse-order booster selection |
| VP and scoring overview | Base p.8 | Triggered scoring and ranking-track updates |
| Power cycle | Base p.9 | Charge/spend/gain/discard semantics and Gaia-area separation |
| Six rounds and four phases | Base p.10 | Income, Gaia, Actions, Clean-up; game ends after round 6 Actions |
| Mine/build, range, terraforming | Base pp.11-12 | Accessibility, Q.I.C. range extension, planet ring, build costs |
| Gaia Project | Base p.12 | Transdim targeting, available Gaiaformer, research-dependent power movement |
| Upgrades and tech tiles | Base p.13 | Legal upgrade graph, costs, adjacency discount, tile advancement |
| Federation formation | Base pp.14-15 | Power threshold, minimal connection, satellite placement/cost, token choice |
| Research and shared actions | Base p.15 | Knowledge cost, level-5 gate, one-use shared actions |
| Special/free/passive/pass actions | Base pp.16-17 | Timing, ownership, power charging, pass order/booster exchange |
| End scoring | Base p.18 | 18/12/6/0 rankings with tie splitting, research and resource scoring |
| Advanced faction/map/turn-order setup | Base p.19 | Faction-board exclusivity, variable board, optional variable turn order |
| Fourteen faction rules | Base pp.20-21 | Every base ability and Planetary Institute override |
| Six research tracks | Base p.22 | Persistent values versus one-time rewards/income |
| Base power/Q.I.C. actions and boosters | Base p.23 | Shared-action effects and booster effects |
| Round scoring and tech tiles | Base p.24 | Trigger definitions and standard-tech semantics |

### 3.2 Lost Fleet

| Surface | Official location | Required engine responsibility |
|---|---|---|
| Component/replacement inventory | Lost Fleet pp.2-3 | Revised components replace marked base counterparts; expansion pools are not additive in every case |
| Four-player map setup | Lost Fleet p.5 | All ten Space Sector tiles, prescribed 05/06/07 sides, two central 01-04 sectors, ten Interspace tiles, eight Deep Space sectors |
| Board overlays and random sides | Lost Fleet pp.5-6 | Scoring extension, extra advanced tile, colonization overlay, adjusted Economy levels 3/4 |
| Four spaceship boards and rewards | Lost Fleet pp.6-7 | Spaceship availability, new standard tech, artifacts, expansion federation tokens |
| Four new factions and setup | Lost Fleet pp.7-8, 13, 16 | Tinkeroids, Darkanians, Moweyds, Space Giants; nonstandard starting structures/planets/terraforming |
| Exploration boards/shuttles | Lost Fleet p.8 | Three shuttles for 3-4 players plus faction-specific costs/adjustments |
| Staged initial structures | Lost Fleet p.8 | Base factions, then expansion factions, then Ivits |
| Explore spaceship action | Lost Fleet p.9 | Range, one shuttle per ship per player, numbered spaces, charge/cost differences |
| Examine artifact action | Lost Fleet p.9 | Twilight prerequisite, discard six power from any areas, artifact acquisition |
| New planets and altered base actions | Lost Fleet p.10 | Protoplanet: three steps and 6 VP; Asteroid: permanently consume Gaiaformer and waive mine cost; no satellites on spaceship tiles |
| Expansion action spaces | Lost Fleet pp.10, 13-14 | Covered base Q.I.C. actions, access controlled by explored ships, action tokens, resource modifiers |
| Exploration-board special actions | Lost Fleet p.11 | Once-per-round faction action timing and effects |
| New boosters/scoring/tech/federation/artifacts | Lost Fleet pp.14-15 | Complete trigger/effect catalog and final scoring definitions |

### 3.3 Four-player Lost Fleet setup facts that must be modeled

The official four-player map is **not** “sectors 01-07 plus Deep Space.” It uses all ten Space Sector tiles, with the white-numbered sides of 05/06/07, two random sectors from 01-04 at the center, the other eight around them, ten four-player Interspace tiles, and all eight Deep Space tiles on random sides (Lost Fleet p.5). The current legacy requirement instead says `01-07` (`aidlc-docs/inception/requirements/requirements.md:141-149`) and is rejected.

Setup also includes independent seeded choices/state for:

- round boosters, round scoring, final scoring, advanced tech, and replacement components (Lost Fleet p.3);
- which side of the four-player scoring extension is used and the extra advanced tile (Lost Fleet p.5);
- which side of the adjusted Economy overlay is used (Lost Fleet p.6);
- new standard tech placements, artifacts, and expansion federation tokens on spaceship boards (Lost Fleet p.6);
- the Moweyds/Tinkeroids terraforming-color order and post-faction resolution (Lost Fleet p.8);
- player-chosen initial structures and first boosters (Lost Fleet p.8 plus Base p.7/p.19).

A seed can determine component layout, but it cannot silently replace player decisions unless the PRD explicitly defines that product deviation.

## 4. Confirmed terminology and model conflicts

Use canonical rulebook terms at the protocol/domain boundary; aliases may exist only in presentation/localization.

| Canonical term | Conflict found | Required resolution |
|---|---|---|
| Tinkeroids, Darkanians, Moweyds, Space Giants | Current code invents `Shipwrights`, `Navigators`, `Pioneers`, `Explorers` (`gaia-engine/src/game_state.rs:229-256`; `gaia-engine/data/factions.toml:228-290`) | Delete invented identities from the new catalog; use the four official factions |
| Protoplanet | Code uses `ProtoPlanet`; legacy UI language is inconsistent | Prefer `protoplanet` in external schema; internal enum naming may be `Protoplanet` |
| Space Sector, Deep Space sector, Interspace tile | Legacy documents conflate sector classes and label sectors 09/10 as Lost Fleet (`gaia-engine/data/sectors.toml:495-543`) | Model three distinct spatial concepts; 09/10 remain base Space Sectors |
| spaceship board versus single-hex spaceship tile | Lost Fleet explicitly distinguishes them (p.6) | Use separate types such as `SpaceshipBoardId` and `InterspaceSpaceshipTile` |
| explore a spaceship | Legacy prose sometimes treats spaceships as colonized/traversed | Exploration never establishes a range origin and is not colonization (Lost Fleet p.9) |
| Exploration Shuttle | No complete current model exists | Represent inventory, deployment slot, ship ownership/access, and permanent placement |
| Power Areas I/II/III and Gaia Area | Legacy says “Braintrust 1/2/3” (`requirements.md:198-202`) | Use official power-cycle terms; Brainstone is Taklons-specific |
| structure | Legacy mixes “building,” “mine,” satellite, Gaiaformer | Maintain explicit `Structure`, `Satellite`, `Gaiaformer`, `ExplorationShuttle`, and marker categories |
| Lost Planet | Legacy BR treats it as a normal build target and removes the token | Navigation level 5 places and colonizes it immediately; it counts as a mine but no mine piece is placed and cannot be upgraded (Base p.22) |
| asteroid/protoplanet | Legacy calls both “special planets” and assigns invented scoring | Preserve distinct colonization rules and official scoring only (Lost Fleet pp.10, 14-15) |

The legacy planet list is not trustworthy: it mixes Terra with “Earth,” Volcanic with “Mars/Volcano,” Titanium with Transdim/“Acid,” and “Landless” (`aidlc-docs/inception/requirements/requirements.md:166-173`). The canonical base types are Terra, Swamp, Desert, Oxide, Volcanic, Titanium, Ice, Transdim, Gaia, and Lost Planet; the expansion adds Asteroid and Protoplanet.

## 5. Confirmed data and rule defects

### 5.1 Factions data is not reusable as facts

- The four expansion factions are fictitious, have ordinary base-game home planets, and start with two mines (`gaia-engine/data/factions.toml:228-290`). Officially all four start on Asteroid or Protoplanet and begin with one structure; Tinkeroids begin with a Planetary Institute (Lost Fleet pp.7, 13).
- Terrans are shown officially with four tokens in Area I and four in Area II (Base p.6), while TOML records 2/4 (`gaia-engine/data/factions.toml:11-13`).
- `starting_structures` stores relative offsets, but official advanced setup requires players to choose legal board coordinates in a staged order (Base p.19; Lost Fleet p.8). These rows are neither faction facts nor legal placement state.
- Lost Fleet applies setup adjustments to Ivits, Bescods, and Lantids and adds exploration-board data (Lost Fleet p.8), none of which the TOML schema can represent.

**Disposition:** retain only the idea of a data-driven catalog. Re-transcribe every base faction board and expansion exploration/faction board with dual review; do not copy current values.

### 5.2 Research data is extensively wrong

Official base research is fully specified at Base p.22. Confirmed contradictions in `gaia-engine/data/research_tracks.toml` include:

- Terraforming gives 2 ore at levels 1 and 4 and a federation token at level 5; current data gives ore at level 3 and 5 VP at level 5 (`:5-15`).
- Navigation gives Q.I.C. at levels 1 and 3 and places the Lost Planet at level 5; current data marks Lost Planet at level 2 and a federation token/5 VP at level 5 (`:18-28`).
- Artificial Intelligence rewards are 1/1/2/2/4 Q.I.C.; current levels 3 and 5 are wrong (`:31-41`).
- Gaia Project level 2 gains three power tokens, level 4 gains a Gaiaformer, and level 5 scores 4 VP plus 1 per colonized Gaia Planet; current data instead gives credits and a generic federation/5 VP (`:44-54`).
- Economy level 5 is a one-time 3 ore, 6 credits, and charge 6, with level-4 income lost; current data models recurring income plus federation/5 VP (`:57-67`).
- Science level 5 is immediate 9 knowledge, not federation/5 VP (`:70-80`).
- Lost Fleet randomly overlays Economy levels 3 and 4 (Lost Fleet p.6), so a single static base table is insufficient.

**Disposition:** reject values and schema; rebuild with typed effect timing (`immediate`, `income`, `persistent capability`, `placement`) and setup-selected overlays.

### 5.3 Map data is acknowledged placeholder material

- `sectors.toml` admits Deep Space planet data is placeholder and requires physical verification (`gaia-engine/data/sectors.toml:583-586`).
- Current 09/10 `is_lost_fleet` flags are false concepts; both are ordinary base Space Sector tiles used in official four-player setup.
- Deep Space positions are all `(0,0)` placeholders (`gaia-engine/src/randomizer.rs:168-188`).
- Interspace tiles are absent from `GameSetup` despite being mandatory ten-tile four-player content (Lost Fleet p.5; compare `gaia-engine/src/randomizer.rs:193-217`).
- The architecture document itself labels its planet layouts as examples requiring transcription (`docs/architecture/map-data-model.md`, sections 2.3-2.4), so it cannot validate `sectors.toml`.

**Disposition:** hex geometry may be reused after tests, but all sector face layouts, Interspace contents, legal rotations/origins, and placement constraints require a new visually verified dataset.

### 5.4 Randomizer contract is internally inconsistent

The legacy requirement defines the seed hash initialization using XOR (`1779033703 ^ seed.length`, `aidlc-docs/inception/requirements/requirements.md:44-54`). Current Rust uses wrapping addition (`gaia-engine/src/randomizer.rs:17-25`) while claiming JavaScript compatibility. The cited cross-language vectors are not registered in normal Cargo test execution, and `tests/property/prng_vectors.rs` contains only self-consistency properties, not known expected output vectors.

Current setup also:

- samples only fourteen base factions (`gaia-engine/src/randomizer.rs:69-73`);
- uses incomplete base-only booster pools (`:80-83`);
- selects incorrect Lost Fleet final-scoring conditions (`:240-299`);
- randomly chooses both sides of 05/06/07, contrary to Lost Fleet four-player setup (`:150-156` versus Lost Fleet p.5);
- fixes sectors 01-04 to four “center” positions even though the official four-player expansion board has only two central sectors (`:113-136` versus Lost Fleet p.5);
- omits Interspace tiles and spaceship constraints;
- gives all Deep Space sectors the same origin (`:168-188`).

**Disposition:** the deterministic RNG abstraction and Fisher-Yates shape may be retained, but the algorithm/version and every setup sampling step need a new golden-vector contract.

### 5.5 Legacy business rules contain confirmed rule inversions

Examples from `aidlc-docs/construction/gaia-engine/functional-design/business-rules.md`:

| Legacy claim | Official rule | Result |
|---|---|---|
| Mine costs 2 ore, 0 credits (BR-C06) | Mine costs 1 ore, 2 credits (Base p.11) | Reject |
| Upgrade costs omit credits and use incorrect ore (BR-U01) | Costs are printed and explained at Base p.13 | Reject |
| Trading station costs more when adjacent (BR-U03) | It costs 3 credits near an opponent, otherwise 6, plus 2 ore (Base p.13) | Reject wording/data |
| Satellite costs 1 Q.I.C. (BR-F05) | Discard one power per satellite (Base p.14) | Reject |
| Planetary Institute power 4 | Base value is 3; a standard tech tile can raise PI/Academies to 4 (Base pp.14, 24) | Reject generic value |
| Research levels 3-5 use “alliance slots” and level 5 gives a token (BR-R03/R04) | Only one player can occupy level 5; advancing there flips a federation token; only Terraforming level 5 grants the setup token (Base pp.15, 22) | Reject |
| Gaia Projects take two rounds and always use four power (BR-G03/G04) | Power cost depends on Gaia research; transformation occurs in the following Gaia phase (Base pp.10, 12, 22) | Reject |
| Lost Planet is later built on and token removed (BR-LF04) | Navigation level 5 immediately places/colonizes it; satellite marker remains (Base p.22) | Reject |
| Protoplanet cost is unresolved/Q.I.C. based (BR-LF07) | Three terraforming steps and normal mine cost; score 6 VP (Lost Fleet p.10) | Reject |
| Expansion final scores are explored ships/special planets/highest track (BR-SC05) | Most asteroids; PI-to-Academy distance; most Deep Space sectors (Lost Fleet p.15) | Reject |

### 5.6 Current final scoring identifiers are fabricated

`FinalScoringCondition::{MostExploredShips, MostSpecialPlanets, HighestSingleTrack}` (`gaia-engine/src/game_state.rs:196-209`) do not correspond to the expansion’s three final scoring tiles. Official conditions are:

1. most Asteroids colonized;
2. longest range distance between the player’s Planetary Institute and one Academy (zero if either required type is absent);
3. most Deep Space sectors with at least one colonized planet, with the Lost Planet counted as a colonized planet (Lost Fleet p.15).

## 6. Current tests: execution and authority assessment

Fresh command: `cargo test -p gaia-engine`.

Result: exit 0, **14 executed tests passed** (5 crate-local terraforming tests and 9 bidding integration tests), with **1 ignored doc test** and 3 compiler warnings. This does not validate the apparent test suite:

- `gaia-engine/tests/bidding.rs` imports only `tests/unit/bidding.rs` (`gaia-engine/tests/bidding.rs:1-2`).
- Files under `tests/unit/` and `tests/property/` are otherwise not registered as integration-test roots and did not run.
- Therefore map, randomizer, rule-engine, scoring, serialization, federation, resource, action, and property files are dormant under normal `cargo test`.
- The dormant federation test explicitly locks the incorrect generic Planetary Institute power value of 4 (`gaia-engine/tests/property/federation.rs:41-44`).
- The PRNG tests prove only internal determinism/range/permutation, not compatibility with the stated external algorithm.
- Passing bidding tests validate a legacy custom setup mechanism, not an official Gaia rule, and cannot establish product correctness until setup policy is decided.

**Conclusion:** current green tests are build smoke evidence only. No current rule test is authoritative without re-registration and rulebook traceability.

## 7. Reuse matrix

| Artifact/surface | Reuse level | Conditions |
|---|---|---|
| Official PDFs | **Authoritative** | Freeze hashes; cite page and encode rule IDs |
| Clarified specification | **Authoritative product overlay** | Explicit decisions override books only where stated |
| Hex axial coordinate/distance/rotation utilities | **Likely reusable** | Register tests; add visual/golden layout fixtures; verify no coordinate collisions |
| Generic Fisher-Yates implementation | **Conditionally reusable** | Choose/version seed algorithm, add known vectors in Rust and browser, test full setup snapshots |
| Serialization round-trip test pattern | **Reusable pattern only** | Register tests and add semantic recovery equivalence, schema-version tests |
| Error/event/type separation ideas | **Reusable concepts** | Redesign around one authoritative transition path; do not preserve legacy wire schema |
| Base `FactionId` names | **Partially reusable** | Keep fourteen official names; normalize spelling such as Bal T'aks/Hadsch Hallas externally |
| Current expansion faction IDs/data | **Do not reuse** | Replace with four official factions and their actual boards/rules |
| `factions.toml` values/starting structures | **Do not reuse as facts** | Full re-transcription and dual verification required |
| `research_tracks.toml` | **Do not reuse** | Values and effect timing are wrong; expansion overlay unsupported |
| Standard/deep-space sector planet data | **Do not reuse as verified data** | Visual transcription from authoritative components/PDF; current Deep Space data is declared placeholder |
| Current randomizer setup steps | **Do not reuse** | Official four-player Lost Fleet layout and component pools differ materially |
| Current final-scoring enum/logic | **Do not reuse** | Expansion conditions are fabricated |
| Legacy `business-rules.md` | **Negative test source only** | Convert confirmed conflicts into regression tests; never treat as authority |
| Bidding/faction-pair auction | **Product decision pending** | Not an official setup rule; retain only if explicitly approved |
| Existing rule/property tests | **Test ideas only** | Register, correct bad expectations, add rulebook page traceability and scenario fixtures |
| Existing visual assets | **Unresolved** | Licensing/redistribution and factual correspondence must be established |

## 8. Planning blockers requiring explicit resolution

These decisions materially alter the PRD, state machine, and E2E test:

1. **Faction selection mechanism.** Official advanced setup is sequential choice of a faction board/side (Base p.19). Legacy requirements introduce random pair selection plus bidding (`requirements.md:56-79`), but the clarified spec does not retain or reject bidding. Decide official selection, custom auction, or deterministic assignment.
2. **Turn order mode.** Clockwise order is default; variable turn order is optional and determined by pass order (Base p.19). Legacy bidding also lets winners select turn-order positions. Choose one authoritative rule.
3. **Deterministic board fairness.** Lost Fleet allows the last player to rotate Space Sectors to improve fairness (p.4/p.5). A fully shareable seed needs either (a) deterministic raw random layout plus manual pregame adjustment recorded in state, or (b) a precisely specified automated fairness solver. Legacy “Center Balance” is not an official rule and is not sufficiently defined.
4. **Authoritative component transcription.** The PDF text does not expose every icon/value/face layout as machine-readable text. Create a reviewed catalog for all faction boards, exploration boards, sector faces, Interspace sets, tech tiles, boosters, scoring tiles, spaceship actions, federation tokens, artifacts, adjusted boards, and supplies before engine implementation.
5. **Spaceship-distance interpretation.** For 3-4 players, Lost Fleet p.4/p.5 says no spaceship tile may be “within 3 spaces” of another. The legacy architecture reduces this to distance `>= 3` (`docs/architecture/map-data-model.md`, section 3.3), which may be an off-by-one interpretation. Golden board fixtures or publisher clarification are needed.
6. **Expansion randomized sides/options.** Decide that all official random choices (Economy overlay side, scoring extension side, tile/token/artifact placements, Deep Space sides) are seed-derived and serialize the results; do not reroll on recovery.
7. **Rules errata/FAQ policy.** No official errata/FAQ is present in `docs/`. Before freezing rules, determine whether a publisher FAQ/errata exists and record its precedence and version.
8. **Asset licensing.** The clarified spec already flags this (`.omx/specs/deep-interview-gaia-lost-fleet-core.md:71-74`). Do not plan redistribution of scanned rule/component art until rights are resolved.

## 9. Residual uncertainties that need not block architecture

- Browser visual fidelity and supported-browser baseline can remain conservative as the clarified spec permits.
- Internal event history is allowed for recovery even though replay UI is out of scope.
- Internal enum capitalization (`Qic`, `Protoplanet`) is an implementation convention as long as the versioned external contract uses canonical stable identifiers.
- A milestone sequence may first validate base generic rules and then expansion overlays/factions, but Autopilot completion remains the complete base-plus-Lost-Fleet four-player game.

## 10. Recommended plan constraints

1. Build a rule/component catalog first, with every record carrying `source_file`, `pdf_page`, `verification_status`, and a stable rule/component ID.
2. Require two-person/independent-pass verification for image-derived data such as sector faces and tile icons.
3. Express rule-changing faction/tech/booster effects as typed commands/triggers, not free-form callbacks or catch-all stubs.
4. Make setup a state machine that separates seed-derived layout from player choices and persists both.
5. Use a single pure transition function for live play, rule tests, event replay/recovery, and browser E2E fixtures, matching the clarified specification.
6. Make every rule test traceable to a rulebook page or explicit product-decision ID; convert each confirmed legacy conflict above into a regression test.
7. Add golden fixtures for: full four-player Lost Fleet setup, all six phase transitions, each faction-specific setup, each new planet/action, all final-scoring ties, disconnect pause/resume, and durable restart equivalence.

## 11. Audit stop condition

This audit establishes that the present rule/data layer is not a safe implementation baseline and identifies the concrete authority gaps the consensus plan must close. It does not implement rules or select the unresolved product options.
