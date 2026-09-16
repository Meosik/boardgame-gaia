//! Cheap seed prefilter using the exact native selection RNG/order/board pairing.
//! Every accepted setup must still be verified by Environment before use.
use gaia_engine::{game_state::FactionId, Randomizer, SetupPolicy};

fn lineup(seed: &str) -> Result<Vec<FactionId>, Box<dyn std::error::Error>> {
    let mut state = SetupPolicy::initialize(vec![0, 1, 2, 3], FactionId::all());
    let mut rng = Randomizer::new(&format!("{seed}:rl-factions"));
    let mut result = Vec::new();
    for player in 0..4 {
        // ai_decisions sorts complete serialized decisions. During selection
        // the only differing field is the serialized faction name.
        let mut choices: Vec<_> = state
            .available_factions
            .iter()
            .map(|f| Ok((serde_json::to_string(f)?, *f)))
            .collect::<Result<_, serde_json::Error>>()?;
        choices.sort_by(|a, b| a.0.cmp(&b.0));
        let faction = choices[rng.random_int(choices.len())].1;
        SetupPolicy::select_faction(&mut state, player, faction)?;
        result.push(faction);
    }
    Ok(result)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let prefix = std::env::args().nth(1).ok_or("seed prefix required")?;
    let limit: usize = std::env::args().nth(2).ok_or("limit required")?.parse()?;
    let targets = [
        FactionId::Xenos,
        FactionId::HadschHallas,
        FactionId::Terrans,
        FactionId::Taklons,
    ];
    for attempt in 0..limit {
        let seed = format!("{prefix}-{attempt}");
        let factions = lineup(&seed)?;
        if targets.iter().all(|f| factions.contains(f)) {
            println!(
                "{}",
                serde_json::json!({"seed": seed, "factions": factions})
            );
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn selection_matches_real_native_environment() -> Result<(), Box<dyn std::error::Error>> {
        for seed in (0..24)
            .map(|i| format!("lineup-parity-{i}"))
            .chain(["quartet-pilot-20260913-424".into(), "종족😀".into()])
        {
            let env = gaia_rl::Environment::new(&seed, 2000)?;
            let actual: Vec<_> = env
                .state()
                .players
                .iter()
                .filter_map(|p| p.faction)
                .collect();
            assert_eq!(super::lineup(&seed)?, actual, "{seed}");
        }
        Ok(())
    }
}
