//! Offline self-play environment. No server, database or browser dependencies.
pub const ENGINE_BUILD_ID: &str = env!("GAIA_ENGINE_BUILD_ID");
pub const SOURCE_MANIFEST: &str = include_str!(concat!(env!("OUT_DIR"), "/source-manifest.txt"));
pub mod env;
pub use env::{DecisionSnapshot, EnvError, Environment, ENV_SCHEMA_VERSION};

#[cfg(feature = "python")]
mod python {
    use super::*;
    use pyo3::exceptions::PyRuntimeError;
    use pyo3::prelude::*;

    pyo3::create_exception!(_native, StepLimitError, PyRuntimeError);

    fn environment_error(error: EnvError) -> PyErr {
        match error {
            EnvError::StepLimit(_) => StepLimitError::new_err(error.to_string()),
            other => PyRuntimeError::new_err(other.to_string()),
        }
    }

    fn error(error: impl std::fmt::Display) -> PyErr {
        PyRuntimeError::new_err(error.to_string())
    }

    #[pyclass(name = "Environment")]
    struct PyEnvironment {
        inner: Environment,
    }

    #[pymethods]
    impl PyEnvironment {
        #[new]
        #[pyo3(signature = (seed, max_steps=10000))]
        fn new(seed: &str, max_steps: usize) -> PyResult<Self> {
            Ok(Self {
                inner: Environment::new(seed, max_steps).map_err(error)?,
            })
        }
        #[staticmethod]
        #[pyo3(signature = (state_json, max_steps=10000))]
        fn from_state_json(state_json: &str, max_steps: usize) -> PyResult<Self> {
            let state = serde_json::from_str(state_json).map_err(error)?;
            Ok(Self {
                inner: Environment::from_state(state, max_steps).map_err(error)?,
            })
        }
        fn reset(&mut self, seed: &str) -> PyResult<()> {
            self.inner.reset(seed).map_err(error)
        }
        fn snapshot_json(&self) -> PyResult<String> {
            serde_json::to_string(&self.inner.snapshot().map_err(error)?).map_err(error)
        }
        fn fork(&self, decision_id: u64, candidate_index: usize) -> PyResult<Self> {
            Ok(Self { inner: self.inner.fork(decision_id, candidate_index).map_err(environment_error)? })
        }
        fn preview_state_json(&self, decision_id: u64, candidate_index: usize) -> PyResult<String> {
            let state = self.inner.preview_state(decision_id, candidate_index)
                .map_err(environment_error)?;
            serde_json::to_string(&state).map_err(error)
        }
        fn step(&mut self, decision_id: u64, candidate_index: usize) -> PyResult<()> {
            self.inner
                .step(decision_id, candidate_index)
                .map_err(environment_error)
        }
        fn is_terminal(&self) -> bool {
            self.inner.is_terminal()
        }
        fn final_scores(&self) -> Option<Vec<(u8, i32)>> {
            self.inner.final_scores().map(|s| s.to_vec())
        }
        fn rewards(&self) -> Vec<f32> {
            self.inner.rewards().to_vec()
        }
    }

    #[pyfunction]
    fn ping(name: &str) -> String {
        format!("gaia_rl (Rust) says hello, {name}")
    }
    #[pyfunction]
    fn sum_ints(values: Vec<i64>) -> i64 {
        values.iter().sum()
    }
    #[pyfunction]
    fn evaluation_facts_json(state_json: &str, player_id: u8) -> PyResult<String> {
        let state: gaia_engine::GameState = serde_json::from_str(state_json).map_err(error)?;
        let facts = gaia_engine::rules::engine::evaluation_data::facts(&state, player_id).map_err(error)?;
        serde_json::to_string(&facts).map_err(error)
    }
    #[pyfunction]
    fn evaluation_successor_json(state_json: &str, player_id: u8, action_json: &str) -> PyResult<String> {
        let mut state = serde_json::from_str(state_json).map_err(error)?;
        let action = serde_json::from_str(action_json).map_err(error)?;
        gaia_engine::RuleEngine::apply_action(&mut state, player_id, action).map_err(error)?;
        serde_json::to_string(&state).map_err(error)
    }
    #[pyfunction]
    fn evaluation_pass_next_round_json(state_json: &str, player_id: u8) -> PyResult<String> {
        let state = serde_json::from_str(state_json).map_err(error)?;
        let projected = gaia_engine::rules::engine::evaluation_data::passed_next_round(&state, player_id)
            .map_err(error)?;
        serde_json::to_string(&projected).map_err(error)
    }

    #[pymodule]
    fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_class::<PyEnvironment>()?;
        m.add("StepLimitError", m.py().get_type::<StepLimitError>())?;
        m.add("ENV_SCHEMA_VERSION", ENV_SCHEMA_VERSION)?;
        m.add("ENGINE_BUILD_ID", ENGINE_BUILD_ID)?;
        m.add("SOURCE_MANIFEST", SOURCE_MANIFEST)?;
        m.add_function(wrap_pyfunction!(ping, m)?)?;
        m.add_function(wrap_pyfunction!(sum_ints, m)?)?;
        m.add_function(wrap_pyfunction!(evaluation_facts_json, m)?)?;
        m.add_function(wrap_pyfunction!(evaluation_successor_json, m)?)?;
        m.add_function(wrap_pyfunction!(evaluation_pass_next_round_json, m)?)?;
        Ok(())
    }
}
