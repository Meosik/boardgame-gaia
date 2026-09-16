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
