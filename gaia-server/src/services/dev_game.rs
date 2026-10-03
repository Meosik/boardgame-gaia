use gaia_engine::{
    error::RuleError,
    game_state::{
        FactionId, GameEvent, GamePhase, HexCoord, PendingCharge, PlanetType, PlayerId, SetupPhase,
    },
    GameAction, GameSetup, GameState, MapEngine, RuleEngine, SetupAction,
};
use gaia_protocol::{CommandId, Revision};
use sha2::{Digest, Sha256};

use crate::{
    coordinator::{self, broadcast_snapshot, CommandResult},
    error::{ServerError, ServerResult},
    room::manager::Room,
    state::AppState,
};

/// Only the authenticated controller of a server-created manual DEV game may act for a seat.
pub(crate) fn is_manual_controller(room: &Room, player: PlayerId) -> bool {
    room.host_player == player
        && room.dev_human_player == Some(player)
        && room
            .game_state
            .as_ref()
            .is_some_and(|state| state.dev_controller == Some(player))
}

pub(crate) fn acting_player(room: &Room, authenticated_player: PlayerId) -> PlayerId {
    if !is_manual_controller(room, authenticated_player) {
        return authenticated_player;
    }
    room.game_state
        .as_ref()
        .and_then(required_player)
        .unwrap_or(authenticated_player)
}

pub struct DevGameService;

impl DevGameService {
    pub async fn trigger_power_charge(
        app: &AppState,
        room_code: &str,
        player_id: PlayerId,
        coord: HexCoord,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let outcome =
            coordinator::apply_command(app, room_code, command_id, expected_revision, |room| {
                enter_dev_power_charge(room, player_id, coord)
            })
            .await?;

        broadcast_snapshot(app, room_code, outcome.revision).await;
        Ok(outcome)
    }
}

fn enter_dev_power_charge(
    room: &mut Room,
    player_id: PlayerId,
    coord: HexCoord,
) -> Result<Vec<GameEvent>, RuleError> {
    if room.dev_human_player != Some(player_id) {
        return Err(RuleError::ActionNotAllowed(
            "power charge test is available only to the DEV human seat".into(),
        ));
    }

    let player_id = acting_player(room, player_id);
    let state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
    let active_player = match state.phase {
        GamePhase::ActionPhase { active_player } => active_player,
        _ => return Err(RuleError::WrongPhase),
    };
    if state.turn_order.get(active_player).copied() != Some(player_id) {
        return Err(RuleError::NotYourTurn);
    }

    let structure = state
        .board
        .hexes
        .get(&coord)
        .and_then(|hex| {
            hex.structures
                .iter()
                .find(|structure| structure.owner == player_id)
        })
        .ok_or_else(|| {
            RuleError::ActionNotAllowed("select one of your buildings to charge power".into())
        })?;
    let owner = structure.owner;
    let kind = structure.kind;
    let max_power = RuleEngine::structure_power_value_at(state, owner, coord, kind) as u8;
    if max_power == 0 {
        return Err(RuleError::ActionNotAllowed(
            "the selected structure has no power value".into(),
        ));
    }

    state.phase = GamePhase::ChargePowerPending {
        queue: vec![PendingCharge {
            player: player_id,
            hex: coord,
            max_power,
        }],
        resume_active_player: Some(active_player),
    };
    Ok(vec![])
}

/// Build a one-seat, real-engine game with three virtual opponents for UI development. Room
/// invitation, bidding, and faction selection are completed through the normal RuleEngine. The
/// human places their own starting structures while the opponents follow the normal setup order
/// automatically; everything travels through the normal WebSocket and RuleEngine paths.
pub fn build_dev_game_state(
    room_code: &str,
    seed: &str,
    player_id: PlayerId,
    bot_player_ids: &[PlayerId],
    setup: &GameSetup,
    faction: FactionId,
) -> ServerResult<GameState> {
    build_game_state_with_factions(
        room_code,
        seed,
        player_id,
        bot_player_ids,
        setup,
        faction,
        dev_bot_factions(faction),
    )
}

