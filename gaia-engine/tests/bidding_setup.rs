use gaia_engine::game_state::{FactionId, GamePhase, SetupPhase};
use gaia_engine::rules::actions::SetupAction;
use gaia_engine::{MapEngine, Randomizer, RuleEngine, ScoringEngine};

fn apply(game: &mut gaia_engine::GameState, player: u8, action: SetupAction) {
    RuleEngine::apply_setup_action(game, player, action)
        .unwrap_or_else(|error| panic!("setup action for player {player} failed: {error}"));
}

#[test]
fn three_auctions_assign_factions_and_turn_order_then_auto_assign_fourth_player() {
    let setup = Randomizer::generate_bidding_setup("fixed-bidding-flow")
        .unwrap_or_else(|error| panic!("valid seed should generate a bidding setup: {error}"));
    assert_eq!(setup.factions.len(), 4);
    for faction in &setup.factions {
        assert!(!setup
            .factions
            .iter()
            .any(|candidate| candidate != faction && *candidate == faction.other_board_side()));
    }

    let offered = setup.factions.clone();
    let players = vec![
        (7, "Host".to_string()),
        (3, "P2".to_string()),
        (9, "P3".to_string()),
        (1, "P4".to_string()),
    ];
    let mut game = MapEngine::init_game_state_with_bidding("BID1", "BID1", &players, &setup)
        .unwrap_or_else(|error| {
            panic!("four players and four factions should initialize: {error}")
        });

    assert_eq!(
        game.phase,
        GamePhase::Setup(SetupPhase::Bidding { active_player: 7 })
    );

    // Auction 1: player 3 wins for 4 VP.
    apply(&mut game, 7, SetupAction::PlaceBid { amount: 3 });
    apply(&mut game, 3, SetupAction::PlaceBid { amount: 4 });
    apply(&mut game, 9, SetupAction::PassBid);
    apply(&mut game, 1, SetupAction::PassBid);
    apply(&mut game, 7, SetupAction::PassBid);
    assert_eq!(
        game.phase,
        GamePhase::Setup(SetupPhase::BiddingChoice { winner: 3 })
    );
    apply(
        &mut game,
        3,
        SetupAction::ChooseBidReward {
            faction: offered[0],
            turn_position: 4,
        },
    );

    // The next auction resets to zero and starts clockwise/right of winner 3.
    let bidding = game
        .bidding
        .as_ref()
        .unwrap_or_else(|| panic!("bidding remains active"));
    assert_eq!(bidding.highest_bid, 0);
    assert_eq!(bidding.highest_bidder, None);
    assert!(bidding.passed_players.is_empty());
    assert_eq!(
        game.phase,
        GamePhase::Setup(SetupPhase::Bidding { active_player: 9 })
    );

    // Auction 2: player 1 wins for 2 VP.
    apply(&mut game, 9, SetupAction::PassBid);
    apply(&mut game, 1, SetupAction::PlaceBid { amount: 2 });
    apply(&mut game, 7, SetupAction::PassBid);
    apply(
        &mut game,
        1,
        SetupAction::ChooseBidReward {
            faction: offered[1],
            turn_position: 1,
        },
    );
    assert_eq!(
        game.phase,
        GamePhase::Setup(SetupPhase::Bidding { active_player: 7 })
    );

    // Auction 3: host wins for 1 VP. Player 9 then gets the final faction,
    // position, and a zero bid without a fourth auction.
    apply(&mut game, 7, SetupAction::PlaceBid { amount: 1 });
    apply(&mut game, 9, SetupAction::PassBid);
    apply(
        &mut game,
        7,
        SetupAction::ChooseBidReward {
            faction: offered[2],
            turn_position: 3,
        },
    );

    assert!(matches!(
        game.phase,
        GamePhase::Setup(SetupPhase::StartingStructures {
            active_player,
            placement_index: 0,
            ..
        }) if game.turn_order.contains(&active_player)
    ));
    assert_eq!(game.round, 0);
    assert_eq!(game.turn_order, vec![1, 9, 7, 3]);
    let player_3 = game
        .player(3)
        .unwrap_or_else(|| panic!("player 3 should exist"));
    assert_eq!(player_3.faction, Some(offered[0]));
    assert_eq!(player_3.setup_bid_vp, 4);
    let player_1 = game
        .player(1)
        .unwrap_or_else(|| panic!("player 1 should exist"));
    assert_eq!(player_1.faction, Some(offered[1]));
    assert_eq!(player_1.setup_bid_vp, 2);
    let player_7 = game
        .player(7)
        .unwrap_or_else(|| panic!("player 7 should exist"));
    assert_eq!(player_7.faction, Some(offered[2]));
    assert_eq!(player_7.setup_bid_vp, 1);
    let player_9 = game
        .player(9)
        .unwrap_or_else(|| panic!("player 9 should exist"));
    assert_eq!(player_9.faction, Some(offered[3]));
    assert_eq!(player_9.setup_bid_vp, 0);
    assert!(
        game.players.iter().all(|player| player.vp == 10),
        "bids must not alter VP before final scoring"
    );

    let breakdowns = ScoringEngine::calculate_final_scoring_breakdown(&game);
    for (player, expected_penalty) in [(3, -4), (1, -2), (7, -1), (9, 0)] {
        let breakdown = breakdowns
            .iter()
            .find(|breakdown| breakdown.player_id == player)
            .unwrap_or_else(|| panic!("player {player} should have a final score breakdown"));
        assert_eq!(breakdown.bid_penalty_vp, expected_penalty);
        assert_eq!(
            breakdown.total_vp,
            breakdown.gameplay_vp
                + breakdown.bid_penalty_vp
                + breakdown.final_tile_vp
                + breakdown.research_vp
                + breakdown.resource_vp
                + breakdown.faction_vp
        );
    }
}

#[test]
fn bidding_initializer_rejects_non_four_player_or_non_four_faction_setup() {
    let setup = Randomizer::generate_bidding_setup("invalid-bidding-count")
        .unwrap_or_else(|error| panic!("valid seed should generate a bidding setup: {error}"));
    let three_players = vec![
        (0, "P1".to_string()),
        (1, "P2".to_string()),
        (2, "P3".to_string()),
    ];

    assert!(
        MapEngine::init_game_state_with_bidding("BID2", "BID2", &three_players, &setup).is_err()
    );

    let mut too_many_factions = setup.clone();
    too_many_factions.factions.push(FactionId::Terrans);
    let four_players = vec![
        (0, "P1".to_string()),
        (1, "P2".to_string()),
        (2, "P3".to_string()),
        (3, "P4".to_string()),
    ];
    assert!(MapEngine::init_game_state_with_bidding(
        "BID3",
        "BID3",
        &four_players,
        &too_many_factions
    )
    .is_err());
}
