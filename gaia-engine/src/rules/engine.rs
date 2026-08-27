use super::actions::{
    FederationTokenChoice, FreeActionKind, GameAction, SetupAction, TechTileChoice, TechTileRef,
};
use super::terraforming::{cost_for_distance, ring_distance};
use crate::bidding::{BiddingPolicy, BiddingStage, BiddingState};
use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::faction::registry::global as faction_registry;
use crate::game_state::{
    AcademyType, ArtifactId, Booster, BrainstoneLocation, FactionId, FederationToken,
    FinalScoringCondition, GaiaDecisionKind, GameEvent, GamePhase, GameState, HexCoord,
    PendingCharge, PendingGaiaDecision, PendingIncomeOrder, PlacedStructure, PlanetType, PlayerId,
    PlayerState, PowerCycle, ResearchTrack, ResourceDelta, ResourceKind, Resources, RoundCondition,
    SetupPhase, ShipId, SpaceshipId, StructureType, TechTile, VpReason,
};
use crate::map::MapEngine;
use crate::scoring::ScoringEngine;
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
const MAX_FREE_ACTION_COUNT: u8 = 30;

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

/// Player's basic Navigation range plus any action-specific `bonus_range` (Twilight's +3,
/// Gleens' +2, etc.) and Lost Fleet Tech tile 12's permanent "+1 basic range for the rest of the
/// game" — the single shared choke point for every range lookup in this file, so that tile's
/// bonus applies everywhere range is computed rather than needing 10 separate call sites touched.
fn player_nav_range(player: &PlayerState, bonus_range: u8) -> u8 {
    let nav_level = player.research_tracks.navigation as usize;
    let tech_tile_bonus = if player_active_tech_tile_ids(player).contains(&12) {
        1
    } else {
        0
    };
    NAV_RANGE[nav_level.min(NAV_RANGE.len() - 1)]
        .saturating_add(bonus_range)
        .saturating_add(tech_tile_bonus)
}

/// This player's Standard Tech tile ids whose effect is currently active — owned and not covered
/// by an Advanced Tech tile (rulebook p.15: "A covered tech tile has no effect"). Every ongoing
/// tech tile effect (range, income, event/pass-time triggers, power value, special actions)
/// should check this instead of `player.tech_tiles` directly; the one-time "immediately" grants
/// already fired at acquisition and duplicate-ownership/covering checks still use the raw list
/// since those care about what's owned, not what's currently active.
fn player_active_tech_tile_ids(player: &PlayerState) -> Vec<u8> {
    player
        .tech_tiles
        .iter()
        .map(|t| t.0)
        .filter(|id| !player.covered_tech_tiles.iter().any(|c| c.0 == *id))
        .collect()
}

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
        if let GameAction::TaklonsChargePower { gain_before } = action {
            return validate_taklons_charge_power(state, player_id, *gain_before);
        }
        if let GameAction::ChooseIncomeOrder { charge_first } = action {
            return validate_choose_income_order(state, player_id, *charge_first);
        }
        if let GameAction::TerransGaiaConversion { kind, count } = action {
            return validate_terrans_gaia_conversion(state, player_id, kind, *count);
        }
        if let GameAction::ItarsGaiaTechTile { tile, track } = action {
            return validate_itars_gaia_tech_tile(state, player_id, tile, *track);
        }
        if matches!(action, GameAction::FinishGaiaDecision) {
            return validate_finish_gaia_decision(state, player_id);
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
            GameAction::Upgrade {
                coord,
                to,
                tech_tile_choice,
            } => validate_upgrade(state, player_id, *coord, *to, tech_tile_choice.as_ref()),
            GameAction::ResearchAdvance { track } => validate_research(state, player_id, *track),
            GameAction::FormFederation {
                hexes,
                satellite_hexes,
                token,
                bonus_build_coord,
                bonus_tech_tile,
            } => validate_federation(
                state,
                player_id,
                hexes,
                satellite_hexes,
                *token,
                *bonus_build_coord,
                bonus_tech_tile.as_ref(),
            ),
            GameAction::PowerAction { id, coord } => {
                validate_power_action(state, player_id, *id, *coord)
            }
            GameAction::SpecialAction { id } => validate_special_action(state, player_id, *id),
            GameAction::AmbasSwapPlanetaryInstitute { mine_coord } => {
                validate_ambas_swap_planetary_institute(state, player_id, *mine_coord)
            }
            GameAction::FiraksDowngradeResearchLab { coord, track } => {
                validate_firaks_downgrade_research_lab(state, player_id, *coord, *track)
            }
            GameAction::BescodsLowestResearchAdvance { track } => {
                validate_bescods_lowest_research_advance(state, player_id, *track)
            }
            GameAction::IvitsPlaceSpaceStation { coord } => {
                validate_ivits_place_space_station(state, player_id, *coord)
            }
            GameAction::TinkeroidsUseTile { tile, coord } => {
                validate_tinkeroids_use_tile(state, player_id, *tile, *coord)
            }
            GameAction::MoweydsPlacePowerRing { coord } => {
                validate_moweyds_place_power_ring(state, player_id, *coord)
            }
            GameAction::TechTileSpecialAction { tile } => {
                validate_tech_tile_special_action(state, player_id, tile)
            }
            GameAction::GaiaFormation { coord } => {
                validate_gaia_formation(state, player_id, *coord)
            }
            GameAction::RoundBoosterImmediateGaiaFormation { coord } => {
                validate_round_booster_immediate_gaia_formation(state, player_id, *coord)
            }
            GameAction::RoundBoosterRangeBuild { coord } => {
                validate_round_booster_range_build(state, player_id, *coord)
            }
            GameAction::RoundBoosterRangeGaiaFormation { coord } => {
                validate_round_booster_range_gaia_formation(state, player_id, *coord)
            }
            GameAction::RoundBoosterRangeExploreSpaceship { ship } => {
                validate_round_booster_range_explore_spaceship(state, player_id, *ship)
            }
            GameAction::Pass { booster_id } => validate_pass(state, player_id, *booster_id),
            GameAction::AcademyQicAction => validate_academy_qic_action(state, player_id),
            GameAction::FreeAction { kind, count } => {
                validate_free_action(state, player_id, kind, *count)
            }
            GameAction::ExploreSpaceship { ship } => {
                validate_explore_spaceship(state, player_id, *ship)
            }
            GameAction::ExamineArtifact {
                artifact,
                copy_federation_token_kind,
                bonus_build_coord,
                bonus_tech_tile,
                bonus_research_track,
            } => validate_examine_artifact(
                state,
                player_id,
                *artifact,
                *copy_federation_token_kind,
                *bonus_build_coord,
                bonus_tech_tile.as_ref(),
                *bonus_research_track,
            ),
            GameAction::SpaceshipCreditTerraform { coord } => {
                validate_spaceship_credit_terraform(state, player_id, *coord)
            }
            GameAction::TwilightFreeResearchLab { coord } => {
                validate_twilight_free_research_lab(state, player_id, *coord)
            }
            GameAction::TwilightReplayFederationToken {
                token_kind,
                bonus_build_coord,
                bonus_tech_tile,
                bonus_research_track,
            } => validate_twilight_replay_federation_token(
                state,
                player_id,
                *token_kind,
                *bonus_build_coord,
                bonus_tech_tile.as_ref(),
                *bonus_research_track,
            ),
            GameAction::TwilightRangeBuild { coord } => {
                validate_twilight_range_build(state, player_id, *coord)
            }
            GameAction::TwilightRangeGaiaFormation { coord } => {
                validate_twilight_range_gaia_formation(state, player_id, *coord)
            }
            GameAction::TwilightRangeExploreSpaceship { ship } => {
                validate_twilight_range_explore_spaceship(state, player_id, *ship)
            }
            GameAction::RebellionFreeTradingStation { coord } => {
                validate_rebellion_free_trading_station(state, player_id, *coord)
            }
            GameAction::RebellionCreditsAndQic => {
                validate_rebellion_credits_and_qic(state, player_id)
            }
            GameAction::RebellionGainTechTile { tile, track } => {
                validate_rebellion_gain_tech_tile(state, player_id, tile, *track)
            }
            GameAction::TFMarsTechBonus => validate_tfmars_tech_bonus(state, player_id),
            GameAction::TFMarsGaiaFormation { coord } => {
                validate_tfmars_gaia_formation(state, player_id, *coord)
            }
            GameAction::EclipsePlanetTypeBonus => {
                validate_eclipse_planet_type_bonus(state, player_id)
            }
            GameAction::EclipseResearchBoost { track } => {
                validate_eclipse_research_boost(state, player_id, *track)
            }
            GameAction::EclipseAsteroidMine { coord } => {
                validate_eclipse_asteroid_mine(state, player_id, *coord)
            }
            GameAction::GleensBuildMine { coord } => {
                validate_gleens_build_mine(state, player_id, *coord)
            }
            GameAction::GleensGaiaFormation { coord } => {
                validate_gleens_gaia_formation(state, player_id, *coord)
            }
            GameAction::GleensExploreSpaceship { ship } => {
                validate_gleens_explore_spaceship(state, player_id, *ship)
            }
            GameAction::SpaceGiantsBuildMine { coord } => {
                validate_space_giants_build_mine(state, player_id, *coord)
            }
            GameAction::ChargePower { .. } => unreachable!("handled above"),
            GameAction::TaklonsChargePower { .. } => unreachable!("handled above"),
            GameAction::ChooseIncomeOrder { .. } => unreachable!("handled above"),
            GameAction::TerransGaiaConversion { .. }
            | GameAction::ItarsGaiaTechTile { .. }
            | GameAction::FinishGaiaDecision => unreachable!("handled above"),
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
            GameAction::Upgrade {
                coord,
                to,
                tech_tile_choice,
            } => apply_upgrade(state, player_id, coord, to, tech_tile_choice),
            GameAction::ResearchAdvance { track } => apply_research(state, player_id, track),
            GameAction::FormFederation {
                hexes,
                satellite_hexes,
                token,
                bonus_build_coord,
                bonus_tech_tile,
            } => apply_federation(
                state,
                player_id,
                hexes,
                satellite_hexes,
                token,
                bonus_build_coord,
                bonus_tech_tile,
            ),
            GameAction::PowerAction { id, coord } => {
                apply_power_action(state, player_id, id, coord)
            }
            GameAction::SpecialAction { id } => apply_special_action(state, player_id, id),
            GameAction::AmbasSwapPlanetaryInstitute { mine_coord } => {
                apply_ambas_swap_planetary_institute(state, player_id, mine_coord)
            }
            GameAction::FiraksDowngradeResearchLab { coord, track } => {
                apply_firaks_downgrade_research_lab(state, player_id, coord, track)
            }
            GameAction::BescodsLowestResearchAdvance { track } => {
                apply_bescods_lowest_research_advance(state, player_id, track)
            }
            GameAction::IvitsPlaceSpaceStation { coord } => {
                apply_ivits_place_space_station(state, player_id, coord)
            }
            GameAction::TinkeroidsUseTile { tile, coord } => {
                apply_tinkeroids_use_tile(state, player_id, tile, coord)
            }
            GameAction::MoweydsPlacePowerRing { coord } => {
                apply_moweyds_place_power_ring(state, player_id, coord)
            }
            GameAction::TechTileSpecialAction { tile } => {
                apply_tech_tile_special_action(state, player_id, &tile)
            }
            GameAction::GaiaFormation { coord } => apply_gaia_formation(state, player_id, coord),
            GameAction::RoundBoosterImmediateGaiaFormation { coord } => {
                apply_round_booster_immediate_gaia_formation(state, player_id, coord)
            }
            GameAction::RoundBoosterRangeBuild { coord } => {
                apply_round_booster_range_build(state, player_id, coord)
            }
            GameAction::RoundBoosterRangeGaiaFormation { coord } => {
                apply_round_booster_range_gaia_formation(state, player_id, coord)
            }
            GameAction::RoundBoosterRangeExploreSpaceship { ship } => {
                apply_round_booster_range_explore_spaceship(state, player_id, ship)
            }
            GameAction::Pass { booster_id } => apply_pass(state, player_id, booster_id),
            GameAction::AcademyQicAction => apply_academy_qic_action(state, player_id),
            GameAction::FreeAction { kind, count } => {
                apply_free_action(state, player_id, kind, count)
            }
            GameAction::ExploreSpaceship { ship } => {
                apply_explore_spaceship(state, player_id, ship)
            }
            GameAction::ExamineArtifact {
                artifact,
                copy_federation_token_kind,
                bonus_build_coord,
                bonus_tech_tile,
                bonus_research_track,
            } => apply_examine_artifact(
                state,
                player_id,
                artifact,
                copy_federation_token_kind,
                bonus_build_coord,
                bonus_tech_tile,
                bonus_research_track,
            ),
            GameAction::SpaceshipCreditTerraform { coord } => {
                apply_spaceship_credit_terraform(state, player_id, coord)
            }
            GameAction::TwilightFreeResearchLab { coord } => {
                apply_twilight_free_research_lab(state, player_id, coord)
            }
            GameAction::TwilightReplayFederationToken {
                token_kind,
                bonus_build_coord,
                bonus_tech_tile,
                bonus_research_track,
            } => apply_twilight_replay_federation_token(
                state,
                player_id,
                token_kind,
                bonus_build_coord,
                bonus_tech_tile,
                bonus_research_track,
            ),
            GameAction::TwilightRangeBuild { coord } => {
                apply_twilight_range_build(state, player_id, coord)
            }
            GameAction::TwilightRangeGaiaFormation { coord } => {
                apply_twilight_range_gaia_formation(state, player_id, coord)
            }
            GameAction::TwilightRangeExploreSpaceship { ship } => {
                apply_twilight_range_explore_spaceship(state, player_id, ship)
            }
            GameAction::RebellionFreeTradingStation { coord } => {
                apply_rebellion_free_trading_station(state, player_id, coord)
            }
            GameAction::RebellionCreditsAndQic => apply_rebellion_credits_and_qic(state, player_id),
            GameAction::RebellionGainTechTile { tile, track } => {
                apply_rebellion_gain_tech_tile(state, player_id, tile, track)
            }
            GameAction::TFMarsTechBonus => apply_tfmars_tech_bonus(state, player_id),
            GameAction::TFMarsGaiaFormation { coord } => {
                apply_tfmars_gaia_formation(state, player_id, coord)
            }
            GameAction::EclipsePlanetTypeBonus => apply_eclipse_planet_type_bonus(state, player_id),
            GameAction::EclipseResearchBoost { track } => {
                apply_eclipse_research_boost(state, player_id, track)
            }
            GameAction::EclipseAsteroidMine { coord } => {
                apply_eclipse_asteroid_mine(state, player_id, coord)
            }
            GameAction::GleensBuildMine { coord } => {
                apply_gleens_build_mine(state, player_id, coord)
            }
            GameAction::GleensGaiaFormation { coord } => {
                apply_gleens_gaia_formation(state, player_id, coord)
            }
            GameAction::GleensExploreSpaceship { ship } => {
                apply_gleens_explore_spaceship(state, player_id, ship)
            }
            GameAction::SpaceGiantsBuildMine { coord } => {
                apply_space_giants_build_mine(state, player_id, coord)
            }
            GameAction::ChargePower { accept } => apply_charge_power(state, player_id, accept),
            GameAction::TaklonsChargePower { gain_before } => {
                apply_taklons_charge_power(state, player_id, gain_before)
            }
            GameAction::ChooseIncomeOrder { charge_first } => {
                apply_choose_income_order(state, player_id, charge_first)
            }
            GameAction::TerransGaiaConversion { kind, count } => {
                apply_terrans_gaia_conversion(state, player_id, kind, count)
            }
            GameAction::ItarsGaiaTechTile { tile, track } => {
                apply_itars_gaia_tech_tile(state, player_id, tile, track)
            }
            GameAction::FinishGaiaDecision => apply_finish_gaia_decision(state, player_id),
        }
    }

    /// Returns the set of GameActions that are currently legal for `player_id`.
    /// Used by the AI sidecar and for client-side highlighting.
    pub fn get_valid_actions(state: &GameState, player_id: PlayerId) -> Vec<GameAction> {
        if let Ok(entry) = ensure_gaia_decision_phase(state, player_id) {
            let mut actions = vec![GameAction::FinishGaiaDecision];
            match entry.kind {
                GaiaDecisionKind::TerransPowerConversion => {
                    for kind in [
                        FreeActionKind::PowerToQic,
                        FreeActionKind::PowerToOre,
                        FreeActionKind::PowerToKnowledge,
                        FreeActionKind::PowerToCredit,
                    ] {
                        let candidate = GameAction::TerransGaiaConversion { kind, count: 1 };
                        if Self::validate_action(state, player_id, &candidate).is_ok() {
                            actions.push(candidate);
                        }
                    }
                }
                GaiaDecisionKind::ItarsTechTile => {
                    for tile in &state.research_board.tech_tiles {
                        for &track in &ResearchTrack::all() {
                            let candidate = GameAction::ItarsGaiaTechTile {
                                tile: tile.clone(),
                                track,
                            };
                            if Self::validate_action(state, player_id, &candidate).is_ok() {
                                actions.push(candidate);
                            }
                        }
                    }
                }
            }
            return actions;
        }
        if ensure_income_order_phase(state, player_id).is_ok() {
            return vec![
                GameAction::ChooseIncomeOrder {
                    charge_first: false,
                },
                GameAction::ChooseIncomeOrder { charge_first: true },
            ];
        }
        if ensure_charge_power_phase(state, player_id).is_ok() {
            let mut actions = vec![GameAction::ChargePower { accept: false }];
            if state.player(player_id).is_some_and(taklons_pi_is_active) {
                actions.push(GameAction::TaklonsChargePower { gain_before: true });
                actions.push(GameAction::TaklonsChargePower { gain_before: false });
            } else {
                actions.push(GameAction::ChargePower { accept: true });
            }
            return actions;
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
        let nav_range = player_nav_range(player, 0);
        let my_structure_hexes: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
        let reachable = MapEngine::reachable_hexes(&state.board, &my_structure_hexes, nav_range);
        for coord in &reachable {
            if can_build_at(state, player_id, *coord) {
                actions.push(GameAction::Build { coord: *coord });
            }
        }

        // Upgrade — enumerate own structures that can be upgraded
        for s in &player.structures {
            let targets = upgrade_targets(player, s.kind);
            for to in targets {
                if validate_upgrade(state, player_id, s.hex, to, None).is_ok() {
                    actions.push(GameAction::Upgrade {
                        coord: s.hex,
                        to,
                        tech_tile_choice: None,
                    });
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

        // Round-booster special actions. Enumerate the whole board rather than the base
        // navigation reachable set because both actions can still extend range with QIC and
        // booster 8 adds its printed +3 range before that extension.
        for &coord in state.board.hexes.keys() {
            if validate_round_booster_immediate_gaia_formation(state, player_id, coord).is_ok() {
                actions.push(GameAction::RoundBoosterImmediateGaiaFormation { coord });
            }
            if validate_round_booster_range_build(state, player_id, coord).is_ok() {
                actions.push(GameAction::RoundBoosterRangeBuild { coord });
            }
            if validate_round_booster_range_gaia_formation(state, player_id, coord).is_ok() {
                actions.push(GameAction::RoundBoosterRangeGaiaFormation { coord });
            }
        }
        for ship in SpaceshipId::all() {
            if validate_round_booster_range_explore_spaceship(state, player_id, ship).is_ok() {
                actions.push(GameAction::RoundBoosterRangeExploreSpaceship { ship });
            }
        }

        // Academy(Qic) action
        if validate_academy_qic_action(state, player_id).is_ok() {
            actions.push(GameAction::AcademyQicAction);
        }

        // Repeatable free actions (single-use representatives; callers can
        // batch them by increasing `count`).
        for kind in FreeActionKind::ALL {
            if validate_free_action(state, player_id, &kind, 1).is_ok() {
                actions.push(GameAction::FreeAction { kind, count: 1 });
            }
        }

        // Base-faction Planetary Institute / board special actions.
        if player.faction == Some(FactionId::Ambas) {
            for structure in &player.structures {
                if structure.kind != StructureType::Mine {
                    continue;
                }
                let candidate = GameAction::AmbasSwapPlanetaryInstitute {
                    mine_coord: structure.hex,
                };
                if Self::validate_action(state, player_id, &candidate).is_ok() {
                    actions.push(candidate);
                }
            }
        }
        if player.faction == Some(FactionId::Firaks) {
            for structure in &player.structures {
                if structure.kind != StructureType::ResearchLab {
                    continue;
                }
                for &track in &ResearchTrack::all() {
                    let candidate = GameAction::FiraksDowngradeResearchLab {
                        coord: structure.hex,
                        track,
                    };
                    if Self::validate_action(state, player_id, &candidate).is_ok() {
                        actions.push(candidate);
                    }
                }
            }
        }
        if player.faction == Some(FactionId::Bescods) {
            for &track in &ResearchTrack::all() {
                let candidate = GameAction::BescodsLowestResearchAdvance { track };
                if Self::validate_action(state, player_id, &candidate).is_ok() {
                    actions.push(candidate);
                }
            }
        }
        if player.faction == Some(FactionId::Ivits) {
            for &coord in state.board.hexes.keys() {
                let candidate = GameAction::IvitsPlaceSpaceStation { coord };
                if Self::validate_action(state, player_id, &candidate).is_ok() {
                    actions.push(candidate);
                }
            }
        }
        if player.faction == Some(FactionId::Tinkeroids) {
            for tile in 1..=6u8 {
                let coord_candidates: Vec<Option<HexCoord>> = if matches!(tile, 1 | 5) {
                    state.board.hexes.keys().map(|&c| Some(c)).collect()
                } else {
                    vec![None]
                };
                for coord in coord_candidates {
                    let candidate = GameAction::TinkeroidsUseTile { tile, coord };
                    if Self::validate_action(state, player_id, &candidate).is_ok() {
                        actions.push(candidate);
                    }
                }
            }
        }
        if player.faction == Some(FactionId::Moweyds) {
            for &coord in state.board.hexes.keys() {
                let candidate = GameAction::MoweydsPlacePowerRing { coord };
                if Self::validate_action(state, player_id, &candidate).is_ok() {
                    actions.push(candidate);
                }
            }
        }

        // Explore a Lost Fleet Spaceship
        for ship in SpaceshipId::all() {
            if validate_explore_spaceship(state, player_id, ship).is_ok() {
                actions.push(GameAction::ExploreSpaceship { ship });
            }
        }

        // Examine an Artifact: one candidate per artifact currently on the Twilight spaceship.
        // Artifact 10 ("Copy the effect of a Federation Token you own") is expanded into its
        // concrete legal choices too, mirroring `TwilightReplayFederationToken`'s enumeration.
        if let Some(twilight_board) = state
            .spaceship_boards
            .iter()
            .find(|b| b.id == SpaceshipId::Twilight)
        {
            let pool = twilight_board.artifact_pool.clone();
            for artifact in pool {
                if artifact_effect(artifact) != ArtifactEffect::CopyFederationEffect {
                    let candidate = GameAction::ExamineArtifact {
                        artifact,
                        copy_federation_token_kind: None,
                        bonus_build_coord: None,
                        bonus_tech_tile: None,
                        bonus_research_track: None,
                    };
                    if Self::validate_action(state, player_id, &candidate).is_ok() {
                        actions.push(candidate);
                    }
                    continue;
                }
                let mut replay_token_kinds = Vec::new();
                for token in &player.federation_tokens {
                    if replay_token_kinds.contains(&token.0) {
                        continue;
                    }
                    replay_token_kinds.push(token.0);
                    match federation_token_kind(token.0) {
                        FederationTokenKind::LostFleetFreeBuildUnlimitedRange
                        | FederationTokenKind::LostFleetFreeBuild3Steps => {
                            for &coord in state.board.hexes.keys() {
                                let candidate = GameAction::ExamineArtifact {
                                    artifact,
                                    copy_federation_token_kind: Some(token.0),
                                    bonus_build_coord: Some(coord),
                                    bonus_tech_tile: None,
                                    bonus_research_track: None,
                                };
                                if Self::validate_action(state, player_id, &candidate).is_ok() {
                                    actions.push(candidate);
                                }
                            }
                        }
                        FederationTokenKind::LostFleetTechTileOfChoice => {
                            for tile in &state.research_board.tech_tiles {
                                for &track in &ResearchTrack::all() {
                                    let candidate = GameAction::ExamineArtifact {
                                        artifact,
                                        copy_federation_token_kind: Some(token.0),
                                        bonus_build_coord: None,
                                        bonus_tech_tile: Some(tile.clone()),
                                        bonus_research_track: Some(track),
                                    };
                                    if Self::validate_action(state, player_id, &candidate).is_ok() {
                                        actions.push(candidate);
                                    }
                                }
                            }
                        }
                        _ => {
                            let candidate = GameAction::ExamineArtifact {
                                artifact,
                                copy_federation_token_kind: Some(token.0),
                                bonus_build_coord: None,
                                bonus_tech_tile: None,
                                bonus_research_track: None,
                            };
                            if Self::validate_action(state, player_id, &candidate).is_ok() {
                                actions.push(candidate);
                            }
                        }
                    }
                }
            }
        }

        // Spaceship Credit action: 1 free terraforming step, paid in credits
        for coord in &reachable {
            if validate_spaceship_credit_terraform(state, player_id, *coord).is_ok() {
                actions.push(GameAction::SpaceshipCreditTerraform { coord: *coord });
            }
        }

        // Twilight's free TradingStation -> ResearchLab action
        for s in &player.structures {
            if s.kind == StructureType::TradingStation
                && validate_twilight_free_research_lab(state, player_id, s.hex).is_ok()
            {
                actions.push(GameAction::TwilightFreeResearchLab { coord: s.hex });
            }
        }

        // Twilight's Federation-token replay. Targeted Lost Fleet tokens are expanded into
        // their concrete legal choices so AI callers never receive an incomplete action.
        let mut replay_token_kinds = Vec::new();
        for token in &player.federation_tokens {
            if replay_token_kinds.contains(&token.0) {
                continue;
            }
            replay_token_kinds.push(token.0);
            match federation_token_kind(token.0) {
                FederationTokenKind::LostFleetFreeBuildUnlimitedRange
                | FederationTokenKind::LostFleetFreeBuild3Steps => {
                    for &coord in state.board.hexes.keys() {
                        let candidate = GameAction::TwilightReplayFederationToken {
                            token_kind: token.0,
                            bonus_build_coord: Some(coord),
                            bonus_tech_tile: None,
                            bonus_research_track: None,
                        };
                        if Self::validate_action(state, player_id, &candidate).is_ok() {
                            actions.push(candidate);
                        }
                    }
                }
                FederationTokenKind::LostFleetTechTileOfChoice => {
                    for tile in &state.research_board.tech_tiles {
                        for &track in &ResearchTrack::all() {
                            let candidate = GameAction::TwilightReplayFederationToken {
                                token_kind: token.0,
                                bonus_build_coord: None,
                                bonus_tech_tile: Some(tile.clone()),
                                bonus_research_track: Some(track),
                            };
                            if Self::validate_action(state, player_id, &candidate).is_ok() {
                                actions.push(candidate);
                            }
                        }
                    }
                }
                _ => {
                    let candidate = GameAction::TwilightReplayFederationToken {
                        token_kind: token.0,
                        bonus_build_coord: None,
                        bonus_tech_tile: None,
                        bonus_research_track: None,
                    };
                    if Self::validate_action(state, player_id, &candidate).is_ok() {
                        actions.push(candidate);
                    }
                }
            }
        }

        // Twilight's +3-range space supports exactly one of Build/Gaia/Explore, and all three
        // variants resolve to the same shared action-space id.
        for &coord in state.board.hexes.keys() {
            if validate_twilight_range_build(state, player_id, coord).is_ok() {
                actions.push(GameAction::TwilightRangeBuild { coord });
            }
            if validate_twilight_range_gaia_formation(state, player_id, coord).is_ok() {
                actions.push(GameAction::TwilightRangeGaiaFormation { coord });
            }
        }
        for ship in SpaceshipId::all() {
            if validate_twilight_range_explore_spaceship(state, player_id, ship).is_ok() {
                actions.push(GameAction::TwilightRangeExploreSpaceship { ship });
            }
        }

        // Rebellion's free Mine -> TradingStation action
        for s in &player.structures {
            if s.kind == StructureType::Mine
                && validate_rebellion_free_trading_station(state, player_id, s.hex).is_ok()
            {
                actions.push(GameAction::RebellionFreeTradingStation { coord: s.hex });
            }
        }

        // Rebellion's knowledge -> credits+QIC conversion
        if validate_rebellion_credits_and_qic(state, player_id).is_ok() {
            actions.push(GameAction::RebellionCreditsAndQic);
        }

        // Rebellion's Standard Tech tile action includes the research track advanced by the
        // acquisition, matching the explicit selection used by the client.
        for tile in &state.research_board.tech_tiles {
            for &track in &ResearchTrack::all() {
                if validate_rebellion_gain_tech_tile(state, player_id, tile, track).is_ok() {
                    actions.push(GameAction::RebellionGainTechTile {
                        tile: tile.clone(),
                        track,
                    });
                }
            }
        }

        // T F Mars' QIC -> VP-per-tech-tile conversion
        if validate_tfmars_tech_bonus(state, player_id).is_ok() {
            actions.push(GameAction::TFMarsTechBonus);
        }

        // T F Mars' flat-power immediate Gaia Formation
        for coord in &reachable {
            if validate_tfmars_gaia_formation(state, player_id, *coord).is_ok() {
                actions.push(GameAction::TFMarsGaiaFormation { coord: *coord });
            }
        }

        // Eclipse's QIC -> VP-per-planet-type conversion
        if validate_eclipse_planet_type_bonus(state, player_id).is_ok() {
            actions.push(GameAction::EclipsePlanetTypeBonus);
        }

        // Eclipse's power+knowledge -> research track advance
        for &track in &ResearchTrack::all() {
            if validate_eclipse_research_boost(state, player_id, track).is_ok() {
                actions.push(GameAction::EclipseResearchBoost { track });
            }
        }

        // Eclipse's credit-paid Asteroid mine
        for coord in &reachable {
            if validate_eclipse_asteroid_mine(state, player_id, *coord).is_ok() {
                actions.push(GameAction::EclipseAsteroidMine { coord: *coord });
            }
        }

        // Gleens' Exploration Board special action: like Twilight's +3-range space, this
        // supports exactly one of Build/Gaia/Explore (range +2), all sharing the same
        // once-per-round flag — iterate every board hex since the range bonus can reach beyond
        // `reachable`.
        for &coord in state.board.hexes.keys() {
            if validate_gleens_build_mine(state, player_id, coord).is_ok() {
                actions.push(GameAction::GleensBuildMine { coord });
            }
            if validate_gleens_gaia_formation(state, player_id, coord).is_ok() {
                actions.push(GameAction::GleensGaiaFormation { coord });
            }
        }
        for ship in SpaceshipId::all() {
            if validate_gleens_explore_spaceship(state, player_id, ship).is_ok() {
                actions.push(GameAction::GleensExploreSpaceship { ship });
            }
        }

        // Space Giants' Exploration Board special action: Build a Mine with 2 free terraforming
        // steps, normal range.
        for coord in &reachable {
            if validate_space_giants_build_mine(state, player_id, *coord).is_ok() {
                actions.push(GameAction::SpaceGiantsBuildMine { coord: *coord });
            }
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

    /// Applies the first round's income after setup has assigned factions and
    /// boosters, then opens the first action phase. Setup unit tests can keep
    /// inspecting the pre-income `Setup::Complete` snapshot while the server
    /// uses this single transition instead of skipping round-one income.
    pub fn start_first_round(state: &mut GameState) -> Result<Vec<GameEvent>, RuleError> {
        if state.phase != GamePhase::Setup(SetupPhase::Complete) || state.round != 1 {
            return Err(RuleError::WrongPhase);
        }

        let pending_income_orders = apply_income_phase(state);
        let mut events = vec![GameEvent::RoundStarted { round: 1 }];
        if pending_income_orders.is_empty() {
            events.extend(continue_round_transition_after_income(state, 0));
        } else {
            state.phase = GamePhase::IncomeOrderPending {
                queue: pending_income_orders,
                round: 0,
            };
        }
        Ok(events)
    }

    // ── Round transition ──────────────────────────────────────────────────

    /// Advances from `RoundScoring{round}` through the Income phase (rulebook
    /// p.10) and Gaia phase (rulebook p.11) into the next round's
    /// `ActionPhase`. Round-tile VP is already applied incrementally by
    /// `check_round_tile_bonus` as qualifying actions happen during the
    /// round, so this does not re-derive it from the event log (which
    /// nothing currently populates).
    pub fn advance_to_next_round(state: &mut GameState) -> Result<Vec<GameEvent>, RuleError> {
        let GamePhase::RoundScoring { round } = state.phase else {
            return Err(RuleError::WrongPhase);
        };
        let pending_income_orders = apply_income_phase(state);
        if pending_income_orders.is_empty() {
            Ok(continue_round_transition_after_income(state, round))
        } else {
            state.phase = GamePhase::IncomeOrderPending {
                queue: pending_income_orders,
                round,
            };
            Ok(Vec::new())
        }
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

/// Reachability + automatic QIC-for-range cost, shared by `Build`, `GaiaFormation`, and
/// `ExploreSpaceship` (rulebook p.11, "Build a Mine": "you can spend any number of Q.I.C. to
/// increase your range by two spaces for each Q.I.C. spent" — confirmed by the worked example,
/// Navigation level 2 / basic range 2 / spend 1 QIC -> range 4. The Lost Fleet expansion
/// explicitly reuses this exact rule for "Start a Gaia Project" and "Explore a Lost Fleet
/// Spaceship": `docs/GP_Exp_Rule_EN_V1_Web.pdf`, "you may still spend Q.I.C.s to increase your
/// range... just like when you increase the range of the 'Build a Mine' or 'Start a Gaia
/// Project' actions"). Rather than let the player pick an arbitrary QIC amount, this computes
/// the minimum needed to reach `target` and returns that — a rational player never spends more
/// than the minimum, and every other derived cost in this engine is similarly auto-computed
/// rather than exposed as a player choice.
fn range_and_qic_cost(
    state: &GameState,
    player_id: PlayerId,
    starts: &[HexCoord],
    nav_range: u8,
    nav_level: u8,
    target: HexCoord,
) -> Result<u8, RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let max_range = nav_range.saturating_add(player.resources.qic.saturating_mul(2));
    let distance = MapEngine::shortest_distance(&state.board, starts, target, max_range).ok_or(
        RuleError::OutOfRange {
            hex: target,
            range: nav_range,
            nav_level,
        },
    )?;
    Ok(distance.saturating_sub(nav_range).div_ceil(2))
}

fn validate_build(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_build_impl(state, player_id, coord, 0, 0, false, 0)
}

/// Shared by the normal `Build` action, the power-action board's two
/// "build a mine with N free terraforming steps" slots (rulebook Appendix
/// III, ids 2 and 6), and Federation-token-granted free builds:
/// `free_terraform_steps` reduces the terraforming distance charged in ore
/// before `cost_for_distance` runs, `power_cost` (paid from bowl3, like any
/// other power action) is checked alongside the mine's usual ore/credits
/// cost, and `unlimited_range` (Lost Fleet Federation token, expansion
/// Appendix VI: "receive a Build a Mine action of limitless range") skips
/// reachability/QIC-for-range entirely instead of computing it.
fn validate_build_impl(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    free_terraform_steps: u8,
    power_cost: u8,
    unlimited_range: bool,
    bonus_range: u8,
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

    // A completed Gaia Project keeps its owner as a reservation marker between the Gaia phase
    // and that player's later Build action. That owner may build the first Mine there; every
    // other owned planet remains occupied. Opponent cohabitation still waits for Lantids' rule.
    if let Some(owner) = planet.owner {
        let own_completed_gaia_project = owner == player_id
            && planet.is_gaia_formed
            && !player
                .structures
                .iter()
                .any(|structure| structure.hex == coord)
            && hex.structures.is_empty();
        if !own_completed_gaia_project {
            return Err(RuleError::TargetOccupied(coord));
        }
    }

    // Must not be Transdim unless already Gaia-formed
    if planet.planet_type == PlanetType::Transdim && !planet.is_gaia_formed {
        return Err(RuleError::InvalidTarget(coord));
    }

    // Reachability — range determined by Navigation research track, extendable with QIC.
    // `unlimited_range` (Lost Fleet Federation token) skips this entirely.
    let qic_for_range = if unlimited_range {
        0
    } else {
        let nav_level = player.research_tracks.navigation as usize;
        let nav_range = player_nav_range(player, bonus_range);
        let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
        range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)?
    };

    // Gaia planet: costs 1 QIC instead of terraforming steps.
    // Asteroid/ProtoPlanet (Lost Fleet expansion's QIC-board-overlay rule): Asteroid needs an
    // available Gaiaformer and pays no ore/credit cost at all; ProtoPlanet needs a flat 3
    // terraforming steps regardless of home planet type (bypasses the normal ring-distance
    // lookup, which is meaningless for a planet type no faction currently starts adjacent to).
    let target_type = if planet.is_gaia_formed {
        PlanetType::Gaia
    } else {
        planet.planet_type
    };

    if target_type == PlanetType::Asteroid {
        if player.gaiaformers_available() == 0 {
            return Err(RuleError::NoGaiaformerAvailable);
        }
        if player.resources.qic < qic_for_range {
            return Err(RuleError::InsufficientResources(
                crate::game_state::ResourceKind::Qic,
            ));
        }
        if power_cost > 0 && spendable_power_value(&player.resources.power) < power_cost {
            return Err(RuleError::InsufficientResources(
                crate::game_state::ResourceKind::Power,
            ));
        }
        return Ok(());
    }

    let (terraform_ore, qic_cost) =
        if planet.is_gaia_formed && player.faction == Some(FactionId::Gleens) {
            // Gleens always pay 1 ore rather than QIC to colonize Gaia planets.
            (1u8, 0u8)
        } else if planet.is_gaia_formed {
            (0u8, gaia_qic_cost(state, player_id)) // rulebook p.11; some factions override
        } else if target_type == PlanetType::ProtoPlanet {
            let steps = 3u8.saturating_sub(free_terraform_steps);
            (
                cost_for_distance(steps, player.research_tracks.terraforming),
                0,
            )
        } else {
            let ore = terraform_ore_cost_with_free_steps(
                state,
                player_id,
                target_type,
                player.research_tracks.terraforming,
                free_terraform_steps,
            );
            (ore, 0)
        };
    let qic_cost = qic_cost.saturating_add(qic_for_range);

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
    if power_cost > 0 && spendable_power_value(&player.resources.power) < power_cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }

    Ok(())
}

fn apply_build(state: &mut GameState, player_id: PlayerId, coord: HexCoord) -> Vec<GameEvent> {
    apply_build_impl(state, player_id, coord, 0, 0, false, 0)
}

/// Shared by the normal `Build` action and the power-action board's two
/// "build a mine with N free terraforming steps" slots — see
/// `validate_build_impl`.
fn apply_build_impl(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
    free_terraform_steps: u8,
    power_cost: u8,
    unlimited_range: bool,
    bonus_range: u8,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let hex = match state.board.hexes.get(&coord) {
        Some(h) => h.clone(),
        None => return events,
    };
    let qic_for_range = if unlimited_range {
        0
    } else {
        state
            .player(player_id)
            .map(|player| {
                let nav_level = player.research_tracks.navigation as usize;
                let nav_range = player_nav_range(player, bonus_range);
                let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
                range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)
                    .unwrap_or(0)
            })
            .unwrap_or(0)
    };
    let is_gaia_formed = hex.planet.as_ref().is_some_and(|p| p.is_gaia_formed);
    let planet_type_raw = hex.planet.as_ref().map(|p| p.planet_type);
    let scoring_planet_type = if is_gaia_formed {
        Some(PlanetType::Gaia)
    } else {
        planet_type_raw
    };
    let is_asteroid = !is_gaia_formed && planet_type_raw == Some(PlanetType::Asteroid);
    let is_protoplanet = !is_gaia_formed && planet_type_raw == Some(PlanetType::ProtoPlanet);
    let terraforming_steps = if is_gaia_formed || is_asteroid {
        0
    } else if is_protoplanet {
        3u8.saturating_sub(free_terraform_steps)
    } else {
        planet_type_raw.map_or(0, |target_type| {
            terraforming_distance(state, player_id, target_type).unwrap_or(0)
        })
    };
    let is_new_planet_type = scoring_planet_type
        .is_some_and(|target_type| !has_colonized_planet_type(state, player_id, target_type));
    let is_first_mine_in_sector = MapEngine::sector_id_at(&state.board, coord)
        .is_some_and(|sector_id| !has_colonized_sector(state, player_id, sector_id));

    let is_gleens = state
        .player(player_id)
        .is_some_and(|player| player.faction == Some(FactionId::Gleens));
    let (terraform_ore, qic_cost) = if is_gaia_formed && is_gleens {
        (1u8, 0u8)
    } else if is_gaia_formed {
        (0u8, gaia_qic_cost(state, player_id))
    } else if is_asteroid {
        (0u8, 0u8)
    } else if is_protoplanet {
        let track_level = state
            .player(player_id)
            .map_or(0, |p| p.research_tracks.terraforming);
        (cost_for_distance(terraforming_steps, track_level), 0u8)
    } else if let Some(target_type) = planet_type_raw {
        let track_level = state
            .player(player_id)
            .map_or(0, |p| p.research_tracks.terraforming);
        (
            terraform_ore_cost_with_free_steps(
                state,
                player_id,
                target_type,
                track_level,
                free_terraform_steps,
            ),
            0,
        )
    } else {
        (0u8, 0u8)
    };
    let qic_cost = qic_cost.saturating_add(qic_for_range);
    // Asteroid (Lost Fleet): "you do not need to pay the build costs (1 ore and 2 credits) for
    // the mine" — waives the base mine cost entirely, not just terraforming.
    let (ore_cost, credits_cost) = if is_asteroid {
        (0u8, 0u8)
    } else {
        (MINE_ORE_COST + terraform_ore, MINE_CREDITS_COST)
    };

    if let Some(player) = state.player_mut(player_id) {
        player.resources.ore = player.resources.ore.saturating_sub(ore_cost);
        player.resources.credits = player.resources.credits.saturating_sub(credits_cost);
        player.resources.qic = player.resources.qic.saturating_sub(qic_cost);
        spend_power(&mut player.resources.power, power_cost);
        let delta = ResourceDelta {
            ore: -(ore_cost as i8),
            credits: -(credits_cost as i8),
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

        if is_asteroid {
            player.resources.spent_gaia_formers =
                player.resources.spent_gaia_formers.saturating_add(1);
        }
        if is_protoplanet {
            // Rulebook: 6VP for building a mine on a Protoplanet, except 0VP if it was your own
            // starting planet — that exception can't trigger yet since no currently-implemented
            // faction starts on a Protoplanet.
            player.vp = player.vp.saturating_add(6);
        }
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

    // Rulebook p.14: "When colonizing planets directly adjacent to one of your federations,
    // these new planets enlarge the existing federation without any advantage for you." Silent —
    // no new token, no VP, no connectivity/power-threshold check (those only gate the explicit
    // `FormFederation` action) — just extends `federated_hexes` so the hex counts toward that
    // federation's power from now on and can't later be claimed by a separate `FormFederation`.
    if let Some(player) = state.player(player_id) {
        let touches_existing_federation = coord
            .neighbors()
            .iter()
            .any(|n| player.federated_hexes.contains(n));
        if touches_existing_federation {
            if let Some(player) = state.player_mut(player_id) {
                player.federated_hexes.push(coord);
            }
        }
    }

    events.push(GameEvent::StructureBuilt {
        player: player_id,
        hex: coord,
        kind: StructureType::Mine,
    });
    if is_asteroid {
        events.push(GameEvent::AsteroidColonized {
            player: player_id,
            hex: coord,
        });
    }
    if is_protoplanet {
        events.push(GameEvent::ProtoPlanetColonized {
            player: player_id,
            hex: coord,
        });
    }
    if is_gaia_formed && is_gleens {
        if let Some(player) = state.player_mut(player_id) {
            player.vp = player.vp.saturating_add(2);
        }
        events.push(GameEvent::VpAwarded {
            player: player_id,
            amount: 2,
            reason: VpReason::FactionSpecial,
        });
    }

    // Geodens PI: the first Mine built on each planet type after the PI is
    // constructed grants 3 knowledge. Pre-PI types are seeded during the PI
    // upgrade, so this check is naturally non-retroactive.
    let grants_geodens_knowledge = scoring_planet_type.is_some_and(|planet_type| {
        state.player(player_id).is_some_and(|player| {
            player.faction == Some(FactionId::Geodens)
                && player_has_planetary_institute(player)
                && !player.geodens_rewarded_planet_types.contains(&planet_type)
        })
    });
    if let Some(planet_type) = scoring_planet_type.filter(|_| grants_geodens_knowledge) {
        if let Some(player) = state.player_mut(player_id) {
            player.geodens_rewarded_planet_types.push(planet_type);
            player.resources.knowledge = player.resources.knowledge.saturating_add(3);
        }
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta: ResourceDelta {
                knowledge: 3,
                ..ResourceDelta::zero()
            },
        });
    }

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
        1,
    ));
    events.extend(check_tech_tile_event_bonus(
        state,
        player_id,
        &RoundCondition::BuildMine,
        1,
    ));
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::TerraformingStep,
        terraforming_steps,
    ));
    events.extend(check_tech_tile_event_bonus(
        state,
        player_id,
        &RoundCondition::TerraformingStep,
        terraforming_steps,
    ));
    if scoring_planet_type == Some(PlanetType::Gaia) {
        events.extend(check_round_tile_bonus(
            state,
            player_id,
            &RoundCondition::BuildMineOnGaia,
            1,
        ));
        events.extend(check_tech_tile_event_bonus(
            state,
            player_id,
            &RoundCondition::BuildMineOnGaia,
            1,
        ));
    }
    if is_new_planet_type {
        events.extend(check_round_tile_bonus(
            state,
            player_id,
            &RoundCondition::BuildMineOnNewPlanetType,
            1,
        ));
    }
    if is_first_mine_in_sector {
        events.extend(check_round_tile_bonus(
            state,
            player_id,
            &RoundCondition::BuildMineInNewSector,
            1,
        ));
    }

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
    tech_tile_choice: Option<&TechTileChoice>,
) -> Result<(), RuleError> {
    validate_upgrade_impl(state, player_id, coord, to, false, tech_tile_choice)
}