/// Four distinct factions for an AI game, varied by seed, never two sides of one board.
/// The first entry is the human's unless `human` fixes it.
pub fn ai_game_factions(seed: &str, human: Option<FactionId>) -> (FactionId, Vec<FactionId>) {
    let mut pool = FactionId::all();
    let digest = Sha256::digest(format!("{seed}:ai-factions").as_bytes());
    for index in (1..pool.len()).rev() {
        let swap_index = usize::from(digest[index % digest.len()]) % (index + 1);
        pool.swap(index, swap_index);
    }
    let human = human.unwrap_or(pool[0]);
    let mut chosen = vec![human];
    for faction in pool {
        if chosen.len() == 4 {
            break;
        }
        if chosen
            .iter()
            .all(|taken| *taken != faction && taken.other_board_side() != faction)
        {
            chosen.push(faction);
        }
    }
    (human, chosen.split_off(1))
}

pub fn build_game_state_with_factions(
    room_code: &str,
    seed: &str,
    player_id: PlayerId,
    bot_player_ids: &[PlayerId],
    setup: &GameSetup,
    faction: FactionId,
    bot_factions: Vec<FactionId>,
) -> ServerResult<GameState> {
    let mut players = vec![(player_id, "DEV".to_string())];
    players.extend(
        bot_player_ids
            .iter()
            .zip(bot_factions.iter())
            .map(|(id, faction)| (*id, format!("BOT · {}", faction_label(*faction)))),
    );
    let mut state = MapEngine::init_game_state(room_code, seed, &players, setup);
    let mut events = Vec::new();
    for (id, selected_faction) in std::iter::once((player_id, faction)).chain(
        bot_player_ids
            .iter()
            .copied()
            .zip(bot_factions.iter().copied()),
    ) {
        events.extend(
            RuleEngine::apply_setup_action(
                &mut state,
                id,
                SetupAction::SelectFaction {
                    faction: selected_faction,
                },
            )
            .map_err(dev_setup_error)?,
        );
    }
    assign_simulated_dev_bids(&mut state, room_code);

    if !matches!(
        state.phase,
        GamePhase::Setup(SetupPhase::StartingStructures { .. })
    ) {
        return Err(ServerError::Internal(
            "dev game did not reach starting structure placement".into(),
        ));
    }
    state.event_log.extend(events);

    Ok(state)
}

/// DEV games skip the actual bidding screen, so give the four seats a plausible bid result.
/// The room code makes the order vary between rooms while keeping one room stable on reconnect.
fn assign_simulated_dev_bids(state: &mut GameState, room_code: &str) {
    let mut bids = [0_u32, 1, 2, 4];
    let digest = Sha256::digest(format!("{room_code}:simulated-bids").as_bytes());
    for index in (1..bids.len()).rev() {
        let swap_index = usize::from(digest[index]) % (index + 1);
        bids.swap(index, swap_index);
    }
    for (player, bid) in state.players.iter_mut().zip(bids) {
        player.setup_bid_vp = bid;
    }
}

/// Advances every virtual opponent through the normal setup actions until the human seat must
/// act again. Opponent planets are chosen deterministically, preferring legal home planets nearest
/// to the human's existing mines so opponent-adjacency upgrade costs are easy to exercise.
pub fn auto_advance_dev_setup(
    state: &mut GameState,
    human_player: PlayerId,
) -> Result<Vec<GameEvent>, RuleError> {
    if state.dev_controller.is_some() {
        return Ok(Vec::new());
    }
    let mut events = Vec::new();
    loop {
        match state.phase {
            GamePhase::Setup(SetupPhase::StartingStructures { active_player, .. })
                if active_player != human_player =>
            {
                let coord = automatic_starting_coord(state, active_player, human_player)
                    .ok_or_else(|| {
                        RuleError::ActionNotAllowed(
                            "virtual opponent has no legal starting planet".into(),
                        )
                    })?;
                events.extend(RuleEngine::apply_setup_action(
                    state,
                    active_player,
                    SetupAction::PlaceStartingStructure { coord },
                )?);
            }
            GamePhase::Setup(SetupPhase::StartingBoosters { active_player, .. })
                if active_player != human_player =>
            {
                let booster_id =
                    state
                        .boosters
                        .first()
                        .map(|booster| booster.0)
                        .ok_or_else(|| {
                            RuleError::ActionNotAllowed(
                                "virtual opponent has no starting booster".into(),
                            )
                        })?;
                events.extend(RuleEngine::apply_setup_action(
                    state,
                    active_player,
                    SetupAction::SelectStartingBooster { booster_id },
                )?);
            }
            _ => break,
        }
    }
    Ok(events)
}

