// TypeScript mirror of gaia-engine Rust types after the WebSocket boundary
// converts Rust's canonical "q,r" HexCoord strings into { q, r } objects.

export type PlayerId = number; // 0..3
export type ShipId = number;

/** Mirrors `gaia_engine::game_state::SpaceshipId` — a plain fieldless enum, so it serializes
 * as a bare string (Twilight = 0, Rebellion = 1, TFMars = 2, Eclipse = 3 in `ShipId` terms). */
export type SpaceshipId = 'Twilight' | 'Rebellion' | 'TFMars' | 'Eclipse';
export type BoosterId = number;

// ── Coordinates ───────────────────────────────────────────────────────────────

export interface HexCoord {
  q: number;
  r: number;
}

// ── Enums ─────────────────────────────────────────────────────────────────────

export type PlanetType =
  | 'Terra' | 'Swamp' | 'Desert' | 'Oxide' | 'Titanium'
  | 'Volcanic' | 'Ice' | 'Transdim' | 'Gaia' | 'LostPlanet'
  | 'Asteroid' | 'ProtoPlanet';

export type AcademyType = 'Science' | 'Qic';

export type StructureType =
  | 'Mine'
  | 'TradingStation'
  | 'ResearchLab'
  | 'PlanetaryInstitute'
  | { Academy: AcademyType }
  | 'Satellite'
  | 'SpaceStation';

export type SpaceTileKind = 'Single' | 'Outer';

export type ResearchTrack =
  | 'Terraforming' | 'Navigation' | 'ArtificialIntelligence'
  | 'GaiaProject' | 'Economy' | 'Science';

export type ResourceKind = 'Ore' | 'Credits' | 'Knowledge' | 'Qic' | 'Power';

export type FinalScoringCondition =
  | 'MostStructuresInFederation' | 'MostBuildings' | 'MostPlanetTypes'
  | 'MostGaiaPlanets' | 'MostSectors' | 'MostSatellites'
  | 'MostDeepSpaceSectors' | 'MostAsteroids' | 'GreatestDistancePiAcademy';

export type FactionId =
  | 'Terrans' | 'Lantids' | 'Xenos' | 'Gleens' | 'Taklons' | 'Ambas'
  | 'HadschHallas' | 'Ivits' | 'Geodens' | 'BalTaks' | 'Firaks' | 'Bescods'
  | 'Nevlas' | 'Itars'
  | 'Tinkeroids' | 'Moweyds' | 'SpaceGiants' | 'Darkanians';

// ── Resources ─────────────────────────────────────────────────────────────────

export interface PowerCycle {
  bowl1: number;
  bowl2: number;
  bowl3: number;
  gaia_bowl: number;
  gaia_forming: number;
  /** Taklons' distinct Brainstone; null for other factions. */
  brainstone?: 'Area1' | 'Area2' | 'Area3' | 'Gaia' | null;
}

export interface Resources {
  ore: number;
  credits: number;
  knowledge: number;
  qic: number;
  power: PowerCycle;
  spent_gaia_formers: number;
}

export interface ResourceDelta {
  ore: number;
  credits: number;
  knowledge: number;
  qic: number;
}

// ── Player State ──────────────────────────────────────────────────────────────

export interface ResearchTracks {
  terraforming: number;
  navigation: number;
  ai: number;
  gaia: number;
  economy: number;
  science: number;
}

export interface Structure {
  hex: HexCoord;
  kind: StructureType;
}

