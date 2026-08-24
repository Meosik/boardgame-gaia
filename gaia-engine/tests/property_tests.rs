/// Entry point for the `tests/property/` test suite.
///
/// Cargo only auto-discovers top-level files in `tests/` as separate test
/// binaries; the `tests/property/` directory is a plain module tree that
/// must be pulled in from a root file. This file is that root — it resolves
/// `tests/property/mod.rs`, which in turn declares each test module.
///
/// Run with: cargo test -p gaia-engine --test property_tests
mod property;
