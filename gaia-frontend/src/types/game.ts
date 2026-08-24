// TypeScript mirror of gaia-engine Rust types (serialized via serde_json)

export type PlayerId = number; // 0..3
export type ShipId = number;
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
  | 'MostGaiaplanets' | 'MostSectors' | 'MostSatellites'
  | 'MostExploredShips' | 'MostSpecialPlanets' | 'HighestSingleTrack';

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
  research_tracks: ResearchTracks;
  vp: number;
  passed: boolean;
  federation_tokens: number[];
  alliance_tiles: { track: ResearchTrack }[];
  explored_ships: ShipId[];
  gaiaformers_total: number;
  gaiaformers_deployed: number;
  /** Rulebook p.15: special action spaces (incl. Academy(Qic)) are once per
   * round — reset when the round transitions. */
  academy_qic_action_used_this_round: boolean;
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
}

// ── Research Board ────────────────────────────────────────────────────────────

export interface TrackState {
  player_levels: Record<PlayerId, number>;
  alliance_taken: (PlayerId | null)[];
}

export interface ResearchBoard {
  tracks: Record<ResearchTrack, TrackState>;
  tech_tiles: number[];
  advanced_tech_tiles: (number | null)[];
  federation_tokens: number[];
}

// ── Scoring ───────────────────────────────────────────────────────────────────

export interface FinalScoringTile {
  condition: FinalScoringCondition;
  vp_1st: number;
  vp_2nd: number;
  vp_3rd: number;
}

export type RoundCondition =
  | 'BuildMine' | 'Upgrade' | 'ResearchAdvance' | 'GaiaProject'
  | 'BuildStation' | 'FormFederation' | 'BuildAcademy';

export interface RoundTile {
  id: number;
  condition: RoundCondition;
  vp_per_unit: number;
}

// ── Phase Enums ───────────────────────────────────────────────────────────────

export type SetupPhase =
  | { FactionSelection: { active_player: PlayerId } }
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

export type GamePhase =
  | { Setup: SetupPhase }
  | 'GaiaPhase'
  | 'IncomePhase'
  | 'GaiaformingPhase'
  | { ActionPhase: { active_player: number } }
  | { ChargePowerPending: { queue: PendingCharge[]; resume_active_player: number | null } }
  | { IncomeOrderPending: { queue: PendingIncomeOrder[]; round: number } }
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
  turn_order: PlayerId[];
  current_player: number;
  /** Shared power-action board slot ids already taken this round (rulebook
   * Appendix III — exclusive across all players, reset at Clean-up). */
  used_power_actions: number[];
  /** Shared QIC-action board slot ids already taken this round (see
   * `qic_action_slot_id` on the engine side for the kind→id mapping). */
  used_qic_action_slots: number[];
}

// ── Game Setup (pre-game randomizer output) ───────────────────────────────────

export interface GameSetup {
  factions: FactionId[];
  round_tile_ids: number[];
  boosters: number[];
  final_scoring: FinalScoringTile[];
  tech_tile_ids: number[];
  sector_layout: SectorPlacement[];
  deep_space_layout: SectorPlacement[];
  seed: string;
}

// ── Actions ───────────────────────────────────────────────────────────────────

export type SetupAction =
  { type: 'SelectFaction'; faction: FactionId };

/** Mirrors `gaia_engine::rules::actions::QicActionKind` — no `#[serde(tag)]`
 * attribute on the Rust enum, so this uses serde's default externally-tagged
 * representation: a bare string for unit variants, `{ VariantName: {...} }`
 * for struct variants. */
export type QicActionKind =
  | 'GainOre'
  | 'ResearchStep'
  | { BuildSatellite: { coord: HexCoord } }
  | { ColoniseLostPlanet: { coord: HexCoord } };

/** Mirrors `gaia_engine::rules::actions::GameAction` exactly (field names,
 * `#[serde(tag = "type", rename_all = "PascalCase")]`). */
export type GameAction =
  | { type: 'Build'; coord: HexCoord }
  | { type: 'Upgrade'; coord: HexCoord; to: StructureType }
  | { type: 'ResearchAdvance'; track: ResearchTrack }
  | { type: 'FormFederation'; hexes: HexCoord[] }
  | { type: 'PowerAction'; id: number }
  | { type: 'SpecialAction'; id: number }
  | { type: 'GaiaFormation'; coord: HexCoord }
  | { type: 'QicAction'; kind: QicActionKind }
  | { type: 'Pass'; booster_id: number | null }
  | { type: 'ChargePower'; accept: boolean }
  | { type: 'ChooseIncomeOrder'; charge_first: boolean }
  | { type: 'AcademyQicAction' };

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