/// Shared by the normal `Upgrade` action and Twilight's free TradingStation->ResearchLab
/// Appendix II action space — see `validate_upgrade`/`TwilightFreeResearchLabUpgrade`. `free`
/// skips the ore/credit cost check entirely (that action is "at no additional cost"). The
/// Twilight/Rebellion free-upgrade callers always pass `tech_tile_choice: None` — this pass
/// only wires the tech-tile-choice reward into the normal `Upgrade` action, not those two rarer
/// Lost Fleet variants.
fn validate_upgrade_impl(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    to: StructureType,
    free: bool,
    tech_tile_choice: Option<&TechTileChoice>,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let existing = player
        .structures
        .iter()
        .find(|s| s.hex == coord)
        .ok_or(RuleError::InvalidTarget(coord))?;

    // Validate upgrade path
    let is_bescods = player.faction == Some(FactionId::Bescods);
    let valid_upgrade = match (existing.kind, to) {
        (StructureType::Mine, StructureType::TradingStation) => true,
        (StructureType::TradingStation, StructureType::ResearchLab) => true,
        (StructureType::TradingStation, StructureType::PlanetaryInstitute) => {
            !is_bescods
                && !player
                    .structures
                    .iter()
                    .any(|s| s.kind == StructureType::PlanetaryInstitute)
        }
        (StructureType::ResearchLab, StructureType::Academy(_)) => !is_bescods,
        (StructureType::TradingStation, StructureType::Academy(_)) => is_bescods,
        (StructureType::ResearchLab, StructureType::PlanetaryInstitute) => {
            is_bescods
                && !player
                    .structures
                    .iter()
                    .any(|s| s.kind == StructureType::PlanetaryInstitute)
        }
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

    if let Some(choice) = tech_tile_choice {
        validate_tech_tile_choice(state, player_id, choice)?;
    }

    if free {
        return Ok(());
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
    tech_tile_choice: Option<TechTileChoice>,
) -> Vec<GameEvent> {
    apply_upgrade_impl(state, player_id, coord, to, false, tech_tile_choice)
}

fn apply_upgrade_impl(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
    to: StructureType,
    free: bool,
    tech_tile_choice: Option<TechTileChoice>,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let geodens_seeded_planet_types = if to == StructureType::PlanetaryInstitute
        && state
            .player(player_id)
            .is_some_and(|player| player.faction == Some(FactionId::Geodens))
    {
        Some(colonized_planet_types(state, player_id))
    } else {
        None
    };

    let from = match state
        .player(player_id)
        .and_then(|p| p.structures.iter().find(|s| s.hex == coord))
        .map(|s| s.kind)
    {
        Some(k) => k,
        None => return events,
    };

    let (ore_cost, credits_cost) = if free {
        (0, 0)
    } else {
        upgrade_cost(
            &from,
            &to,
            has_opponent_structure_nearby(state, player_id, coord),
        )
    };
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
        if let Some(types) = geodens_seeded_planet_types {
            player.geodens_rewarded_planet_types = types;
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

    // Gleens faction appendix: constructing their Planetary Institute immediately
    // grants their unique Federation token. It is not taken from the shared supply,
    // but otherwise behaves exactly like forming a Federation: its printed reward is
    // applied and round scoring for forming a Federation triggers.
    if to == StructureType::PlanetaryInstitute
        && state
            .player(player_id)
            .is_some_and(|player| player.faction == Some(FactionId::Gleens))
    {
        const GLEENS_FEDERATION_TOKEN_KIND: u8 = 16;
        let token = FederationToken(GLEENS_FEDERATION_TOKEN_KIND);
        if let Some(player) = state.player_mut(player_id) {
            player.federation_tokens.push(token.clone());
        }
        apply_federation_token_direct_reward(state, player_id, GLEENS_FEDERATION_TOKEN_KIND);
        events.push(GameEvent::FederationFormed {
            player: player_id,
            hexes: vec![coord],
            token,
        });
        events.extend(check_round_tile_bonus(
            state,
            player_id,
            &RoundCondition::FormFederation,
            1,
        ));
    }

    let round_condition = match to {
        StructureType::TradingStation => Some(RoundCondition::UpgradeTradingStation),
        StructureType::PlanetaryInstitute | StructureType::Academy(_) => {
            Some(RoundCondition::UpgradeLargeBuilding)
        }
        StructureType::ResearchLab => Some(RoundCondition::UpgradeResearchLab),
        _ => None,
    };
    if let Some(condition) = round_condition {
        events.extend(check_round_tile_bonus(state, player_id, &condition, 1));
        events.extend(check_tech_tile_event_bonus(state, player_id, &condition, 1));
    }

    if let Some(choice) = tech_tile_choice {
        events.extend(apply_tech_tile_choice(state, player_id, &choice));
    }

    if !maybe_enter_charge_power_phase(state, player_id, coord) {
        advance_turn(state);
    }
    events
}

// ── Tech tiles ───────────────────────────────────────────────────────────────
//
// Base rulebook p.15, "Research Progress": "Tech tiles grant you various benefits, such as
// immediate resources or income... Whenever you gain a tech tile, you may advance in a research
// area... You can take any standard tech tile, except one you already own. No faction can own
// more than one of the same tech tile, even if it is covered by an advanced tech tile... Instead
// of taking a standard tech tile, you can take an advanced tech tile [if] your player token
// [is] on level 4 or 5 of the research area [it sits under]. When you take an advanced tech
// tile, you may advance in any research area." Standard tile ids 2-10 are the base game's 9
// tiles; ids 11-14 are the Lost Fleet expansion's Appendix V "New Tech Tiles" (added to the
// standard pool — the expansion's own components list, "12 Standard Tech tiles," is the best
// available read of where these 4 belong, since Appendix V doesn't say). Advanced tile ids are
// 1-22, minus 18 (that scan is missing — see `gaia-frontend/src/assets/tech_tiles/advanced/`).
// Effects confirmed against those scans plus, for the 4 Lost Fleet ones, the expansion rulebook
// text directly (`docs/GP_Exp_Rule_EN_V1_Web.pdf` p.15, Appendix V).

/// Lost Fleet Appendix V tile: "Immediately and only once receive a 'Build a Mine' action with
/// up to 2 free terraforming steps and without paying the cost for that mine." Needs a target
/// hex, so it's handled specially rather than through `apply_tech_tile_immediate_reward`.
const TECH_TILE_LOST_FLEET_FREE_BUILD_MINE: u8 = 11;

fn research_track_index(track: ResearchTrack) -> usize {
    match track {
        ResearchTrack::Terraforming => 0,
        ResearchTrack::Navigation => 1,
        ResearchTrack::ArtificialIntelligence => 2,
        ResearchTrack::GaiaProject => 3,
        ResearchTrack::Economy => 4,
        ResearchTrack::Science => 5,
    }
}

fn validate_tech_tile_choice(
    state: &GameState,
    player_id: PlayerId,
    choice: &TechTileChoice,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    match choice {
        TechTileChoice::Standard {
            tile,
            advance_track,
            bonus_build_coord,
        } => {
            if !state.research_board.tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile isn't available".to_string(),
                ));
            }
            if player.tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "you already own that Tech tile".to_string(),
                ));
            }
            if tile.0 == TECH_TILE_LOST_FLEET_FREE_BUILD_MINE {
                let coord = bonus_build_coord.ok_or_else(|| {
                    RuleError::ActionNotAllowed("this Tech tile requires a target hex".to_string())
                })?;
                validate_build_impl(state, player_id, coord, 2, 0, false, 0)?;
            } else if bonus_build_coord.is_some() {
                return Err(RuleError::ActionNotAllowed(
                    "this Tech tile doesn't take a target hex".to_string(),
                ));
            }
            if let Some(track) = advance_track {
                validate_free_research_advance(state, player_id, *track)?;
            }
        }
        TechTileChoice::Advanced {
            track,
            covered_tile,
            advance_track,
        } => {
            if state.research_board.advanced_tech_tiles[research_track_index(*track)].is_none() {
                return Err(RuleError::ActionNotAllowed(
                    "no Advanced Tech tile remains for that research track".to_string(),
                ));
            }
            if player.research_tracks.get(*track) < 4 {
                return Err(RuleError::ActionNotAllowed(
                    "requires level 4 or 5 on that research track".to_string(),
                ));
            }
            validate_has_a_green_federation_token(player)?;
            if !player.tech_tiles.contains(covered_tile) {
                return Err(RuleError::ActionNotAllowed(
                    "must cover one of your own Standard Tech tiles".to_string(),
                ));
            }
            if player.covered_tech_tiles.contains(covered_tile) {
                return Err(RuleError::ActionNotAllowed(
                    "that Standard Tech tile is already covered".to_string(),
                ));
            }
            if let Some(t) = advance_track {
                validate_free_research_advance(state, player_id, *t)?;
            }
        }
    }
    Ok(())
}

fn apply_tech_tile_choice(
    state: &mut GameState,
    player_id: PlayerId,
    choice: &TechTileChoice,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    match choice {
        TechTileChoice::Standard {
            tile,
            advance_track,
            bonus_build_coord,
        } => {
            if transfer_tech_tile_to_player(state, player_id, tile) {
                events.push(GameEvent::TechTileGained {
                    player: player_id,
                    tile: tile.clone(),
                });
                events.extend(apply_tech_tile_immediate_reward(state, player_id, tile.0));
                if tile.0 == TECH_TILE_LOST_FLEET_FREE_BUILD_MINE {
                    if let Some(coord) = bonus_build_coord {
                        events.extend(apply_build_impl(state, player_id, *coord, 2, 0, false, 0));
                    }
                }
            }
            if let Some(track) = advance_track {
                events.extend(apply_free_research_advance(state, player_id, *track));
            }
        }
        TechTileChoice::Advanced {
            track,
            covered_tile,
            advance_track,
        } => {
            let index = research_track_index(*track);
            if let Some(tile) = state.research_board.advanced_tech_tiles[index].take() {
                if let Some(player) = state.player_mut(player_id) {
                    player.advanced_tech_tiles.push(tile.clone());
                    player.covered_tech_tiles.push(covered_tile.clone());
                    flip_a_federation_token(player);
                }
                events.push(GameEvent::AdvancedTechTileGained {
                    player: player_id,
                    tile: tile.clone(),
                });
                events.extend(apply_advanced_tech_tile_immediate_reward(
                    state, player_id, tile.0,
                ));
            }
            if let Some(t) = advance_track {
                events.extend(apply_free_research_advance(state, player_id, *t));
            }
        }
    }
    events
}

fn grant_vp(
    state: &mut GameState,
    player_id: PlayerId,
    vp: i32,
    reason: VpReason,
) -> Vec<GameEvent> {
    if vp == 0 {
        return vec![];
    }
    if let Some(player) = state.player_mut(player_id) {
        player.vp += vp;
    }
    vec![GameEvent::VpAwarded {
        player: player_id,
        amount: vp,
        reason,
    }]
}

/// Live counts tech tiles key their per-unit rewards off. Standard-sector and Deep-Space-sector
/// counts follow the round/final scoring tiles' existing convention: a sector "counted" once the
/// player has colonized at least one planet in it, deduplicated by sector id.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TechTileCounter {
    TradingStationsOnBoard,
    FederationTokensOwned,
    StandardSectorsColonized,
    DeepSpaceSectorsColonized,
    GaiaPlanetsColonized,
    MinesOnBoard,
    LargeBuildingsOwned,
    PlanetTypesColonized,
    ResearchLabsOwned,
    AsteroidsColonized,
}