export interface PlayerState {
  player_id: PlayerId;
  nickname: string;
  faction: FactionId | null;
  resources: Resources;
  structures: Structure[];
  /** Artifact 8/12 virtual mines: scoring/objective mines without a board coordinate or piece. */
  artifact_mines?: PlanetType[];
  research_tracks: ResearchTracks;
  vp: number;
  /** Setup auction cost, deducted only when final scoring is calculated. */
  setup_bid_vp: number;
  passed: boolean;
  /** Currently owned round booster; GameState.boosters is the available pool. */
  booster?: number | null;
  federation_tokens: number[];
  /** Federation tokens flipped from green to gray (rulebook p.14) — spent for research level 5
   * or an Advanced Tech tile. Just a record; flipped tokens grant nothing further. */
  gray_federation_tokens?: number[];
  alliance_tiles: { track: ResearchTrack }[];
  explored_ships: ShipId[];
  /** Lost Fleet: Exploration Shuttles not yet deployed to a spaceship (starts at 3). */
  exploration_shuttles_available: number;
  gaiaformers_total: number;
  gaiaformers_deployed: number;
  gaiaformers_in_gaia_area?: number;
  /** Rulebook p.15: special action spaces (incl. Academy(Qic)) are once per
   * round — reset when the round transitions. */
  academy_qic_action_used_this_round: boolean;
  /** Lost Fleet Exploration Board special action (`GP_Exp_Rule_EN_V1_Web.pdf` p.10): once per
   * round each, reset when the round transitions. Meaningless for other factions. */
  gleens_special_action_used_this_round: boolean;
  space_giants_special_action_used_this_round: boolean;
  /** Special action printed on the currently owned round booster; reset during Clean-up. */
  round_booster_special_action_used_this_round?: boolean;
  /** Base-faction board special action (Ambas, Firaks, Bescods); reset during Clean-up. */
  faction_special_action_used_this_round?: boolean;
  /** Planet types already consumed by Geodens' post-PI first-colonization reward. */
  geodens_rewarded_planet_types?: PlanetType[];
  /** Every hex (colonized planet or satellite) already committed to a formed Federation —
   * each can only be part of one. */
  federated_hexes?: HexCoord[];
  /** Tinkeroids only: ids (1-6) of Tinkering tiles already used this game. */
  tinkeroids_tiles_used?: number[];
  /** Moweyds only: hexes where a Power Ring has been placed (at most 6). */
  moweyds_power_ring_hexes?: HexCoord[];
  /** Standard Tech tile ids owned (2-10 base game, 11-14 Lost Fleet Appendix V). */
  tech_tiles?: number[];
  /** Advanced Tech tile ids owned (1-22). */
  advanced_tech_tiles?: number[];
  /** Standard Tech tile ids covered by an Advanced Tech tile — still owned, but their ongoing
   * effects (income, event/pass-time triggers, power value, special action) no longer apply. */
  covered_tech_tiles?: number[];
  /** Standard Tech tile ids whose "as a special action" ability was already used this round. */
  tech_tile_special_actions_used_this_round?: number[];
  /** Same as `tech_tile_special_actions_used_this_round`, for Advanced Tech tiles. */
  advanced_tech_tile_special_actions_used_this_round?: number[];
}

// ── Board State ───────────────────────────────────────────────────────────────

export interface Planet {
  planet_type: PlanetType;
  is_gaia_formed: boolean;
  owner: PlayerId | null;
}

export interface PlacedStructure {
  owner: PlayerId;
  kind: StructureType;
}

export interface Hex {
  coord: HexCoord;
  planet: Planet | null;
  space_tile_kind: SpaceTileKind | null;
  structures: PlacedStructure[];
  satellites: PlayerId[];
}

export interface Sector {
  id: number;
  rotation: number;
  origin: HexCoord;
}

export interface SectorPlacement {
  sector_id: number;
  side?: string | null;
  origin: HexCoord;
  rotation: number;
}

export interface BoardState {
  sectors: Sector[];
  hexes: Record<string, Hex>; // key = "q,r"
  lost_planet: HexCoord | null;
  /** Lost Fleet: where each of the 4 spaceship tiles sits on the map, placed among the 10
   * Interspace tile holes per the 4-player variable setup — see `MapEngine::place_interspace_tiles`. */
  spaceship_tiles: Partial<Record<SpaceshipId, HexCoord>>;
}

