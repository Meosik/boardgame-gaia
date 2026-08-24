use super::actions::{GameAction, QicActionKind, SetupAction};
use super::terraforming::{cost_for_distance, ring_distance};
use crate::error::RuleError;
use crate::faction::ability::FactionAbility;
use crate::faction::registry::global as faction_registry;
use crate::game_state::{
    AcademyType, FederationToken, GameEvent, GamePhase, GameState, HexCoord, PendingCharge,
    PendingIncomeOrder, PlacedStructure, PlanetType, PlayerId, PlayerState, PowerCycle,
    ResearchTrack, ResourceDelta, ResourceKind, Resources, RoundCondition, SetupPhase,
    StructureType, VpReason,
};
use crate::map::MapEngine;
use crate::setup_policy::SetupPolicy;

// ── Constants ─────────────────────────────────────────────────────────────────

const MINE_ORE_COST: u8 = 1;
const MINE_CREDITS_COST: u8 = 2;
const RESEARCH_KNOWLEDGE_COST: u8 = 4;
const FEDERATION_MIN_POWER: u32 = 7;
const MAX_MINES: usize = 8;
const MAX_TRADING_STATIONS: usize = 4;
const MAX_RESEARCH_LABS: usize = 3;
const MAX_ACADEMIES: usize = 2;

// ── Structure round income (faction boards; universal unless a faction's
// `factions.toml` entry overrides it — see `apply_structure_income`) ────────
const UNIVERSAL_MINE_BASE: u8 = 1;
const UNIVERSAL_MINE_TABLE: [u8; MAX_MINES] = [1, 1, 0, 1, 1, 1, 1, 1];
const UNIVERSAL_TRADING_STATION_BASE: u8 = 0;
const UNIVERSAL_TRADING_STATION_TABLE: [u8; MAX_TRADING_STATIONS] = [3, 4, 4, 5];
const UNIVERSAL_RESEARCH_LAB_BASE: u8 = 1;
const UNIVERSAL_RESEARCH_LAB_TABLE: [u8; MAX_RESEARCH_LABS] = [1, 1, 1];
const UNIVERSAL_ACADEMY_SCIENCE_KNOWLEDGE: u8 = 2;
const UNIVERSAL_PLANETARY_INSTITUTE_CHARGE: u8 = 4;
const UNIVERSAL_PI_BONUS_POWER_TOKENS: u8 = 1;

/// Navigation range by research track level (0-5).
/// Rulebook p.22: 0→1, 1→1, 2→2, 3→2, 4→3, 5→4.
const NAV_RANGE: [u8; 6] = [1, 1, 2, 2, 3, 4];

/// Power tokens to move to Gaia area per Gaia Project track level (0-5).
/// Rulebook p.22: level 0 → cannot start; 1-2 → 6; 3 → 4; 4-5 → 3.
const GAIA_POWER_COST: [u8; 6] = [u8::MAX, 6, 6, 4, 3, 3];

// ── RuleEngine ────────────────────────────────────────────────────────────────

/// Stateless rule executor.  All methods are associated functions that take
/// `GameState` by reference (for validation) or by mutable reference (for mutation).
pub struct RuleEngine;

impl RuleEngine {
    // ── Public API ─────────────────────────────────────────────────────────

    /// Full validation of `action` for `player_id` in the current state.
    /// Returns `Ok(())` when the action is legal, `Err(RuleError)` otherwise.
    pub fn validate_action(
        state: &GameState,
        player_id: PlayerId,
        action: &GameAction,
    ) -> Result<(), RuleError> {
        if let GameAction::ChargePower { accept } = action {
            return validate_charge_power(state, player_id, *accept);
        }
        if let GameAction::ChooseIncomeOrder { charge_first } = action {
            return validate_choose_income_order(state, player_id, *charge_first);
        }

        ensure_action_phase(state, player_id)?;
        let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

        match action {
            GameAction::Pass { .. } => {} // Pass is always allowed when it's your turn
            _ if player.passed => return Err(RuleError::AlreadyPassed),
            _ => {}
        }

        match action {
            GameAction::Build { coord } => validate_build(state, player_id, *coord),
            GameAction::Upgrade { coord, to } => validate_upgrade(state, player_id, *coord, *to),
            GameAction::ResearchAdvance { track } => validate_research(state, player_id, *track),
            GameAction::FormFederation { hexes } => validate_federation(state, player_id, hexes),
            GameAction::PowerAction { id } => validate_power_action(state, player_id, *id),
            GameAction::SpecialAction { id } => validate_special_action(state, player_id, *id),
            GameAction::GaiaFormation { coord } => {
                validate_gaia_formation(state, player_id, *coord)
            }
            GameAction::QicAction { kind } => validate_qic_action(state, player_id, kind),
            GameAction::Pass { booster_id } => validate_pass(state, player_id, *booster_id),
            GameAction::AcademyQicAction => validate_academy_qic_action(state, player_id),
            GameAction::ChargePower { .. } => unreachable!("handled above"),
            GameAction::ChooseIncomeOrder { .. } => unreachable!("handled above"),
        }
    }

    /// Validates `action`, then applies it.  Returns produced events on success.
    pub fn apply_action(
        state: &mut GameState,
        player_id: PlayerId,
        action: GameAction,
    ) -> Result<Vec<GameEvent>, RuleError> {
        Self::validate_action(state, player_id, &action)?;
        Ok(Self::apply_unchecked(state, player_id, action))
    }

    /// Applies `action` unconditionally.  **Caller must have already called
    /// `validate_action` and received `Ok(())`.**  Never panics under that contract.
    pub fn apply_unchecked(
        state: &mut GameState,
        player_id: PlayerId,
        action: GameAction,
    ) -> Vec<GameEvent> {
        match action {
            GameAction::Build { coord } => apply_build(state, player_id, coord),
            GameAction::Upgrade { coord, to } => apply_upgrade(state, player_id, coord, to),
            GameAction::ResearchAdvance { track } => apply_research(state, player_id, track),
            GameAction::FormFederation { hexes } => apply_federation(state, player_id, hexes),
            GameAction::PowerAction { id } => apply_power_action(state, player_id, id),
            GameAction::SpecialAction { id } => apply_special_action(state, player_id, id),
            GameAction::GaiaFormation { coord } => apply_gaia_formation(state, player_id, coord),
            GameAction::QicAction { kind } => apply_qic_action(state, player_id, kind),
            GameAction::Pass { booster_id } => apply_pass(state, player_id, booster_id),
            GameAction::AcademyQicAction => apply_academy_qic_action(state, player_id),
            GameAction::ChargePower { accept } => apply_charge_power(state, player_id, accept),
            GameAction::ChooseIncomeOrder { charge_first } => {
                apply_choose_income_order(state, player_id, charge_first)
            }
        }
    }