fn distinct_colonized_sector_count(
    state: &GameState,
    player_id: PlayerId,
    category: crate::data::SectorCategory,
) -> u32 {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    let mut sector_ids: Vec<u8> = player
        .structures
        .iter()
        .filter_map(|s| MapEngine::sector_id_at(&state.board, s.hex))
        .filter(|&id| crate::data::category_for_sector(id) == category)
        .collect();
    sector_ids.sort_unstable();
    sector_ids.dedup();
    sector_ids.len() as u32
}

fn tech_tile_counter_value(
    state: &GameState,
    player_id: PlayerId,
    counter: TechTileCounter,
) -> u32 {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    match counter {
        TechTileCounter::TradingStationsOnBoard => player
            .structures
            .iter()
            .filter(|s| s.kind == StructureType::TradingStation)
            .count() as u32,
        TechTileCounter::FederationTokensOwned => player.federation_tokens.len() as u32,
        TechTileCounter::StandardSectorsColonized => {
            distinct_colonized_sector_count(state, player_id, crate::data::SectorCategory::Standard)
        }
        TechTileCounter::DeepSpaceSectorsColonized => distinct_colonized_sector_count(
            state,
            player_id,
            crate::data::SectorCategory::DeepSpace,
        ),
        TechTileCounter::GaiaPlanetsColonized => player
            .structures
            .iter()
            .filter(|s| {
                state
                    .board
                    .hexes
                    .get(&s.hex)
                    .and_then(|hex| hex.planet.as_ref())
                    .is_some_and(|planet| planet.is_gaia_formed)
            })
            .count() as u32,
        TechTileCounter::MinesOnBoard => {
            player
                .structures
                .iter()
                .filter(|s| s.kind == StructureType::Mine)
                .count() as u32
                + player.artifact_mines.len() as u32
        }
        TechTileCounter::LargeBuildingsOwned => player
            .structures
            .iter()
            .filter(|s| {
                matches!(
                    s.kind,
                    StructureType::PlanetaryInstitute | StructureType::Academy(_)
                )
            })
            .count() as u32,
        TechTileCounter::PlanetTypesColonized => {
            colonized_planet_types(state, player_id).len() as u32
        }
        TechTileCounter::ResearchLabsOwned => player
            .structures
            .iter()
            .filter(|s| s.kind == StructureType::ResearchLab)
            .count() as u32,
        TechTileCounter::AsteroidsColonized => {
            player
                .structures
                .iter()
                .filter(|s| {
                    state
                        .board
                        .hexes
                        .get(&s.hex)
                        .and_then(|hex| hex.planet.as_ref())
                        .is_some_and(|planet| {
                            !planet.is_gaia_formed && planet.planet_type == PlanetType::Asteroid
                        })
                })
                .count() as u32
                + player
                    .artifact_mines
                    .iter()
                    .filter(|planet_type| **planet_type == PlanetType::Asteroid)
                    .count() as u32
        }
    }
}

/// One-time rewards applied the moment a Standard Tech tile is taken (rulebook p.15 wording:
/// "immediately and only once"). Ids not listed here either grant no immediate reward (the 3
/// "income" tiles, applied during Income phase — see `tech_tile_income`), have an ongoing effect
/// wired elsewhere (6, 8, 12, 14 — see the sections below), are a special action (10), or are the
/// free-build-mine tile (11, handled by its caller since it needs a target coord).
fn apply_tech_tile_immediate_reward(
    state: &mut GameState,
    player_id: PlayerId,
    id: u8,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    match id {
        4 => {
            // std_04: immediately gain 1 ore and 1 QIC.
            if let Some(player) = state.player_mut(player_id) {
                add_resource(player, ResourceKind::Ore, 1);
                add_resource(player, ResourceKind::Qic, 1);
            }
            events.push(GameEvent::ResourceChanged {
                player: player_id,
                delta: ResourceDelta {
                    ore: 1,
                    qic: 1,
                    ..ResourceDelta::zero()
                },
            });
        }
        7 => {
            // std_07: immediately score 7 VP.
            events.extend(grant_vp(
                state,
                player_id,
                7,
                VpReason::TechTile { tile_id: id },
            ));
        }
        9 => {
            // std_09: immediately gain 1 knowledge for each planet type colonized.
            let count =
                tech_tile_counter_value(state, player_id, TechTileCounter::PlanetTypesColonized);
            if count > 0 {
                if let Some(player) = state.player_mut(player_id) {
                    add_resource(player, ResourceKind::Knowledge, count as u8);
                }
                events.push(GameEvent::ResourceChanged {
                    player: player_id,
                    delta: ResourceDelta {
                        knowledge: count as i8,
                        ..ResourceDelta::zero()
                    },
                });
            }
        }
        13 => {
            // LF3: immediately score 6 VP per Planetary Institute/Academy plus 4 VP per Deep
            // Space sector colonized (Appendix V's one combined-condition tile).
            let large =
                tech_tile_counter_value(state, player_id, TechTileCounter::LargeBuildingsOwned);
            let deep = tech_tile_counter_value(
                state,
                player_id,
                TechTileCounter::DeepSpaceSectorsColonized,
            );
            let vp = 6 * large as i32 + 4 * deep as i32;
            events.extend(grant_vp(
                state,
                player_id,
                vp,
                VpReason::TechTile { tile_id: id },
            ));
        }
        _ => {}
    }
    events
}

/// One-time rewards applied the moment an Advanced Tech tile is taken. Ids not listed here have
/// an ongoing effect wired elsewhere (3, 4, 7, 8, 11, 14, 15, 16, 17, 19) or are special actions
/// (20, 21, 22).
fn apply_advanced_tech_tile_immediate_reward(
    state: &mut GameState,
    player_id: PlayerId,
    id: u8,
) -> Vec<GameEvent> {
    let per_unit = match id {
        1 => Some((TechTileCounter::TradingStationsOnBoard, 4)),
        2 => Some((TechTileCounter::FederationTokensOwned, 5)),
        6 => Some((TechTileCounter::StandardSectorsColonized, 2)),
        9 => Some((TechTileCounter::GaiaPlanetsColonized, 2)),
        10 => Some((TechTileCounter::MinesOnBoard, 2)),
        12 => Some((TechTileCounter::DeepSpaceSectorsColonized, 4)),
        13 => Some((TechTileCounter::LargeBuildingsOwned, 6)),
        _ => None,
    };
    if let Some((counter, vp_per_unit)) = per_unit {
        let count = tech_tile_counter_value(state, player_id, counter);
        return grant_vp(
            state,
            player_id,
            vp_per_unit * count as i32,
            VpReason::TechTile { tile_id: id },
        );
    }
    if id == 5 {
        // adv_05: immediately gain 1 ore for each Space sector colonized.
        let count =
            tech_tile_counter_value(state, player_id, TechTileCounter::StandardSectorsColonized);
        if count > 0 {
            if let Some(player) = state.player_mut(player_id) {
                add_resource(player, ResourceKind::Ore, count as u8);
            }
            return vec![GameEvent::ResourceChanged {
                player: player_id,
                delta: ResourceDelta {
                    ore: count as i8,
                    ..ResourceDelta::zero()
                },
            }];
        }
    }
    vec![]
}

/// Flat resource grant for a Tech tile's "as a special action" ability.
#[derive(Debug, Clone, Copy)]
struct TechTileSpecialActionEffect {
    ore: u8,
    credits: u8,
    knowledge: u8,
    qic: u8,
    /// Standard tile 10 only: "as a special action, charge 4 power" — moves existing power
    /// tokens forward a bowl (`apply_power_charge`), not a fresh grant.
    charge_power: u8,
}

impl TechTileSpecialActionEffect {
    const fn zero() -> Self {
        Self {
            ore: 0,
            credits: 0,
            knowledge: 0,
            qic: 0,
            charge_power: 0,
        }
    }
}

fn tech_tile_special_action_effect(id: u8) -> Option<TechTileSpecialActionEffect> {
    match id {
        10 => Some(TechTileSpecialActionEffect {
            charge_power: 4,
            ..TechTileSpecialActionEffect::zero()
        }),
        _ => None,
    }
}

fn advanced_tech_tile_special_action_effect(id: u8) -> Option<TechTileSpecialActionEffect> {
    match id {
        20 => Some(TechTileSpecialActionEffect {
            knowledge: 3,
            ..TechTileSpecialActionEffect::zero()
        }),
        21 => Some(TechTileSpecialActionEffect {
            ore: 3,
            ..TechTileSpecialActionEffect::zero()
        }),
        22 => Some(TechTileSpecialActionEffect {
            qic: 1,
            credits: 5,
            ..TechTileSpecialActionEffect::zero()
        }),
        _ => None,
    }
}

fn validate_tech_tile_special_action(
    state: &GameState,
    player_id: PlayerId,
    tile: &TechTileRef,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    match tile {
        TechTileRef::Standard { tile } => {
            if !player.tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "you don't own that Tech tile".to_string(),
                ));
            }
            if player.covered_tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile is covered by an Advanced Tech tile and has no effect"
                        .to_string(),
                ));
            }
            if tech_tile_special_action_effect(tile.0).is_none() {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile has no special action".to_string(),
                ));
            }
            if player
                .tech_tile_special_actions_used_this_round
                .contains(&tile.0)
            {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile's special action was already used this round".to_string(),
                ));
            }
        }
        TechTileRef::Advanced { tile } => {
            if !player.advanced_tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "you don't own that Tech tile".to_string(),
                ));
            }
            if advanced_tech_tile_special_action_effect(tile.0).is_none() {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile has no special action".to_string(),
                ));
            }
            if player
                .advanced_tech_tile_special_actions_used_this_round
                .contains(&tile.0)
            {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile's special action was already used this round".to_string(),
                ));
            }
        }
    }
    Ok(())
}

fn apply_tech_tile_special_action(
    state: &mut GameState,
    player_id: PlayerId,
    tile: &TechTileRef,
) -> Vec<GameEvent> {
    let effect = match tile {
        TechTileRef::Standard { tile } => tech_tile_special_action_effect(tile.0),
        TechTileRef::Advanced { tile } => advanced_tech_tile_special_action_effect(tile.0),
    };
    let Some(effect) = effect else {
        advance_turn(state);
        return vec![];
    };
    let mut events = Vec::new();
    if let Some(player) = state.player_mut(player_id) {
        match tile {
            TechTileRef::Standard { tile } => player
                .tech_tile_special_actions_used_this_round
                .push(tile.0),
            TechTileRef::Advanced { tile } => player
                .advanced_tech_tile_special_actions_used_this_round
                .push(tile.0),
        }
        if effect.charge_power > 0 {
            apply_power_charge(&mut player.resources.power, effect.charge_power);
        }
        if effect.ore > 0 {
            add_resource(player, ResourceKind::Ore, effect.ore);
        }
        if effect.credits > 0 {
            add_resource(player, ResourceKind::Credits, effect.credits);
        }
        if effect.knowledge > 0 {
            add_resource(player, ResourceKind::Knowledge, effect.knowledge);
        }
        if effect.qic > 0 {
            add_resource(player, ResourceKind::Qic, effect.qic);
        }
        if effect.ore > 0 || effect.credits > 0 || effect.knowledge > 0 || effect.qic > 0 {
            events.push(GameEvent::ResourceChanged {
                player: player_id,
                delta: ResourceDelta {
                    ore: effect.ore as i8,
                    credits: effect.credits as i8,
                    knowledge: effect.knowledge as i8,
                    qic: effect.qic as i8,
                },
            });
        }
    }
    advance_turn(state);
    events
}

/// Tech tile equivalent of `check_round_tile_bonus` for the "whenever you X, score N VP" ongoing
/// tiles — checked at the same call sites as round tile bonuses, but iterates every owned
/// Standard/Advanced tile (several could match the same condition, unlike the single active round
/// tile) rather than a single tile. Advanced tile 16 ("whenever you take a QIC action, score 4
/// VP") isn't listed here — `RoundCondition` has no QIC-action variant, and this engine's closest
/// analog to the base-board's dedicated QIC action is Academy(Qic)'s passive action, which is
/// granted directly at its own apply site instead.
fn tech_tile_event_vp_per_unit(id: u8, condition: &RoundCondition) -> Option<i32> {
    match (id, condition) {
        (8, RoundCondition::BuildMineOnGaia) => Some(8), // std_08
        _ => None,
    }
}

fn advanced_tech_tile_event_vp_per_unit(id: u8, condition: &RoundCondition) -> Option<i32> {
    match (id, condition) {
        (3, RoundCondition::UpgradeTradingStation) => Some(3),
        (4, RoundCondition::BuildMine) => Some(3),
        (8, RoundCondition::ResearchAdvance) => Some(2),
        (17, RoundCondition::TerraformingStep) => Some(2),
        _ => None,
    }
}

fn check_tech_tile_event_bonus(
    state: &mut GameState,
    player_id: PlayerId,
    condition: &RoundCondition,
    units: u8,
) -> Vec<GameEvent> {
    if units == 0 {
        return vec![];
    }
    let Some(player) = state.player(player_id) else {
        return vec![];
    };
    let mut events = Vec::new();
    for tile_id in player_active_tech_tile_ids(player) {
        if let Some(vp_per_unit) = tech_tile_event_vp_per_unit(tile_id, condition) {
            events.extend(grant_vp(
                state,
                player_id,
                vp_per_unit * i32::from(units),
                VpReason::TechTile { tile_id },
            ));
        }
    }
    let player = state.player(player_id).unwrap_or_else(|| unreachable!());
    for tile_id in player
        .advanced_tech_tiles
        .iter()
        .map(|t| t.0)
        .collect::<Vec<_>>()
    {
        if let Some(vp_per_unit) = advanced_tech_tile_event_vp_per_unit(tile_id, condition) {
            events.extend(grant_vp(
                state,
                player_id,
                vp_per_unit * i32::from(units),
                VpReason::TechTile { tile_id },
            ));
        }
    }
    events
}

/// "When you pass" Tech tiles (rulebook p.15 wording e.g. "when you pass, you gain 2 victory
/// points for each asteroid that you have colonized") — a live final tally at the moment the
/// player passes, distinct from `check_tech_tile_event_bonus`'s per-action triggers.
fn tech_tile_pass_bonus(id: u8) -> Option<(TechTileCounter, i32)> {
    match id {
        14 => Some((TechTileCounter::AsteroidsColonized, 2)), // LF4
        _ => None,
    }
}

fn advanced_tech_tile_pass_bonus(id: u8) -> Option<(TechTileCounter, i32)> {
    match id {
        7 => Some((TechTileCounter::ResearchLabsOwned, 3)),
        11 => Some((TechTileCounter::FederationTokensOwned, 3)),
        14 => Some((TechTileCounter::AsteroidsColonized, 2)),
        15 => Some((TechTileCounter::DeepSpaceSectorsColonized, 2)),
        19 => Some((TechTileCounter::PlanetTypesColonized, 1)),
        _ => None,
    }
}

fn apply_tech_tile_pass_bonus(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    let Some(player) = state.player(player_id) else {
        return vec![];
    };
    let mut events = Vec::new();
    for tile_id in player_active_tech_tile_ids(player) {
        if let Some((counter, vp_per_unit)) = tech_tile_pass_bonus(tile_id) {
            let count = tech_tile_counter_value(state, player_id, counter);
            events.extend(grant_vp(
                state,
                player_id,
                vp_per_unit * count as i32,
                VpReason::TechTile { tile_id },
            ));
        }
    }
    let player = state.player(player_id).unwrap_or_else(|| unreachable!());
    for tile_id in player
        .advanced_tech_tiles
        .iter()
        .map(|t| t.0)
        .collect::<Vec<_>>()
    {
        if let Some((counter, vp_per_unit)) = advanced_tech_tile_pass_bonus(tile_id) {
            let count = tech_tile_counter_value(state, player_id, counter);
            events.extend(grant_vp(
                state,
                player_id,
                vp_per_unit * count as i32,
                VpReason::TechTile { tile_id },
            ));
        }
    }
    events
}

/// Standard tile 6's ongoing power-value bonus ("Your large buildings — Planetary Institute and
/// Academy — have a power value of 4") — checked alongside `bescods_home_planet_power_bonus`/
/// `moweyds_power_ring_bonus` wherever a structure's power value matters.
fn tech_tile_large_building_power_bonus(
    state: &GameState,
    player_id: PlayerId,
    kind: StructureType,
) -> u32 {
    if !matches!(
        kind,
        StructureType::PlanetaryInstitute | StructureType::Academy(_)
    ) {
        return 0;
    }
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    if player_active_tech_tile_ids(player).contains(&6) {
        1
    } else {
        0
    }
}

/// Sum of `tech_tile_large_building_power_bonus` across every PI/Academy the player owns among
/// `hexes` — the multi-hex counterpart used for federation power (mirrors
/// `bescods_home_planet_power_bonus`/`moweyds_power_ring_bonus`'s shape).
fn tech_tile_large_building_power_bonus_for_hexes(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
) -> u32 {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    if !player_active_tech_tile_ids(player).contains(&6) {
        return 0;
    }
    hexes
        .iter()
        .filter_map(|coord| state.board.hexes.get(coord))
        .flat_map(|hex| &hex.structures)
        .filter(|structure| {
            structure.owner == player_id
                && matches!(
                    structure.kind,
                    StructureType::PlanetaryInstitute | StructureType::Academy(_)
                )
        })
        .count() as u32
}

// ── Base-faction special actions ─────────────────────────────────────────────

fn validate_base_faction_special_action(
    state: &GameState,
    player_id: PlayerId,
    faction: FactionId,
    requires_planetary_institute: bool,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.faction != Some(faction) {
        return Err(RuleError::ActionNotAllowed(
            "action belongs to a different faction".to_string(),
        ));
    }
    if player.faction_special_action_used_this_round {
        return Err(RuleError::ActionNotAllowed(
            "faction special action has already been used this round".to_string(),
        ));
    }
    if requires_planetary_institute && !player_has_planetary_institute(player) {
        return Err(RuleError::ActionNotAllowed(
            "requires the Planetary Institute".to_string(),
        ));
    }
    Ok(())
}

fn validate_ambas_swap_planetary_institute(
    state: &GameState,
    player_id: PlayerId,
    mine_coord: HexCoord,
) -> Result<(), RuleError> {
    validate_base_faction_special_action(state, player_id, FactionId::Ambas, true)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if !player
        .structures
        .iter()
        .any(|structure| structure.hex == mine_coord && structure.kind == StructureType::Mine)
    {
        return Err(RuleError::InvalidTarget(mine_coord));
    }
    Ok(())
}

fn apply_ambas_swap_planetary_institute(
    state: &mut GameState,
    player_id: PlayerId,
    mine_coord: HexCoord,
) -> Vec<GameEvent> {
    let Some(pi_coord) = state.player(player_id).and_then(|player| {
        player
            .structures
            .iter()
            .find(|structure| structure.kind == StructureType::PlanetaryInstitute)
            .map(|structure| structure.hex)
    }) else {
        return Vec::new();
    };

    if let Some(player) = state.player_mut(player_id) {
        for structure in &mut player.structures {
            if structure.hex == pi_coord {
                structure.kind = StructureType::Mine;
            } else if structure.hex == mine_coord {
                structure.kind = StructureType::PlanetaryInstitute;
            }
        }
        player.faction_special_action_used_this_round = true;
    }
    for (coord, kind) in [
        (pi_coord, StructureType::Mine),
        (mine_coord, StructureType::PlanetaryInstitute),
    ] {
        if let Some(hex) = state.board.hexes.get_mut(&coord) {
            if let Some(structure) = hex
                .structures
                .iter_mut()
                .find(|structure| structure.owner == player_id)
            {
                structure.kind = kind;
            }
        }
    }

    advance_turn(state);
    vec![GameEvent::StructuresSwapped {
        player: player_id,
        first: pi_coord,
        second: mine_coord,
    }]
}

fn validate_firaks_downgrade_research_lab(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    validate_base_faction_special_action(state, player_id, FactionId::Firaks, true)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if !player
        .structures
        .iter()
        .any(|structure| structure.hex == coord && structure.kind == StructureType::ResearchLab)
    {
        return Err(RuleError::InvalidTarget(coord));
    }
    let trading_station_count = player
        .structures
        .iter()
        .filter(|structure| structure.kind == StructureType::TradingStation)
        .count();
    if trading_station_count >= MAX_TRADING_STATIONS {
        return Err(RuleError::StructureLimit(StructureType::TradingStation));
    }
    validate_free_research_advance(state, player_id, track)
}

fn apply_firaks_downgrade_research_lab(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    if let Some(player) = state.player_mut(player_id) {
        if let Some(structure) = player
            .structures
            .iter_mut()
            .find(|structure| structure.hex == coord)
        {
            structure.kind = StructureType::TradingStation;
        }
        player.faction_special_action_used_this_round = true;
    }
    if let Some(hex) = state.board.hexes.get_mut(&coord) {
        if let Some(structure) = hex
            .structures
            .iter_mut()
            .find(|structure| structure.owner == player_id)
        {
            structure.kind = StructureType::TradingStation;
        }
    }

    let mut events = vec![GameEvent::StructureUpgraded {
        player: player_id,
        hex: coord,
        from: StructureType::ResearchLab,
        to: StructureType::TradingStation,
    }];
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::UpgradeTradingStation,
        1,
    ));
    events.extend(check_tech_tile_event_bonus(
        state,
        player_id,
        &RoundCondition::UpgradeTradingStation,
        1,
    ));
    events.extend(apply_free_research_advance(state, player_id, track));
    if !maybe_enter_charge_power_phase(state, player_id, coord) {
        advance_turn(state);
    }
    events
}

fn validate_bescods_lowest_research_advance(
    state: &GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    validate_base_faction_special_action(state, player_id, FactionId::Bescods, false)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let lowest_level = ResearchTrack::all()
        .into_iter()
        .map(|candidate| player.research_tracks.get(candidate))
        .min()
        .unwrap_or(0);
    if player.research_tracks.get(track) != lowest_level {
        return Err(RuleError::ActionNotAllowed(
            "Bescods may only advance a currently lowest research track".to_string(),
        ));
    }
    validate_free_research_advance(state, player_id, track)
}

fn apply_bescods_lowest_research_advance(
    state: &mut GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    if let Some(player) = state.player_mut(player_id) {
        player.faction_special_action_used_this_round = true;
    }
    let events = apply_free_research_advance(state, player_id, track);
    advance_turn(state);
    events
}

/// Ivits Planetary Institute special action's QIC-for-range cost — accessibility "follows the
/// same rules as the 'Build a Mine' action" (rulebook Appendix I), including range extension.
fn ivits_space_station_qic_for_range(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<u8, RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let nav_level = player.research_tracks.navigation as usize;
    let nav_range = player_nav_range(player, 0);
    let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
    range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)
}

fn validate_ivits_place_space_station(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_base_faction_special_action(state, player_id, FactionId::Ivits, true)?;
    let hex = state
        .board
        .hexes
        .get(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    if hex.planet.is_some() {
        return Err(RuleError::InvalidTarget(coord));
    }
    if hex
        .structures
        .iter()
        .any(|s| s.kind == StructureType::SpaceStation)
    {
        return Err(RuleError::TargetOccupied(coord));
    }
    let qic_for_range = ivits_space_station_qic_for_range(state, player_id, coord)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.resources.qic < qic_for_range {
        return Err(RuleError::InsufficientResources(ResourceKind::Qic));
    }
    Ok(())
}

fn apply_ivits_place_space_station(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    let qic_for_range = ivits_space_station_qic_for_range(state, player_id, coord).unwrap_or(0);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player.resources.qic.saturating_sub(qic_for_range);
        player.structures.push(crate::game_state::Structure {
            hex: coord,
            kind: StructureType::SpaceStation,
        });
        player.faction_special_action_used_this_round = true;
    }
    if let Some(hex) = state.board.hexes.get_mut(&coord) {
        hex.structures.push(PlacedStructure {
            owner: player_id,
            kind: StructureType::SpaceStation,
        });
    }
    advance_turn(state);
    vec![GameEvent::SpaceStationPlaced {
        player: player_id,
        hex: coord,
    }]
}

// ── Tinkeroids Tinkering tiles ──────────────────────────────────────────────

/// Tile ids usable in rounds 1-3 vs. 4-6 (rulebook Appendix I: "3 of the tiles are to be used
/// in rounds 1-3, and the rest in rounds 4-6"). Effects confirmed against the tile scans at
/// `gaia-frontend/src/assets/tinkering_tiles/`: 1 = Build a Mine with 1 free terraforming step
/// (the one tile the rulebook prose also spells out), 2 = gain 1 QIC, 3 = charge 4 power (the
/// same effect as round booster 4's income, `apply_power_charge`), 4 = gain 2 QIC, 5 = Build a
/// Mine with 3 free terraforming steps, 6 = gain 3 knowledge. Each of the 6 tiles is usable at
/// most once per game.
fn tinkeroids_tiles_for_round(round: u8) -> &'static [u8] {
    if round <= 3 {
        &[1, 2, 3]
    } else {
        &[4, 5, 6]
    }
}

/// `Some(free_steps)` for the 2 "Build a Mine" tiles (1 and 5); `None` for the 4 flat
/// resource-gain tiles, which take no target hex.
fn tinkeroids_tile_free_terraform_steps(tile: u8) -> Option<u8> {
    match tile {
        1 => Some(1),
        5 => Some(3),
        _ => None,
    }
}

fn validate_tinkeroids_use_tile(
    state: &GameState,
    player_id: PlayerId,
    tile: u8,
    coord: Option<HexCoord>,
) -> Result<(), RuleError> {
    validate_base_faction_special_action(state, player_id, FactionId::Tinkeroids, true)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if !tinkeroids_tiles_for_round(state.round).contains(&tile) {
        return Err(RuleError::ActionNotAllowed(
            "that Tinkering tile isn't available this round".to_string(),
        ));
    }
    if player.tinkeroids_tiles_used.contains(&tile) {
        return Err(RuleError::ActionNotAllowed(
            "that Tinkering tile has already been used".to_string(),
        ));
    }
    match (tinkeroids_tile_free_terraform_steps(tile), coord) {
        (Some(free_steps), Some(coord)) => {
            validate_build_impl(state, player_id, coord, free_steps, 0, false, 0)
        }
        (Some(_), None) => Err(RuleError::ActionNotAllowed(
            "this Tinkering tile requires a target hex to build a mine".to_string(),
        )),
        (None, Some(_)) => Err(RuleError::ActionNotAllowed(
            "this Tinkering tile doesn't take a target hex".to_string(),
        )),
        (None, None) => Ok(()),
    }
}

fn apply_tinkeroids_use_tile(
    state: &mut GameState,
    player_id: PlayerId,
    tile: u8,
    coord: Option<HexCoord>,
) -> Vec<GameEvent> {
    if let Some(player) = state.player_mut(player_id) {
        player.tinkeroids_tiles_used.push(tile);
        player.faction_special_action_used_this_round = true;
    }
    if let Some(free_steps) = tinkeroids_tile_free_terraform_steps(tile) {
        let Some(coord) = coord else {
            return vec![]; // already validated; defensive no-op
        };
        return apply_build_impl(state, player_id, coord, free_steps, 0, false, 0);
    }
    let mut events = Vec::new();
    if let Some(player) = state.player_mut(player_id) {
        match tile {
            2 => {
                add_resource(player, ResourceKind::Qic, 1);
                events.push(GameEvent::ResourceChanged {
                    player: player_id,
                    delta: ResourceDelta {
                        qic: 1,
                        ..ResourceDelta::zero()
                    },
                });
            }
            3 => apply_power_charge(&mut player.resources.power, 4),
            4 => {
                add_resource(player, ResourceKind::Qic, 2);
                events.push(GameEvent::ResourceChanged {
                    player: player_id,
                    delta: ResourceDelta {
                        qic: 2,
                        ..ResourceDelta::zero()
                    },
                });
            }
            6 => {
                player.resources.knowledge = player.resources.knowledge.saturating_add(3);
                events.push(GameEvent::ResourceChanged {
                    player: player_id,
                    delta: ResourceDelta {
                        knowledge: 3,
                        ..ResourceDelta::zero()
                    },
                });
            }
            _ => {}
        }
    }
    advance_turn(state);
    events
}

// ── Moweyds Power Rings ──────────────────────────────────────────────────────

/// Physical supply cap (expansion components list: "6 Power Rings (for the Moweyds faction)").
const MOWEYDS_POWER_RING_SUPPLY: usize = 6;
/// Power value added to a Power-Ringed hex's structure, both for federation power and for the
/// amount opponents may charge (rulebook Appendix I: "The power value of your structure on this
/// planet increases by 2").
const MOWEYDS_POWER_RING_BONUS: u32 = 2;

fn validate_moweyds_place_power_ring(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_base_faction_special_action(state, player_id, FactionId::Moweyds, true)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.moweyds_power_ring_hexes.len() >= MOWEYDS_POWER_RING_SUPPLY {
        return Err(RuleError::ActionNotAllowed(
            "no Power Rings remain in the supply".to_string(),
        ));
    }
    if player.moweyds_power_ring_hexes.contains(&coord) {
        return Err(RuleError::ActionNotAllowed(
            "that hex already has a Power Ring".to_string(),
        ));
    }
    let has_own_structure = state.board.hexes.get(&coord).is_some_and(|hex| {
        hex.structures
            .iter()
            .any(|s| s.owner == player_id && s.kind != StructureType::Satellite)
    });
    if !has_own_structure {
        return Err(RuleError::ActionNotAllowed(
            "Power Rings can only be placed on a hex with one of your own buildings".to_string(),
        ));
    }
    Ok(())
}

