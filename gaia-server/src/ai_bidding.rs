//! Bidding for AI seats (the teacher workers do not handle the setup auction).
//!
//! Each option is a (faction, turn position) pair. Its value is a faction prior plus a small
//! turn-position term; an AI bids up to half of what its best option is worth over an average
//! remaining option, and as the auction winner takes its best option.
//!
//! The faction priors are the midpoints of the expected scores in uiqoo's guide B19 (2023,
//! Steam AI games, maps chosen by the player): S 180–220, A 170–200, B 160–190, C 130–190.
//! B19 gives no Lost Fleet faction, so those four use the median prior. The turn-position term
//! (3/2/1/0 VP for 1st..4th) and the one-half bid factor are judgments, not measurements, and are
//! kept small so AI bids stay within the usual 0–10 VP range of human games.
use gaia_engine::{
    game_state::{FactionId, GamePhase, PlayerId, SetupPhase},
    BiddingStage, GameState, SetupAction,
};

/// B19 expected-score midpoints; Lost Fleet factions get the median of the others.
pub fn faction_prior(faction: FactionId) -> f64 {
    match faction {
        FactionId::Ivits => 205.0,
        FactionId::Firaks => 200.0,
        FactionId::Terrans | FactionId::Itars => 195.0,
        FactionId::HadschHallas | FactionId::BalTaks => 185.0,
        FactionId::Nevlas => 180.0,
        FactionId::Geodens | FactionId::Taklons | FactionId::Ambas => 175.0,
        FactionId::Gleens | FactionId::Xenos => 170.0,
        FactionId::Bescods => 165.0,
        FactionId::Lantids => 155.0,
        FactionId::Tinkeroids
        | FactionId::Moweyds
        | FactionId::SpaceGiants
        | FactionId::Darkanians => 177.5,
    }
}

/// Earlier seats act first each round; worth a little (judgment, see module docs).
pub fn turn_position_value(position: u8) -> f64 {
    match position {
        1 => 3.0,
        2 => 2.0,
        3 => 1.0,
        _ => 0.0,
    }
}

const BID_FACTOR: f64 = 0.5;

fn options(factions: &[FactionId], positions: &[u8]) -> Vec<(f64, FactionId, u8)> {
    let mut all = Vec::new();
    for &faction in factions {
        for &position in positions {
            all.push((
                faction_prior(faction) + turn_position_value(position),
                faction,
                position,
            ));
        }
    }
    // Highest value first; ties broken by enum order and position for determinism.
    all.sort_by(|a, b| {
        b.0.partial_cmp(&a.0)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then((a.1 as u8).cmp(&(b.1 as u8)))
            .then(a.2.cmp(&b.2))
    });
    all
}

/// The most VP this AI pays to choose first now.
pub fn willing_bid(factions: &[FactionId], positions: &[u8]) -> u32 {
    let all = options(factions, positions);
    let Some(best) = all.first() else {
        return 0;
    };
    let mean = all.iter().map(|option| option.0).sum::<f64>() / all.len() as f64;
    ((best.0 - mean) * BID_FACTOR).floor().max(0.0) as u32
}

/// The setup action for an AI seat in an auction phase, or `None` outside one.
pub fn decide(state: &GameState, player: PlayerId) -> Option<SetupAction> {
    let bidding = state.bidding.as_ref()?;
    match (&state.phase, &bidding.stage) {
        (GamePhase::Setup(SetupPhase::Bidding { active_player }), BiddingStage::Auction)
            if *active_player == player =>
        {
            let willing = willing_bid(
                &bidding.available_factions,
                &bidding.available_turn_positions,
            );
            let next = bidding.highest_bid + 1;
            if bidding.highest_bidder != Some(player) && next <= willing {
                Some(SetupAction::PlaceBid { amount: next })
            } else {
                Some(SetupAction::PassBid)
            }
        }
        (
            GamePhase::Setup(SetupPhase::BiddingChoice { winner }),
            BiddingStage::WinnerChoice { .. },
        ) if *winner == player => {
            let (_, faction, turn_position) = *options(
                &bidding.available_factions,
                &bidding.available_turn_positions,
            )
            .first()?;
            Some(SetupAction::ChooseBidReward {
                faction,
                turn_position,
            })
        }
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bids_more_for_a_stronger_best_option_and_never_negative() {
        let strong = willing_bid(
            &[
                FactionId::Ivits,
                FactionId::Lantids,
                FactionId::Gleens,
                FactionId::Xenos,
            ],
            &[1, 2, 3, 4],
        );
        let flat = willing_bid(
            &[
                FactionId::Geodens,
                FactionId::Taklons,
                FactionId::Ambas,
                FactionId::Terrans,
            ],
            &[3, 4],
        );
        assert!(strong > flat, "{strong} vs {flat}");
        assert!(strong <= 20);
        assert_eq!(willing_bid(&[FactionId::Geodens], &[4]), 0);
    }

    #[test]
    fn the_winner_takes_the_best_faction_and_earliest_seat() {
        let best = options(&[FactionId::Lantids, FactionId::Firaks], &[2, 4]);
        assert_eq!((best[0].1, best[0].2), (FactionId::Firaks, 2));
    }

    #[test]
    fn four_ai_bidders_finish_the_auction_into_starting_structures() {
        use gaia_engine::{MapEngine, Randomizer, RuleEngine};
        for seed in ["bid-a", "bid-b", "bid-c", "bid-d", "bid-e"] {
            let setup = Randomizer::generate_bidding_setup(seed).expect("setup");
            let players: Vec<(PlayerId, String)> =
                (1..=4).map(|id| (id, format!("P{id}"))).collect();
            let mut state = MapEngine::init_game_state_with_bidding("BID", seed, &players, &setup)
                .expect("init");
            for _ in 0..200 {
                let player = match state.phase {
                    GamePhase::Setup(SetupPhase::Bidding { active_player }) => active_player,
                    GamePhase::Setup(SetupPhase::BiddingChoice { winner }) => winner,
                    _ => break,
                };
                let action = decide(&state, player).expect("an auction action");
                RuleEngine::apply_setup_action(&mut state, player, action).expect("legal");
            }
            assert!(
                matches!(
                    state.phase,
                    GamePhase::Setup(SetupPhase::StartingStructures { .. })
                ),
                "{seed}: {:?}",
                state.phase
            );
            let factions: Vec<_> = state.players.iter().filter_map(|p| p.faction).collect();
            assert_eq!(factions.len(), 4, "{seed}");
            assert!(state.players.iter().all(|p| p.setup_bid_vp <= 20), "{seed}");
        }
    }
}