/// Runs virtual DEV seats until control returns to the human (or the human must resolve a
/// pending decision). Each bot takes a small, deterministic number of ordinary legal actions
/// before passing, so the harness exercises both intervening turns and pass-order changes.
pub fn auto_advance_dev_actions(
    room: &mut Room,
    human_player: PlayerId,
) -> Result<Vec<GameEvent>, RuleError> {
    let state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
    if state.dev_controller.is_some() {
        return Ok(Vec::new());
    }
    if room.dev_bot_action_round != state.round {
        room.dev_bot_action_counts.clear();
        room.dev_bot_action_round = state.round;
    }

    let mut events = Vec::new();
    for _ in 0..64 {
        let Some(active_player) = required_player(state) else {
            break;
        };
        if active_player == human_player {
            break;
        }

        let action = if matches!(state.phase, GamePhase::ActionPhase { .. }) {
            let completed = room
                .dev_bot_action_counts
                .get(&active_player)
                .copied()
                .unwrap_or(0);
            let target = dev_bot_action_target(state, human_player, active_player);
            if completed >= target {
                automatic_pass(state, active_player)?
            } else if let Some(action) = automatic_main_action(state, active_player, completed) {
                action
            } else {
                automatic_pass(state, active_player)?
            }
        } else {
            automatic_pending_action(state, active_player)?
        };

        let is_main_action = matches!(state.phase, GamePhase::ActionPhase { .. })
            && !matches!(
                action,
                GameAction::Pass { .. } | GameAction::FreeAction { .. }
            );
        events.extend(super::game_action::apply_logged_action(
            state,
            active_player,
            action,
        )?);
        if is_main_action {
            *room.dev_bot_action_counts.entry(active_player).or_insert(0) += 1;
        }
    }
    Ok(events)
}

/// One legal move for an automated seat when the AI worker is unavailable or fails:
/// the same simple choices the DEV bots make (setup placement/booster, a ranked main action
/// or pass, a conservative pending response).
pub(crate) fn fallback_step(
    state: &mut GameState,
    player: PlayerId,
    human_player: PlayerId,
) -> Result<Vec<GameEvent>, RuleError> {
    match state.phase {
        GamePhase::Setup(SetupPhase::StartingStructures { .. }) => {
            let coord = automatic_starting_coord(state, player, human_player).ok_or_else(|| {
                RuleError::ActionNotAllowed("automated seat has no legal starting planet".into())
            })?;
            RuleEngine::apply_setup_action(
                state,
                player,
                SetupAction::PlaceStartingStructure { coord },
            )
        }
        GamePhase::Setup(SetupPhase::StartingBoosters { .. }) => {
            let booster_id = state
                .boosters
                .first()
                .map(|booster| booster.0)
                .ok_or_else(|| {
                    RuleError::ActionNotAllowed("automated seat has no starting booster".into())
                })?;
            RuleEngine::apply_setup_action(
                state,
                player,
                SetupAction::SelectStartingBooster { booster_id },
            )
        }
        GamePhase::Setup(SetupPhase::Bidding { .. } | SetupPhase::BiddingChoice { .. }) => {
            let action = crate::ai_bidding::decide(state, player).ok_or_else(|| {
                RuleError::ActionNotAllowed("automated seat cannot act in this auction".into())
            })?;
            RuleEngine::apply_setup_action(state, player, action)
        }
        GamePhase::ActionPhase { .. } => {
            let action = match automatic_main_action(state, player, 0) {
                Some(action) => action,
                None => automatic_pass(state, player)?,
            };
            super::game_action::apply_logged_action(state, player, action)
        }
        _ => {
            let action = automatic_pending_action(state, player)?;
            super::game_action::apply_logged_action(state, player, action)
        }
    }
}