fn apply_moweyds_place_power_ring(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    if let Some(player) = state.player_mut(player_id) {
        player.moweyds_power_ring_hexes.push(coord);
        player.faction_special_action_used_this_round = true;
    }
    advance_turn(state);
    vec![GameEvent::PowerRingPlaced {
        player: player_id,
        hex: coord,
    }]
}

/// Extra federation power from Power Rings placed on any of `hexes` — added alongside
/// `bescods_home_planet_power_bonus` wherever federation power is summed.
fn moweyds_power_ring_bonus(state: &GameState, player_id: PlayerId, hexes: &[HexCoord]) -> u32 {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    if player.faction != Some(FactionId::Moweyds) {
        return 0;
    }
    hexes
        .iter()
        .filter(|coord| player.moweyds_power_ring_hexes.contains(coord))
        .count() as u32
        * MOWEYDS_POWER_RING_BONUS
}

// ── Research ──────────────────────────────────────────────────────────────────
//
// Base rulebook p.14: "In order to advance to level 5 of a research area, in addition to any
// other costs, you must flip one of your federation tokens from its green side to its gray side
// (this is the same cost as for taking an advanced tech tile). Only one player can advance to
// level 5 of each research area. Each time your research token advances from level 2 to level 3
// in any research area, you charge three power (this also applies if you advanced by taking a
// tech tile)." None of this — the level-5 exclusivity, the token-flip cost, or the level-2-to-3
// power charge — was implemented before; `TrackState.alliance_taken` looked like a plausible
// pre-existing hook for the exclusivity check, but it (and the sibling `PlayerState.alliance_tiles`/
// `AllianceTile`) turned out to be dead code with zero rulebook connection and zero other
// read/write sites anywhere in the engine — not reused here, left untouched.

/// Whether any OTHER player already holds level 5 on `track`.
fn research_level_5_taken_by_another_player(
    state: &GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> bool {
    state
        .research_board
        .tracks
        .get(&track)
        .is_some_and(|track_state| {
            track_state
                .player_levels
                .iter()
                .any(|(&pid, &level)| pid != player_id && level >= 5)
        })
}

/// The green-token-flip cost shared by "advance to level 5" and "take an Advanced Tech tile."
fn validate_has_a_green_federation_token(player: &PlayerState) -> Result<(), RuleError> {
    if player.federation_tokens.is_empty() {
        return Err(RuleError::ActionNotAllowed(
            "requires flipping a Federation token from green to gray, but none are owned"
                .to_string(),
        ));
    }
    Ok(())
}

fn flip_a_federation_token(player: &mut PlayerState) {
    if let Some(token) = player.federation_tokens.pop() {
        player.gray_federation_tokens.push(token);
    }
}

/// Shared by every research-track-advancing action's validate function (paid `ResearchAdvance`,
/// every free-advance path, Eclipse's power+knowledge boost): rejects an already-maxed track,
/// and — specifically for the step from level 4 to level 5 — rejects it if another player
/// already holds level 5 or if the player has no green Federation token left to flip.
fn validate_research_track_advance(
    state: &GameState,
    player_id: PlayerId,
    player: &PlayerState,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let level = player.research_tracks.get(track);
    if level >= 5 {
        return Err(RuleError::ActionNotAllowed(
            "research track is at maximum level".to_string(),
        ));
    }
    if level == 4 {
        if research_level_5_taken_by_another_player(state, player_id, track) {
            return Err(RuleError::ActionNotAllowed(
                "another player has already reached level 5 of that research track".to_string(),
            ));
        }
        validate_has_a_green_federation_token(player)?;
    }
    Ok(())
}

/// Increments `track` by one level, applying the level-2-to-3 power charge and the level-5
/// token flip along the way — callers must validate via `validate_research_track_advance` first.
fn advance_research_track_level(
    state: &mut GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> u8 {
    let Some(player) = state.player_mut(player_id) else {
        return 0;
    };
    player.research_tracks.increment(track);
    let new_level = player.research_tracks.get(track);
    if new_level == 3 {
        apply_power_charge(&mut player.resources.power, 3);
    }
    if new_level == 5 {
        flip_a_federation_token(player);
    }
    // Mirrors `player.research_tracks` into the shared board's per-track level map — the only
    // thing `research_level_5_taken_by_another_player` can see, since it has to check every
    // player's level on `track`, not just this one player's.
    state
        .research_board
        .tracks
        .entry(track)
        .or_default()
        .player_levels
        .insert(player_id, new_level);
    new_level
}

fn validate_research(
    state: &GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    validate_faction_research_access(player, track)?;
    if player.resources.knowledge < RESEARCH_KNOWLEDGE_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Knowledge,
        ));
    }
    validate_research_track_advance(state, player_id, player, track)?;
    Ok(())
}

fn apply_research(
    state: &mut GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    if let Some(player) = state.player_mut(player_id) {
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
    } else {
        return events;
    };
    let new_level = advance_research_track_level(state, player_id, track);
    events.push(GameEvent::ResearchAdvanced {
        player: player_id,
        track,
        level: new_level,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
        1,
    ));
    events.extend(check_tech_tile_event_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
        1,
    ));
    advance_turn(state);
    events
}

fn validate_free_research_advance(
    state: &GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    validate_faction_research_access(player, track)?;
    validate_research_track_advance(state, player_id, player, track)?;
    Ok(())
}

fn validate_faction_research_access(
    player: &PlayerState,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    if player.faction == Some(FactionId::BalTaks)
        && track == ResearchTrack::Navigation
        && !player_has_planetary_institute(player)
    {
        return Err(RuleError::ActionNotAllowed(
            "Bal T'aks cannot advance Navigation before building their Planetary Institute"
                .to_string(),
        ));
    }
    Ok(())
}

/// Advances research without paying the normal 4-knowledge action cost and without advancing
/// the turn. Used when gaining a Standard Tech tile from a Lost Fleet action.
fn apply_free_research_advance(
    state: &mut GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    if state.player(player_id).is_none() {
        return Vec::new();
    }
    let level = advance_research_track_level(state, player_id, track);
    let mut events = vec![GameEvent::ResearchAdvanced {
        player: player_id,
        track,
        level,
    }];
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
        1,
    ));
    events.extend(check_tech_tile_event_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
        1,
    ));
    events
}

// ── Federation ────────────────────────────────────────────────────────────────

/// A Federation token's reward (rulebook p.14 "4) Form a Federation": "immediately gain
/// everything shown on the token"). Ids 1-7 are the base-game supply (`docs/EN_Gaia_rulebook_lo.pdf`
/// p.2 components image; individual photos in `gaia-frontend/src/assets/federation_tokens/` later
/// caught a misread — the rulebook crop's green hex icon on the id-2 token was misidentified as
/// ore, corrected to QIC per `fed_token_03_score_8_vp_and_gain_1_qic.jpg`'s filename and the
/// user's confirmation): 12 VP (x3, no resources); 8 VP + 1 QIC (x3); 8 VP + 2 power, entering
/// bowl1 as fresh tokens (x3, confirmed with the user); 7 VP + 2 ore (x3); 7 VP + 6 credits (x3);
/// 6 VP + 2 knowledge (x3); 1 ore + 1 knowledge + 2 credits, no VP (x1) — 19 total. Both sides of
/// each physical token show the same reward icons (only the backing color differs — green vs
/// gray — confirmed with the user), so the green/gray distinction carries no separate data this
/// engine would need to model even if the flip-for-Advanced-Tech mechanic existed. Ids 8-15 are
/// the Lost Fleet expansion's 8 spaceship-tied tokens, one per
/// physical token (confirmed directly against the physical components by the user — the
/// rulebook's Appendix VI page only spells out 4 of these 8 in prose, presumably because the
/// other 4 just follow the base game's already-explained "VP + resources" token pattern): 8 VP +
/// 8 credits; 12 VP (the rulebook notes this variant stays flippable for Advanced Tech/level-5
/// research even after use, unlike the base-game 12 VP token — that flip mechanic doesn't exist
/// anywhere in this engine yet, so this is modeled as plain 12 VP); 4 VP + 4 knowledge; 4 VP + 2
/// ore + 1 QIC; 1 Standard Tech tile of the player's choice; 7 VP + 2 power as **fresh tokens
/// directly into bowl3** ("Area III" — confirmed via `fed_lf_..._7.jpg`'s "+2"/"III" icon; an
/// earlier verbal description as "charged" turned out to be imprecise once the photo arrived); a
/// free "Build a Mine" with up to 3 free terraforming steps (QIC-extendable range, same as normal
/// Build); a free "Build a Mine" of limitless range (ore still costs for terraforming, QIC still
/// costs for Gaia planets). Id 16 is the Gleens' unique Planetary-Institute token; it has the
/// same printed resource reward as base token id 7 but is granted independently of the supply.
enum FederationTokenKind {
    Flat12Vp,
    Vp8PlusQic1,
    Vp8PlusPower2,
    Vp7PlusOre2,
    Vp7PlusCredits6,
    Vp6PlusKnowledge2,
    Ore1Knowledge1Credits2,
    LostFleetVp8PlusCredits8,
    LostFleetFlat12Vp,
    LostFleetVp4PlusKnowledge4,
    LostFleetVp4PlusOre2PlusQic1,
    LostFleetTechTileOfChoice,
    LostFleetVp7PlusPower2ToArea3,
    LostFleetFreeBuild3Steps,
    LostFleetFreeBuildUnlimitedRange,
}

/// Maps a Federation token id to its reward — see `FederationTokenKind`. Any id outside 1-16
/// (which shouldn't happen; both pools are seeded only with these ids) falls back to `Flat12Vp`,
/// the simplest confirmed effect, rather than a made-up amount.
fn federation_token_kind(id: u8) -> FederationTokenKind {
    match id {
        2 => FederationTokenKind::Vp8PlusQic1,
        3 => FederationTokenKind::Vp8PlusPower2,
        4 => FederationTokenKind::Vp7PlusOre2,
        5 => FederationTokenKind::Vp7PlusCredits6,
        6 => FederationTokenKind::Vp6PlusKnowledge2,
        7 => FederationTokenKind::Ore1Knowledge1Credits2,
        8 => FederationTokenKind::LostFleetVp8PlusCredits8,
        9 => FederationTokenKind::LostFleetFlat12Vp,
        10 => FederationTokenKind::LostFleetVp4PlusKnowledge4,
        11 => FederationTokenKind::LostFleetVp4PlusOre2PlusQic1,
        12 => FederationTokenKind::LostFleetTechTileOfChoice,
        13 => FederationTokenKind::LostFleetVp7PlusPower2ToArea3,
        14 => FederationTokenKind::LostFleetFreeBuild3Steps,
        15 => FederationTokenKind::LostFleetFreeBuildUnlimitedRange,
        16 => FederationTokenKind::Ore1Knowledge1Credits2,
        _ => FederationTokenKind::Flat12Vp, // id 1, and the fallback for any unexpected id
    }
}

/// Resolves a `FederationTokenChoice` to the token kind id it refers to, checking availability
/// but not consuming it. Shared by `validate_federation`/`apply_federation`.
fn resolve_federation_token_choice(
    state: &GameState,
    player_id: PlayerId,
    token: FederationTokenChoice,
) -> Result<u8, RuleError> {
    match token {
        FederationTokenChoice::Supply { kind } => {
            if !state
                .research_board
                .federation_tokens
                .iter()
                .any(|t| t.0 == kind)
            {
                return Err(RuleError::ActionNotAllowed(
                    "no Federation token of that kind remains in the supply".to_string(),
                ));
            }
            Ok(kind)
        }
        FederationTokenChoice::Spaceship { ship } => {
            let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
            let ship_id = spaceship_id_to_ship_id(ship);
            if !player.explored_ships.contains(&ship_id) {
                return Err(RuleError::ActionNotAllowed(
                    "requires an Exploration Shuttle on that spaceship".to_string(),
                ));
            }
            state
                .spaceship_boards
                .iter()
                .find(|b| b.id == ship)
                .and_then(|b| b.federation_token.as_ref())
                .map(|t| t.0)
                .ok_or_else(|| {
                    RuleError::ActionNotAllowed(
                        "that spaceship's Federation token has already been claimed".to_string(),
                    )
                })
        }
    }
}

/// Every hex a satellite can legally be placed on: exists on the board, has no planet, no
/// structure of any player, no existing satellite of this player, and isn't a Lost Fleet
/// spaceship tile (expansion rulebook: "you may not place a satellite on a spaceship tile").
fn validate_satellite_hex(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let hex = state
        .board
        .hexes
        .get(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    if hex.planet.is_some() {
        return Err(RuleError::ActionNotAllowed(
            "satellites cannot be placed on planets".to_string(),
        ));
    }
    if !hex.structures.is_empty() {
        return Err(RuleError::TargetOccupied(coord));
    }
    if hex.satellites.contains(&player_id) {
        return Err(RuleError::TargetOccupied(coord));
    }
    if state.board.spaceship_tiles.values().any(|&c| c == coord) {
        return Err(RuleError::ActionNotAllowed(
            "cannot place a satellite on a Lost Fleet spaceship tile".to_string(),
        ));
    }
    Ok(())
}

/// Physical per-color supply (`docs/EN_Gaia_rulebook_lo.pdf` components list, "Other Player
/// Pieces (in each player color)": "25 Satellites").
const SATELLITE_SUPPLY_PER_PLAYER: usize = 25;

fn player_satellites_on_board(state: &GameState, player_id: PlayerId) -> usize {
    state
        .board
        .hexes
        .values()
        .filter(|hex| hex.satellites.contains(&player_id))
        .count()
}

/// Total federation power for `hexes`, matching whichever branch (Ivits growth vs. standard)
/// `validate_federation` itself uses — factored out so the minimality check below can recompute
/// it for a hex removed from the submission.
fn federation_power_total(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
    federated_hexes: &[HexCoord],
    is_ivits_growth: bool,
) -> u32 {
    if is_ivits_growth {
        MapEngine::federation_power(&state.board, player_id, federated_hexes)
            .saturating_add(MapEngine::federation_power(&state.board, player_id, hexes))
    } else {
        MapEngine::federation_power(&state.board, player_id, hexes)
            .saturating_add(bescods_home_planet_power_bonus(state, player_id, hexes))
            .saturating_add(moweyds_power_ring_bonus(state, player_id, hexes))
            .saturating_add(tech_tile_large_building_power_bonus_for_hexes(
                state, player_id, hexes,
            ))
    }
}

/// Rulebook p.14: "You cannot form a federation by connecting more planets and satellites than
/// are needed to form it. In other words, if the federation would be valid with at least one
/// fewer planet and one fewer satellite, you must change the federation." Checked as: no single
/// hex among this action's `hexes`/`satellite_hexes` may be dropped while the rest (plus any
/// already-committed federation, for Ivits growth) stays connected and the total power still
/// meets `minimum_power` — a local no-redundant-node check, not a search for some entirely
/// different, smaller federation elsewhere on the board.
fn federation_submission_has_redundant_hex(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
    satellite_hexes: &[HexCoord],
    federated_hexes: &[HexCoord],
    is_ivits_growth: bool,
    minimum_power: u32,
) -> bool {
    let candidates: Vec<HexCoord> = hexes.iter().chain(satellite_hexes).copied().collect();
    for dropped in candidates {
        let remaining_hexes: Vec<HexCoord> =
            hexes.iter().copied().filter(|&h| h != dropped).collect();
        let remaining_satellites: Vec<HexCoord> = satellite_hexes
            .iter()
            .copied()
            .filter(|&h| h != dropped)
            .collect();
        let mut connected: Vec<HexCoord> = remaining_hexes
            .iter()
            .chain(remaining_satellites.iter())
            .copied()
            .collect();
        if is_ivits_growth {
            connected.extend(federated_hexes.iter().copied());
        }
        if !MapEngine::is_connected(&connected) {
            continue;
        }
        let power = federation_power_total(
            state,
            player_id,
            &remaining_hexes,
            federated_hexes,
            is_ivits_growth,
        );
        if power >= minimum_power {
            return true;
        }
    }
    false
}

/// Rulebook p.14: "Planets and satellites of the newly formed federation cannot be directly
/// adjacent to planets or satellites from any of your existing federations." Applies only when
/// forming a genuinely new, separate federation — not to Ivits' single ever-growing federation,
/// which is expected to touch its own existing hexes. The related "colonizing a planet directly
/// adjacent to an existing federation enlarges it for free" mechanic (automatic, silent growth
/// via `Build`, distinct from this action) isn't modeled — deliberately out of scope, see README.
fn federation_touches_an_existing_federation(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
    satellite_hexes: &[HexCoord],
) -> bool {
    let Some(player) = state.player(player_id) else {
        return false;
    };
    if player.federated_hexes.is_empty() {
        return false;
    }
    hexes.iter().chain(satellite_hexes).any(|coord| {
        coord
            .neighbors()
            .iter()
            .any(|n| player.federated_hexes.contains(n))
    })
}

fn validate_federation(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
    satellite_hexes: &[HexCoord],
    token: FederationTokenChoice,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<&TechTile>,
) -> Result<(), RuleError> {
    if hexes.is_empty() {
        return Err(RuleError::FederationDisconnected);
    }

    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    // Every named planet must actually be this player's own colonized structure — rulebook
    // p.14: "You can form a federation only with planets you have colonized."
    for coord in hexes {
        let owned = state.board.hexes.get(coord).is_some_and(|hex| {
            hex.structures
                .iter()
                .any(|s| s.owner == player_id && s.kind != StructureType::Satellite)
        });
        if !owned {
            return Err(RuleError::ActionNotAllowed(
                "federation hexes must be planets you have colonized".to_string(),
            ));
        }
    }

    // Rulebook p.14: "Each planet and satellite can be part of only one federation."
    for coord in hexes.iter().chain(satellite_hexes) {
        if player.federated_hexes.contains(coord) {
            return Err(RuleError::ActionNotAllowed(
                "that hex is already part of an earlier federation".to_string(),
            ));
        }
    }

    for &coord in satellite_hexes {
        validate_satellite_hex(state, player_id, coord)?;
    }

    if !satellite_hexes.is_empty() {
        let already_placed = player_satellites_on_board(state, player_id);
        if already_placed + satellite_hexes.len() > SATELLITE_SUPPLY_PER_PLAYER {
            return Err(RuleError::ActionNotAllowed(
                "no more Satellites remain in your personal supply".to_string(),
            ));
        }
    }

    // Ivits (base rulebook Appendix I): "You can have only one federation during the whole
    // game... After you have formed a federation, to take the 'Form a Federation' action again,
    // you must connect planets to that federation instead of forming a new federation... To
    // build a satellite during this action, you must spend one Q.I.C. instead of discarding one
    // power." `federated_hexes` already holds exactly this player's one-and-only federation's
    // full hex set once it exists (empty until their first `FormFederation`), so its emptiness
    // doubles as the "have I formed my federation yet" flag — no extra state needed.
    let is_ivits_growth =
        player.faction == Some(FactionId::Ivits) && !player.federated_hexes.is_empty();

    if !is_ivits_growth
        && federation_touches_an_existing_federation(state, player_id, hexes, satellite_hexes)
    {
        return Err(RuleError::ActionNotAllowed(
            "a new federation cannot be directly adjacent to one of your existing federations"
                .to_string(),
        ));
    }

    if is_ivits_growth {
        let qic_cost = satellite_hexes.len() as u32;
        if u32::from(player.resources.qic) < qic_cost {
            return Err(RuleError::InsufficientResources(ResourceKind::Qic));
        }
    } else {
        let satellite_power_cost = satellite_hexes.len() as u32;
        let available_power = u32::from(player.resources.power.bowl1)
            + u32::from(player.resources.power.bowl2)
            + u32::from(player.resources.power.bowl3);
        if available_power < satellite_power_cost {
            return Err(RuleError::InsufficientResources(ResourceKind::Power));
        }
    }

    // Connectivity — colonized planets plus any bridging satellites must form one component;
    // for a growing Ivits federation, the existing federation's hexes anchor the new ones too.
    let mut connected: Vec<HexCoord> = hexes.iter().chain(satellite_hexes).copied().collect();
    if is_ivits_growth {
        connected.extend(player.federated_hexes.iter().copied());
    }
    if !MapEngine::is_connected(&connected) {
        return Err(RuleError::FederationDisconnected);
    }

    // Power threshold (satellites and space stations aside — `federation_power` counts a space
    // station as 1 and a satellite as 0, matching Ivits' own rulebook text on both).
    let power = federation_power_total(
        state,
        player_id,
        hexes,
        &player.federated_hexes,
        is_ivits_growth,
    );
    let minimum_power = if is_ivits_growth {
        // "at least to 7X, where X is the number of federation tokens you own plus one (not
        // including the federation token from level 5 of 'Terraforming')" — that specific bonus
        // token isn't a mechanic this engine grants yet, so `federation_tokens.len()` already
        // excludes it and needs no separate subtraction.
        FEDERATION_MIN_POWER.saturating_mul(player.federation_tokens.len() as u32 + 1)
    } else {
        match ability_for(state, player_id)
            .map(FactionAbility::federation_power_rule)
            .unwrap_or(FederationPowerRule::Standard)
        {
            FederationPowerRule::Custom(minimum) => minimum,
            FederationPowerRule::Standard | FederationPowerRule::IvitsRule => FEDERATION_MIN_POWER,
        }
    };
    if power < minimum_power {
        return Err(RuleError::FederationInsufficientPower); // unit variant
    }

    if federation_submission_has_redundant_hex(
        state,
        player_id,
        hexes,
        satellite_hexes,
        &player.federated_hexes,
        is_ivits_growth,
        minimum_power,
    ) {
        return Err(RuleError::ActionNotAllowed(
            "this federation uses more planets/satellites than needed — remove the redundant one"
                .to_string(),
        ));
    }

    let kind = resolve_federation_token_choice(state, player_id, token)?;
    match federation_token_kind(kind) {
        FederationTokenKind::LostFleetFreeBuildUnlimitedRange => {
            let coord = bonus_build_coord.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "this Federation token requires a target hex".to_string(),
                )
            })?;
            validate_build_impl(state, player_id, coord, 0, 0, true, 0)?;
        }
        FederationTokenKind::LostFleetFreeBuild3Steps => {
            let coord = bonus_build_coord.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "this Federation token requires a target hex".to_string(),
                )
            })?;
            validate_build_impl(state, player_id, coord, 3, 0, false, 0)?;
        }
        FederationTokenKind::LostFleetTechTileOfChoice => {
            let tile = bonus_tech_tile.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "this Federation token requires choosing a Tech tile".to_string(),
                )
            })?;
            if !state.research_board.tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile isn't available".to_string(),
                ));
            }
        }
        _ => {}
    }

    Ok(())
}

/// Applies the VP and direct-resource portion of a Federation token effect. Follow-up effects
/// needing a target or selection are handled by the caller. This lets Twilight repeat a token
/// without gaining or consuming another physical Federation token.
fn apply_federation_token_direct_reward(state: &mut GameState, player_id: PlayerId, kind: u8) {
    let Some(player) = state.player_mut(player_id) else {
        return;
    };
    match federation_token_kind(kind) {
        FederationTokenKind::Flat12Vp | FederationTokenKind::LostFleetFlat12Vp => {
            player.vp = player.vp.saturating_add(12);
        }
        FederationTokenKind::Vp8PlusQic1 => {
            player.vp = player.vp.saturating_add(8);
            add_resource(player, ResourceKind::Qic, 1);
        }
        FederationTokenKind::Vp8PlusPower2 => {
            player.vp = player.vp.saturating_add(8);
            player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(2);
        }
        FederationTokenKind::Vp7PlusOre2 => {
            player.vp = player.vp.saturating_add(7);
            add_resource(player, ResourceKind::Ore, 2);
        }
        FederationTokenKind::Vp7PlusCredits6 => {
            player.vp = player.vp.saturating_add(7);
            add_resource(player, ResourceKind::Credits, 6);
        }
        FederationTokenKind::Vp6PlusKnowledge2 => {
            player.vp = player.vp.saturating_add(6);
            add_resource(player, ResourceKind::Knowledge, 2);
        }
        FederationTokenKind::Ore1Knowledge1Credits2 => {
            add_resource(player, ResourceKind::Ore, 1);
            add_resource(player, ResourceKind::Knowledge, 1);
            add_resource(player, ResourceKind::Credits, 2);
        }
        FederationTokenKind::LostFleetVp8PlusCredits8 => {
            player.vp = player.vp.saturating_add(8);
            add_resource(player, ResourceKind::Credits, 8);
        }
        FederationTokenKind::LostFleetVp4PlusKnowledge4 => {
            player.vp = player.vp.saturating_add(4);
            add_resource(player, ResourceKind::Knowledge, 4);
        }
        FederationTokenKind::LostFleetVp4PlusOre2PlusQic1 => {
            player.vp = player.vp.saturating_add(4);
            add_resource(player, ResourceKind::Ore, 2);
            add_resource(player, ResourceKind::Qic, 1);
        }
        FederationTokenKind::LostFleetVp7PlusPower2ToArea3 => {
            player.vp = player.vp.saturating_add(7);
            player.resources.power.bowl3 = player.resources.power.bowl3.saturating_add(2);
        }
        FederationTokenKind::LostFleetFreeBuildUnlimitedRange
        | FederationTokenKind::LostFleetFreeBuild3Steps
        | FederationTokenKind::LostFleetTechTileOfChoice => {}
    }
}

fn apply_federation(
    state: &mut GameState,
    player_id: PlayerId,
    hexes: Vec<HexCoord>,
    satellite_hexes: Vec<HexCoord>,
    token: FederationTokenChoice,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<TechTile>,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let Ok(kind) = resolve_federation_token_choice(state, player_id, token) else {
        return events; // already validated; defensive no-op
    };

    // Build the satellites — normally "discard one power" per satellite (drains bowl1 then
    // bowl2 then bowl3, matching `ExamineArtifact`'s identical "discard N power" pattern), but
    // an Ivits player growing their one-and-only federation instead "spend[s] one Q.I.C." per
    // satellite (rulebook p.20) — and mark every hex used here as permanently committed to this
    // federation (`PlayerState.federated_hexes`).
    if let Some(player) = state.player_mut(player_id) {
        let is_ivits_growth =
            player.faction == Some(FactionId::Ivits) && !player.federated_hexes.is_empty();
        if is_ivits_growth {
            player.resources.qic = player
                .resources
                .qic
                .saturating_sub(satellite_hexes.len() as u8);
        } else {
            let mut remaining = satellite_hexes.len() as u8;
            let from_bowl1 = remaining.min(player.resources.power.bowl1);
            player.resources.power.bowl1 -= from_bowl1;
            remaining -= from_bowl1;
            let from_bowl2 = remaining.min(player.resources.power.bowl2);
            player.resources.power.bowl2 -= from_bowl2;
            remaining -= from_bowl2;
            let from_bowl3 = remaining.min(player.resources.power.bowl3);
            player.resources.power.bowl3 -= from_bowl3;
        }

        player.federated_hexes.extend(hexes.iter().copied());
        player
            .federated_hexes
            .extend(satellite_hexes.iter().copied());
    }
    for &coord in &satellite_hexes {
        if let Some(hex) = state.board.hexes.get_mut(&coord) {
            hex.satellites.push(player_id);
        }
    }
    match token {
        FederationTokenChoice::Supply { kind } => {
            if let Some(pos) = state
                .research_board
                .federation_tokens
                .iter()
                .position(|t| t.0 == kind)
            {
                state.research_board.federation_tokens.remove(pos);
            }
        }
        FederationTokenChoice::Spaceship { ship } => {
            if let Some(board) = state.spaceship_boards.iter_mut().find(|b| b.id == ship) {
                board.federation_token = None;
            }
        }
    }

    let federation_token = FederationToken(kind);
    if let Some(player) = state.player_mut(player_id) {
        player.federation_tokens.push(federation_token.clone());
    }

    apply_federation_token_direct_reward(state, player_id, kind);

    if let FederationTokenKind::LostFleetTechTileOfChoice = federation_token_kind(kind) {
        if let Some(tile) = bonus_tech_tile {
            if transfer_tech_tile_to_player(state, player_id, &tile) {
                events.push(GameEvent::TechTileGained {
                    player: player_id,
                    tile,
                });
            }
        }
    }

    events.push(GameEvent::FederationFormed {
        player: player_id,
        hexes,
        token: federation_token,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::FormFederation,
        1,
    ));

    // The two "free Build a Mine" token kinds delegate turn-completion (and any
    // `ChargePowerPending` suspension) to `apply_build_impl` itself, matching
    // `apply_spaceship_credit_terraform`'s established delegation pattern — calling
    // `advance_turn` again afterward here would double-advance the turn.
    match federation_token_kind(kind) {
        FederationTokenKind::LostFleetFreeBuildUnlimitedRange => {
            if let Some(coord) = bonus_build_coord {
                events.extend(apply_build_impl(state, player_id, coord, 0, 0, true, 0));
            } else {
                advance_turn(state);
            }
        }
        FederationTokenKind::LostFleetFreeBuild3Steps => {
            if let Some(coord) = bonus_build_coord {
                events.extend(apply_build_impl(state, player_id, coord, 3, 0, false, 0));
            } else {
                advance_turn(state);
            }
        }
        _ => {
            advance_turn(state);
        }
    }
    events
}

