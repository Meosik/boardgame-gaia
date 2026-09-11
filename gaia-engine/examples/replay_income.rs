//! Recover income events only when replaying the recorded transition reproduces its full state.
//! JSON-lines in/out; never rewrites a historical game or infers income from net resource deltas.
use gaia_engine::game_state::{GameEvent, GamePhase, GameState, PlayerId, SetupPhase};
use gaia_engine::{GameAction, RuleEngine, SetupAction};
use serde::Deserialize;
use std::io::{self, BufRead, Write};

#[derive(Deserialize)]
struct Transition {
    before: GameState,
    after: GameState,
    player: PlayerId,
    action: serde_json::Value,
}

fn recover(input: Transition) -> Result<Vec<GameEvent>, Box<dyn std::error::Error>> {
    let mut state = input.before;
    let mut events = if matches!(state.phase, GamePhase::Setup(_)) {
        RuleEngine::apply_setup_action(
            &mut state,
            input.player,
            serde_json::from_value::<SetupAction>(input.action)?,
        )?
    } else {
        RuleEngine::apply_action(
            &mut state,
            input.player,
            serde_json::from_value::<GameAction>(input.action)?,
        )?
    };
    // Same decision-free transitions as advance_automatic, retaining their returned events.
    loop {
        let next = match state.phase {
            GamePhase::Setup(SetupPhase::Complete) => RuleEngine::start_first_round(&mut state)?,
            GamePhase::RoundScoring { round: 6 } => RuleEngine::finalize_game(&mut state)?,
            GamePhase::RoundScoring { .. } => RuleEngine::advance_to_next_round(&mut state)?,
            _ => {
                RuleEngine::decision_player(&state)?;
                break;
            }
        };
        events.extend(next);
    }
    if serde_json::to_value(&state)? != serde_json::to_value(&input.after)? {
        return Err(
            "recorded transition differs from current rules; income was not reconstructed".into(),
        );
    }
    Ok(events
        .into_iter()
        .filter(|event| {
            matches!(
                event,
                GameEvent::IncomeReceived { .. } | GameEvent::RoundStarted { .. }
            )
        })
        .collect())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let events = recover(serde_json::from_str(&line?)?)?;
        serde_json::to_writer(&mut out, &events)?;
        writeln!(out)?;
        out.flush()?;
    }
    Ok(())
}
