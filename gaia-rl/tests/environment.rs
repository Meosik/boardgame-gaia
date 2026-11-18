use gaia_engine::rules::engine::AiDecision;
use gaia_engine::{GameAction, RuleEngine};
use gaia_rl::{EnvError, Environment};

#[test]
fn reset_is_seeded_and_preserves_physical_faction_pairs() {
    let a = Environment::new("rl-reset", 10000).unwrap();
    let b = Environment::new("rl-reset", 10000).unwrap();
    assert_same_json(&a.state().serialize(), &b.state().serialize(), "state");
    assert_eq!(a.legal_actions(), b.legal_actions());
    let factions: Vec<_> = a.state().players.iter().map(|p| p.faction.unwrap()).collect();
    for f in &factions { assert!(!factions.contains(&f.other_board_side())); }
}

#[test]
fn order_suffix_keeps_map_and_factions_and_reorders_setup() {
    let plain = Environment::new("quartet-d-113082", 10000).unwrap();
    let mut ordered = Environment::new("quartet-d-113082@order=2,0,3,1", 10000).unwrap();
    let factions = |env: &Environment| env.state().players.iter().map(|p| p.faction).collect::<Vec<_>>();
    assert_eq!(factions(&plain), factions(&ordered));
    assert_same_json(
        &serde_json::to_value(&plain.state().board).unwrap(),
        &serde_json::to_value(&ordered.state().board).unwrap(),
        "board",
    );
    assert_eq!(plain.state().turn_order, vec![0, 1, 2, 3]);
    assert_eq!(ordered.state().turn_order, vec![2, 0, 3, 1]);
    // Advanced setup: first mines in turn order, then the second stage backwards, then boosters backwards.
    let mut placers = Vec::new();
    let mut pickers = Vec::new();
    loop {
        let player = ordered.current_decision_player().unwrap().unwrap();
        match &ordered.legal_actions()[0] {
            AiDecision::Setup(gaia_engine::SetupAction::PlaceStartingStructure { .. }) => placers.push(player),
            AiDecision::Setup(gaia_engine::SetupAction::SelectStartingBooster { .. }) => pickers.push(player),
            _ => break,
        }
        ordered.step(ordered.decision_id(), 0).unwrap();
    }
    // Some placements are forced and applied automatically, so only the first placer is fixed here.
    assert_eq!(placers[0], 2);
    assert_eq!(pickers, vec![1, 3, 0, 2]);
    assert!(Environment::new("quartet-d-113082@order=2,0,3", 10000).is_err());
    assert!(Environment::new("quartet-d-113082@order=2,0,3,3", 10000).is_err());
}

fn faction_names(env: &Environment) -> Vec<String> {
    env.state().players.iter().map(|p| format!("{:?}", p.faction.unwrap())).collect()
}

fn field_json<T: serde::Serialize>(field: &T) -> serde_json::Value {
    serde_json::to_value(field).unwrap()
}

#[test]
fn factions_suffix_assigns_factions_by_seat_and_keeps_the_setup() {
    let seed = "quartet-e-88365";
    let plain = Environment::new(seed, 10000).unwrap();
    let named = Environment::new(&format!("{seed}@factions=Darkanians,BalTaks,Itars,Ivits"), 10000).unwrap();
    assert_eq!(faction_names(&named), vec!["Darkanians", "BalTaks", "Itars", "Ivits"]);
    let (p, n) = (plain.state(), named.state());
    assert_same_json(&field_json(&p.board), &field_json(&n.board), "board");
    assert_same_json(&field_json(&p.round_tiles), &field_json(&n.round_tiles), "round_tiles");
    assert_same_json(&field_json(&p.final_scoring_tiles), &field_json(&n.final_scoring_tiles), "final_scoring_tiles");
    assert_same_json(&field_json(&p.research_board), &field_json(&n.research_board), "research_board");
    assert_same_json(&field_json(&p.spaceship_boards), &field_json(&n.spaceship_boards), "spaceship_boards");
    assert_same_json(
        &field_json(&p.terraforming_color_order),
        &field_json(&n.terraforming_color_order),
        "terraforming_color_order",
    );
    let a = Environment::new(&format!("{seed}@factions=Darkanians,BalTaks,Itars,Ivits@order=2,0,3,1"), 10000).unwrap();
    let b = Environment::new(&format!("{seed}@order=2,0,3,1@factions=Darkanians,BalTaks,Itars,Ivits"), 10000).unwrap();
    assert_same_json(&a.state().serialize(), &b.state().serialize(), "state");
    assert_eq!(a.state().turn_order, vec![2, 0, 3, 1]);
    assert_eq!(faction_names(&a), vec!["Darkanians", "BalTaks", "Itars", "Ivits"]);
    assert_eq!(faction_names(&b), faction_names(&a));
    let other_side = format!("{:?}", gaia_engine::game_state::FactionId::Terrans.other_board_side());
    for bad in [
        format!("{seed}@factions=Terrans,Xenos,Taklons"),
        format!("{seed}@factions=Terran,Xenos,Taklons,Geodens"),
        format!("{seed}@factions=Terrans,Terrans,Xenos,Taklons"),
        format!("{seed}@factions=Terrans,{other_side},Xenos,Taklons"),
        format!("{seed}@faction=Terrans,Xenos,Taklons,Geodens"),
        format!("{seed}@order=0,1,2,3@order=0,1,2,3"),
    ] {
        assert!(Environment::new(&bad, 10000).is_err(), "{bad} should be refused");
    }
}