/** Lost Fleet: shared state for one spaceship board (expansion rulebook, "Lost Fleet Spaceships"). */
export interface SpaceshipBoard {
  id: SpaceshipId;
  /** Shuttle slots in board order; `null` = open. */
  explorers: (PlayerId | null)[];
  /** Twilight only — remaining Artifact ids available to draw via "Examine an Artifact". */
  artifact_pool: number[];
  /** Lost Fleet Standard Tech pile on this ship (four identical copies at setup). */
  tech_tiles?: number[];
  /** The ship's own Federation token (ids 8-11, `FederationTokenChoice.Spaceship`) — `null` once
   * claimed by a player who explored this ship. */
  federation_token: number | null;
}

// ── Research Board ────────────────────────────────────────────────────────────

export interface TrackState {
  player_levels: Record<PlayerId, number>;
  alliance_taken: (PlayerId | null)[];
}

export interface ResearchBoard {
  tracks: Record<ResearchTrack, TrackState>;
  tech_tiles: number[];
  tech_tile_slots?: (number | null)[];
  advanced_tech_tiles: (number | null)[];
  federation_tokens: number[];
}

// ── Scoring ───────────────────────────────────────────────────────────────────

export interface FinalScoringTile {
  id: number;
  condition: FinalScoringCondition;
  vp_1st: number;
  vp_2nd: number;
  vp_3rd: number;
}

export type RoundCondition =
  | 'BuildMine'
  | 'TerraformingStep'
  | 'BuildMineOnGaia'
  | 'UpgradeTradingStation'
  | 'UpgradeLargeBuilding'
  | 'ResearchAdvance'
  | 'FormFederation'
  | 'BuildMineOnNewPlanetType'
  | 'BuildMineInNewSector'
  | 'UpgradeResearchLab';

export interface RoundTile {
  id: number;
  condition: RoundCondition;
  vp_per_unit: number;
}

// ── Phase Enums ───────────────────────────────────────────────────────────────

export type SetupPhase =
  | { FactionSelection: { active_player: PlayerId } }
  | { Bidding: { active_player: PlayerId } }
  | { BiddingChoice: { winner: PlayerId } }
  | { StartingStructures: {
      active_player: PlayerId;
      placement_index: number;
      kind: StructureType;
    } }
  | { StartingBoosters: {
      active_player: PlayerId;
      selection_index: number;
    } }
  | 'Complete';

/** One opponent's opportunity to charge power during `ChargePowerPending`. */
export interface PendingCharge {
  player: PlayerId;
  hex: HexCoord;
  max_power: number;
}

/** One player's PlanetaryInstitute charge-vs-bonus-token ordering decision
 * during `IncomeOrderPending`. */
export interface PendingIncomeOrder {
  player: PlayerId;
  charge_amount: number;
  bonus_tokens: number;
}

export type GaiaDecisionKind = 'TerransPowerConversion' | 'ItarsTechTile';

/** One player's optional Planetary Institute ability during the Gaia phase. */
export interface PendingGaiaDecision {
  player: PlayerId;
  kind: GaiaDecisionKind;
  remaining_power: number;
}

export type GamePhase =
  | { Setup: SetupPhase }
  | 'GaiaPhase'
  | 'IncomePhase'
  | 'GaiaformingPhase'
  | { ActionPhase: { active_player: number } }
  | { ChargePowerPending: { queue: PendingCharge[]; resume_active_player: number | null } }
  | { IncomeOrderPending: { queue: PendingIncomeOrder[]; round: number } }
  | { GaiaDecisionPending: { queue: PendingGaiaDecision[]; round: number } }
  | { RoundScoring: { round: number } }
  | 'FinalScoring'
  | 'Ended';

// ── Faction selection ─────────────────────────────────────────────────────────

export interface FactionAssignment {
  player: PlayerId;
  faction: FactionId;
}

export interface FactionSelectionState {
  available_factions: FactionId[];
  player_order: PlayerId[];
  current_index: number;
  assignments: FactionAssignment[];
}

export interface BidAssignment {
  player: PlayerId;
  faction: FactionId;
  turn_position: number;
  bid_vp: number;
}

