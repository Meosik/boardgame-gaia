use gaia_engine::game_state::{GamePhase, GameState, PlayerId};
use gaia_engine::rules::engine::{AiActionError, AiCandidateDiagnostics, AiDecision};
use gaia_engine::{MapEngine, Randomizer, RuleEngine, SetupAction};
use serde::{Deserialize, Serialize};

pub const ENV_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, thiserror::Error)]
pub enum EnvError {
    #[error(transparent)]
    Decisions(#[from] AiActionError),
    #[error(transparent)]
    Rule(#[from] gaia_engine::RuleError),
    #[error(transparent)]
    Setup(#[from] gaia_engine::SetupError),
    #[error("stale decision id: expected {expected}, got {actual}")]
    Stale { expected: u64, actual: u64 },
    #[error("candidate index {0} is out of bounds")]
    InvalidIndex(usize),
    #[error("the episode has ended")]
    Ended,
    #[error("episode truncated at the configured {0}-step limit, not a game end")]
    StepLimit(usize),
    #[error("invalid environment configuration: {0}")]
    Configuration(&'static str),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionSnapshot {
    pub schema_version: u32,
    pub engine_build_id: String,
    pub decision_id: u64,
    pub player: Option<PlayerId>,
    pub candidates: Vec<AiDecision>,
    pub state: GameState,
    pub steps: usize,
    #[serde(default)]
    pub candidate_generation: AiCandidateDiagnostics,
}

#[derive(Clone)]
pub struct Environment {
    state: GameState,
    candidates: Vec<AiDecision>,
    decision_id: u64,
    steps: usize,
    max_steps: usize,
    candidate_generation: AiCandidateDiagnostics,
}

impl Environment {
    /// Start from an existing game state (e.g. a live server game) instead of a seed.
    /// Candidates are generated exactly as after any `step`; the decision id starts at 0.
    pub fn from_state(state: GameState, max_steps: usize) -> Result<Self, EnvError> {
        if max_steps == 0 {
            return Err(EnvError::Configuration("max_steps must be positive"));
        }
        let (candidates, candidate_generation) = RuleEngine::ai_decisions_with_diagnostics(&state)?;
        Ok(Self {
            state,
            candidates,
            decision_id: 0,
            steps: 0,
            max_steps,
            candidate_generation,
        })
    }

    pub fn new(seed: &str, max_steps: usize) -> Result<Self, EnvError> {
        if max_steps == 0 {
            return Err(EnvError::Configuration("max_steps must be positive"));
        }
        let (state, candidates, candidate_generation) = Self::initial(seed)?;
        Ok(Self {
            state,
            candidates,
            decision_id: 0,
            steps: 0,
            max_steps,
            candidate_generation,
        })
    }

    fn initial(seed: &str) -> Result<(GameState, Vec<AiDecision>, AiCandidateDiagnostics), EnvError> {
        // Runs recorded before the same-type adjacency fix (engine 7d012a0) replay only on the
        // drawn sector rotations; GAIA_DRAWN_ROTATIONS=1 rebuilds those maps.
        let setup = if std::env::var_os("GAIA_DRAWN_ROTATIONS").is_some_and(|value| value == "1") {
            Randomizer::generate_setup_with_drawn_rotations(seed)?
        } else {
            Randomizer::generate_setup(seed)?
        };
        let players: Vec<_> = (0..4).map(|i| (i, format!("AI-{i}"))).collect();
        let mut state = MapEngine::init_game_state("RL", seed, &players, &setup);
        // Wall-clock metadata is not part of an offline simulation.
        state.created_at = 0;
        let mut rng = Randomizer::new(&format!("{seed}:rl-factions"));
        // Legal sequential selection removes the opposite side of each chosen board, so no
        // two factions can share a physical board. Selection is setup randomness, not training.
        for _ in 0..4 {
            let choices = RuleEngine::ai_decisions(&state)?;
            let candidate = &choices[rng.random_int(choices.len())];
            let Some(player) = RuleEngine::decision_player(&state)? else {
                return Err(EnvError::Ended);
            };
            let AiDecision::Setup(action @ SetupAction::SelectFaction { .. }) = candidate else {
                return Err(EnvError::Configuration("expected faction-selection setup"));
            };
            RuleEngine::apply_setup_action(&mut state, player, action.clone())?;
        }
        RuleEngine::advance_automatic(&mut state)?;
        let (candidates, diagnostics) = RuleEngine::ai_decisions_with_diagnostics(&state)?;
        Ok((state, candidates, diagnostics))
    }

    pub fn reset(&mut self, seed: &str) -> Result<(), EnvError> {
        let (state, candidates, candidate_generation) = Self::initial(seed)?;
        self.state = state;
        self.candidates = candidates;
        self.candidate_generation = candidate_generation;
        self.decision_id += 1;
        self.steps = 0;
        Ok(())
    }

    pub fn state(&self) -> &GameState {
        &self.state
    }
    pub fn legal_actions(&self) -> &[AiDecision] {
        &self.candidates
    }
    pub fn decision_id(&self) -> u64 {
        self.decision_id
    }
    pub fn steps(&self) -> usize {
        self.steps
    }
    pub fn current_decision_player(&self) -> Result<Option<PlayerId>, EnvError> {
        Ok(RuleEngine::decision_player(&self.state)?)
    }
    pub fn is_terminal(&self) -> bool {
        matches!(self.state.phase, GamePhase::Ended { .. })
    }
    pub fn final_scores(&self) -> Option<[(PlayerId, i32); 4]> {
        match &self.state.phase {
            GamePhase::Ended { final_scores, .. } => Some(*final_scores),
            _ => None,
        }
    }
    pub fn rewards(&self) -> [f32; 4] {
        let Some(scores) = self.final_scores() else {
            return [0.0; 4];
        };
        let mean = scores.iter().map(|(_, score)| *score as f32).sum::<f32>() / 4.0;
        let mut rewards = [0.0; 4];
        for (player, score) in scores {
            rewards[usize::from(player)] = (score as f32 - mean) / 100.0;
        }
        rewards
    }
    pub fn snapshot(&self) -> Result<DecisionSnapshot, EnvError> {
        Ok(DecisionSnapshot {
            schema_version: ENV_SCHEMA_VERSION,
            engine_build_id: crate::ENGINE_BUILD_ID.to_owned(),
            decision_id: self.decision_id,
            player: self.current_decision_player()?,
            candidates: self.candidates.clone(),
            state: self.state.clone(),
            steps: self.steps,
            candidate_generation: self.candidate_generation.clone(),
        })
    }

    /// Explore one legal decision without mutating the live offline episode.
    /// Uses the same stale-id, legality and truncation checks as a real step.
    pub fn fork(&self, decision_id: u64, index: usize) -> Result<Self, EnvError> {
        let mut branch = self.clone();
        branch.step(decision_id, index)?;
        Ok(branch)
    }

    /// Candidate generation and automatic transitions also happen on the clone. If any stage
    /// fails, the caller retains the previous decision and can capture/replay it exactly.
    pub fn step(&mut self, decision_id: u64, index: usize) -> Result<(), EnvError> {
        let next = self.preview_state(decision_id, index)?;
        let (candidates, diagnostics) = RuleEngine::ai_decisions_with_diagnostics(&next)?;
        self.state = next;
        self.candidates = candidates;
        self.candidate_generation = diagnostics;
        self.decision_id += 1;
        self.steps += 1;
        Ok(())
    }

    /// Apply the exact paid decision and automatic transitions without enumerating
    /// the next player's candidates. This is a state for evaluation, not a branch
    /// from which an unchecked follow-up may be executed.
    pub fn preview_state(&self, decision_id: u64, index: usize) -> Result<GameState, EnvError> {
        if decision_id != self.decision_id {
            return Err(EnvError::Stale {
                expected: self.decision_id,
                actual: decision_id,
            });
        }
        if self.is_terminal() {
            return Err(EnvError::Ended);
        }
        if self.steps >= self.max_steps {
            return Err(EnvError::StepLimit(self.max_steps));
        }
        let candidate = self
            .candidates
            .get(index)
            .ok_or(EnvError::InvalidIndex(index))?
            .clone();
        let player = self.current_decision_player()?.ok_or(EnvError::Ended)?;
        let mut next = self.state.clone();
        match candidate {
            AiDecision::Setup(action) => {
                RuleEngine::apply_setup_action(&mut next, player, action)?;
            }
            AiDecision::Game(action) => {
                RuleEngine::apply_action(&mut next, player, action)?;
            }
        }
        RuleEngine::advance_automatic(&mut next)?;
        Ok(next)
    }
}