#[test]
fn tiles_suffix_keeps_the_map_and_takes_the_rest_of_the_setup_from_the_tile_seed() {
    let f = "@factions=Terrans,Xenos,Taklons,Geodens";
    let new = |seed: &str| Environment::new(&format!("{seed}{f}"), 10000).unwrap();
    let base = new("quartet-e-88365");
    let tile = new("quartet-d-113082");
    let mixed = new("quartet-e-88365@tiles=quartet-d-113082");
    let same = new("quartet-e-88365@tiles=quartet-e-88365");
    assert_same_json(&same.state().serialize(), &base.state().serialize(), "state");
    let (b, t, m) = (base.state(), tile.state(), mixed.state());
    assert_same_json(&field_json(&m.board), &field_json(&b.board), "board");
    assert_same_json(&field_json(&m.round_tiles), &field_json(&t.round_tiles), "round_tiles");
    assert_same_json(&field_json(&m.boosters), &field_json(&t.boosters), "boosters");
    assert_same_json(&field_json(&m.final_scoring_tiles), &field_json(&t.final_scoring_tiles), "final_scoring_tiles");
    assert_same_json(&field_json(&m.research_board), &field_json(&t.research_board), "research_board");
    assert_same_json(&field_json(&m.spaceship_boards), &field_json(&t.spaceship_boards), "spaceship_boards");
    assert_same_json(
        &field_json(&m.terraforming_color_order),
        &field_json(&t.terraforming_color_order),
        "terraforming_color_order",
    );
    assert_ne!(field_json(&b.board), field_json(&t.board));
    assert_ne!(field_json(&b.research_board), field_json(&t.research_board));
    let drawn = Environment::new("quartet-e-88365@tiles=quartet-d-113082", 10000).unwrap();
    let plain = Environment::new("quartet-e-88365", 10000).unwrap();
    assert_eq!(faction_names(&drawn), faction_names(&plain));
    assert!(Environment::new("quartet-e-88365@tiles=", 10000).is_err());
}

#[test]
fn stale_indices_and_failed_steps_do_not_mutate() {
    let mut env = Environment::new("rl-stale", 10000).unwrap();
    let old = env.state().serialize();
    assert!(matches!(env.step(9, 0), Err(EnvError::Stale { .. })));
    assert!(matches!(env.step(0, usize::MAX), Err(EnvError::InvalidIndex(_))));
    assert_eq!(old, env.state().serialize());
    env.reset("rl-stale").unwrap();
    assert!(matches!(env.step(0, 0), Err(EnvError::Stale { .. })));
}

#[test]
fn fork_matches_real_steps_without_mutating_parent_or_siblings() {
    let mut parent = Environment::new("rl-fork", 10000).unwrap();
    let before = serde_json::to_value(parent.snapshot().unwrap()).unwrap();
    let mut branch = parent.fork(parent.decision_id(), 0).unwrap();
    let sibling = parent.fork(parent.decision_id(), 0).unwrap();
    assert_same_json(&branch.state().serialize(), &sibling.state().serialize(), "siblings");
    assert_eq!(serde_json::to_value(parent.snapshot().unwrap()).unwrap(), before);
    parent.step(parent.decision_id(), 0).unwrap();
    assert_eq!(parent.legal_actions(), branch.legal_actions());
    assert_same_json(&parent.state().serialize(), &branch.state().serialize(), "real step");
    let sibling_before = serde_json::to_value(sibling.snapshot().unwrap()).unwrap();
    branch.step(branch.decision_id(), 0).unwrap();
    assert_eq!(serde_json::to_value(sibling.snapshot().unwrap()).unwrap(), sibling_before);
}