// ── Power action ──────────────────────────────────────────────────────────────

/// Power-action board slots 2 and 6 (rulebook Appendix III) immediately
/// perform a "build a mine" action with this many free terraforming steps
/// instead of granting a plain resource — every other slot is a resource
/// gain (`apply_power_effect`).
fn free_terraform_steps_for_power_action(id: u8) -> u8 {
    match id {
        2 => 2,
        6 => 1,
        _ => 0,
    }
}

fn validate_power_action(
    state: &GameState,
    player_id: PlayerId,
    id: u8,
    coord: Option<HexCoord>,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if state.used_power_actions.contains(&id) {
        return Err(RuleError::ActionNotAllowed(
            "power action slot already taken this round".to_string(),
        ));
    }
    let cost = power_action_token_cost(player, power_action_cost(id));
    let free_steps = free_terraform_steps_for_power_action(id);
    if free_steps > 0 {
        let coord = coord.ok_or_else(|| {
            RuleError::ActionNotAllowed(
                "this power action requires a target hex to build a mine".to_string(),
            )
        })?;
        return validate_build_impl(state, player_id, coord, free_steps, cost, false, 0);
    }
    if spendable_power_value(&player.resources.power) < cost {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }
    Ok(())
}

fn apply_power_action(
    state: &mut GameState,
    player_id: PlayerId,
    id: u8,
    coord: Option<HexCoord>,
) -> Vec<GameEvent> {
    let cost = state
        .player(player_id)
        .map(|player| power_action_token_cost(player, power_action_cost(id)))
        .unwrap_or_else(|| power_action_cost(id));
    state.used_power_actions.push(id);
    let free_steps = free_terraform_steps_for_power_action(id);
    if free_steps > 0 {
        let Some(coord) = coord else {
            return vec![]; // already validated; defensive no-op
        };
        return apply_build_impl(state, player_id, coord, free_steps, cost, false, 0);
    }
    let mut events = Vec::new();
    let delta = apply_power_effect(state, player_id, id, cost);
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
    let ability = ability_for(state, player_id).ok_or_else(|| {
        RuleError::ActionNotAllowed("faction has no implemented special action".to_string())
    })?;
    if !ability.has_special_action() {
        return Err(RuleError::ActionNotAllowed(
            "faction has no implemented special action".to_string(),
        ));
    }
    ability.special_action(state, player_id).map(|_| ())
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
    validate_gaia_formation_impl(state, player_id, coord, 0)
}

fn validate_gaia_formation_impl(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    bonus_range: u8,
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
    let available_power = active_power_tokens(&player.resources.power);
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

    // Reachability, extendable with QIC (rulebook p.11, reused by Lost Fleet's "Start a Gaia
    // Project" text verbatim).
    let nav_level = player.research_tracks.navigation as usize;
    let nav_range = player_nav_range(player, bonus_range);
    let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
    let qic_for_range =
        range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)?;
    if player.resources.qic < qic_for_range {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Qic,
        ));
    }

    Ok(())
}

fn apply_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    apply_gaia_formation_impl(state, player_id, coord, 0)
}

fn apply_gaia_formation_impl(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
    bonus_range: u8,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let qic_for_range = state
        .player(player_id)
        .map(|player| {
            let nav_level = player.research_tracks.navigation as usize;
            let nav_range = player_nav_range(player, bonus_range);
            let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
            range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)
                .unwrap_or(0)
        })
        .unwrap_or(0);

    if let Some(player) = state.player_mut(player_id) {
        let gaia_level = player.research_tracks.gaia as usize;
        let power_needed = GAIA_POWER_COST[gaia_level.min(GAIA_POWER_COST.len() - 1)];

        move_power_to_gaia(&mut player.resources.power, power_needed);

        player.resources.qic = player.resources.qic.saturating_sub(qic_for_range);
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
    advance_turn(state);
    events
}

/// Shared rule for effects that start and complete a Gaia Project in the same action without
/// moving power into the Gaia area. The player must still have a Gaiaformer available and may
/// still pay QIC for range, but the Gaiaformer is returned immediately and therefore never
/// increments `gaiaformers_deployed`.
fn validate_immediate_gaia_formation_impl(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    bonus_range: u8,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.gaiaformers_available() == 0 {
        return Err(RuleError::NoGaiaformerAvailable);
    }

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

    let nav_level = player.research_tracks.navigation as usize;
    let nav_range = player_nav_range(player, bonus_range);
    let starts: Vec<HexCoord> = player
        .structures
        .iter()
        .map(|structure| structure.hex)
        .collect();
    let qic_for_range =
        range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)?;
    if player.resources.qic < qic_for_range {
        return Err(RuleError::InsufficientResources(ResourceKind::Qic));
    }
    Ok(())
}

fn apply_immediate_gaia_formation_impl(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
    bonus_range: u8,
) -> Vec<GameEvent> {
    let qic_for_range = state
        .player(player_id)
        .map(|player| {
            let nav_level = player.research_tracks.navigation as usize;
            let nav_range = player_nav_range(player, bonus_range);
            let starts: Vec<HexCoord> = player
                .structures
                .iter()
                .map(|structure| structure.hex)
                .collect();
            range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)
                .unwrap_or(0)
        })
        .unwrap_or(0);

    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player.resources.qic.saturating_sub(qic_for_range);
    }
    if let Some(planet) = state
        .board
        .hexes
        .get_mut(&coord)
        .and_then(|hex| hex.planet.as_mut())
    {
        planet.owner = Some(player_id);
        planet.is_gaia_formed = true;
    }

    advance_turn(state);
    vec![
        GameEvent::GaiaFormingStarted {
            player: player_id,
            hex: coord,
        },
        GameEvent::GaiaFormingComplete {
            player: player_id,
            hex: coord,
        },
    ]
}

const ROUND_BOOSTER_IMMEDIATE_GAIA: u8 = 5;
const ROUND_BOOSTER_RANGE_PLUS_THREE: u8 = 8;
const ROUND_BOOSTER_RANGE_BONUS: u8 = 3;

fn validate_round_booster_special_access(
    state: &GameState,
    player_id: PlayerId,
    booster_id: u8,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.booster != Some(Booster(booster_id)) {
        return Err(RuleError::ActionNotAllowed(
            "requires owning the matching round booster".to_string(),
        ));
    }
    if player.round_booster_special_action_used_this_round {
        return Err(RuleError::ActionNotAllowed(
            "this round booster's special action has already been used this round".to_string(),
        ));
    }
    Ok(())
}

fn validate_round_booster_immediate_gaia_formation(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_round_booster_special_access(state, player_id, ROUND_BOOSTER_IMMEDIATE_GAIA)?;
    validate_immediate_gaia_formation_impl(state, player_id, coord, 0)
}

fn mark_round_booster_special_used(state: &mut GameState, player_id: PlayerId) {
    if let Some(player) = state.player_mut(player_id) {
        player.round_booster_special_action_used_this_round = true;
    }
}

fn apply_round_booster_immediate_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    mark_round_booster_special_used(state, player_id);
    apply_immediate_gaia_formation_impl(state, player_id, coord, 0)
}

fn validate_round_booster_range_build(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_round_booster_special_access(state, player_id, ROUND_BOOSTER_RANGE_PLUS_THREE)?;
    validate_build_impl(
        state,
        player_id,
        coord,
        0,
        0,
        false,
        ROUND_BOOSTER_RANGE_BONUS,
    )
}

fn apply_round_booster_range_build(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    mark_round_booster_special_used(state, player_id);
    apply_build_impl(
        state,
        player_id,
        coord,
        0,
        0,
        false,
        ROUND_BOOSTER_RANGE_BONUS,
    )
}

fn validate_round_booster_range_gaia_formation(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_round_booster_special_access(state, player_id, ROUND_BOOSTER_RANGE_PLUS_THREE)?;
    validate_gaia_formation_impl(state, player_id, coord, ROUND_BOOSTER_RANGE_BONUS)
}

fn apply_round_booster_range_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    mark_round_booster_special_used(state, player_id);
    apply_gaia_formation_impl(state, player_id, coord, ROUND_BOOSTER_RANGE_BONUS)
}

fn validate_round_booster_range_explore_spaceship(
    state: &GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Result<(), RuleError> {
    validate_round_booster_special_access(state, player_id, ROUND_BOOSTER_RANGE_PLUS_THREE)?;
    validate_explore_spaceship_impl(state, player_id, ship, ROUND_BOOSTER_RANGE_BONUS)
}

fn apply_round_booster_range_explore_spaceship(
    state: &mut GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Vec<GameEvent> {
    mark_round_booster_special_used(state, player_id);
    apply_explore_spaceship_impl(state, player_id, ship, ROUND_BOOSTER_RANGE_BONUS)
}

// ── Lost Fleet: Explore a Spaceship / Examine an Artifact ──────────────────────
// Expansion rulebook (`docs/GP_Exp_Rule_EN_V1_Web.pdf`), "11) Action: Explore a Lost Fleet
// Spaceship" and "12) Action: Examine an Artifact". Map placement of the 4 spaceship tiles
// (`BoardState.spaceship_tiles`, set up in `MapEngine::init_game_state`) is a simplified
// stand-in for the expansion's real player-count-dependent Interspace-tile variable setup —
// see the plan this was implemented from for the scope note.

const SPACESHIP_DEPLOY_VP_COST: i32 = 5;
const ARTIFACT_EXAMINE_POWER_COST: u8 = 6;
/// Appendix II action space id for `SpaceshipCreditTerraform` in `used_spaceship_actions`.
const SPACESHIP_ACTION_CREDIT_TERRAFORM: u8 = 1;
const SPACESHIP_CREDIT_TERRAFORM_COST: u8 = 3;

fn spaceship_id_to_ship_id(id: SpaceshipId) -> ShipId {
    match id {
        SpaceshipId::Twilight => 0,
        SpaceshipId::Rebellion => 1,
        SpaceshipId::TFMars => 2,
        SpaceshipId::Eclipse => 3,
    }
}

/// Power charged (from the supply, into bowl3) for the Nth explorer of a spaceship (N = shuttle
/// slot index, 0-based). Confirmed directly from a physical shuttle-slot photo (slot 1: no
/// charge icon; slot 2: charge 2; slot 3: charge 2; slot 4: charge 3) — the earlier PDF-render
/// crop wasn't sharp enough to resolve the digits and was misread as "all identical, flat 1".
/// Assumed consistent across all 4 spaceships (only Twilight's slot column was directly seen).
fn spaceship_shuttle_power_charge(slot_index: usize) -> u8 {
    const TABLE: [u8; 4] = [0, 2, 2, 3];
    TABLE.get(slot_index).copied().unwrap_or(3)
}

fn validate_explore_spaceship(
    state: &GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Result<(), RuleError> {
    validate_explore_spaceship_impl(state, player_id, ship, 0)
}

fn validate_explore_spaceship_impl(
    state: &GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
    bonus_range: u8,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    if player.exploration_shuttles_available == 0 {
        return Err(RuleError::ActionNotAllowed(
            "no Exploration Shuttles available".to_string(),
        ));
    }

    let board = state
        .spaceship_boards
        .iter()
        .find(|b| b.id == ship)
        .ok_or_else(|| RuleError::ActionNotAllowed("unknown spaceship".to_string()))?;
    if board.explorers.contains(&Some(player_id)) {
        return Err(RuleError::ActionNotAllowed(
            "already explored this spaceship".to_string(),
        ));
    }
    if board.explorers.iter().all(Option::is_some) {
        return Err(RuleError::ActionNotAllowed(
            "spaceship has no free shuttle slots".to_string(),
        ));
    }

    let coord = *state.board.spaceship_tiles.get(&ship).ok_or_else(|| {
        RuleError::ActionNotAllowed("spaceship not placed on the map".to_string())
    })?;
    // Reachability, extendable with QIC — Lost Fleet explicitly reuses the base-game "1 QIC =
    // +2 range" rule for this action ("Note that you can also use the '+3 Range' [action] for
    // the new action 'Explore a Lost Fleet Spaceship'" implies the same QIC-based extension
    // applies to the action's own base range too).
    let nav_level = player.research_tracks.navigation as usize;
    let nav_range = player_nav_range(player, bonus_range);
    let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
    let qic_for_range =
        range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)?;
    if player.resources.qic < qic_for_range {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Qic,
        ));
    }

    if player.vp < SPACESHIP_DEPLOY_VP_COST {
        return Err(RuleError::ActionNotAllowed(
            "insufficient VP to deploy an Exploration Shuttle".to_string(),
        ));
    }
    if player.faction == Some(FactionId::Taklons)
        && !matches!(
            player.resources.power.brainstone,
            Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2 | BrainstoneLocation::Area3)
        )
    {
        return Err(RuleError::ActionNotAllowed(
            "Taklons must have their Brainstone in the active power cycle to explore a spaceship"
                .to_string(),
        ));
    }

    Ok(())
}

fn apply_explore_spaceship(
    state: &mut GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Vec<GameEvent> {
    apply_explore_spaceship_impl(state, player_id, ship, 0)
}

fn apply_explore_spaceship_impl(
    state: &mut GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
    bonus_range: u8,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    let slot_index = state
        .spaceship_boards
        .iter()
        .find(|b| b.id == ship)
        .and_then(|b| b.explorers.iter().position(Option::is_none));

    let qic_for_range = state
        .board
        .spaceship_tiles
        .get(&ship)
        .copied()
        .and_then(|coord| {
            state.player(player_id).map(|player| {
                let nav_level = player.research_tracks.navigation as usize;
                let nav_range = player_nav_range(player, bonus_range);
                let starts: Vec<HexCoord> = player.structures.iter().map(|s| s.hex).collect();
                range_and_qic_cost(state, player_id, &starts, nav_range, nav_level as u8, coord)
                    .unwrap_or(0)
            })
        })
        .unwrap_or(0);

    if let Some(player) = state.player_mut(player_id) {
        player.vp -= SPACESHIP_DEPLOY_VP_COST;
        player.resources.qic = player.resources.qic.saturating_sub(qic_for_range);
        player.exploration_shuttles_available =
            player.exploration_shuttles_available.saturating_sub(1);
        player.explored_ships.push(spaceship_id_to_ship_id(ship));
        if player.faction == Some(FactionId::Taklons) {
            move_brainstone_to_gaia(&mut player.resources.power);
        }
    }

    if let Some(idx) = slot_index {
        if let Some(board) = state.spaceship_boards.iter_mut().find(|b| b.id == ship) {
            board.explorers[idx] = Some(player_id);
        }
        if idx > 0 {
            if let Some(player) = state.player_mut(player_id) {
                apply_power_charge(
                    &mut player.resources.power,
                    spaceship_shuttle_power_charge(idx),
                );
            }
        }
    }

    events.push(GameEvent::ShipExplored {
        player: player_id,
        ship_id: spaceship_id_to_ship_id(ship),
    });
    advance_turn(state);
    events
}

fn validate_examine_artifact(
    state: &GameState,
    player_id: PlayerId,
    artifact: ArtifactId,
    copy_federation_token_kind: Option<u8>,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<&TechTile>,
    bonus_research_track: Option<ResearchTrack>,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let twilight = spaceship_id_to_ship_id(SpaceshipId::Twilight);
    if !player.explored_ships.contains(&twilight) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Twilight spaceship".to_string(),
        ));
    }

    let total_power = u32::from(player.resources.power.bowl1)
        + u32::from(player.resources.power.bowl2)
        + u32::from(player.resources.power.bowl3);
    if total_power < u32::from(ARTIFACT_EXAMINE_POWER_COST) {
        return Err(RuleError::InsufficientResources(ResourceKind::Power));
    }
    if player.faction == Some(FactionId::Taklons)
        && !matches!(
            player.resources.power.brainstone,
            Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2 | BrainstoneLocation::Area3)
        )
    {
        return Err(RuleError::ActionNotAllowed(
            "Taklons must additionally move their Brainstone to the Gaia area".to_string(),
        ));
    }

    let has_artifact = state
        .spaceship_boards
        .iter()
        .find(|b| b.id == SpaceshipId::Twilight)
        .is_some_and(|b| b.artifact_pool.contains(&artifact));
    if !has_artifact {
        return Err(RuleError::ActionNotAllowed(
            "that Artifact isn't available on the Twilight spaceship".to_string(),
        ));
    }

    if artifact_effect(artifact) == ArtifactEffect::CopyFederationEffect {
        let token_kind = copy_federation_token_kind.ok_or_else(|| {
            RuleError::ActionNotAllowed(
                "this Artifact requires choosing an owned Federation token to copy".to_string(),
            )
        })?;
        validate_owned_federation_token_effect(
            state,
            player_id,
            token_kind,
            bonus_build_coord,
            bonus_tech_tile,
            bonus_research_track,
        )?;
    }

    Ok(())
}

/// A drawn Artifact's effect (expansion rulebook Appendix VII, p.15). All 13 physical tokens'
/// effects are confirmed from individual photos. Unknown ids fall back to `FlatVp7` as the
/// closest-confirmed default rather than a made-up amount.
#[derive(Clone, Copy, PartialEq, Eq)]
enum ArtifactEffect {
    /// Defensive fallback for an unknown artifact id: retain the historical 7 VP behavior without
    /// inventing a virtual planet type.
    FlatVp7,
    /// "Immediately and only once receive 2 victory points for each Deep Space sector in which
    /// you have colonized at least 1 planet." (`gaia-frontend/src/assets/artifacts/artifact_01`)
    VpPerDeepSpaceSector,
    /// "Gain 2 power as income. Place them in Area III." (`artifact_02`)
    PowerToBowl3Two,
    /// "Immediately and only once receive 1 knowledge and 1 ore." (`artifact_03`)
    OreAndKnowledgeOne,
    /// "Immediately and only once receive 3 victory points for each level in the Gaia Project
    /// research area." (`artifact_04`)
    VpPerGaiaProjectLevel,
    /// "Immediately and only once receive 3 victory points for each level in the Science
    /// research area." (`artifact_05`; matches the rulebook's own worked example on the
    /// Appendix VII page — Science level 5 -> 15 VP — for this same "VP per track level"
    /// family, confirming the multiplier).
    VpPerScienceLevel,
    /// "Immediately and only once receive 3 credits and 3 ore." (`artifact_06`)
    CreditsThreeAndOreThree,
    /// "Immediately and only once receive 3 knowledge and 1 QIC." (`artifact_07`)
    KnowledgeThreeAndQicOne,
    /// "Immediately and only once receive 7 victory points." (`artifact_08`). It also counts as
    /// building a coordinate-less Protoplanet mine for every scoring/objective purpose, but not
    /// as colonizing a sector and without the ordinary +6 VP Protoplanet build reward.
    FlatVp7PlusProtoPlanetMine,
    /// "Immediately and only once receive 5 credits and 2 ore." (`artifact_09`)
    CreditsFiveAndOreTwo,
    /// "Immediately and only once receive 3 victory points, plus 1 additional victory point for
    /// each distinct planet type you have colonized." (`artifact_11`) Reuses
    /// `FinalScoringCondition::MostPlanetTypes`'s counting logic via `ScoringEngine`, since it's
    /// exactly the same "distinct colonized planet types" count used there.
    FlatVp3PlusVpPerColonizedPlanetType,
    /// "Immediately and only once receive 7 victory points." (`artifact_12`) Per the user's
    /// direct description this token's full text also grants a coordinate-less Asteroid mine for
    /// every scoring/objective purpose. It consumes no Gaiaformer or physical Mine and belongs to
    /// no sector or federation.
    FlatVp7PlusAsteroidMine,
    /// "Immediately and only once receive 3 victory points for each research area in which you
    /// have reached at least level 3." (`artifact_13`)
    VpPerResearchTrackAtLevel3Plus,
    /// "Copy the effect of a Federation Token you own." (`artifact_10`) Reuses the same
    /// federation-token-effect-replay mechanism as the Twilight spaceship's "Score a Federation
    /// Token Again" action space (`validate_owned_federation_token_effect`/
    /// `apply_owned_federation_token_effect`) — see `ExamineArtifact`'s
    /// `copy_federation_token_kind`/`bonus_*` fields.
    CopyFederationEffect,
}

/// Maps a drawn Artifact to its effect — all 13 ids correspond directly to the confirmed photos
/// in `gaia-frontend/src/assets/artifacts/artifact_01` through `_13`.
fn artifact_effect(id: ArtifactId) -> ArtifactEffect {
    match id.0 {
        1 => ArtifactEffect::VpPerDeepSpaceSector,
        2 => ArtifactEffect::PowerToBowl3Two,
        3 => ArtifactEffect::OreAndKnowledgeOne,
        4 => ArtifactEffect::VpPerGaiaProjectLevel,
        5 => ArtifactEffect::VpPerScienceLevel,
        6 => ArtifactEffect::CreditsThreeAndOreThree,
        7 => ArtifactEffect::KnowledgeThreeAndQicOne,
        8 => ArtifactEffect::FlatVp7PlusProtoPlanetMine,
        9 => ArtifactEffect::CreditsFiveAndOreTwo,
        10 => ArtifactEffect::CopyFederationEffect,
        11 => ArtifactEffect::FlatVp3PlusVpPerColonizedPlanetType,
        12 => ArtifactEffect::FlatVp7PlusAsteroidMine,
        13 => ArtifactEffect::VpPerResearchTrackAtLevel3Plus,
        _ => ArtifactEffect::FlatVp7, // fallback for any uncatalogued id
    }
}

/// Count of research tracks in which `player_id` has reached at least level 3 — used by
/// `ArtifactEffect::VpPerResearchTrackAtLevel3Plus`.
fn count_research_tracks_at_level_3_plus(state: &GameState, player_id: PlayerId) -> usize {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    let t = &player.research_tracks;
    [
        t.terraforming,
        t.navigation,
        t.ai,
        t.gaia,
        t.economy,
        t.science,
    ]
    .into_iter()
    .filter(|&level| level >= 3)
    .count()
}

/// Count of distinct Deep Space sectors in which `player_id` has colonized at least 1 planet —
/// used by `ArtifactEffect::VpPerDeepSpaceSector`.
fn count_colonized_deep_space_sectors(state: &GameState, player_id: PlayerId) -> usize {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    let mut sector_ids: std::collections::HashSet<u8> = std::collections::HashSet::new();
    for structure in &player.structures {
        if let Some(sector_id) = MapEngine::sector_id_at(&state.board, structure.hex) {
            if crate::data::category_for_sector(sector_id) == crate::data::SectorCategory::DeepSpace
            {
                sector_ids.insert(sector_id);
            }
        }
    }
    sector_ids.len()
}

fn apply_examine_artifact(
    state: &mut GameState,
    player_id: PlayerId,
    artifact: ArtifactId,
    copy_federation_token_kind: Option<u8>,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<TechTile>,
    bonus_research_track: Option<ResearchTrack>,
) -> Vec<GameEvent> {
    let mut events = Vec::new();

    if let Some(player) = state.player_mut(player_id) {
        let mut remaining = ARTIFACT_EXAMINE_POWER_COST;
        let from_bowl1 = remaining.min(player.resources.power.bowl1);
        player.resources.power.bowl1 -= from_bowl1;
        remaining -= from_bowl1;
        let from_bowl2 = remaining.min(player.resources.power.bowl2);
        player.resources.power.bowl2 -= from_bowl2;
        remaining -= from_bowl2;
        let from_bowl3 = remaining.min(player.resources.power.bowl3);
        player.resources.power.bowl3 -= from_bowl3;
        if player.faction == Some(FactionId::Taklons) {
            move_brainstone_to_gaia(&mut player.resources.power);
        }
    }

    let taken = state
        .spaceship_boards
        .iter_mut()
        .find(|b| b.id == SpaceshipId::Twilight)
        .and_then(|b| {
            let index = b.artifact_pool.iter().position(|&a| a == artifact)?;
            Some(b.artifact_pool.remove(index))
        });

    if let Some(artifact) = taken {
        // Computed against `&state` before the mutable borrow below, since these all need read
        // access to the board/player before `player_mut` takes an exclusive borrow.
        let deep_space_sectors = count_colonized_deep_space_sectors(state, player_id);
        let colonized_planet_types = ScoringEngine::final_scoring_metric(
            state,
            player_id,
            &FinalScoringCondition::MostPlanetTypes,
        );
        let tracks_at_level_3_plus = count_research_tracks_at_level_3_plus(state, player_id);
        let effect = artifact_effect(artifact);
        let artifact_mine = match effect {
            ArtifactEffect::FlatVp7PlusProtoPlanetMine => Some(PlanetType::ProtoPlanet),
            ArtifactEffect::FlatVp7PlusAsteroidMine => Some(PlanetType::Asteroid),
            _ => None,
        };
        let is_new_planet_type = artifact_mine
            .is_some_and(|planet_type| !has_colonized_planet_type(state, player_id, planet_type));

        if effect == ArtifactEffect::CopyFederationEffect {
            if let Some(token_kind) = copy_federation_token_kind {
                events.extend(apply_owned_federation_token_effect(
                    state,
                    player_id,
                    token_kind,
                    bonus_build_coord,
                    bonus_tech_tile,
                    bonus_research_track,
                ));
            }
        } else if let Some(player) = state.player_mut(player_id) {
            match effect {
                ArtifactEffect::VpPerDeepSpaceSector => {
                    player.vp = player.vp.saturating_add(deep_space_sectors as i32 * 2);
                }
                ArtifactEffect::PowerToBowl3Two => {
                    player.resources.power.bowl3 = player.resources.power.bowl3.saturating_add(2);
                }
                ArtifactEffect::OreAndKnowledgeOne => {
                    add_resource(player, ResourceKind::Ore, 1);
                    add_resource(player, ResourceKind::Knowledge, 1);
                }
                ArtifactEffect::VpPerGaiaProjectLevel => {
                    let vp = i32::from(player.research_tracks.gaia) * 3;
                    player.vp = player.vp.saturating_add(vp);
                }
                ArtifactEffect::VpPerScienceLevel => {
                    let vp = i32::from(player.research_tracks.science) * 3;
                    player.vp = player.vp.saturating_add(vp);
                }
                ArtifactEffect::CreditsThreeAndOreThree => {
                    add_resource(player, ResourceKind::Credits, 3);
                    add_resource(player, ResourceKind::Ore, 3);
                }
                ArtifactEffect::KnowledgeThreeAndQicOne => {
                    add_resource(player, ResourceKind::Knowledge, 3);
                    add_resource(player, ResourceKind::Qic, 1);
                }
                ArtifactEffect::FlatVp7 => {
                    player.vp = player.vp.saturating_add(7);
                }
                ArtifactEffect::FlatVp7PlusProtoPlanetMine => {
                    player.vp = player.vp.saturating_add(7);
                    if !player.artifact_mines.contains(&PlanetType::ProtoPlanet) {
                        player.artifact_mines.push(PlanetType::ProtoPlanet);
                    }
                }
                ArtifactEffect::CreditsFiveAndOreTwo => {
                    add_resource(player, ResourceKind::Credits, 5);
                    add_resource(player, ResourceKind::Ore, 2);
                }
                ArtifactEffect::FlatVp3PlusVpPerColonizedPlanetType => {
                    let vp = 3 + colonized_planet_types as i32;
                    player.vp = player.vp.saturating_add(vp);
                }
                ArtifactEffect::FlatVp7PlusAsteroidMine => {
                    player.vp = player.vp.saturating_add(7);
                    if !player.artifact_mines.contains(&PlanetType::Asteroid) {
                        player.artifact_mines.push(PlanetType::Asteroid);
                    }
                }
                ArtifactEffect::VpPerResearchTrackAtLevel3Plus => {
                    let vp = tracks_at_level_3_plus as i32 * 3;
                    player.vp = player.vp.saturating_add(vp);
                }
                ArtifactEffect::CopyFederationEffect => unreachable!("handled above"),
            }
        }
        if artifact_mine.is_some() {
            events.extend(check_round_tile_bonus(
                state,
                player_id,
                &RoundCondition::BuildMine,
                1,
            ));
            events.extend(check_tech_tile_event_bonus(
                state,
                player_id,
                &RoundCondition::BuildMine,
                1,
            ));
            if is_new_planet_type {
                events.extend(check_round_tile_bonus(
                    state,
                    player_id,
                    &RoundCondition::BuildMineOnNewPlanetType,
                    1,
                ));
            }
        }
        events.push(GameEvent::ArtifactExamined {
            player: player_id,
            artifact,
        });
    }

    advance_turn(state);
    events
}

