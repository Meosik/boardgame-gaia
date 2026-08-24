/// Entry point for the `tests/unit/` test suite.
///
/// Cargo only auto-discovers top-level files in `tests/` as separate test
/// binaries; the `tests/unit/` directory is a plain module tree that must be
/// pulled in from a root file. This file is that root — it resolves
/// `tests/unit/mod.rs`, which in turn declares each test module.
///
/// Run with: cargo test -p gaia-engine --test unit_tests
mod unit;