export type BiddingStage =
  | 'Auction'
  | { WinnerChoice: { winner: PlayerId; bid_vp: number } }
  | 'Complete';

export interface BiddingState {
  clockwise_order: PlayerId[];
  remaining_players: PlayerId[];
  available_factions: FactionId[];
  available_turn_positions: number[];
  active_player: PlayerId;
  highest_bid: number;
  highest_bidder: PlayerId | null;
  passed_players: PlayerId[];
  stage: BiddingStage;
  assignments: BidAssignment[];
}

// ── Game State ────────────────────────────────────────────────────────────────

export interface GameState {
  players: PlayerState[];
  board: BoardState;
  research_board: ResearchBoard;
  round: number;
  phase: GamePhase;
  round_tiles: RoundTile[];
  final_scoring_tiles: FinalScoringTile[];
  boosters: number[];
  faction_selection: FactionSelectionState | null;
  bidding: BiddingState | null;
  turn_order: PlayerId[];
  current_player: number;
  /** Shared power-action board slot ids already taken this round (rulebook
   * Appendix III — exclusive across all players, reset at Clean-up). The
   * QIC-action board doesn't exist under this project's always-Lost-Fleet
   * ruleset (a Lost Fleet board piece covers it entirely) — see README. */
  used_power_actions: number[];
  /** Lost Fleet: the 4 spaceship boards' shared explore/artifact state. */
  spaceship_boards: SpaceshipBoard[];
  /** Lost Fleet Appendix II action space ids used this round (shared across players and reset
   * during Clean-up). id 1 = `SpaceshipCreditTerraform`, id 2 =
   * `TwilightFreeResearchLab`, id 3 = `RebellionFreeTradingStation`, id 4 =
   * `RebellionCreditsAndQic`, id 5 = `TFMarsTechBonus`, id 6 = `TFMarsGaiaFormation`, id 7 =
   * `EclipsePlanetTypeBonus`, id 8 = `EclipseResearchBoost`, id 9 = `EclipseAsteroidMine`, id 10 =
   * `TwilightReplayFederationToken`, id 11 = all three `TwilightRange*` target modes, id 12 =
   * `RebellionGainTechTile`. */
  used_spaceship_actions: number[];
  /** Durable engine events included in snapshots for reconnect-safe UI logs. */
  event_log?: GameEvent[];
}

export interface FreeActionTakenEvent {
  FreeActionTaken: {
    player: PlayerId;
    kind: FreeActionKind;
    count: number;
  };
}

/** Events use serde's default externally-tagged enum representation. */
export type GameEvent = FreeActionTakenEvent | Record<string, unknown>;

// ── Game Setup (pre-game randomizer output) ───────────────────────────────────

export type SetupMode = 'sequential' | 'bidding';

export interface GameSetup {
  setup_mode: SetupMode;
  factions: FactionId[];
  round_tile_ids: number[];
  boosters: number[];
  final_scoring: FinalScoringTile[];
  tech_tile_ids: number[];
  tech_tile_slot_ids?: number[];
  sector_layout: SectorPlacement[];
  deep_space_layout: SectorPlacement[];
  seed: string;
}

/** `GET /rooms/:code/preview_board` — the board/tiles `room.setup`/`room.seed` would produce if
 * the game started right now, computed read-only (never mutates room state) so the waiting room
 * can show the randomized layout, and let the host reroll it, before anyone readies up. */
export interface PreviewBoard {
  seed: string;
  board: BoardState;
  round_tiles: RoundTile[];
  final_scoring_tiles: FinalScoringTile[];
  spaceship_boards: SpaceshipBoard[];
  research_board?: ResearchBoard;
}

// ── Actions ───────────────────────────────────────────────────────────────────