/// Appendix II ("New Action Spaces") — a Credit action unlocked once the player has explored
/// T F Mars specifically: "the same as the power action 'Take 1 free terraforming step' from
/// the base game, except it costs 3 credits." Shared, once-per-round exclusivity is tracked in
/// `used_spaceship_actions` and reset during Clean-up. Originally modeled
/// as "requires any explored spaceship" since the specific ship wasn't identified yet; confirmed
/// directly against T F Mars' own board image to be its third action slot, alongside
/// `TFMarsTechBonus` and `TFMarsGaiaFormation`.
fn validate_spaceship_credit_terraform(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let tf_mars = spaceship_id_to_ship_id(SpaceshipId::TFMars);
    if !player.explored_ships.contains(&tf_mars) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the T F Mars spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_CREDIT_TERRAFORM)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if player.resources.credits < SPACESHIP_CREDIT_TERRAFORM_COST {
        return Err(RuleError::InsufficientResources(ResourceKind::Credits));
    }

    validate_build_impl(state, player_id, coord, 1, 0, false, 0)
}

fn apply_spaceship_credit_terraform(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_CREDIT_TERRAFORM);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.credits = player
            .resources
            .credits
            .saturating_sub(SPACESHIP_CREDIT_TERRAFORM_COST);
    }
    apply_build_impl(state, player_id, coord, 1, 0, false, 0)
}

/// Appendix II action space id for `TwilightFreeResearchLab` in `used_spaceship_actions`.
const SPACESHIP_ACTION_TWILIGHT_RESEARCH_LAB: u8 = 2;
/// Activation cost for `TwilightFreeResearchLab` — the granted upgrade itself has no
/// *additional* cost, but the action space still costs power + ore to trigger (confirmed
/// directly: every Appendix II action space except the QIC-cost ones shows a power/ore/
/// knowledge cost above it; Rebellion's parallel "free Mine -> Trading Station" space costs
/// 3 power + 1 ore, so by the same pattern Twilight's Trading Station -> Research Lab space
/// costs 3 power + 2 ore — the two "3+1 / 3+2 ore" icon variants seen on the Appendix II
/// rulebook page).
const TWILIGHT_RESEARCH_LAB_POWER_COST: u8 = 3;
const TWILIGHT_RESEARCH_LAB_ORE_COST: u8 = 2;

fn validate_twilight_free_research_lab(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let twilight = spaceship_id_to_ship_id(SpaceshipId::Twilight);
    if !player.explored_ships.contains(&twilight) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Twilight spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_TWILIGHT_RESEARCH_LAB)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if spendable_power_value(&player.resources.power) < TWILIGHT_RESEARCH_LAB_POWER_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }
    if player.resources.ore < TWILIGHT_RESEARCH_LAB_ORE_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Ore,
        ));
    }

    validate_upgrade_impl(
        state,
        player_id,
        coord,
        StructureType::ResearchLab,
        true,
        None,
    )
}

fn apply_twilight_free_research_lab(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_TWILIGHT_RESEARCH_LAB);
    if let Some(player) = state.player_mut(player_id) {
        spend_power(
            &mut player.resources.power,
            TWILIGHT_RESEARCH_LAB_POWER_COST,
        );
        player.resources.ore = player
            .resources
            .ore
            .saturating_sub(TWILIGHT_RESEARCH_LAB_ORE_COST);
    }
    apply_upgrade_impl(
        state,
        player_id,
        coord,
        StructureType::ResearchLab,
        true,
        None,
    )
}

const SPACESHIP_ACTION_TWILIGHT_REPLAY_FEDERATION: u8 = 10;
const SPACESHIP_ACTION_TWILIGHT_RANGE: u8 = 11;
const TWILIGHT_REPLAY_FEDERATION_QIC_COST: u8 = 3;
const TWILIGHT_RANGE_KNOWLEDGE_COST: u8 = 1;
const TWILIGHT_RANGE_BONUS: u8 = 3;

fn validate_twilight_access(
    state: &GameState,
    player_id: PlayerId,
    action_id: u8,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let twilight = spaceship_id_to_ship_id(SpaceshipId::Twilight);
    if !player.explored_ships.contains(&twilight) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Twilight spaceship".to_string(),
        ));
    }
    if state.used_spaceship_actions.contains(&action_id) {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    Ok(())
}

/// Shared by `TwilightReplayFederationToken` and Artifact 10's "Copy the effect of a
/// Federation Token you own" (`ArtifactEffect::CopyFederationEffect`) — both actions replay one
/// Federation token effect the player already holds, without gaining or consuming another
/// token. Validates ownership of `token_kind` and any follow-up choice its effect needs (a
/// target hex, or a Tech tile + research track) — the direct-reward kinds need no follow-up.
fn validate_owned_federation_token_effect(
    state: &GameState,
    player_id: PlayerId,
    token_kind: u8,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<&TechTile>,
    bonus_research_track: Option<ResearchTrack>,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if !player
        .federation_tokens
        .iter()
        .any(|token| token.0 == token_kind)
    {
        return Err(RuleError::ActionNotAllowed(
            "player does not own that Federation token".to_string(),
        ));
    }

    match federation_token_kind(token_kind) {
        FederationTokenKind::LostFleetFreeBuildUnlimitedRange => {
            let coord = bonus_build_coord.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "this Federation token requires a target hex".to_string(),
                )
            })?;
            validate_build_impl(state, player_id, coord, 0, 0, true, 0)?;
        }
        FederationTokenKind::LostFleetFreeBuild3Steps => {
            let coord = bonus_build_coord.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "this Federation token requires a target hex".to_string(),
                )
            })?;
            validate_build_impl(state, player_id, coord, 3, 0, false, 0)?;
        }
        FederationTokenKind::LostFleetTechTileOfChoice => {
            let tile = bonus_tech_tile.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "this Federation token requires choosing a Tech tile".to_string(),
                )
            })?;
            if !state.research_board.tech_tiles.contains(tile) {
                return Err(RuleError::ActionNotAllowed(
                    "that Tech tile isn't available".to_string(),
                ));
            }
            let track = bonus_research_track.ok_or_else(|| {
                RuleError::ActionNotAllowed(
                    "gaining a Tech tile requires choosing a research track".to_string(),
                )
            })?;
            validate_free_research_advance(state, player_id, track)?;
        }
        _ => {}
    }
    Ok(())
}

/// Apply half of `validate_owned_federation_token_effect` — does not call `advance_turn`, since
/// callers differ on when the turn ends (Artifact 10 always ends it once at the end of
/// `apply_examine_artifact`; Twilight's own replay action ends it itself).
fn apply_owned_federation_token_effect(
    state: &mut GameState,
    player_id: PlayerId,
    token_kind: u8,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<TechTile>,
    bonus_research_track: Option<ResearchTrack>,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    apply_federation_token_direct_reward(state, player_id, token_kind);

    match federation_token_kind(token_kind) {
        FederationTokenKind::LostFleetFreeBuildUnlimitedRange => {
            if let Some(coord) = bonus_build_coord {
                events.extend(apply_build_impl(state, player_id, coord, 0, 0, true, 0));
            }
        }
        FederationTokenKind::LostFleetFreeBuild3Steps => {
            if let Some(coord) = bonus_build_coord {
                events.extend(apply_build_impl(state, player_id, coord, 3, 0, false, 0));
            }
        }
        FederationTokenKind::LostFleetTechTileOfChoice => {
            if let (Some(tile), Some(track)) = (bonus_tech_tile, bonus_research_track) {
                if transfer_tech_tile_to_player(state, player_id, &tile) {
                    events.push(GameEvent::TechTileGained {
                        player: player_id,
                        tile,
                    });
                    events.extend(apply_free_research_advance(state, player_id, track));
                }
            }
        }
        _ => {}
    }
    events
}

fn validate_twilight_replay_federation_token(
    state: &GameState,
    player_id: PlayerId,
    token_kind: u8,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<&TechTile>,
    bonus_research_track: Option<ResearchTrack>,
) -> Result<(), RuleError> {
    validate_twilight_access(
        state,
        player_id,
        SPACESHIP_ACTION_TWILIGHT_REPLAY_FEDERATION,
    )?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.resources.qic < TWILIGHT_REPLAY_FEDERATION_QIC_COST {
        return Err(RuleError::InsufficientResources(ResourceKind::Qic));
    }
    validate_owned_federation_token_effect(
        state,
        player_id,
        token_kind,
        bonus_build_coord,
        bonus_tech_tile,
        bonus_research_track,
    )
}

fn apply_twilight_replay_federation_token(
    state: &mut GameState,
    player_id: PlayerId,
    token_kind: u8,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<TechTile>,
    bonus_research_track: Option<ResearchTrack>,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_TWILIGHT_REPLAY_FEDERATION);
    let mut events = Vec::new();
    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player
            .resources
            .qic
            .saturating_sub(TWILIGHT_REPLAY_FEDERATION_QIC_COST);
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta: ResourceDelta {
                qic: -(TWILIGHT_REPLAY_FEDERATION_QIC_COST as i8),
                ..ResourceDelta::zero()
            },
        });
    }
    events.extend(apply_owned_federation_token_effect(
        state,
        player_id,
        token_kind,
        bonus_build_coord,
        bonus_tech_tile,
        bonus_research_track,
    ));
    advance_turn(state);
    events
}

fn validate_twilight_range_common(state: &GameState, player_id: PlayerId) -> Result<(), RuleError> {
    validate_twilight_access(state, player_id, SPACESHIP_ACTION_TWILIGHT_RANGE)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.resources.knowledge < TWILIGHT_RANGE_KNOWLEDGE_COST {
        return Err(RuleError::InsufficientResources(ResourceKind::Knowledge));
    }
    Ok(())
}

fn validate_twilight_range_build(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_twilight_range_common(state, player_id)?;
    validate_build_impl(state, player_id, coord, 0, 0, false, TWILIGHT_RANGE_BONUS)
}

fn validate_twilight_range_gaia_formation(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_twilight_range_common(state, player_id)?;
    validate_gaia_formation_impl(state, player_id, coord, TWILIGHT_RANGE_BONUS)
}

fn validate_twilight_range_explore_spaceship(
    state: &GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Result<(), RuleError> {
    validate_twilight_range_common(state, player_id)?;
    validate_explore_spaceship_impl(state, player_id, ship, TWILIGHT_RANGE_BONUS)
}

fn apply_twilight_range_cost(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_TWILIGHT_RANGE);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.knowledge = player
            .resources
            .knowledge
            .saturating_sub(TWILIGHT_RANGE_KNOWLEDGE_COST);
    }
    vec![GameEvent::ResourceChanged {
        player: player_id,
        delta: ResourceDelta {
            knowledge: -(TWILIGHT_RANGE_KNOWLEDGE_COST as i8),
            ..ResourceDelta::zero()
        },
    }]
}

fn apply_twilight_range_build(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    let mut events = apply_twilight_range_cost(state, player_id);
    events.extend(apply_build_impl(
        state,
        player_id,
        coord,
        0,
        0,
        false,
        TWILIGHT_RANGE_BONUS,
    ));
    events
}

fn apply_twilight_range_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    let mut events = apply_twilight_range_cost(state, player_id);
    events.extend(apply_gaia_formation_impl(
        state,
        player_id,
        coord,
        TWILIGHT_RANGE_BONUS,
    ));
    events
}

fn apply_twilight_range_explore_spaceship(
    state: &mut GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Vec<GameEvent> {
    let mut events = apply_twilight_range_cost(state, player_id);
    events.extend(apply_explore_spaceship_impl(
        state,
        player_id,
        ship,
        TWILIGHT_RANGE_BONUS,
    ));
    events
}

/// Appendix II action space ids for Rebellion's first two action modes in
/// `used_spaceship_actions`.
const SPACESHIP_ACTION_REBELLION_TRADING_STATION: u8 = 3;
const SPACESHIP_ACTION_REBELLION_CREDITS_AND_QIC: u8 = 4;
const REBELLION_TRADING_STATION_POWER_COST: u8 = 3;
const REBELLION_TRADING_STATION_ORE_COST: u8 = 1;
const REBELLION_CREDITS_AND_QIC_KNOWLEDGE_COST: u8 = 2;

fn validate_rebellion_free_trading_station(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let rebellion = spaceship_id_to_ship_id(SpaceshipId::Rebellion);
    if !player.explored_ships.contains(&rebellion) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Rebellion spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_REBELLION_TRADING_STATION)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if spendable_power_value(&player.resources.power) < REBELLION_TRADING_STATION_POWER_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }
    if player.resources.ore < REBELLION_TRADING_STATION_ORE_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Ore,
        ));
    }

    validate_upgrade_impl(
        state,
        player_id,
        coord,
        StructureType::TradingStation,
        true,
        None,
    )
}

fn apply_rebellion_free_trading_station(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_REBELLION_TRADING_STATION);
    if let Some(player) = state.player_mut(player_id) {
        spend_power(
            &mut player.resources.power,
            REBELLION_TRADING_STATION_POWER_COST,
        );
        player.resources.ore = player
            .resources
            .ore
            .saturating_sub(REBELLION_TRADING_STATION_ORE_COST);
    }
    apply_upgrade_impl(
        state,
        player_id,
        coord,
        StructureType::TradingStation,
        true,
        None,
    )
}

fn validate_rebellion_credits_and_qic(
    state: &GameState,
    player_id: PlayerId,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let rebellion = spaceship_id_to_ship_id(SpaceshipId::Rebellion);
    if !player.explored_ships.contains(&rebellion) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Rebellion spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_REBELLION_CREDITS_AND_QIC)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if player.resources.knowledge < REBELLION_CREDITS_AND_QIC_KNOWLEDGE_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Knowledge,
        ));
    }

    Ok(())
}

fn apply_rebellion_credits_and_qic(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    let mut events = Vec::new();
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_REBELLION_CREDITS_AND_QIC);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.knowledge = player
            .resources
            .knowledge
            .saturating_sub(REBELLION_CREDITS_AND_QIC_KNOWLEDGE_COST);
        add_resource(player, ResourceKind::Credits, 2);
        let qic_gain_kind = add_resource(player, ResourceKind::Qic, 1);
        let mut delta = ResourceDelta {
            credits: 2,
            knowledge: -(REBELLION_CREDITS_AND_QIC_KNOWLEDGE_COST as i8),
            ..ResourceDelta::zero()
        };
        match qic_gain_kind {
            ResourceKind::Ore => delta.ore = 1,
            ResourceKind::Qic => delta.qic = 1,
            _ => {}
        }
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });
    }
    advance_turn(state);
    events
}

const SPACESHIP_ACTION_REBELLION_GAIN_TECH_TILE: u8 = 12;
const REBELLION_GAIN_TECH_TILE_QIC_COST: u8 = 3;

fn validate_rebellion_gain_tech_tile(
    state: &GameState,
    player_id: PlayerId,
    tile: &TechTile,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let rebellion = spaceship_id_to_ship_id(SpaceshipId::Rebellion);
    if !player.explored_ships.contains(&rebellion) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Rebellion spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_REBELLION_GAIN_TECH_TILE)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if player.resources.qic < REBELLION_GAIN_TECH_TILE_QIC_COST {
        return Err(RuleError::InsufficientResources(ResourceKind::Qic));
    }
    if !state.research_board.tech_tiles.contains(tile) {
        return Err(RuleError::ActionNotAllowed(
            "that Tech tile isn't available".to_string(),
        ));
    }
    validate_free_research_advance(state, player_id, track)
}

fn apply_rebellion_gain_tech_tile(
    state: &mut GameState,
    player_id: PlayerId,
    tile: TechTile,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_REBELLION_GAIN_TECH_TILE);
    let mut events = Vec::new();
    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player
            .resources
            .qic
            .saturating_sub(REBELLION_GAIN_TECH_TILE_QIC_COST);
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta: ResourceDelta {
                qic: -(REBELLION_GAIN_TECH_TILE_QIC_COST as i8),
                ..ResourceDelta::zero()
            },
        });
    }
    if transfer_tech_tile_to_player(state, player_id, &tile) {
        events.push(GameEvent::TechTileGained {
            player: player_id,
            tile,
        });
        events.extend(apply_free_research_advance(state, player_id, track));
    }
    advance_turn(state);
    events
}

/// Appendix II action space ids for T F Mars' and Eclipse's implemented actions in
/// `used_spaceship_actions`.
const SPACESHIP_ACTION_TFMARS_TECH_BONUS: u8 = 5;
const SPACESHIP_ACTION_TFMARS_GAIA_FORMATION: u8 = 6;
const SPACESHIP_ACTION_ECLIPSE_PLANET_TYPE_BONUS: u8 = 7;
const SPACESHIP_ACTION_ECLIPSE_RESEARCH_BOOST: u8 = 8;
const SPACESHIP_ACTION_ECLIPSE_ASTEROID_MINE: u8 = 9;
const TFMARS_TECH_BONUS_QIC_COST: u8 = 2;
const TFMARS_GAIA_FORMATION_POWER_COST: u8 = 2;
const ECLIPSE_PLANET_TYPE_BONUS_QIC_COST: u8 = 2;
const ECLIPSE_RESEARCH_BOOST_POWER_COST: u8 = 3;
const ECLIPSE_RESEARCH_BOOST_KNOWLEDGE_COST: u8 = 2;
const ECLIPSE_ASTEROID_MINE_CREDITS_COST: u8 = 6;

fn validate_tfmars_tech_bonus(state: &GameState, player_id: PlayerId) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let tf_mars = spaceship_id_to_ship_id(SpaceshipId::TFMars);
    if !player.explored_ships.contains(&tf_mars) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the T F Mars spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_TFMARS_TECH_BONUS)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if player.resources.qic < TFMARS_TECH_BONUS_QIC_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Qic,
        ));
    }

    Ok(())
}

fn apply_tfmars_tech_bonus(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    let mut events = Vec::new();
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_TFMARS_TECH_BONUS);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player
            .resources
            .qic
            .saturating_sub(TFMARS_TECH_BONUS_QIC_COST);
        let vp = 2 + player.tech_tiles.len() as i32;
        player.vp = player.vp.saturating_add(vp);
        let delta = ResourceDelta {
            qic: -(TFMARS_TECH_BONUS_QIC_COST as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });
    }
    advance_turn(state);
    events
}

/// Flat-cost, once-per-round alternative to the normal `GaiaFormation` action: pays 2 power from
/// bowl3, moves no power into the Gaia area, and immediately transforms the target. The
/// Gaiaformer therefore remains available for reuse during the same round.
fn validate_tfmars_gaia_formation(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let tf_mars = spaceship_id_to_ship_id(SpaceshipId::TFMars);
    if !player.explored_ships.contains(&tf_mars) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the T F Mars spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_TFMARS_GAIA_FORMATION)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if spendable_power_value(&player.resources.power) < TFMARS_GAIA_FORMATION_POWER_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }
    validate_immediate_gaia_formation_impl(state, player_id, coord, 0)
}

fn apply_tfmars_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_TFMARS_GAIA_FORMATION);
    if let Some(player) = state.player_mut(player_id) {
        spend_power(
            &mut player.resources.power,
            TFMARS_GAIA_FORMATION_POWER_COST,
        );
    }
    apply_immediate_gaia_formation_impl(state, player_id, coord, 0)
}

fn validate_eclipse_planet_type_bonus(
    state: &GameState,
    player_id: PlayerId,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let eclipse = spaceship_id_to_ship_id(SpaceshipId::Eclipse);
    if !player.explored_ships.contains(&eclipse) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Eclipse spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_ECLIPSE_PLANET_TYPE_BONUS)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if player.resources.qic < ECLIPSE_PLANET_TYPE_BONUS_QIC_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Qic,
        ));
    }

    Ok(())
}

fn apply_eclipse_planet_type_bonus(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    let mut events = Vec::new();
    // Computed against `&state` before `player_mut` takes an exclusive borrow.
    let colonized_planet_types = ScoringEngine::final_scoring_metric(
        state,
        player_id,
        &FinalScoringCondition::MostPlanetTypes,
    );

    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_ECLIPSE_PLANET_TYPE_BONUS);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.qic = player
            .resources
            .qic
            .saturating_sub(ECLIPSE_PLANET_TYPE_BONUS_QIC_COST);
        let vp = 2 + colonized_planet_types as i32;
        player.vp = player.vp.saturating_add(vp);
        let delta = ResourceDelta {
            qic: -(ECLIPSE_PLANET_TYPE_BONUS_QIC_COST as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });
    }
    advance_turn(state);
    events
}

/// Alternative to the normal `ResearchAdvance` action: costs 3 power + 2 knowledge instead of
/// the base game's flat 4 knowledge (`RESEARCH_KNOWLEDGE_COST`), but otherwise behaves
/// identically (track-max check, `ResearchAdvanced` event, round tile bonus check).
fn validate_eclipse_research_boost(
    state: &GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let eclipse = spaceship_id_to_ship_id(SpaceshipId::Eclipse);
    if !player.explored_ships.contains(&eclipse) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Eclipse spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_ECLIPSE_RESEARCH_BOOST)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if spendable_power_value(&player.resources.power) < ECLIPSE_RESEARCH_BOOST_POWER_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Power,
        ));
    }
    if player.resources.knowledge < ECLIPSE_RESEARCH_BOOST_KNOWLEDGE_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Knowledge,
        ));
    }
    validate_research_track_advance(state, player_id, player, track)?;

    Ok(())
}

fn apply_eclipse_research_boost(
    state: &mut GameState,
    player_id: PlayerId,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    let mut events = Vec::new();
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_ECLIPSE_RESEARCH_BOOST);

    if let Some(player) = state.player_mut(player_id) {
        spend_power(
            &mut player.resources.power,
            ECLIPSE_RESEARCH_BOOST_POWER_COST,
        );
        player.resources.knowledge = player
            .resources
            .knowledge
            .saturating_sub(ECLIPSE_RESEARCH_BOOST_KNOWLEDGE_COST);
        let delta = ResourceDelta {
            knowledge: -(ECLIPSE_RESEARCH_BOOST_KNOWLEDGE_COST as i8),
            ..ResourceDelta::zero()
        };
        events.push(GameEvent::ResourceChanged {
            player: player_id,
            delta,
        });
    } else {
        return events;
    };
    let new_level = advance_research_track_level(state, player_id, track);
    events.push(GameEvent::ResearchAdvanced {
        player: player_id,
        track,
        level: new_level,
    });
    events.extend(check_round_tile_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
        1,
    ));
    events.extend(check_tech_tile_event_bonus(
        state,
        player_id,
        &RoundCondition::ResearchAdvance,
        1,
    ));
    advance_turn(state);
    events
}

