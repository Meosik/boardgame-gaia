//! Reproduce candidate-generation costs from a saved, trusted offline snapshot.
use gaia_engine::rules::engine::AiDecision;
use gaia_engine::RuleEngine;
use gaia_rl::DecisionSnapshot;
use std::time::Instant;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let input = args.next().ok_or("expected snapshot JSON path")?;
    let output = args.next().ok_or("expected new output JSON path")?;
    let snapshot: DecisionSnapshot = serde_json::from_slice(&std::fs::read(input)?)?;
    let indices: Vec<usize> = args.map(|arg| arg.parse()).collect::<Result<_, _>>()?;
    let mut results = Vec::new();
    for index in indices {
        let mut state = snapshot.state.clone();
        let actor = snapshot.player.ok_or("terminal input")?;
        let candidate = snapshot.candidates.get(index).ok_or("invalid index")?;
        match candidate {
            AiDecision::Game(action) => {
                RuleEngine::apply_action(&mut state, actor, action.clone())?
            }
            AiDecision::Setup(action) => {
                RuleEngine::apply_setup_action(&mut state, actor, action.clone())?
            }
        };
        RuleEngine::advance_automatic(&mut state)?;
        let actor = RuleEngine::decision_player(&state)?.ok_or("terminal continuation")?;
        let started = Instant::now();
        let representatives = RuleEngine::get_valid_actions(&state, actor);
        let ui_seconds = started.elapsed().as_secs_f64();
        let started = Instant::now();
        let candidates = RuleEngine::ai_decisions(&state)?;
        let seconds = started.elapsed().as_secs_f64();
        println!(
            "index {index}: UI {ui_seconds:.6}s, AI {seconds:.6}s, {} candidates",
            candidates.len()
        );
        results.push(serde_json::json!({"index": index, "state": state,
            "representatives": representatives, "candidates": candidates,
            "ui_seconds": ui_seconds, "seconds": seconds}));
    }
    let file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output)?;
    serde_json::to_writer(file, &results)?;
    Ok(())
}