export type SetupAction =
  | { type: 'SelectFaction'; faction: FactionId }
  | { type: 'PlaceBid'; amount: number }
  | { type: 'PassBid' }
  | { type: 'ChooseBidReward'; faction: FactionId; turn_position: number }
  | { type: 'PlaceStartingStructure'; coord: HexCoord }
  | { type: 'SelectStartingBooster'; booster_id: number };

/** Mirrors `gaia_engine::rules::actions::FreeActionKind` — all variants are
 * unit variants with no `#[serde(tag)]` attribute, so each serializes as a
 * bare string (serde's default externally-tagged form for unit variants). */
export type FreeActionKind =
  | 'BurnPower'
  | 'CreditsToQic'
  | 'CreditsToOre'
  | 'CreditsToKnowledge'
  | 'GaiaformerToQic'
  | 'PowerToGaiaKnowledge'
  | 'OreToPowerBowl3'
  | 'PowerToQic'
  | 'PowerToOre'
  | 'QicToOre'
  | 'PowerToKnowledge'
  | 'PowerToCredit'
  | 'KnowledgeToCredit'
  | 'OreToCredit'
  | 'OreToPower';

/** Mirrors `gaia_engine::rules::actions::FederationTokenChoice` (`#[serde(tag = "source",
 * rename_all = "PascalCase")]`). `kind` ids: 1-7 base-game supply, 8-11 Lost Fleet spaceship
 * tokens (see `federation_token_kind` in `rules/engine.rs`). */
export type FederationTokenChoice =
  | { source: 'Supply'; kind: number }
  | { source: 'Spaceship'; ship: SpaceshipId };

/** Mirrors `gaia_engine::rules::actions::TechTileChoice` (`#[serde(tag = "kind", rename_all =
 * "PascalCase")]`), taken as part of `GameAction::Upgrade`. `bonus_build_coord` is required
 * exactly when `tile` is 11 (the Lost Fleet free-Build-a-Mine tile). */
export type TechTileChoice =
  | {
      kind: 'Standard';
      tile: number;
      advance_track?: ResearchTrack | null;
      bonus_build_coord?: HexCoord | null;
    }
  | {
      kind: 'Advanced';
      track: ResearchTrack;
      covered_tile: number;
      advance_track?: ResearchTrack | null;
    };

/** Mirrors `gaia_engine::rules::actions::TechTileRef` (`#[serde(tag = "pool", rename_all =
 * "PascalCase")]`) — a tile the player already owns, for `GameAction::TechTileSpecialAction`. */
export type TechTileRef =
  | { pool: 'Standard'; tile: number }
  | { pool: 'Advanced'; tile: number };

/** Mirrors `gaia_engine::rules::actions::GameAction` exactly (field names,
 * `#[serde(tag = "type", rename_all = "PascalCase")]`). */