pub(crate) fn required_player(state: &GameState) -> Option<PlayerId> {
    match &state.phase {
        GamePhase::Setup(
            SetupPhase::FactionSelection { active_player }
            | SetupPhase::Bidding { active_player }
            | SetupPhase::StartingStructures { active_player, .. }
            | SetupPhase::StartingBoosters { active_player, .. },
        ) => Some(*active_player),
        GamePhase::Setup(SetupPhase::BiddingChoice { winner }) => Some(*winner),
        GamePhase::ActionPhase { active_player } => state.turn_order.get(*active_player).copied(),
        GamePhase::ChargePowerPending { queue, .. }
        | GamePhase::LostPlanetChargePowerPending { queue, .. } => {
            queue.first().map(|entry| entry.player)
        }
        GamePhase::LostPlanetPlacementPending { player, .. }
        | GamePhase::TinkeroidsTileSelectionPending { player, .. } => Some(*player),
        GamePhase::IncomeOrderPending { queue, .. } => queue.first().map(|entry| entry.player),
        GamePhase::GaiaDecisionPending { queue, .. } => queue.first().map(|entry| entry.player),
        _ => None,
    }
}

fn dev_bot_action_target(state: &GameState, human_player: PlayerId, bot_player: PlayerId) -> u8 {
    let bots = state
        .turn_order
        .iter()
        .copied()
        .filter(|player| *player != human_player)
        .collect::<Vec<_>>();
    let bot_index = bots
        .iter()
        .position(|player| *player == bot_player)
        .unwrap_or(0);
    let rotation = usize::from(state.round.saturating_sub(1)) % bots.len().max(1);
    u8::try_from((bot_index + rotation) % bots.len().max(1) + 1).unwrap_or(1)
}

fn automatic_main_action(
    state: &GameState,
    player_id: PlayerId,
    completed: u8,
) -> Option<GameAction> {
    let mut candidates = RuleEngine::get_valid_actions(state, player_id)
        .into_iter()
        .filter(|action| {
            matches!(
                action,
                GameAction::Build { .. }
                    | GameAction::ResearchAdvance { .. }
                    | GameAction::GaiaFormation { .. }
                    | GameAction::PowerAction { coord: None, .. }
                    | GameAction::AcademyQicAction
                    | GameAction::SpecialAction { .. }
            )
        })
        .collect::<Vec<_>>();
    candidates.sort_by_key(|action| (automatic_action_rank(action), format!("{action:?}")));
    if !candidates.is_empty() {
        let rotate_by = (usize::from(player_id) + usize::from(completed)) % candidates.len();
        candidates.rotate_left(rotate_by);
    }

    candidates.into_iter().find(|action| {
        let mut probe = state.clone();
        RuleEngine::apply_action(&mut probe, player_id, action.clone()).is_ok()
            && matches!(
                probe.phase,
                GamePhase::ActionPhase { .. } | GamePhase::RoundScoring { .. }
            )
    })
}

fn automatic_action_rank(action: &GameAction) -> u8 {
    match action {
        GameAction::ResearchAdvance { .. } => 0,
        GameAction::Build { .. } => 1,
        GameAction::GaiaFormation { .. } => 2,
        GameAction::PowerAction { .. } => 3,
        GameAction::AcademyQicAction => 4,
        GameAction::SpecialAction { .. } => 5,
        _ => 6,
    }
}

fn automatic_pass(state: &GameState, player_id: PlayerId) -> Result<GameAction, RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let booster_id = if state.round < 6 && player.booster.is_some() {
        Some(
            state
                .boosters
                .first()
                .map(|booster| booster.0)
                .ok_or_else(|| {
                    RuleError::ActionNotAllowed(
                        "virtual opponent has no available booster when passing".into(),
                    )
                })?,
        )
    } else {
        None
    };
    Ok(GameAction::Pass { booster_id })
}

fn automatic_pending_action(
    state: &GameState,
    player_id: PlayerId,
) -> Result<GameAction, RuleError> {
    RuleEngine::get_valid_actions(state, player_id)
        .into_iter()
        .find(|action| {
            matches!(
                action,
                GameAction::ChargePower { accept: false }
                    | GameAction::ChooseIncomeOrder {
                        charge_first: false
                    }
                    | GameAction::FinishGaiaDecision
                    | GameAction::SelectTinkeringTile { .. }
                    | GameAction::PlaceLostPlanet { .. }
            )
        })
        .ok_or_else(|| {
            RuleError::ActionNotAllowed(
                "virtual opponent has no automatic response for its pending decision".into(),
            )
        })
}