/// Alternative to the normal `Build` action's Asteroid branch: costs 6 credits (activation fee,
/// deducted separately) instead of the Asteroid branch's usual zero ore/credit cost, but
/// otherwise reuses it as-is (Gaiaformer availability, reachability extendable with QIC).
/// Restricted to Asteroid targets specifically — `validate_build_impl`/`apply_build_impl` would
/// otherwise accept any buildable planet type.
fn validate_eclipse_asteroid_mine(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;

    let eclipse = spaceship_id_to_ship_id(SpaceshipId::Eclipse);
    if !player.explored_ships.contains(&eclipse) {
        return Err(RuleError::ActionNotAllowed(
            "requires an Exploration Shuttle on the Eclipse spaceship".to_string(),
        ));
    }
    if state
        .used_spaceship_actions
        .contains(&SPACESHIP_ACTION_ECLIPSE_ASTEROID_MINE)
    {
        return Err(RuleError::ActionNotAllowed(
            "this spaceship action space has already been used this round".to_string(),
        ));
    }
    if player.resources.credits < ECLIPSE_ASTEROID_MINE_CREDITS_COST {
        return Err(RuleError::InsufficientResources(
            crate::game_state::ResourceKind::Credits,
        ));
    }
    let hex = state
        .board
        .hexes
        .get(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    let planet = hex.planet.as_ref().ok_or(RuleError::InvalidTarget(coord))?;
    if planet.planet_type != PlanetType::Asteroid {
        return Err(RuleError::InvalidTarget(coord));
    }

    validate_build_impl(state, player_id, coord, 0, 0, false, 0)
}

fn apply_eclipse_asteroid_mine(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    state
        .used_spaceship_actions
        .push(SPACESHIP_ACTION_ECLIPSE_ASTEROID_MINE);
    if let Some(player) = state.player_mut(player_id) {
        player.resources.credits = player
            .resources
            .credits
            .saturating_sub(ECLIPSE_ASTEROID_MINE_CREDITS_COST);
    }
    apply_build_impl(state, player_id, coord, 0, 0, false, 0)
}

// ── Lost Fleet Exploration Board special actions (Gleens / Space Giants) ────────

/// `GP_Exp_Rule_EN_V1_Web.pdf` p.10: "The Space Giants and the Gleens each have a special
/// action on their Exploration board that they can use once per round." Distinct from the
/// Space Giants' Planetary Institute one-time tech-tile ability (`GameAction::SpecialAction`,
/// `SpaceGiantsAbility::special_action`) — this is a per-round action available to every
/// player of that faction, gated only by faction identity, not by any built structure.
const GLEENS_SPECIAL_ACTION_RANGE_BONUS: u8 = 2;
const SPACE_GIANTS_SPECIAL_ACTION_FREE_TERRAFORM_STEPS: u8 = 2;

fn validate_gleens_special_common(state: &GameState, player_id: PlayerId) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.faction != Some(FactionId::Gleens) {
        return Err(RuleError::ActionNotAllowed(
            "only the Gleens have this Exploration Board special action".to_string(),
        ));
    }
    if player.gleens_special_action_used_this_round {
        return Err(RuleError::ActionNotAllowed(
            "the Gleens' Exploration Board special action has already been used this round"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_gleens_build_mine(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_gleens_special_common(state, player_id)?;
    validate_build_impl(
        state,
        player_id,
        coord,
        0,
        0,
        false,
        GLEENS_SPECIAL_ACTION_RANGE_BONUS,
    )
}

fn validate_gleens_gaia_formation(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    validate_gleens_special_common(state, player_id)?;
    validate_gaia_formation_impl(state, player_id, coord, GLEENS_SPECIAL_ACTION_RANGE_BONUS)
}

fn validate_gleens_explore_spaceship(
    state: &GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Result<(), RuleError> {
    validate_gleens_special_common(state, player_id)?;
    validate_explore_spaceship_impl(state, player_id, ship, GLEENS_SPECIAL_ACTION_RANGE_BONUS)
}

fn mark_gleens_special_action_used(state: &mut GameState, player_id: PlayerId) {
    if let Some(player) = state.player_mut(player_id) {
        player.gleens_special_action_used_this_round = true;
    }
}

fn apply_gleens_build_mine(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    mark_gleens_special_action_used(state, player_id);
    apply_build_impl(
        state,
        player_id,
        coord,
        0,
        0,
        false,
        GLEENS_SPECIAL_ACTION_RANGE_BONUS,
    )
}

fn apply_gleens_gaia_formation(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    mark_gleens_special_action_used(state, player_id);
    apply_gaia_formation_impl(state, player_id, coord, GLEENS_SPECIAL_ACTION_RANGE_BONUS)
}

fn apply_gleens_explore_spaceship(
    state: &mut GameState,
    player_id: PlayerId,
    ship: SpaceshipId,
) -> Vec<GameEvent> {
    mark_gleens_special_action_used(state, player_id);
    apply_explore_spaceship_impl(state, player_id, ship, GLEENS_SPECIAL_ACTION_RANGE_BONUS)
}

fn validate_space_giants_build_mine(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<(), RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.faction != Some(FactionId::SpaceGiants) {
        return Err(RuleError::ActionNotAllowed(
            "only the Space Giants have this Exploration Board special action".to_string(),
        ));
    }
    if player.space_giants_special_action_used_this_round {
        return Err(RuleError::ActionNotAllowed(
            "the Space Giants' Exploration Board special action has already been used this round"
                .to_string(),
        ));
    }
    validate_build_impl(
        state,
        player_id,
        coord,
        SPACE_GIANTS_SPECIAL_ACTION_FREE_TERRAFORM_STEPS,
        0,
        false,
        0,
    )
}

fn apply_space_giants_build_mine(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Vec<GameEvent> {
    if let Some(player) = state.player_mut(player_id) {
        player.space_giants_special_action_used_this_round = true;
    }
    apply_build_impl(
        state,
        player_id,
        coord,
        SPACE_GIANTS_SPECIAL_ACTION_FREE_TERRAFORM_STEPS,
        0,
        false,
        0,
    )
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
    let (mut kind, amount) = data
        .and_then(|d| d.academy_qic_action.as_ref())
        .and_then(|bonus| Some((bonus.resource_kind()?, bonus.amount)))
        .unwrap_or((ResourceKind::Qic, 1));

    if let Some(player) = state.player_mut(player_id) {
        kind = add_resource(player, kind, amount);
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

    // Advanced tile 16: "from now on, whenever you take a QIC action, score 4 VP" — this
    // engine's closest analog to the base-board's dedicated QIC action is Academy(Qic)'s
    // passive action (see `tech_tile_event_vp_per_unit`'s doc comment for why `RoundCondition`
    // doesn't cover it).
    if state
        .player(player_id)
        .is_some_and(|player| player.advanced_tech_tiles.iter().any(|t| t.0 == 16))
    {
        events.extend(grant_vp(
            state,
            player_id,
            4,
            VpReason::TechTile { tile_id: 16 },
        ));
    }

    advance_turn(state);
    events
}

// ── Free actions ──────────────────────────────────────────────────────────────

/// Base cost for a free action. "Power" normally means bowl3, the only
/// spendable bowl; `BurnPower` and Gaiaformer movement use dedicated paths.
/// Power-token destination variants are likewise applied explicitly below.
fn free_action_cost(kind: &FreeActionKind) -> (ResourceKind, u8) {
    match kind {
        // BurnPower has two different bowl2 outcomes and is handled by the
        // dedicated validation/application branches below.
        FreeActionKind::BurnPower => (ResourceKind::Power, 0),
        FreeActionKind::CreditsToQic => (ResourceKind::Credits, 4),
        FreeActionKind::CreditsToOre => (ResourceKind::Credits, 3),
        FreeActionKind::CreditsToKnowledge => (ResourceKind::Credits, 4),
        FreeActionKind::GaiaformerToQic => (ResourceKind::Qic, 0),
        FreeActionKind::PowerToGaiaKnowledge => (ResourceKind::Power, 1),
        FreeActionKind::OreToPowerBowl3 => (ResourceKind::Ore, 1),
        FreeActionKind::PowerToQic => (ResourceKind::Power, 4),
        FreeActionKind::PowerToOre => (ResourceKind::Power, 3),
        FreeActionKind::QicToOre => (ResourceKind::Qic, 1),
        FreeActionKind::PowerToKnowledge => (ResourceKind::Power, 4),
        FreeActionKind::PowerToCredit => (ResourceKind::Power, 1),
        FreeActionKind::KnowledgeToCredit => (ResourceKind::Knowledge, 1),
        FreeActionKind::OreToCredit => (ResourceKind::Ore, 1),
        FreeActionKind::OreToPower => (ResourceKind::Ore, 1),
    }
}

/// `(resource gained, amount)` for a free action — meaningless for
/// `OreToPower`, whose gain `apply_free_action` handles directly.
fn free_action_gain(kind: &FreeActionKind) -> (ResourceKind, u8) {
    match kind {
        FreeActionKind::BurnPower => (ResourceKind::Power, 0),
        FreeActionKind::CreditsToQic => (ResourceKind::Qic, 1),
        FreeActionKind::CreditsToOre => (ResourceKind::Ore, 1),
        FreeActionKind::CreditsToKnowledge => (ResourceKind::Knowledge, 1),
        FreeActionKind::GaiaformerToQic => (ResourceKind::Qic, 1),
        FreeActionKind::PowerToGaiaKnowledge => (ResourceKind::Knowledge, 1),
        FreeActionKind::OreToPowerBowl3 => (ResourceKind::Power, 0),
        FreeActionKind::PowerToQic => (ResourceKind::Qic, 1),
        FreeActionKind::PowerToOre => (ResourceKind::Ore, 1),
        FreeActionKind::QicToOre => (ResourceKind::Ore, 1),
        FreeActionKind::PowerToKnowledge => (ResourceKind::Knowledge, 1),
        FreeActionKind::PowerToCredit => (ResourceKind::Credits, 1),
        FreeActionKind::KnowledgeToCredit => (ResourceKind::Credits, 1),
        FreeActionKind::OreToCredit => (ResourceKind::Credits, 1),
        FreeActionKind::OreToPower => (ResourceKind::Power, 0), // unused; see apply_free_action
    }
}

fn validate_free_action(
    state: &GameState,
    player_id: PlayerId,
    kind: &FreeActionKind,
    count: u8,
) -> Result<(), RuleError> {
    if count == 0 || count > MAX_FREE_ACTION_COUNT {
        return Err(RuleError::ActionNotAllowed(
            "free-action count must be between 1 and 30".into(),
        ));
    }
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let faction = player.faction;
    let has_pi = player
        .structures
        .iter()
        .any(|structure| structure.kind == StructureType::PlanetaryInstitute);
    let faction_action_allowed = match kind {
        FreeActionKind::CreditsToQic
        | FreeActionKind::CreditsToOre
        | FreeActionKind::CreditsToKnowledge => {
            faction == Some(crate::game_state::FactionId::HadschHallas) && has_pi
        }
        FreeActionKind::GaiaformerToQic => faction == Some(crate::game_state::FactionId::BalTaks),
        FreeActionKind::PowerToGaiaKnowledge => {
            faction == Some(crate::game_state::FactionId::Nevlas)
        }
        FreeActionKind::OreToPowerBowl3 => faction == Some(crate::game_state::FactionId::Xenos),
        _ => true,
    };
    if !faction_action_allowed {
        return Err(RuleError::ActionNotAllowed(
            "free action is not available to this faction".into(),
        ));
    }
    if matches!(kind, FreeActionKind::GaiaformerToQic) {
        if player.gaiaformers_available() < count {
            return Err(RuleError::ActionNotAllowed(
                "not enough available Gaiaformers".into(),
            ));
        }
        return Ok(());
    }
    if matches!(kind, FreeActionKind::BurnPower) {
        let required = u16::from(count) * 2;
        let available = u16::from(player.resources.power.bowl2)
            + u16::from(player.resources.power.brainstone == Some(BrainstoneLocation::Area2));
        if available < required {
            return Err(RuleError::InsufficientResources(ResourceKind::Power));
        }
        return Ok(());
    }
    let (spend_kind, spend_amount) = free_action_cost(kind);
    let available = match spend_kind {
        ResourceKind::Ore => player.resources.ore,
        ResourceKind::Credits => player.resources.credits,
        ResourceKind::Knowledge => player.resources.knowledge,
        ResourceKind::Qic => player.resources.qic,
        ResourceKind::Power => spendable_power_value(&player.resources.power),
    };
    let total_cost = u16::from(spend_amount) * u16::from(count);
    if u16::from(available) < total_cost {
        return Err(RuleError::InsufficientResources(spend_kind));
    }
    Ok(())
}

/// Unlike every other action handler, this deliberately does **not** call
/// `advance_turn` — free actions (rulebook p.15) don't end the turn and may
/// be taken any number of times.
fn apply_free_action(
    state: &mut GameState,
    player_id: PlayerId,
    kind: FreeActionKind,
    count: u8,
) -> Vec<GameEvent> {
    let (spend_kind, spend_amount) = free_action_cost(&kind);
    let total_spend = spend_amount.saturating_mul(count);
    let mut delta = ResourceDelta::zero();
    if let Some(player) = state.player_mut(player_id) {
        if matches!(kind, FreeActionKind::BurnPower) {
            for _ in 0..count {
                if player.resources.power.brainstone == Some(BrainstoneLocation::Area2)
                    && player.resources.power.bowl2 > 0
                {
                    // Preserve the unique token: discard one normal token and
                    // move the Brainstone to Area III.
                    player.resources.power.bowl2 -= 1;
                    player.resources.power.brainstone = Some(BrainstoneLocation::Area3);
                } else {
                    player.resources.power.bowl2 = player.resources.power.bowl2.saturating_sub(2);
                    player.resources.power.bowl3 = player.resources.power.bowl3.saturating_add(1);
                }
            }
            if player.faction == Some(crate::game_state::FactionId::Itars) {
                player.resources.power.gaia_forming =
                    player.resources.power.gaia_forming.saturating_add(count);
            }
            return free_action_events(player_id, kind, count, delta);
        }
        if matches!(kind, FreeActionKind::GaiaformerToQic) {
            player.gaiaformers_in_gaia_area = player.gaiaformers_in_gaia_area.saturating_add(count);
            player.resources.qic = player.resources.qic.saturating_add(count);
            delta.qic += count as i8;
            return free_action_events(player_id, kind, count, delta);
        }
        match spend_kind {
            ResourceKind::Ore => {
                player.resources.ore = player.resources.ore.saturating_sub(total_spend);
                delta.ore -= total_spend as i8;
            }
            ResourceKind::Credits => {
                player.resources.credits = player.resources.credits.saturating_sub(total_spend);
                delta.credits -= total_spend as i8;
            }
            ResourceKind::Knowledge => {
                player.resources.knowledge = player.resources.knowledge.saturating_sub(total_spend);
                delta.knowledge -= total_spend as i8;
            }
            ResourceKind::Qic => {
                player.resources.qic = player.resources.qic.saturating_sub(total_spend);
                delta.qic -= total_spend as i8;
            }
            ResourceKind::Power => {
                spend_power(&mut player.resources.power, total_spend);
            }
        }

        if matches!(kind, FreeActionKind::OreToPower) {
            player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(count);
        } else if matches!(kind, FreeActionKind::OreToPowerBowl3) {
            player.resources.power.bowl3 = player.resources.power.bowl3.saturating_add(count);
        } else if matches!(kind, FreeActionKind::PowerToGaiaKnowledge) {
            player.resources.power.gaia_forming =
                player.resources.power.gaia_forming.saturating_add(count);
            player.resources.knowledge = player.resources.knowledge.saturating_add(count);
            delta.knowledge += count as i8;
        } else {
            let (gain_kind, gain_amount) = free_action_gain(&kind);
            let total_gain = gain_amount.saturating_mul(count);
            let actual_gain_kind = add_resource(player, gain_kind, total_gain);
            match actual_gain_kind {
                ResourceKind::Ore => delta.ore += total_gain as i8,
                ResourceKind::Credits => delta.credits += total_gain as i8,
                ResourceKind::Knowledge => delta.knowledge += total_gain as i8,
                ResourceKind::Qic => delta.qic += total_gain as i8,
                ResourceKind::Power => {}
            }
        }
    }
    free_action_events(player_id, kind, count, delta)
}

fn free_action_events(
    player_id: PlayerId,
    kind: FreeActionKind,
    count: u8,
    delta: ResourceDelta,
) -> Vec<GameEvent> {
    vec![
        GameEvent::FreeActionTaken {
            player: player_id,
            kind: kind.as_str().to_string(),
            count,
        },
        GameEvent::ResourceChanged {
            player: player_id,
            delta,
        },
    ]
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
    if state.round >= 6 && booster_id.is_some() {
        return Err(RuleError::ActionNotAllowed(
            "a new booster is not chosen in the final round".to_string(),
        ));
    }
    if state.round < 6 && player.booster.is_some() && booster_id.is_none() {
        return Err(RuleError::ActionNotAllowed(
            "choose an available booster before passing".to_string(),
        ));
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

    let old_booster = state
        .player(player_id)
        .and_then(|player| player.booster.clone());
    if let Some(booster) = &old_booster {
        let amount = round_booster_pass_vp(state, player_id, booster.0);
        if amount > 0 {
            if let Some(player) = state.player_mut(player_id) {
                player.vp += amount;
            }
            events.push(GameEvent::VpAwarded {
                player: player_id,
                amount,
                reason: VpReason::RoundBooster {
                    booster_id: booster.0,
                },
            });
        }
    }

    let new_booster = booster_id.and_then(|id| {
        let index = state.boosters.iter().position(|booster| booster.0 == id)?;
        Some(state.boosters.remove(index))
    });
    if let Some(booster) = old_booster.clone() {
        state.boosters.push(booster);
    }
    if let Some(player) = state.player_mut(player_id) {
        player.booster = new_booster;
        player.passed = true;
    }

    events.push(GameEvent::PlayerPassed {
        player: player_id,
        booster: old_booster.unwrap_or(crate::game_state::Booster(0)),
    });

    events.extend(apply_tech_tile_pass_bonus(state, player_id));

    advance_turn(state);
    events
}

fn round_booster_pass_vp(state: &GameState, player_id: PlayerId, booster_id: u8) -> i32 {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    let count = match booster_id {
        1 => player
            .structures
            .iter()
            .filter(|structure| structure.kind == StructureType::ResearchLab)
            .count() as u32,
        3 => {
            player
                .structures
                .iter()
                .filter(|structure| structure.kind == StructureType::Mine)
                .count() as u32
                + player.artifact_mines.len() as u32
        }
        4 => player
            .structures
            .iter()
            .filter(|structure| {
                matches!(
                    structure.kind,
                    StructureType::PlanetaryInstitute | StructureType::Academy(_)
                )
            })
            .count() as u32,
        6 => u32::from(
            player
                .gaiaformers_total
                .saturating_sub(player.resources.spent_gaia_formers),
        ),
        7 => player
            .structures
            .iter()
            .filter(|structure| structure.kind == StructureType::TradingStation)
            .count() as u32,
        10 => ScoringEngine::final_scoring_metric(
            state,
            player_id,
            &FinalScoringCondition::MostPlanetTypes,
        ),
        11 => ScoringEngine::final_scoring_metric(
            state,
            player_id,
            &FinalScoringCondition::MostGaiaPlanets,
        ),
        14 => ScoringEngine::final_scoring_metric(
            state,
            player_id,
            &FinalScoringCondition::MostDeepSpaceSectors,
        ),
        _ => 0,
    };
    let vp_per_unit = match booster_id {
        1 | 6 => 3,
        7 | 14 => 2,
        4 => 4,
        3 | 10 | 11 => 1,
        _ => 0,
    };
    (count * vp_per_unit) as i32
}

// ── Setup-phase application ───────────────────────────────────────────────────

fn apply_setup(
    state: &mut GameState,
    player_id: PlayerId,
    action: SetupAction,
) -> Result<Vec<GameEvent>, RuleError> {
    match action {
        SetupAction::SelectFaction { faction } => {
            apply_sequential_faction_selection(state, player_id, faction)
        }
        SetupAction::PlaceBid { amount } => apply_setup_bid(state, player_id, amount),
        SetupAction::PassBid => apply_setup_bid_pass(state, player_id),
        SetupAction::ChooseBidReward {
            faction,
            turn_position,
        } => apply_setup_bid_choice(state, player_id, faction, turn_position),
        SetupAction::PlaceStartingStructure { coord } => {
            apply_starting_structure(state, player_id, coord)
        }
        SetupAction::SelectStartingBooster { booster_id } => {
            apply_starting_booster(state, player_id, booster_id)
        }
    }
}

fn apply_sequential_faction_selection(
    state: &mut GameState,
    player_id: PlayerId,
    faction: crate::game_state::FactionId,
) -> Result<Vec<GameEvent>, RuleError> {
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
        begin_starting_structure_placement(state)?;
    }
    if !is_complete {
        state.phase = if let Some(active_player) = next_player {
            GamePhase::Setup(SetupPhase::FactionSelection { active_player })
        } else {
            return Err(RuleError::WrongPhase);
        };
    }

    Ok(vec![event])
}

fn apply_setup_bid(
    state: &mut GameState,
    player_id: PlayerId,
    amount: u32,
) -> Result<Vec<GameEvent>, RuleError> {
    let phase = {
        let bidding = state.bidding.as_mut().ok_or(RuleError::WrongPhase)?;
        BiddingPolicy::place_bid(bidding, player_id, amount)?;
        setup_phase_for_bidding(bidding)?
    };
    state.phase = GamePhase::Setup(phase);
    Ok(vec![GameEvent::BidPlaced {
        player: player_id,
        amount,
    }])
}

fn apply_setup_bid_pass(
    state: &mut GameState,
    player_id: PlayerId,
) -> Result<Vec<GameEvent>, RuleError> {
    let phase = {
        let bidding = state.bidding.as_mut().ok_or(RuleError::WrongPhase)?;
        BiddingPolicy::pass(bidding, player_id)?;
        setup_phase_for_bidding(bidding)?
    };
    state.phase = GamePhase::Setup(phase);
    Ok(vec![GameEvent::BidPassed { player: player_id }])
}

fn apply_setup_bid_choice(
    state: &mut GameState,
    player_id: PlayerId,
    faction: crate::game_state::FactionId,
    turn_position: u8,
) -> Result<Vec<GameEvent>, RuleError> {
    let (created, next_phase, final_turn_order) = {
        let bidding = state.bidding.as_mut().ok_or(RuleError::WrongPhase)?;
        let created = BiddingPolicy::choose(bidding, player_id, faction, turn_position)?;
        let next_phase = setup_phase_for_bidding(bidding)?;
        let final_turn_order = bidding.turn_order();
        (created, next_phase, final_turn_order)
    };

    let mut events = Vec::with_capacity(created.len() * 2);
    for assignment in created {
        let player = state
            .player_mut(assignment.player)
            .ok_or(RuleError::NotYourTurn)?;
        player.faction = Some(assignment.faction);
        player.setup_bid_vp = assignment.bid_vp;
        events.push(GameEvent::BidWon {
            player: assignment.player,
            amount: assignment.bid_vp,
            faction: assignment.faction,
            turn_position: assignment.turn_position,
        });
        events.push(GameEvent::FactionSelected {
            player: assignment.player,
            faction: assignment.faction,
        });
    }

    if let Some(turn_order) = final_turn_order {
        state.turn_order = turn_order;
        seed_starting_resources(state);
        begin_starting_structure_placement(state)?;
    } else {
        state.phase = GamePhase::Setup(next_phase);
    }
    Ok(events)
}

fn setup_phase_for_bidding(bidding: &BiddingState) -> Result<SetupPhase, RuleError> {
    match bidding.stage {
        BiddingStage::Auction => Ok(SetupPhase::Bidding {
            active_player: bidding.active_player,
        }),
        BiddingStage::WinnerChoice { winner, .. } => Ok(SetupPhase::BiddingChoice { winner }),
        BiddingStage::Complete => Ok(SetupPhase::Complete),
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct StartingPlacement {
    player: PlayerId,
    kind: StructureType,
}

fn faction_starting_structures(
    factions: &[crate::data::FactionData],
    faction: crate::game_state::FactionId,
) -> Vec<StructureType> {
    factions
        .iter()
        .find(|data| data.faction_id() == Some(faction))
        .map(|data| {
            data.starting_structures
                .iter()
                .filter_map(|structure| {
                    crate::data::factions::parse_structure_kind(&structure.kind)
                })
                .collect()
        })
        .unwrap_or_default()
}

/// Advanced-setup placement order (base rulebook p.19 plus Lost Fleet
/// Appendix I): first mines clockwise, second-stage structures
/// counterclockwise, Xenos' third mine, then Ivits' Planetary Institute.
fn starting_placement_queue(state: &GameState) -> Vec<StartingPlacement> {
    let factions = crate::data::load_factions().factions;
    let structures_for = |player_id: PlayerId| {
        state
            .player(player_id)
            .and_then(|player| player.faction)
            .map(|faction| faction_starting_structures(&factions, faction))
            .unwrap_or_default()
    };

    let mut queue = Vec::new();
    for &player_id in &state.turn_order {
        let structures = structures_for(player_id);
        if structures.len() >= 2 {
            queue.push(StartingPlacement {
                player: player_id,
                kind: structures[0],
            });
        }
    }
    for &player_id in state.turn_order.iter().rev() {
        let Some(faction) = state.player(player_id).and_then(|player| player.faction) else {
            continue;
        };
        if faction == crate::game_state::FactionId::Ivits {
            continue;
        }
        let structures = structures_for(player_id);
        let second_stage = if structures.len() >= 2 {
            structures.get(1)
        } else {
            structures.first()
        };
        if let Some(&kind) = second_stage {
            queue.push(StartingPlacement {
                player: player_id,
                kind,
            });
        }
    }
    for &player_id in &state.turn_order {
        if state.player(player_id).and_then(|player| player.faction)
            != Some(crate::game_state::FactionId::Xenos)
        {
            continue;
        }
        for kind in structures_for(player_id).into_iter().skip(2) {
            queue.push(StartingPlacement {
                player: player_id,
                kind,
            });
        }
    }
    for &player_id in &state.turn_order {
        if state.player(player_id).and_then(|player| player.faction)
            != Some(crate::game_state::FactionId::Ivits)
        {
            continue;
        }
        for kind in structures_for(player_id) {
            queue.push(StartingPlacement {
                player: player_id,
                kind,
            });
        }
    }
    queue
}

fn begin_starting_structure_placement(state: &mut GameState) -> Result<(), RuleError> {
    let queue = starting_placement_queue(state);
    let first = queue.first().ok_or_else(|| {
        RuleError::ActionNotAllowed("no starting structures configured".to_string())
    })?;
    state.phase = GamePhase::Setup(SetupPhase::StartingStructures {
        active_player: first.player,
        placement_index: 0,
        kind: first.kind,
    });
    Ok(())
}

fn apply_starting_structure(
    state: &mut GameState,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<Vec<GameEvent>, RuleError> {
    let (active_player, placement_index) = match state.phase {
        GamePhase::Setup(SetupPhase::StartingStructures {
            active_player,
            placement_index,
            ..
        }) => (active_player, placement_index),
        _ => return Err(RuleError::WrongPhase),
    };
    if active_player != player_id {
        return Err(RuleError::NotYourTurn);
    }

    let queue = starting_placement_queue(state);
    let placement = queue
        .get(placement_index)
        .copied()
        .ok_or(RuleError::WrongPhase)?;
    if placement.player != player_id {
        return Err(RuleError::NotYourTurn);
    }
    let faction = state
        .player(player_id)
        .and_then(|player| player.faction)
        .ok_or(RuleError::WrongPhase)?;
    let factions = crate::data::load_factions().factions;
    let home_planet = factions
        .iter()
        .find(|data| data.faction_id() == Some(faction))
        .and_then(|data| data.home_planet_type())
        .ok_or_else(|| RuleError::ActionNotAllowed("faction home planet missing".to_string()))?;
    let hex = state
        .board
        .hexes
        .get(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    let planet = hex.planet.as_ref().ok_or(RuleError::InvalidTarget(coord))?;
    if planet.planet_type != home_planet || planet.is_gaia_formed {
        return Err(RuleError::InvalidTarget(coord));
    }
    if planet.owner.is_some() || !hex.structures.is_empty() {
        return Err(RuleError::TargetOccupied(coord));
    }

    state
        .player_mut(player_id)
        .ok_or(RuleError::NotYourTurn)?
        .structures
        .push(crate::game_state::Structure {
            hex: coord,
            kind: placement.kind,
        });
    let hex = state
        .board
        .hexes
        .get_mut(&coord)
        .ok_or(RuleError::InvalidTarget(coord))?;
    if let Some(planet) = &mut hex.planet {
        planet.owner = Some(player_id);
    }
    hex.structures.push(PlacedStructure {
        owner: player_id,
        kind: placement.kind,
    });

    let next_index = placement_index + 1;
    if let Some(next) = queue.get(next_index) {
        state.phase = GamePhase::Setup(SetupPhase::StartingStructures {
            active_player: next.player,
            placement_index: next_index,
            kind: next.kind,
        });
    } else {
        begin_starting_booster_selection(state)?;
    }

    Ok(vec![GameEvent::StructureBuilt {
        player: player_id,
        hex: coord,
        kind: placement.kind,
    }])
}

/// Grants every player their faction's starting ore/credits/knowledge/QIC and
/// power bowls once faction selection completes. `factions.toml`'s
/// `starting_structures` are deliberately not placed here — where on the
/// board to put them is handled by the subsequent starting-structure phase.
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
                brainstone: (faction_id == FactionId::Taklons).then_some(BrainstoneLocation::Area1),
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
                add_resource(player, ResourceKind::Qic, effect.qic.max(0) as u8);
                player.gaiaformers_total =
                    player.gaiaformers_total.saturating_add(effect.gaiaformers);
            }
        }
    }
}

fn starting_booster_order(state: &GameState) -> Vec<PlayerId> {
    state.turn_order.iter().rev().copied().collect()
}

fn begin_starting_booster_selection(state: &mut GameState) -> Result<(), RuleError> {
    let order = starting_booster_order(state);
    let first = order.first().copied().ok_or_else(|| {
        RuleError::ActionNotAllowed("no players available for booster selection".to_string())
    })?;
    if state.boosters.len() < order.len() {
        return Err(RuleError::ActionNotAllowed(
            "not enough starting boosters for every player".to_string(),
        ));
    }
    state.phase = GamePhase::Setup(SetupPhase::StartingBoosters {
        active_player: first,
        selection_index: 0,
    });
    Ok(())
}

fn apply_starting_booster(
    state: &mut GameState,
    player_id: PlayerId,
    booster_id: u8,
) -> Result<Vec<GameEvent>, RuleError> {
    let (active_player, selection_index) = match state.phase {
        GamePhase::Setup(SetupPhase::StartingBoosters {
            active_player,
            selection_index,
        }) => (active_player, selection_index),
        _ => return Err(RuleError::WrongPhase),
    };
    if active_player != player_id {
        return Err(RuleError::NotYourTurn);
    }

    let order = starting_booster_order(state);
    if order.get(selection_index).copied() != Some(player_id) {
        return Err(RuleError::NotYourTurn);
    }
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.booster.is_some() {
        return Err(RuleError::ActionNotAllowed(
            "starting booster already selected".to_string(),
        ));
    }
    let booster_index = state
        .boosters
        .iter()
        .position(|booster| booster.0 == booster_id)
        .ok_or_else(|| {
            RuleError::ActionNotAllowed(format!("booster {booster_id} not available"))
        })?;
    let booster = state.boosters.remove(booster_index);
    state
        .player_mut(player_id)
        .ok_or(RuleError::NotYourTurn)?
        .booster = Some(booster.clone());

    let next_index = selection_index + 1;
    if let Some(next_player) = order.get(next_index).copied() {
        state.phase = GamePhase::Setup(SetupPhase::StartingBoosters {
            active_player: next_player,
            selection_index: next_index,
        });
    } else {
        state.round = 1;
        state.phase = GamePhase::Setup(SetupPhase::Complete);
    }

    Ok(vec![GameEvent::BoosterSelected {
        player: player_id,
        booster,
    }])
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
            .flat_map(|hex| hex.structures.iter().map(move |structure| (hex, structure)))
            .filter(|(_, structure)| {
                structure.owner == pid && structure.kind != StructureType::Satellite
            })
            .map(|(hex, structure)| {
                faction_structure_power_value(state, pid, hex.coord, structure.kind)
            })
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
    accept: bool,
) -> Result<(), RuleError> {
    ensure_charge_power_phase(state, player_id)?;
    if accept && state.player(player_id).is_some_and(taklons_pi_is_active) {
        return Err(RuleError::ActionNotAllowed(
            "Taklons with a Planetary Institute must choose whether to gain power before or after charging"
                .to_string(),
        ));
    }
    Ok(())
}

fn validate_taklons_charge_power(
    state: &GameState,
    player_id: PlayerId,
    _gain_before: bool,
) -> Result<(), RuleError> {
    ensure_charge_power_phase(state, player_id)?;
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if !taklons_pi_is_active(player) {
        return Err(RuleError::ActionNotAllowed(
            "requires the Taklons Planetary Institute".to_string(),
        ));
    }
    Ok(())
}

fn taklons_pi_is_active(player: &PlayerState) -> bool {
    player.faction == Some(FactionId::Taklons) && player_has_planetary_institute(player)
}

fn passive_charge_amount(player: &PlayerState, entry: &PendingCharge) -> u8 {
    let movable = movable_power_tokens(&player.resources.power);
    let affordable = player.vp.max(0) as u32 + 1;
    u32::from(entry.max_power).min(movable).min(affordable) as u8
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
            let amount = passive_charge_amount(player, &entry);
            if amount > 0 {
                player.vp -= i32::from(amount) - 1;
                apply_power_charge(&mut player.resources.power, amount);
            }
        }
    }

    finish_pending_charge(state);

    vec![]
}

fn apply_taklons_charge_power(
    state: &mut GameState,
    player_id: PlayerId,
    gain_before: bool,
) -> Vec<GameEvent> {
    let entry = match ensure_charge_power_phase(state, player_id) {
        Ok(entry) => entry,
        Err(_) => return vec![],
    };

    if let Some(player) = state.player_mut(player_id) {
        if gain_before {
            player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(1);
        }
        let amount = passive_charge_amount(player, &entry);
        if amount > 0 {
            player.vp -= i32::from(amount) - 1;
            apply_power_charge(&mut player.resources.power, amount);
        }
        if !gain_before {
            player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(1);
        }
    }

    finish_pending_charge(state);
    vec![]
}

fn finish_pending_charge(state: &mut GameState) {
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

    let mut completed_round = None;
    if let GamePhase::IncomeOrderPending { queue, round } = &mut state.phase {
        if !queue.is_empty() {
            queue.remove(0);
        }
        if queue.is_empty() {
            completed_round = Some(*round);
        }
    }

    completed_round.map_or_else(Vec::new, |round| {
        continue_round_transition_after_income(state, round)
    })
}

// ── Gaia phase ───────────────────────────────────────────────────────────────

/// Rulebook p.11: Transdim planets with a Gaiaformer become Gaia planets and
/// each player's Gaia-area power returns to their power cycle. Players with
/// the Terrans' or Itars' Planetary Institute pause before that power moves so
/// they can resolve their optional faction ability.
fn apply_gaia_phase(state: &mut GameState) -> (Vec<GameEvent>, Vec<PendingGaiaDecision>) {
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
        if let Some(player) = state.player_mut(owner) {
            player.gaiaformers_deployed = player.gaiaformers_deployed.saturating_sub(1);
        }
        events.push(GameEvent::GaiaFormingComplete {
            player: owner,
            hex: coord,
        });
    }

    for player in &mut state.players {
        // Bal T'aks Gaiaformers moved here by their free action return to
        // their faction board and become available again.
        player.gaiaformers_in_gaia_area = 0;
    }

    let mut player_order = state.turn_order.clone();
    for player in &state.players {
        if !player_order.contains(&player.player_id) {
            player_order.push(player.player_id);
        }
    }

    let mut pending = Vec::new();
    for player_id in player_order {
        let Some(player) = state.player(player_id) else {
            continue;
        };
        let amount = player.resources.power.gaia_forming.saturating_add(u8::from(
            player.resources.power.brainstone == Some(BrainstoneLocation::Gaia),
        ));
        if amount == 0 {
            continue;
        }
        let has_pi = player_has_planetary_institute(player);
        let kind = match player.faction {
            Some(FactionId::Terrans) if has_pi => Some(GaiaDecisionKind::TerransPowerConversion),
            Some(FactionId::Itars)
                if has_pi
                    && amount >= 4
                    && itars_has_available_standard_tech_choice(state, player_id) =>
            {
                Some(GaiaDecisionKind::ItarsTechTile)
            }
            _ => None,
        };
        if let Some(kind) = kind {
            pending.push(PendingGaiaDecision {
                player: player_id,
                kind,
                remaining_power: amount,
            });
            continue;
        }

        move_remaining_gaia_power(state, player_id);
    }

    (events, pending)
}

fn player_has_planetary_institute(player: &PlayerState) -> bool {
    player
        .structures
        .iter()
        .any(|structure| structure.kind == StructureType::PlanetaryInstitute)
}

fn itars_has_available_standard_tech_choice(state: &GameState, player_id: PlayerId) -> bool {
    let Some(player) = state.player(player_id) else {
        return false;
    };
    state
        .research_board
        .tech_tiles
        .iter()
        .any(|tile| !player.tech_tiles.contains(tile))
        && ResearchTrack::all()
            .into_iter()
            .any(|track| player.research_tracks.get(track) < 5)
}

fn move_remaining_gaia_power(state: &mut GameState, player_id: PlayerId) {
    let destination = state
        .player(player_id)
        .and_then(|player| player.faction)
        .map(|faction| {
            faction_registry()
                .get(faction)
                .gaia_phase_power_destination()
        })
        .unwrap_or(crate::game_state::PowerBowl::Area1);
    let Some(player) = state.player_mut(player_id) else {
        return;
    };
    let amount = player.resources.power.gaia_forming;
    match destination {
        crate::game_state::PowerBowl::Area1 => {
            player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(amount);
            if player.resources.power.brainstone == Some(BrainstoneLocation::Gaia) {
                player.resources.power.brainstone = Some(BrainstoneLocation::Area1);
            }
        }
        crate::game_state::PowerBowl::Area2 => {
            player.resources.power.bowl2 = player.resources.power.bowl2.saturating_add(amount);
            if player.resources.power.brainstone == Some(BrainstoneLocation::Gaia) {
                player.resources.power.brainstone = Some(BrainstoneLocation::Area2);
            }
        }
    }
    player.resources.power.gaia_forming = 0;
}

fn ensure_gaia_decision_phase(
    state: &GameState,
    player_id: PlayerId,
) -> Result<PendingGaiaDecision, RuleError> {
    match &state.phase {
        GamePhase::GaiaDecisionPending { queue, .. } => match queue.first() {
            Some(entry) if entry.player == player_id => Ok(entry.clone()),
            _ => Err(RuleError::NotYourTurn),
        },
        _ => Err(RuleError::WrongPhase),
    }
}

fn validate_terrans_gaia_conversion(
    state: &GameState,
    player_id: PlayerId,
    kind: &FreeActionKind,
    count: u8,
) -> Result<(), RuleError> {
    let entry = ensure_gaia_decision_phase(state, player_id)?;
    if entry.kind != GaiaDecisionKind::TerransPowerConversion {
        return Err(RuleError::ActionNotAllowed(
            "only the Terrans may convert Gaia-area power here".into(),
        ));
    }
    if count == 0 || count > MAX_FREE_ACTION_COUNT {
        return Err(RuleError::ActionNotAllowed(
            "Gaia conversion count must be between 1 and 30".into(),
        ));
    }
    if !matches!(
        kind,
        FreeActionKind::PowerToQic
            | FreeActionKind::PowerToOre
            | FreeActionKind::PowerToKnowledge
            | FreeActionKind::PowerToCredit
    ) {
        return Err(RuleError::ActionNotAllowed(
            "Terrans may only use power-to-resource free actions during the Gaia phase".into(),
        ));
    }
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.faction != Some(FactionId::Terrans) || !player_has_planetary_institute(player) {
        return Err(RuleError::ActionNotAllowed(
            "requires the Terrans Planetary Institute".into(),
        ));
    }
    let (_, unit_cost) = free_action_cost(kind);
    let total_cost = u16::from(unit_cost) * u16::from(count);
    if u16::from(entry.remaining_power) < total_cost {
        return Err(RuleError::InsufficientResources(ResourceKind::Power));
    }
    Ok(())
}

fn apply_terrans_gaia_conversion(
    state: &mut GameState,
    player_id: PlayerId,
    kind: FreeActionKind,
    count: u8,
) -> Vec<GameEvent> {
    let (_, unit_cost) = free_action_cost(&kind);
    let total_cost = unit_cost.saturating_mul(count);
    let (gain_kind, unit_gain) = free_action_gain(&kind);
    let total_gain = unit_gain.saturating_mul(count);
    let Some(player) = state.player_mut(player_id) else {
        return Vec::new();
    };
    add_resource(player, gain_kind, total_gain);
    let delta = match gain_kind {
        ResourceKind::Ore => ResourceDelta {
            ore: total_gain as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Credits => ResourceDelta {
            credits: total_gain as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Knowledge => ResourceDelta {
            knowledge: total_gain as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Qic => ResourceDelta {
            qic: total_gain as i8,
            ..ResourceDelta::zero()
        },
        ResourceKind::Power => ResourceDelta::zero(),
    };
    if let GamePhase::GaiaDecisionPending { queue, .. } = &mut state.phase {
        if let Some(entry) = queue.first_mut() {
            entry.remaining_power = entry.remaining_power.saturating_sub(total_cost);
        }
    }
    free_action_events(player_id, kind, count, delta)
}

fn validate_itars_gaia_tech_tile(
    state: &GameState,
    player_id: PlayerId,
    tile: &TechTile,
    track: ResearchTrack,
) -> Result<(), RuleError> {
    let entry = ensure_gaia_decision_phase(state, player_id)?;
    if entry.kind != GaiaDecisionKind::ItarsTechTile {
        return Err(RuleError::ActionNotAllowed(
            "only the Itars may gain a Tech tile here".into(),
        ));
    }
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if player.faction != Some(FactionId::Itars) || !player_has_planetary_institute(player) {
        return Err(RuleError::ActionNotAllowed(
            "requires the Itars Planetary Institute".into(),
        ));
    }
    if player.resources.power.gaia_forming < 4 {
        return Err(RuleError::InsufficientResources(ResourceKind::Power));
    }
    if player.tech_tiles.contains(tile) {
        return Err(RuleError::ActionNotAllowed(
            "a player cannot own two copies of the same Standard Tech tile".into(),
        ));
    }
    if !state.research_board.tech_tiles.contains(tile) {
        return Err(RuleError::ActionNotAllowed(
            "that Tech tile isn't available".into(),
        ));
    }
    validate_free_research_advance(state, player_id, track)
}

fn apply_itars_gaia_tech_tile(
    state: &mut GameState,
    player_id: PlayerId,
    tile: TechTile,
    track: ResearchTrack,
) -> Vec<GameEvent> {
    if let Some(player) = state.player_mut(player_id) {
        player.resources.power.gaia_forming = player.resources.power.gaia_forming.saturating_sub(4);
    }
    if let GamePhase::GaiaDecisionPending { queue, .. } = &mut state.phase {
        if let Some(entry) = queue.first_mut() {
            entry.remaining_power = entry.remaining_power.saturating_sub(4);
        }
    }
    let mut events = Vec::new();
    if transfer_tech_tile_to_player(state, player_id, &tile) {
        events.push(GameEvent::TechTileGained {
            player: player_id,
            tile,
        });
        events.extend(apply_free_research_advance(state, player_id, track));
    }
    events
}

fn validate_finish_gaia_decision(state: &GameState, player_id: PlayerId) -> Result<(), RuleError> {
    ensure_gaia_decision_phase(state, player_id)?;
    Ok(())
}

fn apply_finish_gaia_decision(state: &mut GameState, player_id: PlayerId) -> Vec<GameEvent> {
    move_remaining_gaia_power(state, player_id);

    let mut completed_round = None;
    if let GamePhase::GaiaDecisionPending { queue, round } = &mut state.phase {
        if !queue.is_empty() {
            queue.remove(0);
        }
        if queue.is_empty() {
            completed_round = Some(*round);
        }
    }
    if let Some(round) = completed_round {
        finish_round_transition(state, round);
    }
    Vec::new()
}

fn continue_round_transition_after_income(state: &mut GameState, round: u8) -> Vec<GameEvent> {
    let (events, pending) = apply_gaia_phase(state);
    if pending.is_empty() {
        finish_round_transition(state, round);
    } else {
        state.phase = GamePhase::GaiaDecisionPending {
            queue: pending,
            round,
        };
    }
    events
}

// ── Income phase ─────────────────────────────────────────────────────────────

/// Rulebook p.10: at the start of each round, gain resources from the
/// current level of each research track, from built Mine/TradingStation/
/// ResearchLab/Academy/PlanetaryInstitute structures (faction board income
/// rows), the player's round booster, and the faction's passive income
/// ability. Tech-tile income is not modeled yet.
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
                    add_resource(player, ResourceKind::Qic, effect.qic.max(0) as u8);
                    apply_power_charge(&mut player.resources.power, effect.power_charge);
                }
            }
            player.resources.ore = player.resources.ore.saturating_add(passive.ore);
            player.resources.credits = player.resources.credits.saturating_add(passive.credits);
            player.resources.knowledge =
                player.resources.knowledge.saturating_add(passive.knowledge);
            add_resource(player, ResourceKind::Qic, passive.qic);
            // `passive.power` is a fresh bowl grant (e.g. Lantids' "+1 power in Area I" per
            // round, GP_Exp_Rule_EN_V1_Web.pdf p.6), not a charge — direct `saturating_add`,
            // matching every other "+X power tokens to bowlN" grant in this file.
            player.resources.power.bowl1 = player
                .resources
                .power
                .bowl1
                .saturating_add(passive.power.bowl1);
            player.resources.power.bowl2 = player
                .resources
                .power
                .bowl2
                .saturating_add(passive.power.bowl2);
            player.resources.power.bowl3 = player
                .resources
                .power
                .bowl3
                .saturating_add(passive.power.bowl3);
            apply_round_booster_income(player);
            apply_tech_tile_income(player);
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

fn apply_round_booster_income(player: &mut PlayerState) {
    let Some(booster_id) = player.booster.as_ref().map(|booster| booster.0) else {
        return;
    };
    match booster_id {
        1 => player.resources.knowledge = player.resources.knowledge.saturating_add(1),
        2 => {
            player.resources.ore = player.resources.ore.saturating_add(1);
            player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(2);
        }
        3 | 6 | 7 | 10 => player.resources.ore = player.resources.ore.saturating_add(1),
        4 => apply_power_charge(&mut player.resources.power, 4),
        5 => apply_power_charge(&mut player.resources.power, 2),
        8 => apply_power_charge(&mut player.resources.power, 2),
        9 => {
            player.resources.credits = player.resources.credits.saturating_add(2);
            add_resource(player, ResourceKind::Qic, 1);
        }
        11 => player.resources.credits = player.resources.credits.saturating_add(4),
        12 => player.resources.credits = player.resources.credits.saturating_add(2),
        13 => {
            player.resources.ore = player.resources.ore.saturating_add(1);
            player.resources.knowledge = player.resources.knowledge.saturating_add(1);
        }
        14 => player.resources.credits = player.resources.credits.saturating_add(3),
        _ => {}
    }
}

/// Standard Tech tiles 2/3/5's per-round income (rulebook p.15: "Income: ..." — same "granted
/// every Income phase" shape as round boosters, so applied the same way, right alongside
/// `apply_round_booster_income`).
fn apply_tech_tile_income(player: &mut PlayerState) {
    for tile_id in player_active_tech_tile_ids(player) {
        match tile_id {
            2 => {
                player.resources.ore = player.resources.ore.saturating_add(1);
                apply_power_charge(&mut player.resources.power, 1);
            }
            3 => player.resources.credits = player.resources.credits.saturating_add(4),
            5 => {
                player.resources.knowledge = player.resources.knowledge.saturating_add(1);
                player.resources.credits = player.resources.credits.saturating_add(1);
            }
            _ => {}
        }
    }
}

/// Resets `passed` flags and reopens `ActionPhase` for the round after
/// `round` (shared by the immediate-finish and `IncomeOrderPending`-drained
/// paths in `advance_to_next_round`/`apply_choose_income_order`).
fn finish_round_transition(state: &mut GameState, round: u8) {
    for player in &mut state.players {
        player.passed = false;
        player.academy_qic_action_used_this_round = false;
        player.gleens_special_action_used_this_round = false;
        player.space_giants_special_action_used_this_round = false;
        player.round_booster_special_action_used_this_round = false;
        player.faction_special_action_used_this_round = false;
        player.tech_tile_special_actions_used_this_round.clear();
        player
            .advanced_tech_tile_special_actions_used_this_round
            .clear();
    }
    state.used_power_actions.clear();
    state.used_spaceship_actions.clear();
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

fn add_resource(player: &mut PlayerState, kind: ResourceKind, amount: u8) -> ResourceKind {
    let actual_kind = if kind == ResourceKind::Qic
        && player.faction == Some(FactionId::Gleens)
        && !player
            .structures
            .iter()
            .any(|structure| matches!(structure.kind, StructureType::Academy(AcademyType::Qic)))
    {
        ResourceKind::Ore
    } else {
        kind
    };
    match actual_kind {
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
    actual_kind
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

fn movable_power_tokens(power: &PowerCycle) -> u32 {
    u32::from(power.bowl1)
        + u32::from(power.bowl2)
        + u32::from(matches!(
            power.brainstone,
            Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2)
        ))
}

fn active_power_tokens(power: &PowerCycle) -> u8 {
    power
        .bowl1
        .saturating_add(power.bowl2)
        .saturating_add(power.bowl3)
        .saturating_add(u8::from(matches!(
            power.brainstone,
            Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2 | BrainstoneLocation::Area3)
        )))
}

fn spendable_power_value(power: &PowerCycle) -> u8 {
    power
        .bowl3
        .saturating_add(if power.brainstone == Some(BrainstoneLocation::Area3) {
            3
        } else {
            0
        })
}

/// Pays a power cost from Area III. For Taklons, the deterministic default
/// spends the Brainstone whenever it avoids normal-token spending (cost >= 3)
/// or is required to afford the cost; spending it moves it to Area I.
fn spend_power(power: &mut PowerCycle, cost: u8) {
    let use_brainstone =
        power.brainstone == Some(BrainstoneLocation::Area3) && (cost >= 3 || power.bowl3 < cost);
    let normal_cost = if use_brainstone {
        power.brainstone = Some(BrainstoneLocation::Area1);
        cost.saturating_sub(3)
    } else {
        cost
    };
    power.bowl3 = power.bowl3.saturating_sub(normal_cost);
}

/// Moves `count` power tokens from the active cycle into the Gaia area. The
/// Brainstone counts as one token, not three; normal tokens are selected first
/// so an automated action preserves the Brainstone when the ordinary supply is
/// already sufficient.
fn move_power_to_gaia(power: &mut PowerCycle, count: u8) {
    let mut remaining = count;
    for bowl in [&mut power.bowl1, &mut power.bowl2, &mut power.bowl3] {
        let moved = remaining.min(*bowl);
        *bowl -= moved;
        remaining -= moved;
    }
    let moved_brainstone = remaining > 0
        && matches!(
            power.brainstone,
            Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2 | BrainstoneLocation::Area3)
        );
    if moved_brainstone {
        power.brainstone = Some(BrainstoneLocation::Gaia);
        remaining -= 1;
    }
    debug_assert_eq!(remaining, 0, "power movement was validated before apply");
    power.gaia_forming = power
        .gaia_forming
        .saturating_add(count.saturating_sub(u8::from(moved_brainstone)));
}

fn move_brainstone_to_gaia(power: &mut PowerCycle) -> bool {
    if matches!(
        power.brainstone,
        Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2 | BrainstoneLocation::Area3)
    ) {
        power.brainstone = Some(BrainstoneLocation::Gaia);
        true
    } else {
        false
    }
}

/// "Charge `n` power" (rulebook p.9): move up to `n` tokens one bowl
/// forward — Area I must empty before Area II can charge. When Taklons have a
/// choice within the active bowl, charge the Brainstone first so snapshots use
/// the documented "automated brainstone" maximum-charge behavior.
fn apply_power_charge(power: &mut crate::game_state::PowerCycle, n: u8) {
    for _ in 0..n {
        if power.brainstone == Some(BrainstoneLocation::Area1) {
            power.brainstone = Some(BrainstoneLocation::Area2);
        } else if power.bowl1 > 0 {
            power.bowl1 -= 1;
            power.bowl2 = power.bowl2.saturating_add(1);
        } else if power.brainstone == Some(BrainstoneLocation::Area2) {
            power.brainstone = Some(BrainstoneLocation::Area3);
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
    units: u8,
) -> Vec<GameEvent> {
    if units == 0 {
        return vec![];
    }
    let round = state.round as usize;
    if round == 0 || round > state.round_tiles.len() {
        return vec![];
    }
    let tile = &state.round_tiles[round - 1];
    if &tile.condition != condition {
        return vec![];
    }
    let vp = i32::from(tile.vp_per_unit) * i32::from(units);
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

fn bescods_home_planet_power_bonus(
    state: &GameState,
    player_id: PlayerId,
    hexes: &[HexCoord],
) -> u32 {
    let Some(player) = state.player(player_id) else {
        return 0;
    };
    if player.faction != Some(FactionId::Bescods) || !player_has_planetary_institute(player) {
        return 0;
    }
    hexes
        .iter()
        .filter_map(|coord| state.board.hexes.get(coord))
        .filter(|hex| {
            hex.planet.as_ref().is_some_and(|planet| {
                !planet.is_gaia_formed && planet.planet_type == PlanetType::Titanium
            })
        })
        .flat_map(|hex| &hex.structures)
        .filter(|structure| {
            structure.owner == player_id && structure.kind != StructureType::Satellite
        })
        .count() as u32
}

fn faction_structure_power_value(
    state: &GameState,
    player_id: PlayerId,
    coord: HexCoord,
    kind: StructureType,
) -> u32 {
    let bonus = bescods_home_planet_power_bonus(state, player_id, &[coord])
        .saturating_add(moweyds_power_ring_bonus(state, player_id, &[coord]))
        .saturating_add(tech_tile_large_building_power_bonus(state, player_id, kind));
    kind.power_value().saturating_add(bonus)
}

/// Ore cost to colonize `target_type`, honoring a faction's terraforming
/// distance override (see `FactionAbility::terraforming_distance_override`).
/// `free_steps` waives that many terraforming steps before the remainder is
/// priced at `track_level`'s cost-per-step — used by the power-action
/// board's two "free terraforming steps" slots (rulebook Appendix III, ids
/// 2 and 6); the normal `Build` action always passes `free_steps: 0`.
fn terraform_ore_cost_with_free_steps(
    state: &GameState,
    player_id: PlayerId,
    target_type: PlanetType,
    track_level: u8,
    free_steps: u8,
) -> u8 {
    terraforming_distance(state, player_id, target_type).map_or(0, |d| {
        cost_for_distance(d.saturating_sub(free_steps), track_level)
    })
}

fn terraforming_distance(
    state: &GameState,
    player_id: PlayerId,
    target_type: PlanetType,
) -> Option<u8> {
    if let Some(distance) = tinkeroids_moweyds_terraforming_distance(state, player_id, target_type)
    {
        return Some(distance);
    }
    let home_type = home_planet_type(state, player_id)?;
    ability_for(state, player_id)
        .and_then(|ability| ability.terraforming_distance_override(home_type, target_type))
        .or_else(|| ring_distance(home_type, target_type))
}

fn is_standard_colored_planet_type(t: PlanetType) -> bool {
    matches!(
        t,
        PlanetType::Terra
            | PlanetType::Swamp
            | PlanetType::Desert
            | PlanetType::Oxide
            | PlanetType::Titanium
            | PlanetType::Volcanic
            | PlanetType::Ice
    )
}

fn home_planet_type_for_faction(faction_id: FactionId) -> Option<PlanetType> {
    crate::data::load_factions()
        .factions
        .into_iter()
        .find(|f| f.faction_id() == Some(faction_id))
        .and_then(|f| f.home_planet_type())
}

/// Tinkeroids and Moweyds have no home planet color, so their terraforming cost can't be
/// expressed through `FactionAbility::terraforming_distance_override`'s stateless `(from, to)`
/// signature — it depends on which OTHER factions are actually in this game (expansion
/// rulebook p.7, "Choosing Your Faction": "3 base-game planet types (which always includes
/// their opponents' base-game types) will require 3 steps, and the others will require just
/// 1"). Handled directly here rather than through the trait, matching this session's established
/// pattern for state-dependent faction rules (Ambas/Firaks/Bescods/Ivits/etc.). When fewer than
/// 3 opponents have a real base-game home color (i.e. 2+ of the 4 home-less Lost Fleet factions
/// share this game), the "3 types" set simply has fewer than 3 members — the rulebook doesn't
/// specify a fill rule for that edge case, so it's left that way rather than guessed.
fn tinkeroids_moweyds_terraforming_distance(
    state: &GameState,
    player_id: PlayerId,
    target_type: PlanetType,
) -> Option<u8> {
    let player = state.player(player_id)?;
    if !matches!(
        player.faction,
        Some(FactionId::Tinkeroids) | Some(FactionId::Moweyds)
    ) {
        return None;
    }
    if !is_standard_colored_planet_type(target_type) {
        return None;
    }
    let opponents_expensive = state
        .players
        .iter()
        .filter(|p| p.player_id != player_id)
        .filter_map(|p| p.faction)
        .filter_map(home_planet_type_for_faction)
        .filter(|&t| is_standard_colored_planet_type(t))
        .any(|t| t == target_type);
    Some(if opponents_expensive { 3 } else { 1 })
}

fn has_colonized_planet_type(
    state: &GameState,
    player_id: PlayerId,
    target_type: PlanetType,
) -> bool {
    let Some(player) = state.player(player_id) else {
        return false;
    };
    player.artifact_mines.contains(&target_type)
        || player.structures.iter().any(|structure| {
            state
                .board
                .hexes
                .get(&structure.hex)
                .and_then(|hex| hex.planet.as_ref())
                .is_some_and(|planet| {
                    let colonized_type = if planet.is_gaia_formed {
                        PlanetType::Gaia
                    } else {
                        planet.planet_type
                    };
                    colonized_type == target_type
                })
        })
}

fn colonized_planet_types(state: &GameState, player_id: PlayerId) -> Vec<PlanetType> {
    let Some(player) = state.player(player_id) else {
        return Vec::new();
    };
    let mut types = player.artifact_mines.clone();
    for structure in &player.structures {
        let Some(planet) = state
            .board
            .hexes
            .get(&structure.hex)
            .and_then(|hex| hex.planet.as_ref())
        else {
            continue;
        };
        let planet_type = if planet.is_gaia_formed {
            PlanetType::Gaia
        } else {
            planet.planet_type
        };
        if !types.contains(&planet_type) {
            types.push(planet_type);
        }
    }
    types
}

fn has_colonized_sector(state: &GameState, player_id: PlayerId, sector_id: u8) -> bool {
    let Some(player) = state.player(player_id) else {
        return false;
    };
    player
        .structures
        .iter()
        .any(|structure| MapEngine::sector_id_at(&state.board, structure.hex) == Some(sector_id))
}

/// QIC cost to colonize an already Gaia-formed planet, honoring a faction's
/// override (see `FactionAbility::gaia_colonization_qic_cost`). Tinkeroids and Moweyds are
/// handled directly here rather than through the trait, for the same reason as
/// `tinkeroids_moweyds_terraforming_distance` above (rulebook Appendix I: "Making a Gaia planet
/// habitable costs you 2 Q.I.C.s" for both).
fn gaia_qic_cost(state: &GameState, player_id: PlayerId) -> u8 {
    if matches!(
        state.player(player_id).and_then(|p| p.faction),
        Some(FactionId::Tinkeroids) | Some(FactionId::Moweyds)
    ) {
        return 2;
    }
    ability_for(state, player_id).map_or(1, |a| a.gaia_colonization_qic_cost())
}

/// Applies the state mutation implied by an ability-hook-produced event.
/// Handles only the event kinds `FactionAbility` hooks can currently
/// produce (`ResourceChanged`, `TechTileGained`) — this is not a general
/// event-sourcing replay mechanism.
/// Moves `tile` from the shared Standard Tech supply to `player_id`'s own `tech_tiles`, if it's
/// still available. Shared by `apply_ability_event`'s `TechTileGained` handling (a one-shot Space
/// Giants Planetary Institute ability) and the Lost Fleet Federation token that grants "1 Standard
/// Tech tile of your choice" (`apply_federation`) — callers apply any effect-specific side effect
/// (e.g. `pi_ability_used`) themselves; this only moves the tile.
fn transfer_tech_tile_to_player(
    state: &mut GameState,
    player_id: PlayerId,
    tile: &TechTile,
) -> bool {
    let Some(pos) = state
        .research_board
        .tech_tiles
        .iter()
        .position(|t| t == tile)
    else {
        return false;
    };
    state.research_board.tech_tiles.remove(pos);
    if let Some(p) = state.player_mut(player_id) {
        p.tech_tiles.push(tile.clone());
    }
    true
}

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
        GameEvent::TechTileGained { player, tile }
            if transfer_tech_tile_to_player(state, *player, tile) =>
        {
            // The only current producer of `TechTileGained` is a one-shot
            // Planetary Institute ability (see `SpaceGiantsAbility`).
            if let Some(p) = state.player_mut(*player) {
                p.pi_ability_used = true;
            }
        }
        _ => {}
    }
}

fn can_build_at(state: &GameState, player_id: PlayerId, coord: HexCoord) -> bool {
    validate_build(state, player_id, coord).is_ok()
}

fn upgrade_targets(player: &PlayerState, kind: StructureType) -> Vec<StructureType> {
    use crate::game_state::AcademyType;
    use StructureType::*;
    let is_bescods = player.faction == Some(FactionId::Bescods);
    match kind {
        Mine => vec![TradingStation],
        TradingStation if is_bescods => vec![
            ResearchLab,
            Academy(AcademyType::Science),
            Academy(AcademyType::Qic),
        ],
        TradingStation => vec![ResearchLab, PlanetaryInstitute],
        ResearchLab if is_bescods => vec![PlanetaryInstitute],
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
        (TradingStation, Academy(_)) => (6, 6),
        (ResearchLab, PlanetaryInstitute) => (4, 6),
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

/// Power-action board slots 1-7 (rulebook Appendix III — confirmed against
/// `gaia-frontend/src/assets/boards/research_board.jpg`, since the
/// rulebook prose doesn't print these itself). Ids 2 and 6 spend this same
/// cost too, but as part of a mine build (`free_terraform_steps_for_power_action`)
/// rather than a plain resource gain.
fn power_action_cost(id: u8) -> u8 {
    match id {
        1 => 7,
        2 => 5,
        3 => 4,
        4 => 4,
        5 => 4,
        6 => 3,
        7 => 3,
        _ => u8::MAX,
    }
}

fn power_action_token_cost(player: &PlayerState, printed_cost: u8) -> u8 {
    if player.faction == Some(FactionId::Nevlas) && player_has_planetary_institute(player) {
        printed_cost.div_ceil(2)
    } else {
        printed_cost
    }
}

/// Resource-gain power actions (ids 1, 3, 4, 5, 7 — ids 2 and 6 are handled
/// separately by `apply_power_action` as mine builds, not resource gains).
fn apply_power_effect(
    state: &mut GameState,
    player_id: PlayerId,
    id: u8,
    cost: u8,
) -> ResourceDelta {
    let mut delta = ResourceDelta::zero();
    if let Some(player) = state.player_mut(player_id) {
        spend_power(&mut player.resources.power, cost);
        match id {
            1 => {
                player.resources.knowledge += 3;
                delta.knowledge = 3;
            }
            3 => {
                player.resources.ore += 2;
                delta.ore = 2;
            }
            4 => {
                player.resources.credits += 7;
                delta.credits = 7;
            }
            5 => {
                player.resources.knowledge += 2;
                delta.knowledge = 2;
            }
            7 => {
                // Adds 2 fresh power tokens directly to bowl1 — not a charge
                // (which would move existing tokens forward a bowl).
                player.resources.power.bowl1 = player.resources.power.bowl1.saturating_add(2);
            }
            _ => {}
        }
    }
    delta
}