export type GameAction =
  | { type: 'Build'; coord: HexCoord }
  | {
      type: 'Upgrade';
      coord: HexCoord;
      to: StructureType;
      tech_tile_choice?: TechTileChoice | null;
    }
  | { type: 'ResearchAdvance'; track: ResearchTrack }
  | {
      type: 'FormFederation';
      hexes: HexCoord[];
      satellite_hexes?: HexCoord[];
      token: FederationTokenChoice;
      bonus_build_coord?: HexCoord | null;
      bonus_tech_tile?: number | null;
    }
  | { type: 'PowerAction'; id: number; coord: HexCoord | null }
  | { type: 'SpecialAction'; id: number }
  | { type: 'AmbasSwapPlanetaryInstitute'; mine_coord: HexCoord }
  | { type: 'FiraksDowngradeResearchLab'; coord: HexCoord; track: ResearchTrack }
  | { type: 'BescodsLowestResearchAdvance'; track: ResearchTrack }
  | { type: 'IvitsPlaceSpaceStation'; coord: HexCoord }
  | { type: 'TinkeroidsUseTile'; tile: number; coord?: HexCoord | null }
  | { type: 'MoweydsPlacePowerRing'; coord: HexCoord }
  | { type: 'TechTileSpecialAction'; tile: TechTileRef }
  | { type: 'GaiaFormation'; coord: HexCoord }
  | { type: 'RoundBoosterImmediateGaiaFormation'; coord: HexCoord }
  | { type: 'RoundBoosterRangeBuild'; coord: HexCoord }
  | { type: 'RoundBoosterRangeGaiaFormation'; coord: HexCoord }
  | { type: 'RoundBoosterRangeExploreSpaceship'; ship: SpaceshipId }
  | { type: 'Pass'; booster_id: number | null }
  | { type: 'ChargePower'; accept: boolean }
  | { type: 'TaklonsChargePower'; gain_before: boolean }
  | { type: 'ChooseIncomeOrder'; charge_first: boolean }
  | { type: 'TerransGaiaConversion'; kind: FreeActionKind; count: number }
  | { type: 'ItarsGaiaTechTile'; tile: number; track: ResearchTrack }
  | { type: 'FinishGaiaDecision' }
  | { type: 'AcademyQicAction' }
  | { type: 'FreeAction'; kind: FreeActionKind; count: number }
  | { type: 'ExploreSpaceship'; ship: SpaceshipId }
  | {
      type: 'ExamineArtifact';
      artifact: number;
      copy_federation_token_kind?: number | null;
      bonus_build_coord?: HexCoord | null;
      bonus_tech_tile?: number | null;
      bonus_research_track?: ResearchTrack | null;
    }
  | { type: 'SpaceshipCreditTerraform'; coord: HexCoord }
  | { type: 'TwilightFreeResearchLab'; coord: HexCoord }
  | {
      type: 'TwilightReplayFederationToken';
      token_kind: number;
      bonus_build_coord?: HexCoord | null;
      bonus_tech_tile?: number | null;
      bonus_research_track?: ResearchTrack | null;
    }
  | { type: 'TwilightRangeBuild'; coord: HexCoord }
  | { type: 'TwilightRangeGaiaFormation'; coord: HexCoord }
  | { type: 'TwilightRangeExploreSpaceship'; ship: SpaceshipId }
  | { type: 'RebellionFreeTradingStation'; coord: HexCoord }
  | { type: 'RebellionCreditsAndQic' }
  | { type: 'RebellionGainTechTile'; tile: number; track: ResearchTrack }
  | { type: 'TFMarsTechBonus' }
  | { type: 'TFMarsGaiaFormation'; coord: HexCoord }
  | { type: 'EclipsePlanetTypeBonus' }
  | { type: 'EclipseResearchBoost'; track: ResearchTrack }
  | { type: 'EclipseAsteroidMine'; coord: HexCoord }
  | { type: 'GleensBuildMine'; coord: HexCoord }
  | { type: 'GleensGaiaFormation'; coord: HexCoord }
  | { type: 'GleensExploreSpaceship'; ship: SpaceshipId }
  | { type: 'SpaceGiantsBuildMine'; coord: HexCoord };

// ── WebSocket protocol ────────────────────────────────────────────────────────
//
// `join_room` establishes identity before a revision exists to track, so it
// stays a bare frame (mirrors `gaia-server/src/protocol.rs::ClientFrame`).
// Everything that mutates room state — lobby readiness, setup regeneration,
// faction selection, in-game actions — travels as a `CommandEnvelope`
// carrying a client-chosen `command_id` (for idempotent retry) and
// `expected_revision` (for optimistic concurrency), and gets back either a
// direct `command_accepted`/`command_rejected` reply or a room-wide
// `snapshot`/`control` broadcast (mirrors `gaia-protocol`'s
// `CommandEnvelope`/`ServerEnvelope`).

export interface LobbyPlayer {
  player_id: PlayerId;
  nickname: string;
  ready: boolean;
}

export interface LobbyState {
  players: LobbyPlayer[];
  host_player_id: PlayerId;
}

export type ClientCommand =
  | { type: 'player_ready'; ready: boolean }
  | { type: 'regenerate_setup'; seed?: string }
  | { type: 'place_setup_action'; action: SetupAction }
  | { type: 'place_game_action'; action: GameAction };