fn dev_bot_factions(human_faction: FactionId) -> Vec<FactionId> {
    [
        FactionId::Terrans,
        FactionId::Xenos,
        FactionId::Taklons,
        FactionId::HadschHallas,
        FactionId::Geodens,
        FactionId::Firaks,
        FactionId::Nevlas,
        FactionId::Tinkeroids,
        FactionId::Moweyds,
    ]
    .into_iter()
    .filter(|candidate| {
        *candidate != human_faction && *candidate != human_faction.other_board_side()
    })
    .take(3)
    .collect()
}

fn faction_label(faction: FactionId) -> &'static str {
    match faction {
        FactionId::Terrans => "테란",
        FactionId::Xenos => "제노스",
        FactionId::Taklons => "타클론",
        FactionId::HadschHallas => "하쉬 할라",
        FactionId::Geodens => "지오덴",
        FactionId::Firaks => "파이락",
        FactionId::Nevlas => "네블라",
        FactionId::Tinkeroids => "틴커로이드",
        FactionId::Moweyds => "모웨이드",
        FactionId::Lantids => "란티다",
        FactionId::Gleens => "글린",
        FactionId::Ambas => "앰바스",
        FactionId::Ivits => "아이비츠",
        FactionId::BalTaks => "발타크",
        FactionId::Bescods => "베스코드",
        FactionId::Itars => "아이타",
        FactionId::SpaceGiants => "스페이스 자이언트",
        FactionId::Darkanians => "다카니안",
    }
}

fn faction_home_planet(faction: FactionId) -> Option<PlanetType> {
    gaia_engine::data::load_factions()
        .factions
        .into_iter()
        .find(|data| data.faction_id() == Some(faction))
        .and_then(|data| data.home_planet_type())
}