    /// Returns the set of GameActions that are currently legal for `player_id`.
    /// Used by the AI sidecar and for client-side highlighting.
    pub fn get_valid_actions(state: &GameState, player_id: PlayerId) -> Vec<GameAction> {
        if ensure_income_order_phase(state, player_id).is_ok() {
            return vec![
                GameAction::ChooseIncomeOrder {
                    charge_first: false,
                },
                GameAction::ChooseIncomeOrder { charge_first: true },
            ];
        }
        if ensure_charge_power_phase(state, player_id).is_ok() {
            return vec![
                GameAction::ChargePower { accept: false },
                GameAction::ChargePower { accept: true },
            ];
        }
        if ensure_action_phase(state, player_id).is_err() {
            return vec![];
        }
        let player = match state.player(player_id) {
            Some(p) => p,
            None => return vec![],
        };
        if player.passed {
            return vec![];
        }

        let mut actions = vec![GameAction::Pass { booster_id: None }];

        // Build — enumerate reachable planet hexes
        let nav_level = player.research_tracks.navigation as usize;
        let nav_range = NAV_RANGE[nav_level.min(NAV_RANGE.len() - 1)];
        let my_structure_hexes: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
        let reachable = MapEngine::reachable_hexes(&state.board, &my_structure_hexes, nav_range);
        for coord in &reachable {
            if can_build_at(state, player_id, *coord) {
                actions.push(GameAction::Build { coord: *coord });
            }
        }

        // Upgrade — enumerate own structures that can be upgraded
        for s in &player.structures {
            let targets = upgrade_targets(s.kind);
            for to in targets {
                if validate_upgrade(state, player_id, s.hex, to).is_ok() {
                    actions.push(GameAction::Upgrade { coord: s.hex, to });
                }
            }
        }

        // Research advance
        for &track in &ResearchTrack::all() {
            if validate_research(state, player_id, track).is_ok() {
                actions.push(GameAction::ResearchAdvance { track });
            }
        }

        // Gaia formation
        for coord in &reachable {
            if validate_gaia_formation(state, player_id, *coord).is_ok() {
                actions.push(GameAction::GaiaFormation { coord: *coord });
            }
        }

        // Academy(Qic) action
        if validate_academy_qic_action(state, player_id).is_ok() {
            actions.push(GameAction::AcademyQicAction);
        }

        actions
    }

    // ── Setup-phase actions ─────────────────────────────────────────────────

    /// Validates and applies a setup-phase action.
    pub fn apply_setup_action(
        state: &mut GameState,
        player_id: PlayerId,
        action: SetupAction,
    ) -> Result<Vec<GameEvent>, RuleError> {
        ensure_setup_phase(state)?;
        apply_setup(state, player_id, action)
    }

    // ── Round transition ──────────────────────────────────────────────────

    /// Advances from `RoundScoring{round}` through the Gaia phase (rulebook
    /// p.11) and Income phase (rulebook p.10) into the next round's
    /// `ActionPhase`. Round-tile VP is already applied incrementally by
    /// `check_round_tile_bonus` as qualifying actions happen during the
    /// round, so this does not re-derive it from the event log (which
    /// nothing currently populates).
    pub fn advance_to_next_round(state: &mut GameState) -> Result<Vec<GameEvent>, RuleError> {
        let GamePhase::RoundScoring { round } = state.phase else {
            return Err(RuleError::WrongPhase);
        };
        let mut events = Vec::new();

        events.extend(apply_gaia_phase(state));
        let pending_income_orders = apply_income_phase(state);

        if pending_income_orders.is_empty() {
            finish_round_transition(state, round);
        } else {
            state.phase = GamePhase::IncomeOrderPending {
                queue: pending_income_orders,
                round,
            };
        }

        Ok(events)
    }
}

// ── Phase guards ──────────────────────────────────────────────────────────────

fn ensure_action_phase(state: &GameState, player_id: PlayerId) -> Result<(), RuleError> {
    match &state.phase {
        GamePhase::ActionPhase { active_player } => {
            let active_id = state
                .turn_order
                .get(*active_player)
                .copied()
                .ok_or(RuleError::NotYourTurn)?;
            if active_id != player_id {
                return Err(RuleError::NotYourTurn);
            }
            Ok(())
        }
        _ => Err(RuleError::WrongPhase),
    }
}

fn ensure_setup_phase(state: &GameState) -> Result<(), RuleError> {
    match &state.phase {
        GamePhase::Setup(_) => Ok(()),
        _ => Err(RuleError::WrongPhase),
    }
}

// ── Build ─────────────────────────────────────────────────────────────────────

fn validate_build(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    // Structure limit
    let mine_count = player
        .structures
        .iter()
        .filter(|s| s.kind == StructureType::Mine)
        .count();
    if mine_count >= MAX_MINES {
        return Err(RuleError::StructureLimit(StructureType::Mine));
    }

    let hex = state
        .board
        .hexes
        .get(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    let planet = hex.planet.as_ref().ok_or(RuleError::InvalidTarget(coord))?;

    // Must not already be owned by this player
    if planet.owner == Some(player_id) {
        return Err(RuleError::TargetOccupied(coord));
    }

    // Must not be Transdim unless already Gaia-formed
    if planet.planet_type == PlanetType::Transdim && !planet.is_gaia_formed {
        return Err(RuleError::InvalidTarget(coord));
    }

    // Reachability — range determined by Navigation research track
    let nav_level = player.research_tracks.navigation as usize;
    let nav_range = NAV_RANGE[nav_level.min(NAV_RANGE.len() - 1)];
    let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
    let reachable = MapEngine::reachable_hexes(&state.board, &starts, nav_range);
    if !reachable.contains(&coord) {
        return Err(RuleError::OutOfRange {
            hex: coord,
            range: nav_range,
            nav_level: nav_level as u8,
        });
    }

    // Gaia planet: costs 1 QIC instead of terraforming steps
    let target_type = if planet.is_gaia_formed {
        PlanetType::Gaia
    } else {
        planet.planet_type
    };
    let (terraform_ore, qic_cost) = if planet.is_gaia_formed {
        (0u8, gaia_qic_cost(state, player_id)) // rulebook p.11; some factions override
    } else {
        let ore = terraform_ore_cost(
            state,
            player_id,
            target_type,
            player.research_tracks.terraforming,
        );
        (ore, 0)
    };

    let total_ore = MINE_ORE_COST.saturating_add(terraform_ore);
    if player.resources.ore < total_ore {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Ore,
        ));
    }
    if player.resources.credits < MINE_CREDITS_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Credits,
        ));
    }
    if qic_cost > 0 && player.resources.qic < qic_cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Qic,
        ));
    }

    Ok(())
}

fn apply_build(state: &mut GameState, player_id: PlayerId, coord: HexCoord) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let hex = match state.board.hexes.get(&coord) {
        Some(h) => h.clone(),
        None => return events,
    };
    let is_gaia_formed = hex.planet.as_ref().is_some_and(|p| p.is_gaia_formed);
    let planet_type_raw = hex.planet.as_ref().map(|p| p.planet_type);

    let (terraform_ore, qic_cost) = if is_gaia_formed {
        (0u8, gaia_qic_cost(state, player_id))
    } else if let Some(target_type) = planet_type_raw {
        let track_level = state
            .player(player_id)
            .map_or(0, |p| p.research_tracks.terraforming);
        (
            terraform_ore_cost(state, player_id, target_type, track_level),
            0,
        )
    } else {
        (0u8, 0u8)
    };
    let ore_cost = MINE_ORE_COST + terraform_ore;

    if let Some(player) = state.player_mut(player_id) {
        player.resources.ore = player.resources.ore.saturating_sub(ore_cost);
        player.resources.credits = player.resources.credits.saturating_sub(MINE_CREDITS_COST);
        player.resources.qic = player.resources.qic.saturating_sub(qic_cost);
        let delta = ResourceDelta {
            ore: -(ore_cost as i8),
            credits: -(MINE_CREDITS_COST as i8),
            qic: -(qic_cost as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });

        player.structures.push(crate::game_state::Structure {
            hex: coord,
            kind: StructureType::Mine,
        });
    }

    // Mark hex as owned
    if let Some(hex_entry) = state.board.hexes.get_mut(&coord) {
        if let Some(planet) = &mut hex_entry.planet {
            planet.owner = Some(player_id);
        }
        hex_entry.structures.push(PlacedStructure {
            owner: player_id,
            kind: StructureType::Mine,
        });
    }

    events.push(GameEvent::StructureBuilt {
        player: player_id,
        hex: coord,
        kind: StructureType::Mine,
    });

    // Faction ability hook (e.g. Darkanians' first-colonization bonus).
    // A non-empty result is currently always a one-shot "first colonization"
    // bonus, so mark it used here rather than asking `on_build` to mutate state.
    if let Some(ability) = ability_for(state, player_id) {
        let ability_events = ability.on_build(state, player_id, coord);
        if !ability_events.is_empty() {
            if let Some(p) = state.player_mut(player_id) {
                p.first_colonization_bonus_used = true;
            }
        }
        for event in &ability_events {
            apply_ability_event(state, event);
        }
        events.extend(ability_events);
    }

    // Round tile bonus
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::BuildMine,
    ));

    if !maybe_enter_charge_power_phase(state, player_id, coord) {
        advance_turn(state);
    }
    events
}

