use std::collections::HashMap;

use crate::game_state::{
    BoardState, Booster, FinalScoringCondition, FinalScoringTile, GamePhase, GameState, HexCoord,
    PlayerState, PowerCycle, ResearchBoard, ResearchTrack, ResearchTracks, Resources, RoomCode,
    RoundTile, Sector, TechTile, TrackState,
};

// ── GameStateBuilder ──────────────────────────────────────────────────────────

/// Ergonomic builder for constructing minimal `GameState` values in tests.
///
/// Unset fields default to sensible zero-values so tests only need to set
/// the fields that are relevant to the scenario under test.
pub struct GameStateBuilder {
    players: Vec<PlayerState>,
    round: u8,
    phase: GamePhase,
    board: Option<BoardState>,
}

impl GameStateBuilder {
    pub fn new() -> Self {
        Self {
            players: vec![],
            round: 1,
            phase: GamePhase::ActionPhase { active_player: 0 },
            board: None,
        }
    }

    /// Add a player with default zero resources.
    pub fn with_player(mut self, player_id: u8) -> Self {
        self.players.push(minimal_player(player_id));
        self
    }

    /// Add a player and mutate it with `f` before inserting.
    pub fn with_player_fn(mut self, player_id: u8, f: impl FnOnce(&mut PlayerState)) -> Self {
        let mut p = minimal_player(player_id);
        f(&mut p);
        self.players.push(p);
        self
    }

    pub fn with_round(mut self, round: u8) -> Self {
        self.round = round;
        self
    }

    pub fn with_phase(mut self, phase: GamePhase) -> Self {
        self.phase = phase;
        self
    }

    pub fn with_board(mut self, board: BoardState) -> Self {
        self.board = Some(board);
        self
    }

    /// Builds the `GameState`.  Panics if no players were added (tests must
    /// add at least one player to produce a meaningful state).
    pub fn build(self) -> GameState {
        assert!(
            !self.players.is_empty(),
            "GameStateBuilder requires at least one player"
        );
        let turn_order: Vec<u8> = self.players.iter().map(|p| p.player_id).collect();

        GameState {
            room_code: RoomCode("TEST".into()),
            created_at: 0,
            version: 1,
            round: self.round,
            phase: self.phase,
            players: self.players,
            board: self.board.unwrap_or_else(empty_board),
            round_tiles: default_round_tiles(),
            boosters: (1..=7).map(Booster).collect(),
            final_scoring_tiles: default_final_scoring_tiles(),
            research_board: empty_research_board(),
            faction_selection: None,
            bidding: None,
            turn_order,
            current_player: 0,
            used_power_actions: vec![],
            spaceship_boards: vec![],
            used_spaceship_actions: vec![],
            event_log: vec![],
        }
    }
}

impl Default for GameStateBuilder {
    fn default() -> Self {
        Self::new()
    }
}

// ── Minimal defaults ──────────────────────────────────────────────────────────

pub fn minimal_player(player_id: u8) -> PlayerState {
    PlayerState {
        player_id,
        nickname: format!("Player{}", player_id),
        faction: None,
        resources: Resources {
            ore: 4,
            credits: 15,
            knowledge: 3,
            qic: 1,
            power: PowerCycle {
                bowl1: 4,
                bowl2: 4,
                bowl3: 0,
                gaia_bowl: 0,
                gaia_forming: 0,
                brainstone: None,
            },
            spent_gaia_formers: 0,
        },
        structures: vec![],
        research_tracks: ResearchTracks::new(),
        vp: 10,
        setup_bid_vp: 0,
        passed: false,
        booster: None,
        federation_tokens: vec![],
        gray_federation_tokens: vec![],
        alliance_tiles: vec![],
        explored_ships: vec![],
        exploration_shuttles_available: 3,
        gaiaformers_total: 0,
        gaiaformers_deployed: 0,
        gaiaformers_in_gaia_area: 0,
        tech_tiles: vec![],
        advanced_tech_tiles: vec![],
        covered_tech_tiles: vec![],
        pi_ability_used: false,
        first_colonization_bonus_used: false,
        academy_qic_action_used_this_round: false,
        gleens_special_action_used_this_round: false,
        space_giants_special_action_used_this_round: false,
        round_booster_special_action_used_this_round: false,
        faction_special_action_used_this_round: false,
        geodens_rewarded_planet_types: vec![],
        federated_hexes: vec![],
        tinkeroids_tiles_used: vec![],
        moweyds_power_ring_hexes: vec![],
        tech_tile_special_actions_used_this_round: vec![],
        advanced_tech_tile_special_actions_used_this_round: vec![],
    }
}

fn empty_board() -> BoardState {
    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        }],
        hexes: HashMap::new(),
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn empty_research_board() -> ResearchBoard {
    let mut tracks = HashMap::new();
    for track in ResearchTrack::all() {
        tracks.insert(track, TrackState::new());
    }
    ResearchBoard {
        tracks,
        tech_tiles: (1..=6).map(TechTile).collect(),
        advanced_tech_tiles: [None, None, None, None, None, None],
        federation_tokens: vec![],
    }
}

fn default_round_tiles() -> [RoundTile; 6] {
    [
        RoundTile::from_id(1),
        RoundTile::from_id(4),
        RoundTile::from_id(9),
        RoundTile::from_id(3),
        RoundTile::from_id(5),
        RoundTile::from_id(12),
    ]
}

fn default_final_scoring_tiles() -> [FinalScoringTile; 2] {
    [
        FinalScoringTile {
            id: 5,
            condition: FinalScoringCondition::MostBuildings,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            id: 8,
            condition: FinalScoringCondition::MostSectors,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
    ]
}