fn automatic_starting_coord(
    state: &GameState,
    player_id: PlayerId,
    human_player: PlayerId,
) -> Option<HexCoord> {
    let faction = state.player(player_id)?.faction?;
    let home_planet = faction_home_planet(faction)?;
    let human_structures = state
        .player(human_player)
        .map(|player| {
            player
                .structures
                .iter()
                .map(|structure| structure.hex)
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    let mut candidates = state
        .board
        .hexes
        .values()
        .filter(|hex| {
            hex.planet.as_ref().is_some_and(|planet| {
                planet.planet_type == home_planet
                    && !planet.is_gaia_formed
                    && planet.owner.is_none()
                    && hex.structures.is_empty()
            })
        })
        .map(|hex| hex.coord)
        .collect::<Vec<_>>();
    candidates.sort_by_key(|coord| {
        let human_distance = human_structures
            .iter()
            .map(|human| coord.distance(human))
            .min()
            .unwrap_or(u32::MAX);
        (human_distance, coord.q, coord.r)
    });
    candidates.into_iter().next()
}

fn dev_setup_error(error: gaia_engine::RuleError) -> ServerError {
    ServerError::Internal(format!("dev game setup failed: {error}"))
}

#[cfg(test)]
mod tests {
    use std::collections::HashSet;

    use super::{auto_advance_dev_setup, build_dev_game_state, enter_dev_power_charge};
    use gaia_engine::{
        game_state::{FactionId, PlacedStructure, PlanetType, StructureType},
        GamePhase, Randomizer, RuleEngine, SetupAction, SetupPhase,
    };

    use crate::room::manager::{Room, RoomState};

    fn action_phase_dev_room() -> (Room, gaia_engine::game_state::HexCoord) {
        let setup = Randomizer::generate_setup("dev-power-charge")
            .unwrap_or_else(|error| panic!("setup should be generated: {error}"));
        let mut state = build_dev_game_state(
            "DEV003",
            "dev-power-charge",
            7,
            &[8, 9, 10],
            &setup,
            FactionId::Terrans,
        )
        .unwrap_or_else(|error| panic!("dev game should be built: {error}"));
        state.phase = GamePhase::ActionPhase { active_player: 0 };
        let coord = state
            .board
            .hexes
            .keys()
            .next()
            .copied()
            .unwrap_or_else(|| panic!("dev board should contain a hex"));
        state
            .board
            .hexes
            .get_mut(&coord)
            .unwrap_or_else(|| panic!("selected hex should exist"))
            .structures
            .push(PlacedStructure {
                owner: 7,
                kind: StructureType::ResearchLab,
            });

        (
            Room {
                code: "DEV003".into(),
                name: "DEV003".into(),
                password_hash: None,
                host_player: 7,
                players: vec![(7, "DEV".into(), true)],
                state: RoomState::InGame,
                game_state: Some(state),
                setup: Some(setup),
                seed: "dev-power-charge".into(),
                revision: 0,
                connected: HashSet::from([7]),
                paused: false,
                dev_human_player: Some(7),
                dev_bot_action_counts: std::collections::HashMap::new(),
                dev_bot_action_round: 0,
                ai_level: None,
            },
            coord,
        )
    }

    #[test]
    fn dev_setup_accepts_expansion_factions_with_special_starting_structures() {
        let setup = Randomizer::generate_setup("dev-expansion-colors")
            .unwrap_or_else(|e| panic!("setup: {e}"));
        for faction in [FactionId::Tinkeroids, FactionId::Moweyds] {
            let state = build_dev_game_state(
                "DEVX01",
                "dev-expansion-colors",
                7,
                &[8, 9, 10],
                &setup,
                faction,
            )
            .unwrap_or_else(|e| panic!("{faction:?} setup: {e}"));
            assert!(matches!(
                state.phase,
                GamePhase::Setup(SetupPhase::StartingStructures { .. })
            ));
            assert_eq!(
                state
                    .player(7)
                    .unwrap_or_else(|| panic!("human"))
                    .expensive_terraforming_planet_types
                    .len(),
                3
            );
        }
    }

    #[test]
    fn manual_dev_control_keeps_bot_seats_interactive_and_authenticates_controller() {
        let (mut room, _) = action_phase_dev_room();
        let state = room
            .game_state
            .as_mut()
            .unwrap_or_else(|| panic!("DEV state"));
        state.dev_controller = Some(7);
        state.phase = GamePhase::Setup(SetupPhase::StartingStructures {
            active_player: 8,
            placement_index: 1,
            kind: StructureType::Mine,
        });
        let before = serde_json::to_value(&*state).unwrap_or_else(|e| panic!("serialize: {e}"));
        assert!(super::auto_advance_dev_setup(state, 7)
            .unwrap_or_else(|e| panic!("setup: {e}"))
            .is_empty());
        assert_eq!(
            serde_json::to_value(&*state).unwrap_or_else(|e| panic!("serialize: {e}")),
            before
        );
        assert_eq!(super::acting_player(&room, 7), 8);
        assert_eq!(super::acting_player(&room, 9), 9);
        room.game_state
            .as_mut()
            .unwrap_or_else(|| panic!("DEV state"))
            .phase = GamePhase::ActionPhase { active_player: 2 };
        assert_eq!(super::acting_player(&room, 7), 9);
        assert!(super::auto_advance_dev_actions(&mut room, 7)
            .unwrap_or_else(|e| panic!("actions: {e}"))
            .is_empty());
        assert_eq!(super::acting_player(&room, 7), 9);
        room.game_state
            .as_mut()
            .unwrap_or_else(|| panic!("DEV state"))
            .dev_controller = None;
        assert_eq!(super::acting_player(&room, 7), 7);
    }

    #[test]
    fn manual_dev_control_follows_charge_queue_and_survives_serialization() {
        let (mut room, coord) = action_phase_dev_room();
        let state = room
            .game_state
            .as_mut()
            .unwrap_or_else(|| panic!("DEV state"));
        state.dev_controller = Some(7);
        state.phase = GamePhase::ChargePowerPending {
            queue: vec![gaia_engine::game_state::PendingCharge {
                player: 10,
                hex: coord,
                max_power: 2,
            }],
            resume_active_player: Some(1),
        };
        let json = serde_json::to_value(&*state).unwrap_or_else(|e| panic!("serialize: {e}"));
        room.game_state =
            Some(serde_json::from_value(json).unwrap_or_else(|e| panic!("deserialize: {e}")));
        assert_eq!(super::acting_player(&room, 7), 10);
    }

    #[test]
    fn bots_pass_and_allow_all_six_rounds_to_finish() {
        let (mut room, _) = action_phase_dev_room();
        room.game_state
            .as_mut()
            .unwrap_or_else(|| panic!("DEV state should exist"))
            .round = 1;
        for round in 1..=6 {
            // Drive the human through the same pending decisions as a passive test player.
            for _ in 0..64 {
                super::auto_advance_dev_actions(&mut room, 7)
                    .unwrap_or_else(|error| panic!("DEV round should advance: {error}"));
                let state = room
                    .game_state
                    .as_mut()
                    .unwrap_or_else(|| panic!("DEV state should exist"));
                if matches!(state.phase, GamePhase::RoundScoring { .. }) {
                    break;
                }
                assert_eq!(super::required_player(state), Some(7));
                let action = if matches!(state.phase, GamePhase::ActionPhase { .. }) {
                    super::automatic_pass(state, 7)
                        .unwrap_or_else(|error| panic!("DEV round should advance: {error}"))
                } else {
                    super::automatic_pending_action(state, 7)
                        .unwrap_or_else(|error| panic!("DEV round should advance: {error}"))
                };
                RuleEngine::apply_action(state, 7, action)
                    .unwrap_or_else(|error| panic!("DEV round should advance: {error}"));
            }
            let state = room
                .game_state
                .as_mut()
                .unwrap_or_else(|| panic!("DEV state should exist"));
            assert_eq!(state.round, round);
            assert!(state.players.iter().all(|player| player.passed));
            assert!(matches!(state.phase, GamePhase::RoundScoring { .. }));
            if round < 6 {
                RuleEngine::advance_to_next_round(state)
                    .unwrap_or_else(|error| panic!("DEV round should advance: {error}"));
            }
        }
    }

    #[test]
    fn starts_at_first_interactive_mine_placement() {
        let setup = Randomizer::generate_setup("dev-game-test")
            .unwrap_or_else(|error| panic!("setup should be generated: {error}"));
        let state = build_dev_game_state(
            "DEV001",
            "dev-game-test",
            7,
            &[8, 9, 10],
            &setup,
            FactionId::Terrans,
        )
        .unwrap_or_else(|error| panic!("dev game should be built: {error}"));

        assert!(matches!(
            state.phase,
            GamePhase::Setup(SetupPhase::StartingStructures {
                active_player: 7,
                placement_index: 0,
                kind: StructureType::Mine,
            })
        ));
        let player = state
            .player(7)
            .unwrap_or_else(|| panic!("dev player should exist"));
        assert_eq!(player.faction, Some(FactionId::Terrans));
        assert!(player.structures.is_empty());
        assert_eq!(player.resources.power.bowl1, 4);
        assert_eq!(player.resources.power.bowl2, 4);
        assert_eq!(player.resources.power.bowl3, 0);
        assert_eq!(player.resources.ore, 4);
        assert_eq!(player.resources.credits, 15);
        assert_eq!(player.resources.knowledge, 3);
        assert_eq!(player.resources.qic, 1);
        assert_eq!(state.players.len(), 4);
        assert_eq!(state.boosters.len(), 7);
        let mut bids = state
            .players
            .iter()
            .map(|player| player.setup_bid_vp)
            .collect::<Vec<_>>();
        bids.sort_unstable();
        assert_eq!(bids, vec![0, 1, 2, 4]);
    }

    #[test]
    fn virtual_opponents_follow_starting_order_and_leave_four_boosters_for_human() {
        let setup = Randomizer::generate_setup("dev-opponent-placement")
            .unwrap_or_else(|error| panic!("setup should be generated: {error}"));
        let mut state = build_dev_game_state(
            "DEV002",
            "dev-opponent-placement",
            7,
            &[8, 9, 10],
            &setup,
            FactionId::Terrans,
        )
        .unwrap_or_else(|error| panic!("dev game should be built: {error}"));

        let first_terra = state
            .board
            .hexes
            .values()
            .find(|hex| {
                hex.planet
                    .as_ref()
                    .is_some_and(|planet| planet.planet_type == PlanetType::Terra)
            })
            .map(|hex| hex.coord)
            .unwrap_or_else(|| panic!("a Terra planet should exist"));
        RuleEngine::apply_setup_action(
            &mut state,
            7,
            SetupAction::PlaceStartingStructure { coord: first_terra },
        )
        .unwrap_or_else(|error| panic!("human first mine should be placed: {error}"));
        auto_advance_dev_setup(&mut state, 7)
            .unwrap_or_else(|error| panic!("virtual setup should advance: {error}"));

        assert!(matches!(
            state.phase,
            GamePhase::Setup(SetupPhase::StartingStructures {
                active_player: 7,
                placement_index: 7,
                kind: StructureType::Mine,
            })
        ));
        assert_eq!(
            state.player(7).map(|player| player.structures.len()),
            Some(1)
        );
        for bot_id in [8, 9, 10] {
            assert_eq!(
                state.player(bot_id).map(|player| player.structures.len()),
                Some(2)
            );
        }
        let second_terra = state
            .board
            .hexes
            .values()
            .find(|hex| {
                hex.planet.as_ref().is_some_and(|planet| {
                    planet.planet_type == PlanetType::Terra && planet.owner.is_none()
                })
            })
            .map(|hex| hex.coord)
            .unwrap_or_else(|| panic!("a second Terra planet should exist"));
        RuleEngine::apply_setup_action(
            &mut state,
            7,
            SetupAction::PlaceStartingStructure {
                coord: second_terra,
            },
        )
        .unwrap_or_else(|error| panic!("human second mine should be placed: {error}"));
        auto_advance_dev_setup(&mut state, 7)
            .unwrap_or_else(|error| panic!("virtual booster choices should advance: {error}"));

        assert!(matches!(
            state.phase,
            GamePhase::Setup(SetupPhase::StartingBoosters {
                active_player: 7,
                selection_index: 3,
            })
        ));
        assert_eq!(state.boosters.len(), 4);
    }

    #[test]
    fn dev_human_can_open_charge_decision_from_an_owned_building() {
        let (mut room, coord) = action_phase_dev_room();

        enter_dev_power_charge(&mut room, 7, coord)
            .unwrap_or_else(|error| panic!("DEV charge trigger should succeed: {error}"));

        assert!(matches!(
            room.game_state.as_ref().map(|state| &state.phase),
            Some(GamePhase::ChargePowerPending {
                queue,
                resume_active_player: Some(0),
            }) if queue == &vec![gaia_engine::game_state::PendingCharge {
                player: 7,
                hex: coord,
                max_power: 2,
            }]
        ));
    }

    #[test]
    fn dev_charge_trigger_rejects_an_opponent_building() {
        let (mut room, coord) = action_phase_dev_room();
        room.game_state
            .as_mut()
            .and_then(|state| state.board.hexes.get_mut(&coord))
            .and_then(|hex| hex.structures.first_mut())
            .unwrap_or_else(|| panic!("test structure should exist"))
            .owner = 8;

        let result = enter_dev_power_charge(&mut room, 7, coord);

        assert!(matches!(
            result,
            Err(gaia_engine::RuleError::ActionNotAllowed(_))
        ));
    }

    #[test]
    fn ordinary_rooms_cannot_use_the_dev_charge_trigger() {
        let (mut room, coord) = action_phase_dev_room();
        room.dev_human_player = None;

        let result = enter_dev_power_charge(&mut room, 7, coord);

        assert!(matches!(
            result,
            Err(gaia_engine::RuleError::ActionNotAllowed(_))
        ));
        assert!(matches!(
            room.game_state.as_ref().map(|state| &state.phase),
            Some(GamePhase::ActionPhase { active_player: 0 })
        ));
    }

    #[test]
    fn ai_game_factions_are_four_distinct_boards_and_honor_the_human_choice() {
        for seed in ["a", "b", "c", "ai-seats-regression", "x9"] {
            let (human, bots) = super::ai_game_factions(seed, None);
            let all: Vec<_> = std::iter::once(human).chain(bots.iter().copied()).collect();
            assert_eq!(all.len(), 4, "{seed}");
            for (i, a) in all.iter().enumerate() {
                for b in &all[i + 1..] {
                    assert!(
                        a != b && a.other_board_side() != *b,
                        "{seed}: {a:?} vs {b:?}"
                    );
                }
            }
        }
        let (human, bots) = super::ai_game_factions("a", Some(FactionId::Ivits));
        assert_eq!(human, FactionId::Ivits);
        assert!(
            !bots.contains(&FactionId::Ivits)
                && !bots.contains(&FactionId::Ivits.other_board_side())
        );
        assert_ne!(
            super::ai_game_factions("a", None),
            super::ai_game_factions("b", None)
        );
    }
}