// ── Upgrade ───────────────────────────────────────────────────────────────────

fn validate_upgrade(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    to: StructureType,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let existing = player
        .structures
        .iter()
        .find(|s| s.hex == coord)
        .ok_or(RuleError::InvalidTarget(coord))?;

    // Validate upgrade path
    let valid_upgrade = match (existing.kind, to) {
        (StructureType::Mine, StructureType::TradingStation) => true,
        (StructureType::TradingStation, StructureType::ResearchLab) => true,
        (StructureType::TradingStation, StructureType::PlanetaryInstitute) => !player
            .structures
            .iter()
            .any(|s| s.kind == StructureType::PlanetaryInstitute),
        (StructureType::ResearchLab, StructureType::Academy(_)) => true,
        _ => false,
    };
    if !valid_upgrade {
        return Err(RuleError::InvalidUpgrade {
            from: existing.kind,
            to,
        });
    }

    // Structure limits
    match to {
        StructureType::TradingStation => {
            let count = player
                .structures
                .iter()
                .filter(|s| s.kind == StructureType::TradingStation)
                .count();
            if count >= MAX_TRADING_STATIONS {
                return Err(RuleError::StructureLimit(to));
            }
        }
        StructureType::ResearchLab => {
            let count = player
                .structures
                .iter()
                .filter(|s| s.kind == StructureType::ResearchLab)
                .count();
            if count >= MAX_RESEARCH_LABS {
                return Err(RuleError::StructureLimit(to));
            }
        }
        StructureType::Academy(_) => {
            let count = player
                .structures
                .iter()
                .filter(|s| matches!(s.kind, StructureType::Academy(_)))
                .count();
            if count >= MAX_ACADEMIES {
                return Err(RuleError::StructureLimit(to));
            }
        }
        _ => {}
    }

    // Resource check — rulebook p.13 costs
    let (ore_cost, credits_cost) = upgrade_cost(
        &existing.kind,
        &to,
        has_opponent_structure_nearby(state, player_id, coord),
    );
    if player.resources.ore < ore_cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Ore,
        ));
    }
    if player.resources.credits < credits_cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Credits,
        ));
    }

    Ok(())
}

fn apply_upgrade(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
    to: StructureType,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let from = match state
        .player(player_id)
        .and_then(|p| p.structures.iter().find(|s| s.hex == coord))
        .map(|s| s.kind)
    {
        Some(k) => k,
        None => return events,
    };

    let (ore_cost, credits_cost) = upgrade_cost(
        &from,
        &to,
        has_opponent_structure_nearby(state, player_id, coord),
    );
    if let Some(player) = state.player_mut(player_id) {
        player.resources.ore = player.resources.ore.saturating_sub(ore_cost);
        player.resources.credits = player.resources.credits.saturating_sub(credits_cost);
        let delta = ResourceDelta {
            ore: -(ore_cost as i8),
            credits: -(credits_cost as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });

        if let Some(s) = player.structures.iter_mut().find(|s| s.hex == coord) {
            s.kind = to;
        }
    }

    if let Some(hex) = state.board.hexes.get_mut(&coord) {
        if let Some(s) = hex.structures.iter_mut().find(|s| s.owner == player_id) {
            s.kind = to;
        }
    }

    events.push(GameEvent::StructureUpgraded {
        player: player_id,
        hex: coord,
        from,
        to,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::Upgrade,
    ));

    if !maybe_enter_charge_power_phase(state, player_id, coord) {
        advance_turn(state);
    }
    events
}

// ── Research ──────────────────────────────────────────────────────────────────

fn validate_research(
    state: &GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.resources.knowledge < RESEARCH_KNOWLEDGE_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Knowledge,
        ));
    }
    if player.research_tracks.get(track) >= 5 {
        return Err(RuleError::ActionNotAllowed(
            "research track is at maximum level".to_string(),
        ));
    }
    Ok(())
}

fn apply_research(
    state: &mut GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    let new_level = if let Some(player) = state.player_mut(player_id) {
        player.resources.knowledge = player
            .resources
            .knowledge
            .saturating_sub(RESEARCH_KNOWLEDGE_COST);
        let delta = ResourceDelta {
            knowledge: -(RESEARCH_KNOWLEDGE_COST as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });
        player.research_tracks.increment(track);
        player.research_tracks.get(track)
    } else {
        return events;
    };
    events.push(GameEvent::ResearchAdvanced {
        player: player_id,
        track,
        level: new_level,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
    ));
    advance_turn(state);
    events
}

// ── Federation ────────────────────────────────────────────────────────────────

fn validate_federation(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    if hexes.is_empty() {
        return Err(RuleError::FederationDisconnected);
    }

    // No satellites on space tiles
    for coord in hexes {
        if let Some(hex) = state.board.hexes.get(coord) {
            if hex.is_space_tile() {
                return Err(RuleError::SatelliteOnSpaceTile(*coord));
            }
        }
    }

    // Connectivity
    if !MapEngine::is_connected(hexes) {
        return Err(RuleError::FederationDisconnected);
    }

    // Power threshold
    let power = MapEngine::federation_power(&state.board, player_id, hexes);
    if power < FEDERATION_MIN_POWER {
        return Err(RuleError::FederationInsufficientPower); // unit variant
    }

    // Player must have a federation token available
    let _ = player; // used earlier
    Ok(())
}

fn apply_federation(
    state: &mut GameState,
    player_id: PlayerId,
    hexes: Vec<HexCoord>,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    let token = FederationToken(1); // next available token id (simplified)
    if let Some(player) = state.player_mut(player_id) {
        player.federation_tokens.push(token.clone());
    }
    events.push(GameEvent::FederationFormed {
        player: player_id,
        hexes,
        token,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::FormFederation,
    ));
    advance_turn(state);
    events
}

// ── Power action ──────────────────────────────────────────────────────────────

fn validate_power_action(state: &GameState, player_id: PlayerId, id: u8) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if state.used_power_actions.contains(&id) {
        return Err(RuleError::ActionNotAllowed(
            "power action slot already taken this round".to_string(),
        ));
    }
    let cost = power_action_cost(id);
    if player.resources.power.bowl3 < cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }
    Ok(())
}

fn apply_power_action(state: &mut GameState, player_id: PlayerId, id: u8) -> Vec<GameEvent> {
    let mut events = Vec::new();
    let cost = power_action_cost(id);
    let delta = apply_power_effect(state, player_id, id, cost);
    state.used_power_actions.push(id);
    events.push(GameEvent::ResourceChanged {
        player: player_id,
        delta,
    });
    advance_turn(state);
    events
}

// ── Special action ────────────────────────────────────────────────────────────

fn validate_special_action(
    state: &GameState,
    player_id: PlayerId,
    _id: u8,
) -> Result<(), RuleError> {
    state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if let Some(ability) = ability_for(state, player_id) {
        ability.special_action(state, player_id)?;
    }
    Ok(())
}

