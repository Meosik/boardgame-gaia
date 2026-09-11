//! Seeded smoke/benchmark driver; failure writes the exact pre-action state and index.
use gaia_engine::Randomizer;
use gaia_rl::Environment;
use std::time::Instant;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let count: usize = std::env::args().nth(1).unwrap_or_else(|| "1".into()).parse()?;
    let first: usize = std::env::args().nth(2).unwrap_or_else(|| "0".into()).parse()?;
    let started = Instant::now();
    let mut total_steps = 0;
    let mut max_candidates = 0;
    let mut factions = std::collections::BTreeSet::new();
    let mut action_counts = std::collections::BTreeMap::<String, usize>::new();
    for game in first..first + count {
        let seed = format!("rl-smoke-{game}");
        let mut env = Environment::new(&seed, 10000)?;
        for player in &env.state().players { factions.insert(format!("{:?}", player.faction)); }
        let mut policy = Randomizer::new(&format!("{seed}:policy"));
        while !env.is_terminal() {
            max_candidates = max_candidates.max(env.legal_actions().len());
            let index = policy.random_int(env.legal_actions().len());
            let action = serde_json::to_value(&env.legal_actions()[index])?;
            *action_counts.entry(action["action"]["type"].as_str().unwrap_or("unknown").to_owned()).or_default() += 1;
            if let Err(error) = env.step(env.decision_id(), index) {
                let path = std::env::temp_dir().join(format!("gaia-rl-failure-{game}.json"));
                let failure = serde_json::json!({ "seed": seed, "index": index, "snapshot": env.snapshot()?, "error": error.to_string() });
                std::fs::write(&path, serde_json::to_vec_pretty(&failure)?)?;
                return Err(format!("{error}; reproduction: {}", path.display()).into());
            }
        }
        total_steps += env.steps();
        println!("{seed}: {} steps, {:?}", env.steps(), env.final_scores());
    }
    println!("{count} games, {total_steps} decisions, {:.2}s, {:.1} decisions/s", started.elapsed().as_secs_f64(), total_steps as f64 / started.elapsed().as_secs_f64());
    println!("max candidates: {max_candidates}; factions: {}", factions.len());
    println!("actions: {}", serde_json::to_string(&action_counts)?);
    Ok(())
}
