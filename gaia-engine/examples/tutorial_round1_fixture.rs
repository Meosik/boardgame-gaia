//! Regenerate browser fixtures: cargo run -q -p gaia-engine --example tutorial_round1_fixture
use gaia_engine::{tutorial, RuleError};
use serde_json::Value;

fn changes(before: &Value, after: &Value, path: &mut Vec<String>, output: &mut Vec<Value>) {
    if before == after {
        return;
    }
    if let (Some(before), Some(after)) = (before.as_object(), after.as_object()) {
        if before.keys().eq(after.keys()) {
            for (key, value) in after {
                path.push(key.clone());
                changes(&before[key], value, path, output);
                path.pop();
            }
            return;
        }
    }
    output.push(serde_json::json!({ "path": path, "value": after }));
}

fn main() -> Result<(), RuleError> {
    let mut state = tutorial::initial_state("TUTOR", [0, 1, 2, 3])?;
    state.created_at = 0;
    let initial = state.serialize();
    let mut previous = initial.clone();
    let mut frames = Vec::new();
    for step in tutorial::steps() {
        tutorial::apply_step(&mut state, 0, step.action)?;
        let next = state.serialize();
        let mut delta = Vec::new();
        changes(&previous, &next, &mut Vec::new(), &mut delta);
        frames.push(delta);
        previous = next;
    }
    println!(
        "{}",
        serde_json::json!({ "initial": initial, "changes": frames })
    );
    Ok(())
}