#[test]
fn fork_preserves_stale_index_and_step_limit_guards() {
    let env = Environment::new("rl-fork-guards", 1).unwrap();
    let before = serde_json::to_value(env.snapshot().unwrap()).unwrap();
    assert!(matches!(env.fork(99, 0), Err(EnvError::Stale { .. })));
    assert!(matches!(env.fork(0, usize::MAX), Err(EnvError::InvalidIndex(_))));
    let branch = env.fork(0, 0).unwrap();
    assert!(matches!(branch.fork(branch.decision_id(), 0), Err(EnvError::StepLimit(1))));
    assert_eq!(serde_json::to_value(env.snapshot().unwrap()).unwrap(), before);
}

#[test]
fn state_preview_matches_paid_steps_without_changing_parent() {
    let mut env = Environment::new("rl-preview", 10000).unwrap();
    for _ in 0..40 {
        if env.is_terminal() { break; }
        let before = serde_json::to_value(env.snapshot().unwrap()).unwrap();
        for index in [0, env.legal_actions().len() - 1] {
            let preview = env.preview_state(env.decision_id(), index).unwrap();
            let branch = env.fork(env.decision_id(), index).unwrap();
            assert_same_json(&preview.serialize(), &branch.state().serialize(), "preview");
            assert_eq!(serde_json::to_value(env.snapshot().unwrap()).unwrap(), before);
        }
        let index = env.legal_actions().iter().position(|a|
            matches!(a, AiDecision::Game(GameAction::Pass { .. }))).unwrap_or(0);
        env.step(env.decision_id(), index).unwrap();
    }
}

#[test]
fn state_preview_preserves_validation_and_truncation_guards() {
    let mut env = Environment::new("rl-preview-guards", 1).unwrap();
    assert!(matches!(env.preview_state(99, 0), Err(EnvError::Stale { .. })));
    assert!(matches!(env.preview_state(0, usize::MAX), Err(EnvError::InvalidIndex(_))));
    env.step(0, 0).unwrap();
    let before = serde_json::to_value(env.snapshot().unwrap()).unwrap();
    assert!(matches!(env.preview_state(env.decision_id(), 0), Err(EnvError::StepLimit(1))));
    assert_eq!(serde_json::to_value(env.snapshot().unwrap()).unwrap(), before);
}

#[test]
fn identical_actions_finish_identically_and_all_candidates_validate() {
    let mut a = Environment::new("rl-complete", 10000).unwrap();
    let mut b = Environment::new("rl-complete", 10000).unwrap();
    while !a.is_terminal() {
        assert_eq!(a.legal_actions(), b.legal_actions());
        let player = a.current_decision_player().unwrap().unwrap();
        for candidate in a.legal_actions() {
            if let AiDecision::Game(action) = candidate {
                RuleEngine::validate_action(a.state(), player, action).unwrap();
            }
        }
        // Deliberately fast deterministic policy for lifecycle coverage, not a strength test.
        let index = a.legal_actions().iter().position(|a| matches!(a, AiDecision::Game(GameAction::Pass { .. }))).unwrap_or(0);
        a.step(a.decision_id(), index).unwrap();
        b.step(b.decision_id(), index).unwrap();
        assert_same_json(&a.state().serialize(), &b.state().serialize(), "state");
    }
    assert_eq!(a.final_scores(), b.final_scores());
    assert!(a.rewards().iter().sum::<f32>().abs() < 0.00001);
    assert!(a.legal_actions().is_empty());
}

#[test]
fn step_limit_is_not_a_terminal_win() {
    let mut env = Environment::new("rl-limit", 1).unwrap();
    env.step(env.decision_id(), 0).unwrap();
    let snapshot = env.state().serialize();
    assert!(matches!(env.step(env.decision_id(), 0), Err(EnvError::StepLimit(1))));
    assert!(!env.is_terminal());
    assert_eq!(env.final_scores(), None);
    assert_eq!(env.rewards(), [0.0; 4]);
    assert_eq!(snapshot, env.state().serialize());
}

fn assert_same_json(a: &serde_json::Value, b: &serde_json::Value, path: &str) {
    match (a, b) {
        (serde_json::Value::Object(a), serde_json::Value::Object(b)) => {
            assert_eq!(a.keys().collect::<Vec<_>>(), b.keys().collect::<Vec<_>>(), "{path}");
            for (key, value) in a { assert_same_json(value, &b[key], &format!("{path}.{key}")); }
        }
        (serde_json::Value::Array(a), serde_json::Value::Array(b)) => {
            assert_eq!(a.len(), b.len(), "{path}");
            for (i, (a, b)) in a.iter().zip(b).enumerate() { assert_same_json(a, b, &format!("{path}[{i}]")); }
        }
        _ => assert_eq!(a, b, "{path}"),
    }
}