fn apply_special_action(state: &mut GameState, player_id: PlayerId, id: u8) -> Vec<GameEvent> {
    let events = match ability_for(state, player_id) {
        // Already re-validated in validate_special_action; Err here can't happen.
        Some(ability) => ability.special_action(state, player_id).unwrap_or_default(),
        None => {
            log::warn!(
                "special_action id={} for player {} — no faction ability registered",
                id,
                player_id
            );
            vec![]
        }
    };
    for event in &events {
        apply_ability_event(state, event);
    }
    advance_turn(state);
    events
}

// ── Gaia formation ────────────────────────────────────────────────────────────

fn validate_gaia_formation(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    // Gaia Project track level >= 1 required
    let gaia_level = player.research_tracks.gaia as usize;
    if gaia_level == 0 {
        return Err(RuleError::ActionNotAllowed(
            "gaia project track level too low".to_string(),
        ));
    }

    // Must have an available gaiaformer
    if player.gaiaformers_available() == 0 {
        return Err(RuleError::NoGaiaformerAvailable);
    }

    // Power cost: must be able to move N tokens from areas I/II/III to Gaia area
    let power_needed = GAIA_POWER_COST[gaia_level.min(GAIA_POWER_COST.len() - 1)];
    let available_power = player
        .resources
        .power
        .bowl1
        .saturating_add(player.resources.power.bowl2)
        .saturating_add(player.resources.power.bowl3);
    if available_power < power_needed {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }

    // Target must be Transdim and not yet gaia-forming
    let hex = state
        .board
        .hexes
        .get(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    let planet = hex.planet.as_ref().ok_or(RuleError::InvalidTarget(coord))?;
    if planet.planet_type != PlanetType::Transdim {
        return Err(RuleError::InvalidTarget(coord));
    }
    if planet.is_gaia_formed || planet.owner.is_some() {
        return Err(RuleError::TargetOccupied(coord));
    }

    // Reachability
    let nav_level = player.research_tracks.navigation as usize;
    let nav_range = NAV_RANGE[nav_level.min(NAV_RANGE.len() - 1)];
    let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
    let reachable = MapEngine::reachable_hexes(&state.board, &starts, nav_range);
    if !reachable.contains(&coord) {
        return Err(RuleError::OutOfRange {
            hex: coord,
            range: nav_range,
            nav_level: nav_level as u8,
        });
    }

    Ok(())
}

fn apply_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    if let Some(player) = state.player_mut(player_id) {
        let gaia_level = player.research_tracks.gaia as usize;
        let power_needed = GAIA_POWER_COST[gaia_level.min(GAIA_POWER_COST.len() - 1)];

        // Move power tokens from areas I/II/III to Gaia area (bowl1 first, then bowl2, then bowl3)
        let mut remaining = power_needed;
        let from_bowl1 = remaining.min(player.resources.power.bowl1);
        player.resources.power.bowl1 -= from_bowl1;
        remaining -= from_bowl1;
        let from_bowl2 = remaining.min(player.resources.power.bowl2);
        player.resources.power.bowl2 -= from_bowl2;
        remaining -= from_bowl2;
        let from_bowl3 = remaining.min(player.resources.power.bowl3);
        player.resources.power.bowl3 -= from_bowl3;
        player.resources.power.gaia_forming = player
            .resources
            .power
            .gaia_forming
            .saturating_add(power_needed);

        player.gaiaformers_deployed += 1;
    }

    if let Some(hex) = state.board.hexes.get_mut(&coord) {
        if let Some(planet) = &mut hex.planet {
            planet.owner = Some(player_id);
        }
    }

    events.push(GameEvent::GaiaFormingStarted {
        player: player_id,
        hex: coord,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::GaiaProject,
    ));
    advance_turn(state);
    events
}

// ── QIC action ────────────────────────────────────────────────────────────────

fn validate_qic_action(
    state: &GameState,
    player_id: PlayerId,
    kind: &QicActionKind,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if state
        .used_qic_action_slots
        .contains(&qic_action_slot_id(kind))
    {
        return Err(RuleError::ActionNotAllowed(
            "QIC action slot already taken this round".to_string(),
        ));
    }
    let qic_cost = qic_action_cost(kind);
    if player.resources.qic < qic_cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Qic,
        ));
    }

    if let QicActionKind::BuildSatellite { coord } = kind {
        let hex = state
            .board
            .hexes
            .get(coord)
            .ok_or(RuleError::InvalidTarget(*coord))?;
        if hex.is_space_tile() {
            return Err(RuleError::SatelliteOnSpaceTile(*coord));
        }
    }

    Ok(())
}

fn apply_qic_action(
    state: &mut GameState,
    player_id: PlayerId,
    kind: QicActionKind,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    let qic_cost = qic_action_cost(&kind);
    state.used_qic_action_slots.push(qic_action_slot_id(&kind));
    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player.resources.qic.saturating_sub(qic_cost);
        let delta = ResourceDelta {
            qic: -(qic_cost as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });
    }
    match kind {
        QicActionKind::BuildSatellite { coord } => {
            if let Some(hex) = state.board.hexes.get_mut(&coord) {
                hex.satellites.push(player_id);
            }
        }
        QicActionKind::ColoniseLostPlanet { coord } => {
            events.push(GameEvent::ProtoPlanetColonized {
                player: player_id,
                hex: coord,
            });
        }
        QicActionKind::GainOre => {
            if let Some(player) = state.player_mut(player_id) {
                player.resources.ore += 1;
            }
            events.push(GameEvent::ResourceChanged {
                player: player_id,
                delta: ResourceDelta {
                    ore: 1,
                    ..ResourceDelta::zero()
                },
            });
        }
        QicActionKind::ResearchStep => {
            // Treated as a free research advance (no knowledge cost); caller chose track separately
            // In full implementation this would accept a track parameter
        }
    }
    advance_turn(state);
    events
}

// ── Academy(Qic) action ──────────────────────────────────────────────────────

fn validate_academy_qic_action(state: &GameState, player_id: PlayerId) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let has_academy_qic = player
        .structures
        .iter()
        .any(|s| matches!(s.kind, StructureType::Academy(AcademyType::Qic)));
    if !has_academy_qic {
        return Err(RuleError::ActionNotAllowed(
            "requires a built Academy(Qic)".to_string(),
        ));
    }
    if player.academy_qic_action_used_this_round {
        return Err(RuleError::ActionNotAllowed(
            "already used this round".to_string(),
        ));
    }
    Ok(())
}

