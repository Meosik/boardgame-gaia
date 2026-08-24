/// Entry point for the `tests/integration/` test suite.
///
/// Cargo only auto-discovers top-level files in `tests/` as separate test
/// binaries; the `tests/integration/` directory is a plain module tree that
/// must be pulled in from a root file. This file is that root — it resolves
/// `tests/integration/mod.rs`, which in turn declares each test module.
///
/// Run with: cargo test -p gaia-server --test integration_tests
mod integration;