export interface CommandEnvelope {
  type: 'command';
  protocol_version: number;
  schema_hash: string;
  room_id: string;
  command_id: string;
  expected_revision: number;
  command: ClientCommand;
}

export type ClientFrame =
  | { type: 'join_room'; room_code: string; nickname: string; session_token?: string }
  | CommandEnvelope;

export interface ProtocolRejection {
  code: string;
  message_key: string;
}

export interface ControlProjection {
  control_revision: number;
  paused: boolean;
  recovery_hold: boolean;
  missing_seats: number[];
}

/// The lobby-phase view of room state before a `GameState` exists yet —
/// what `snapshot.state` carries prior to `FactionSelection`/`InGame`.
/// Distinguish from a full `GameState` by `phase === 'lobby'` (a `GameState`'s
/// own `phase` is never the bare string `'lobby'`).
export interface LobbySnapshotView {
  phase: 'lobby';
  state: 'lobby' | 'faction_selection' | 'in_game' | 'ended';
  players: { player_id: PlayerId; nickname: string; ready: boolean }[];
  setup: GameSetup | null;
}

export type SnapshotState = LobbySnapshotView | GameState;

export type ServerEnvelope =
  | {
      type: 'command_accepted';
      protocol_version: number;
      schema_hash: string;
      command_id: string;
      revision: number;
    }
  | {
      type: 'command_rejected';
      protocol_version: number;
      schema_hash: string;
      command_id: string | null;
      revision: number;
      rejection: ProtocolRejection;
    }
  | {
      type: 'snapshot';
      protocol_version: number;
      schema_hash: string;
      revision: number;
      state: SnapshotState;
    }
  | {
      type: 'events';
      protocol_version: number;
      schema_hash: string;
      from_revision: number;
      to_revision: number;
      events: unknown[];
    }
  | {
      type: 'control';
      protocol_version: number;
      schema_hash: string;
      control: ControlProjection;
    };

export type LobbyMessage =
  | {
      type: 'room_joined';
      room_code: string;
      player_id: PlayerId;
      session_token: string;
      game_setup: GameSetup;
      revision: number;
    }
  | { type: 'player_joined'; player_id: PlayerId; nickname: string; player_count: number }
  | ({ type: 'lobby_state' } & LobbyState)
  | { type: 'round_ended'; round: number; scores: [PlayerId, number][] }
  | { type: 'game_ended'; final_scores: [PlayerId, number][]; winner: PlayerId }
  | { type: 'room_paused'; paused: boolean; missing_seats: PlayerId[] }
  | { type: 'error'; code: string; message: string };

export type ServerMessage = LobbyMessage | ServerEnvelope;

// ── Room Info (REST response) ─────────────────────────────────────────────────

export interface RoomInfo {
  code: string;
  player_count: number;
  state: 'lobby' | 'faction_selection' | 'in_game' | 'ended';
  game_setup: GameSetup | null;
  players: LobbyPlayer[];
  host_player_id: PlayerId;
}

export interface CreateRoomResponse {
  room_code: string;
  code?: string;
  player_id: PlayerId;
  session_token: string;
  game_setup: GameSetup;
  players: LobbyPlayer[];
  host_player_id: PlayerId;
}

export interface JoinRoomResponse {
  room_code: string;
  player_id: PlayerId;
  session_token: string;
  game_setup: GameSetup;
  players: LobbyPlayer[];
  host_player_id: PlayerId;
  /** Present once the game has started — lets a reconnecting client resync
   * immediately over REST rather than waiting for the first WS broadcast. */
  game_state: GameState | null;
}

// ── Type guards ────────────────────────────────────────────────────────────────

/** A `snapshot.state` is a `GameState` unless it's the lobby-phase view
 * (`phase === 'lobby'`, a value `GameState.phase` never takes). */
export function isGameState(state: SnapshotState): state is GameState {
  return (state as LobbySnapshotView).phase !== 'lobby';
}