/// The repeatable action granted by an Academy(Qic) (rulebook p.13): gain
/// 1 QIC, or the faction's override (`factions.toml`'s `academy_qic_action`
/// — only BalTaks deviates, gaining 4 credits instead).
fn apply_academy_qic_action(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    let mut events = Vec::new();
    let faction = state.player(player_id).and_then(|p| p.faction);
    let factions = crate::data::load_factions().factions;
    let data = faction.and_then(|f| factions.iter().find(|d| d.faction_id() == Some(f)));
    let (kind, amount) = data
        .and_then(|d| d.academy_qic_action.as_ref())
        .and_then(|bonus| Some((bonus.resource_kind()?, bonus.amount)))
        .unwrap_or((ResourceKind::Qic, 1));

    if let Some(player) = state.player_mut(player_id) {
        add_resource(player, kind, amount);
        player.academy_qic_action_used_this_round = true;
    }
    let delta = match kind {
        ResourceKind::Ore => ResourceDelta {
            ore: amount as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Credits => ResourceDelta {
            credits: amount as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Knowledge => ResourceDelta {
            knowledge: amount as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Qic => ResourceDelta {
            qic: amount as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Power => ResourceDelta::zero(), // power isn't tracked in ResourceDelta
    };
    events.push(GameEvent::ResourceChanged {
        player: player_id,
        delta,
    });

    advance_turn(state);
    events
}

// ── Pass ──────────────────────────────────────────────────────────────────────

fn validate_pass(
    state: &GameState,
    player_id: PlayerId,
    booster_id: Option<u8>,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.passed {
        return Err(RuleError::AlreadyPassed);
    }
    if let Some(bid) = booster_id {
        let available = state.boosters.iter().any(|b| b.0 == bid);
        if !available {
            return Err(RuleError::ActionNotAllowed(format!(
                "booster {bid} not available"
            )));
        }
    }
    Ok(())
}

fn apply_pass(
    state: &mut GameState,
    player_id: PlayerId,
    booster_id: Option<u8>,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let booster = booster_id
        .and_then(|id| state.boosters.iter().find(|b| b.0 == id).cloned())
        .unwrap_or(crate::game_state::Booster(0));

    if let Some(player) = state.player_mut(player_id) {
        player.passed = true;
    }

    events.push(GameEvent::PlayerPassed {
        player: player_id,
        booster,
    });

    advance_turn(state);
    events
}

// ── Setup-phase application ───────────────────────────────────────────────────

fn apply_setup(
    state: &mut GameState,
    player_id: PlayerId,
    action: SetupAction,
) -> Result<Vec<GameEvent>, RuleError> {
    let SetupAction::SelectFaction { faction } = action;
    let (event, next_player, is_complete) = {
        let selection = state
            .faction_selection
            .as_mut()
            .ok_or(RuleError::WrongPhase)?;
        let event = SetupPolicy::select_faction(selection, player_id, faction)?;
        (event, selection.current_player(), selection.is_complete())
    };

    let player = state.player_mut(player_id).ok_or(RuleError::NotYourTurn)?;
    player.faction = Some(faction);

    if is_complete {
        seed_starting_resources(state);
    }
    state.phase = if is_complete {
        GamePhase::Setup(SetupPhase::Complete)
    } else if let Some(active_player) = next_player {
        GamePhase::Setup(SetupPhase::FactionSelection { active_player })
    } else {
        return Err(RuleError::WrongPhase);
    };

    Ok(vec![event])
}

/// Grants every player their faction's starting ore/credits/knowledge/QIC and
/// power bowls once faction selection completes. `factions.toml`'s
/// `starting_structures` are deliberately not placed here — where on the
/// board to put them is a player decision the engine doesn't yet model as
/// its own setup step.
fn seed_starting_resources(state: &mut GameState) {
    let factions = crate::data::load_factions().factions;
    for player in &mut state.players {
        let Some(faction_id) = player.faction else {
            continue;
        };
        let Some(data) = factions.iter().find(|f| f.faction_id() == Some(faction_id)) else {
            continue;
        };
        player.resources = Resources {
            ore: data.starting_ore,
            credits: data.starting_credits,
            knowledge: data.starting_knowledge,
            qic: data.starting_qic,
            power: PowerCycle {
                bowl1: data.starting_bowl1,
                bowl2: data.starting_bowl2,
                bowl3: data.starting_bowl3,
                gaia_bowl: 0,
                gaia_forming: 0,
            },
            spent_gaia_formers: 0,
        };
        player.gaiaformers_total = data.gaiaformers;

        for (track, level) in data.starting_tracks() {
            player.research_tracks.set(track, level);
        }
        // Rulebook (setup section, base game): a faction board showing a
        // non-zero starting track level also grants that level's one-time
        // resource bonus immediately — EXCEPT Economy/Science, whose level-1
        // rewards are ongoing per-round income bonuses, not one-time grants.
        for bonus in &data.starting_track_bonuses {
            if bonus.track == "Economy" || bonus.track == "Science" {
                continue;
            }
            if let Some(effect) = crate::data::get_level_effect(&bonus.track, bonus.level) {
                player.resources.ore = player.resources.ore.saturating_add(effect.ore.max(0) as u8);
                player.resources.credits = player
                    .resources
                    .credits
                    .saturating_add(effect.credits.max(0) as u8);
                player.resources.knowledge = player
                    .resources
                    .knowledge
                    .saturating_add(effect.knowledge.max(0) as u8);
                player.resources.qic = player.resources.qic.saturating_add(effect.qic.max(0) as u8);
                player.gaiaformers_total =
                    player.gaiaformers_total.saturating_add(effect.gaiaformers);
            }
        }
    }
}

// ── Turn advancement ──────────────────────────────────────────────────────────

fn advance_turn(state: &mut GameState) {
    let current = match &state.phase {
        GamePhase::ActionPhase { active_player } => *active_player,
        _ => return,
    };
    state.phase = match next_active_player_index(state, current) {
        Some(next) => GamePhase::ActionPhase {
            active_player: next,
        },
        None => GamePhase::RoundScoring { round: state.round },
    };
}

/// The next non-passed player's `turn_order` index after `current`, or
/// `None` if every player (searched a full circle) has passed.
fn next_active_player_index(state: &GameState, current: usize) -> Option<usize> {
    let n = state.turn_order.len();
    if n == 0 {
        return None;
    }
    let mut next = (current + 1) % n;
    for _ in 0..n {
        let pid = state.turn_order.get(next).copied()?;
        if !state.player(pid).is_none_or(|p| p.passed) {
            return Some(next);
        }
        next = (next + 1) % n;
    }
    None
}

// ── Charge Power (Passive Action, rulebook p.16-17) ─────────────────────────

/// Opponents (in clockwise turn order from `builder`) with at least one
/// structure within range 2 of `coord`, each paired with their single
/// highest-power-value qualifying structure's power value. An opponent who
/// has already passed is still eligible (rulebook: "An opponent that has
/// passed can still charge power").
fn eligible_chargers(state: &GameState, builder: PlayerId, coord: HexCoord) -> Vec<PendingCharge> {
    let n = state.turn_order.len();
    let Some(start) = state.turn_order.iter().position(|&p| p == builder) else {
        return vec![];
    };

    let mut chargers = Vec::new();
    for offset in 1..n {
        let pid = state.turn_order[(start + offset) % n];
        let max_power = state
            .board
            .hexes
            .values()
            .filter(|hex| hex.coord.distance(&coord) <= 2)
            .flat_map(|hex| &hex.structures)
            .filter(|s| s.owner == pid && s.kind != StructureType::Satellite)
            .map(|s| s.kind.power_value())
            .max();
        if let Some(power) = max_power {
            if power > 0 {
                chargers.push(PendingCharge {
                    player: pid,
                    hex: coord,
                    max_power: power as u8,
                });
            }
        }
    }
    chargers
}

/// If any opponent is eligible to charge power for this Build/Upgrade,
/// pauses `ActionPhase` into `ChargePowerPending` and returns `true` (the
/// caller must skip its own `advance_turn`). Returns `false` when there are
/// no eligible chargers, so the caller should proceed as before.
fn maybe_enter_charge_power_phase(
    state: &mut GameState,
    builder: PlayerId,
    coord: HexCoord,
) -> bool {
    let queue = eligible_chargers(state, builder, coord);
    if queue.is_empty() {
        return false;
    }
    let current = match &state.phase {
        GamePhase::ActionPhase { active_player } => *active_player,
        _ => return false,
    };
    let resume_active_player = next_active_player_index(state, current);
    state.phase = GamePhase::ChargePowerPending {
        queue,
        resume_active_player,
    };
    true
}

/// Returns a copy of the queue-front entry if `player_id` is next up to
/// decide during `ChargePowerPending`.
fn ensure_charge_power_phase(
    state: &GameState,
    player_id: PlayerId,
) -> Result<PendingCharge, RuleError> {
    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => match queue.first() {
            Some(entry) if entry.player == player_id => Ok(entry.clone()),
            _ => Err(RuleError::NotYourTurn),
        },
        _ => Err(RuleError::WrongPhase),
    }
}

fn validate_charge_power(
    state: &GameState,
    player_id: PlayerId,
    _accept: bool,
) -> Result<(), RuleError> {
    ensure_charge_power_phase(state, player_id)?;
    Ok(())
}

/// All-or-nothing (rulebook p.17): the player cannot pick a partial amount.
/// Accepting charges `min(structure's power value, movable power tokens,
/// affordable VP + 1)` — reduced automatically by the two documented
/// exceptions (not enough tokens left to move; not enough VP) rather than
/// rejected outright.
fn apply_charge_power(state: &mut GameState, player_id: PlayerId, accept: bool) -> Vec<GameEvent> {
    let entry = match ensure_charge_power_phase(state, player_id) {
        Ok(entry) => entry,
        Err(_) => return vec![], // already validated; defensive no-op
    };

    if accept {
        if let Some(player) = state.player_mut(player_id) {
            let movable =
                u32::from(player.resources.power.bowl1) + u32::from(player.resources.power.bowl2);
            let affordable = player.vp.max(0) as u32 + 1;
            let amount = u32::from(entry.max_power).min(movable).min(affordable) as u8;
            if amount > 0 {
                player.vp -= i32::from(amount) - 1;
                apply_power_charge(&mut player.resources.power, amount);
            }
        }
    }

    if let GamePhase::ChargePowerPending {
        queue,
        resume_active_player,
    } = &mut state.phase
    {
        if !queue.is_empty() {
            queue.remove(0);
        }
        if queue.is_empty() {
            state.phase = match resume_active_player {
                Some(idx) => GamePhase::ActionPhase {
                    active_player: *idx,
                },
                None => GamePhase::RoundScoring { round: state.round },
            };
        }
    }

    vec![]
}

/// Returns a copy of the queue-front entry if `player_id` is next up to
/// decide during `IncomeOrderPending`.
fn ensure_income_order_phase(
    state: &GameState,
    player_id: PlayerId,
) -> Result<PendingIncomeOrder, RuleError> {
    match &state.phase {
        GamePhase::IncomeOrderPending { queue, .. } => match queue.first() {
            Some(entry) if entry.player == player_id => Ok(entry.clone()),
            _ => Err(RuleError::NotYourTurn),
        },
        _ => Err(RuleError::WrongPhase),
    }
}

fn validate_choose_income_order(
    state: &GameState,
    player_id: PlayerId,
    _charge_first: bool,
) -> Result<(), RuleError> {
    ensure_income_order_phase(state, player_id)?;
    Ok(())
}

/// Applies this round's PlanetaryInstitute charge and bonus power token in
/// the chosen order — `charge_first` sweeps the fresh token into bowl2 along
/// with whatever the charge already moves; choosing to gain the token first
/// keeps it in bowl1, untouched by this round's charge (see
/// `GameAction::ChooseIncomeOrder`).
fn apply_choose_income_order(
    state: &mut GameState,
    player_id: PlayerId,
    charge_first: bool,
) -> Vec<GameEvent> {
    let entry = match ensure_income_order_phase(state, player_id) {
        Ok(entry) => entry,
        Err(_) => return vec![], // already validated; defensive no-op
    };

    if let Some(player) = state.player_mut(player_id) {
        if charge_first {
            apply_power_charge(&mut player.resources.power, entry.charge_amount);
            player.resources.power.bowl1 = player
                .resources
                .power
                .bowl1
                .saturating_add(entry.bonus_tokens);
        } else {
            player.resources.power.bowl1 = player
                .resources
                .power
                .bowl1
                .saturating_add(entry.bonus_tokens);
            apply_power_charge(&mut player.resources.power, entry.charge_amount);
        }
    }

    if let GamePhase::IncomeOrderPending { queue, round } = &mut state.phase {
        let round = *round;
        if !queue.is_empty() {
            queue.remove(0);
        }
        if queue.is_empty() {
            finish_round_transition(state, round);
        }
    }

    vec![]
}

// ── Gaia phase ───────────────────────────────────────────────────────────────

/// Rulebook p.11: Transdim planets with a Gaiaformer become Gaia planets,
/// and each player's Gaia-area power moves into the power cycle (Area I,
/// except the Terrans move directly to Area II).
fn apply_gaia_phase(state: &mut GameState) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let completed: Vec<(HexCoord, PlayerId)> = state
        .board
        .hexes
        .iter()
        .filter_map(|(coord, hex)| {
            let planet = hex.planet.as_ref()?;
            if planet.planet_type == PlanetType::Transdim && !planet.is_gaia_formed {
                Some((*coord, planet.owner?))
            } else {
                None
            }
        })
        .collect();
    for (coord, owner) in completed {
        if let Some(hex) = state.board.hexes.get_mut(&coord) {
            if let Some(planet) = &mut hex.planet {
                planet.is_gaia_formed = true;
            }
        }
        events.push(GameEvent::GaiaFormingComplete {
            player: owner,
            hex: coord,
        });
    }

    for player in &mut state.players {
        let amount = player.resources.power.gaia_forming;
        if amount == 0 {
            continue;
        }
        let destination = player
            .faction
            .map(|f| faction_registry().get(f).gaia_phase_power_destination())
            .unwrap_or(crate::game_state::PowerBowl::Area1);
        match destination {
            crate::game_state::PowerBowl::Area1 => {
                player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(amount);
            }
            crate::game_state::PowerBowl::Area2 => {
                player.resources.power.bowl2 = player.resources.power.bowl2.saturating_add(amount);
            }
        }
        player.resources.power.gaia_forming = 0;
    }

    events
}

// ── Income phase ─────────────────────────────────────────────────────────────

/// Rulebook p.10: at the start of each round, gain resources from the
/// current level of each research track, from built Mine/TradingStation/
/// ResearchLab/Academy/PlanetaryInstitute structures (faction board income
/// rows), and from the faction's passive income ability. (Round booster /
/// tech tile income are not modeled yet — see README "Known migration work".)
///
/// Returns the players who must choose an order for this round's
/// PlanetaryInstitute charge vs. bonus power token (see
/// `planetary_institute_income`) — every other income effect above is
/// already applied by the time this returns. An empty result means the
/// round can finish immediately; a non-empty one means the caller must
/// enter `GamePhase::IncomeOrderPending` and wait for
/// `GameAction::ChooseIncomeOrder` from each queued player before finishing.
fn apply_income_phase(state: &mut GameState) -> Vec<PendingIncomeOrder> {
    let player_ids: Vec<PlayerId> = state.players.iter().map(|p| p.player_id).collect();
    let factions = crate::data::load_factions().factions;
    let mut pending_income_orders = Vec::new();
    for player_id in player_ids {
        let Some(faction) = state.player(player_id).and_then(|p| p.faction) else {
            continue;
        };
        let track_levels: Vec<(ResearchTrack, u8)> = ResearchTrack::all()
            .into_iter()
            .filter_map(|track| {
                let level = state.player(player_id)?.research_tracks.get(track);
                (level > 0).then_some((track, level))
            })
            .collect();
        let passive = faction_registry()
            .get(faction)
            .passive_income(state, player_id);
        let faction_data = factions.iter().find(|f| f.faction_id() == Some(faction));

        if let Some(player) = state.player_mut(player_id) {
            for (track, level) in track_levels {
                if let Some(effect) = crate::data::get_level_effect(track.as_str(), level) {
                    player.resources.ore =
                        player.resources.ore.saturating_add(effect.ore.max(0) as u8);
                    player.resources.credits = player
                        .resources
                        .credits
                        .saturating_add(effect.credits.max(0) as u8);
                    player.resources.knowledge = player
                        .resources
                        .knowledge
                        .saturating_add(effect.knowledge.max(0) as u8);
                    player.resources.qic =
                        player.resources.qic.saturating_add(effect.qic.max(0) as u8);
                    apply_power_charge(&mut player.resources.power, effect.power_charge);
                }
            }
            player.resources.ore = player.resources.ore.saturating_add(passive.ore);
            player.resources.credits = player.resources.credits.saturating_add(passive.credits);
            player.resources.knowledge =
                player.resources.knowledge.saturating_add(passive.knowledge);
            player.resources.qic = player.resources.qic.saturating_add(passive.qic);
            if let Some(data) = faction_data {
                apply_structure_income(player, data);
                if let Some((charge, bonus_tokens)) = planetary_institute_income(player, data) {
                    if bonus_tokens > 0 {
                        pending_income_orders.push(PendingIncomeOrder {
                            player: player_id,
                            charge_amount: charge,
                            bonus_tokens,
                        });
                    } else {
                        apply_power_charge(&mut player.resources.power, charge);
                    }
                    if let Some(bonus) = &data.planetary_institute_bonus_resource {
                        if let Some(kind) = bonus.resource_kind() {
                            add_resource(player, kind, bonus.amount);
                        }
                    }
                }
            }
        }
    }
    pending_income_orders
}

/// Resets `passed` flags and reopens `ActionPhase` for the round after
/// `round` (shared by the immediate-finish and `IncomeOrderPending`-drained
/// paths in `advance_to_next_round`/`apply_choose_income_order`).
fn finish_round_transition(state: &mut GameState, round: u8) {
    for player in &mut state.players {
        player.passed = false;
        player.academy_qic_action_used_this_round = false;
    }
    state.used_power_actions.clear();
    state.used_qic_action_slots.clear();
    state.round = round + 1;
    state.phase = GamePhase::ActionPhase { active_player: 0 };
}

/// Sum of `table[0..count.min(table.len())]` — the revealed portion of a
/// structure's round-income table for the Nth built (faction board income
/// rows, revealed left-to-right as each structure of that type is built).
fn cumulative_table_income(table: &[u8], count: usize) -> u8 {
    table
        .iter()
        .take(count)
        .fold(0u8, |acc, v| acc.saturating_add(*v))
}

fn add_resource(player: &mut PlayerState, kind: ResourceKind, amount: u8) {
    match kind {
        ResourceKind::Ore => player.resources.ore = player.resources.ore.saturating_add(amount),
        ResourceKind::Credits => {
            player.resources.credits = player.resources.credits.saturating_add(amount)
        }
        ResourceKind::Knowledge => {
            player.resources.knowledge = player.resources.knowledge.saturating_add(amount)
        }
        ResourceKind::Qic => player.resources.qic = player.resources.qic.saturating_add(amount),
        ResourceKind::Power => apply_power_charge(&mut player.resources.power, amount),
    }
}

/// Faction board round income for built Mine/TradingStation/ResearchLab/
/// Academy(Science) structures (PlanetaryInstitute is handled separately by
/// `planetary_institute_income`, since its charge can interact with a
/// per-round bonus power token). Values are universal across factions
/// except where `factions.toml` explicitly overrides them (Firaks/Bescods/
/// Nevlas' ResearchLab, Itars' Academy(Science)). Academy(Qic) has no
/// passive income — it grants a repeatable special action instead, not yet
/// implemented.
fn apply_structure_income(player: &mut PlayerState, data: &crate::data::FactionData) {
    let mine_count = player
        .structures
        .iter()
        .filter(|s| s.kind == StructureType::Mine)
        .count();
    let mine_income = UNIVERSAL_MINE_BASE
        .saturating_add(cumulative_table_income(&UNIVERSAL_MINE_TABLE, mine_count));
    player.resources.ore = player.resources.ore.saturating_add(mine_income);

    let ts_count = player
        .structures
        .iter()
        .filter(|s| s.kind == StructureType::TradingStation)
        .count();
    let (ts_base, ts_table, ts_resource) = match &data.trading_station_income {
        Some(o) => (
            o.base,
            o.table.as_slice(),
            o.resource_kind().unwrap_or(ResourceKind::Credits),
        ),
        None => (
            UNIVERSAL_TRADING_STATION_BASE,
            UNIVERSAL_TRADING_STATION_TABLE.as_slice(),
            ResourceKind::Credits,
        ),
    };
    let ts_income = ts_base.saturating_add(cumulative_table_income(ts_table, ts_count));
    add_resource(player, ts_resource, ts_income);

    let rl_count = player
        .structures
        .iter()
        .filter(|s| s.kind == StructureType::ResearchLab)
        .count();
    let (rl_base, rl_table, rl_resource) = match &data.research_lab_income {
        Some(o) => (
            o.base,
            o.table.as_slice(),
            o.resource_kind().unwrap_or(ResourceKind::Knowledge),
        ),
        None => (
            UNIVERSAL_RESEARCH_LAB_BASE,
            UNIVERSAL_RESEARCH_LAB_TABLE.as_slice(),
            ResourceKind::Knowledge,
        ),
    };
    let rl_income = rl_base.saturating_add(cumulative_table_income(rl_table, rl_count));
    add_resource(player, rl_resource, rl_income);

    let academy_science_count = player
        .structures
        .iter()
        .filter(|s| matches!(s.kind, StructureType::Academy(AcademyType::Science)))
        .count() as u8;
    if academy_science_count > 0 {
        let per_academy = data
            .academy_science_income
            .unwrap_or(UNIVERSAL_ACADEMY_SCIENCE_KNOWLEDGE);
        player.resources.knowledge = player
            .resources
            .knowledge
            .saturating_add(per_academy.saturating_mul(academy_science_count));
    }
}

/// If `player` has built a PlanetaryInstitute, returns its
/// `(charge_amount, bonus_power_tokens)` round income — otherwise `None`.
/// Callers apply the charge directly when there's no bonus token to order
/// against it; when there is, the two must be queued as a
/// `PendingIncomeOrder` for the player to sequence via
/// `GameAction::ChooseIncomeOrder` (see `GamePhase::IncomeOrderPending`).
fn planetary_institute_income(
    player: &PlayerState,
    data: &crate::data::FactionData,
) -> Option<(u8, u8)> {
    let has_pi = player
        .structures
        .iter()
        .any(|s| s.kind == StructureType::PlanetaryInstitute);
    if !has_pi {
        return None;
    }
    let charge = data
        .planetary_institute_charge
        .unwrap_or(UNIVERSAL_PLANETARY_INSTITUTE_CHARGE);
    let bonus_tokens = data
        .planetary_institute_bonus_power_tokens
        .unwrap_or(UNIVERSAL_PI_BONUS_POWER_TOKENS);
    Some((charge, bonus_tokens))
}

/// "Charge `n` power" (rulebook p.14): move up to `n` tokens one bowl
/// forward — bowl1→bowl2 preferred, then bowl2→bowl3 — stopping early if
/// there's nothing left to charge.
fn apply_power_charge(power: &mut crate::game_state::PowerCycle, n: u8) {
    for _ in 0..n {
        if power.bowl1 > 0 {
            power.bowl1 -= 1;
            power.bowl2 = power.bowl2.saturating_add(1);
        } else if power.bowl2 > 0 {
            power.bowl2 -= 1;
            power.bowl3 = power.bowl3.saturating_add(1);
        } else {
            break;
        }
    }
}

// ── Round tile bonus ──────────────────────────────────────────────────────────

fn check_round_tile_bonus(
    state: &mut GameState,
    player_id: PlayerId,
    condition: &RoundCondition,
) -> Vec<GameEvent> {
    let round = state.round as usize;
    if round == 0 || round > state.round_tiles.len() {
        return vec![];
    }
    let tile = &state.round_tiles[round - 1];
    if &tile.condition != condition {
        return vec![];
    }
    let vp = tile.vp_per_unit as i32;
    let tile_id = tile.id;
    if let Some(player) = state.player_mut(player_id) {
        player.vp += vp;
    }
    vec![GameEvent::VpAwarded {
        player: player_id,
        amount: vp,
        reason: VpReason::RoundTile { tile_id },
    }]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn home_planet_type(state: &GameState, player_id: PlayerId) -> Option<PlanetType> {
    let faction_id = state.player(player_id)?.faction?;
    let factions = crate::data::load_factions();
    let data = factions
        .factions
        .into_iter()
        .find(|f| f.faction_id() == Some(faction_id))?;
    data.home_planet_type()
}

/// The registered `FactionAbility` for `player_id`, if they've chosen a faction.
fn ability_for(state: &GameState, player_id: PlayerId) -> Option<&'static dyn FactionAbility> {
    let faction = state.player(player_id)?.faction?;
    Some(faction_registry().get(faction))
}

/// Ore cost to colonize `target_type`, honoring a faction's terraforming
/// distance override (see `FactionAbility::terraforming_distance_override`).
fn terraform_ore_cost(
    state: &GameState,
    player_id: PlayerId,
    target_type: PlanetType,
    track_level: u8,
) -> u8 {
    let Some(home_type) = home_planet_type(state, player_id) else {
        return 0;
    };
    let distance = ability_for(state, player_id)
        .and_then(|a| a.terraforming_distance_override(home_type, target_type))
        .or_else(|| ring_distance(home_type, target_type));
    distance.map_or(0, |d| cost_for_distance(d, track_level))
}

/// QIC cost to colonize an already Gaia-formed planet, honoring a faction's
/// override (see `FactionAbility::gaia_colonization_qic_cost`).
fn gaia_qic_cost(state: &GameState, player_id: PlayerId) -> u8 {
    ability_for(state, player_id).map_or(1, |a| a.gaia_colonization_qic_cost())
}

/// Applies the state mutation implied by an ability-hook-produced event.
/// Handles only the event kinds `FactionAbility` hooks can currently
/// produce (`ResourceChanged`, `TechTileGained`) — this is not a general
/// event-sourcing replay mechanism.
fn apply_ability_event(state: &mut GameState, event: &GameEvent) {
    match event {
        GameEvent::ResourceChanged { player, delta } => {
            if let Some(p) = state.player_mut(*player) {
                p.resources.ore = (i16::from(p.resources.ore) + i16::from(delta.ore))
                    .clamp(0, i16::from(u8::MAX)) as u8;
                p.resources.credits = (i16::from(p.resources.credits) + i16::from(delta.credits))
                    .clamp(0, i16::from(u8::MAX)) as u8;
                p.resources.knowledge = (i16::from(p.resources.knowledge)
                    + i16::from(delta.knowledge))
                .clamp(0, i16::from(u8::MAX)) as u8;
                p.resources.qic = (i16::from(p.resources.qic) + i16::from(delta.qic))
                    .clamp(0, i16::from(u8::MAX)) as u8;
            }
        }
        GameEvent::TechTileGained { player, tile } => {
            if let Some(pos) = state
                .research_board
                .tech_tiles
                .iter()
                .position(|t| t == tile)
            {
                state.research_board.tech_tiles.remove(pos);
            }
            if let Some(p) = state.player_mut(*player) {
                p.tech_tiles.push(tile.clone());
                // The only current producer of `TechTileGained` is a one-shot
                // Planetary Institute ability (see `SpaceGiantsAbility`).
                p.pi_ability_used = true;
            }
        }
        _ => {}
    }
}

fn can_build_at(state: &GameState, player_id: PlayerId, coord: HexCoord) -> bool {
    validate_build(state, player_id, coord).is_ok()
}

fn upgrade_targets(kind: StructureType) -> Vec<StructureType> {
    use crate::game_state::AcademyType;
    use StructureType::*;
    match kind {
        Mine => vec![TradingStation],
        TradingStation => vec![ResearchLab, PlanetaryInstitute],
        ResearchLab => vec![Academy(AcademyType::Science), Academy(AcademyType::Qic)],
        _ => vec![],
    }
}

/// Returns (ore_cost, credits_cost) for an upgrade (rulebook p.13).
/// Mine→TradingStation costs 6 credits normally, reduced to 3 if there's an
/// opponent's structure within range 2 of the mine.
fn upgrade_cost(
    from: &StructureType,
    to: &StructureType,
    mine_has_opponent_neighbor: bool,
) -> (u8, u8) {
    use StructureType::*;
    match (from, to) {
        (Mine, TradingStation) => {
            let credits = if mine_has_opponent_neighbor { 3 } else { 6 };
            (2, credits)
        }
        (TradingStation, ResearchLab) => (3, 5),
        (TradingStation, PlanetaryInstitute) => (4, 6),
        (ResearchLab, Academy(_)) => (6, 6),
        _ => (0, 0),
    }
}

/// Whether any hex within range 2 of `coord` has a structure owned by
/// someone other than `player_id` (rulebook p.13, Mine upgrade discount).
fn has_opponent_structure_nearby(state: &GameState, player_id: PlayerId, coord: HexCoord) -> bool {
    state.board.hexes.values().any(|hex| {
        hex.coord.distance(&coord) <= 2 && hex.structures.iter().any(|s| s.owner != player_id)
    })
}

fn power_action_cost(id: u8) -> u8 {
    // Standard Gaia Project power action costs (board slots 1-7)
    match id {
        1 => 3,
        2 => 4,
        3 => 4,
        4 => 4,
        5 => 4,
        6 => 6,
        7 => 4,
        _ => u8::MAX,
    }
}

fn apply_power_effect(
    state: &mut GameState,
    player_id: PlayerId,
    id: u8,
    cost: u8,
) -> ResourceDelta {
    let mut delta = ResourceDelta::zero();
    if let Some(player) = state.player_mut(player_id) {
        player.resources.power.bowl3 = player.resources.power.bowl3.saturating_sub(cost);
        match id {
            1 => {
                player.resources.ore += 3;
                delta.ore = 3;
            }
            2 => {
                player.resources.ore += 2;
                delta.ore = 2;
            }
            3 => {
                player.resources.knowledge += 2;
                delta.knowledge = 2;
            }
            4 => {
                player.resources.credits += 7;
                delta.credits = 7;
            }
            5 => {
                player.resources.ore += 1;
                delta.ore = 1;
            }
            6 => {
                player.resources.qic += 2;
                delta.qic = 2;
            }
            7 => {
                player.resources.power.bowl2 = player.resources.power.bowl2.saturating_add(2);
            }
            _ => {}
        }
    }
    delta
}

fn qic_action_cost(kind: &QicActionKind) -> u8 {
    match kind {
        QicActionKind::GainOre => 1,
        QicActionKind::ResearchStep => 1,
        QicActionKind::BuildSatellite { .. } => 3,
        QicActionKind::ColoniseLostPlanet { .. } => 2,
    }
}

/// Identifies which shared QIC-action board slot `kind` occupies, ignoring
/// any payload (e.g. `BuildSatellite`'s target coord) — every instance of
/// the same kind is the same once-per-round slot (rulebook Appendix III).
fn qic_action_slot_id(kind: &QicActionKind) -> u8 {
    match kind {
        QicActionKind::GainOre => 1,
        QicActionKind::ResearchStep => 2,
        QicActionKind::BuildSatellite { .. } => 3,
        QicActionKind::ColoniseLostPlanet { .. } => 4,
    }
}
