use gaia_engine::{
    error::RuleError,
    game_state::{
        BrainstoneLocation, FactionId, GameEvent, GamePhase, HexCoord, PendingCharge, PlanetType,
        PlayerId, SetupPhase, StructureType,
    },
    GameSetup, GameState, MapEngine, RuleEngine, SetupAction,
};
use gaia_protocol::{CommandId, Revision};
use sha2::{Digest, Sha256};

use crate::{
    coordinator::{self, broadcast_snapshot, CommandResult},
    error::{ServerError, ServerResult},
    room::manager::Room,
    state::AppState,
};

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
    let bot_factions = dev_bot_factions(faction);
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
        GamePhase::Setup(SetupPhase::StartingStructures {
            active_player,
            placement_index: 0,
            kind: StructureType::Mine,
        }) if active_player == player_id
    ) {
        return Err(ServerError::Internal(
            "dev game did not reach starting mine placement".into(),
        ));
    }
    prepare_dev_human_resources(&mut state, player_id)?;
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

/// The local UI harness is meant to exercise power actions repeatedly without playing several
/// setup rounds first. Only the human DEV seat receives this deliberately non-standard supply;
/// virtual opponents and ordinary games keep their normal power-cycle totals.
pub(crate) fn prepare_dev_human_resources(
    state: &mut GameState,
    player_id: PlayerId,
) -> ServerResult<()> {
    let player = state
        .player_mut(player_id)
        .ok_or_else(|| ServerError::Internal("dev player disappeared during setup".into()))?;
    player.resources.ore = 250;
    player.resources.credits = 250;
    player.resources.knowledge = 250;
    player.resources.qic = 250;
    let power = &mut player.resources.power;
    power.bowl1 = 0;
    power.bowl2 = 0;
    power.bowl3 = 250;
    if matches!(
        power.brainstone,
        Some(BrainstoneLocation::Area1 | BrainstoneLocation::Area2)
    ) {
        power.brainstone = Some(BrainstoneLocation::Area3);
    }
    Ok(())
}

/// Advances every virtual opponent through the normal setup actions until the human seat must
/// act again. Opponent planets are chosen deterministically, preferring legal home planets nearest
/// to the human's existing mines so opponent-adjacency upgrade costs are easy to exercise.
pub fn auto_advance_dev_setup(
    state: &mut GameState,
    human_player: PlayerId,
) -> Result<Vec<GameEvent>, RuleError> {
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
        _ => "상대",
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
            },
            coord,
        )
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
        assert_eq!(player.resources.power.bowl1, 0);
        assert_eq!(player.resources.power.bowl2, 0);
        assert_eq!(player.resources.power.bowl3, 250);
        assert_eq!(player.resources.ore, 250);
        assert_eq!(player.resources.credits, 250);
        assert_eq!(player.resources.knowledge, 250);
        assert_eq!(player.resources.qic, 250);
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
}
