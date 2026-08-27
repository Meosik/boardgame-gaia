use std::{fs, path::PathBuf};

use gaia_protocol::{
    CommandEnvelope, Digest32, ProtocolCompatibilityError, ServerEnvelope, PROTOCOL_VERSION,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
enum FixtureCommand {
    Pass,
    RotateSector { sector_id: u8, steps: u8 },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct FixtureState {
    round: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
enum FixtureEvent {
    Passed,
}

fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("invalid")
        .join(name)
}

fn fixture(name: &str) -> String {
    let path = fixture_path(name);
    fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()))
}

#[test]
fn malformed_command_fixtures_are_rejected() {
    let fixtures = [
        "command-unknown-tag.json",
        "command-extra-envelope-field.json",
        "command-extra-payload-field.json",
        "command-missing-field.json",
        "command-invalid-id.json",
        "command-unsafe-revision.json",
        "command-invalid-digest.json",
    ];

    for fixture_name in fixtures {
        let result =
            serde_json::from_str::<CommandEnvelope<FixtureCommand>>(&fixture(fixture_name));
        assert!(
            result.is_err(),
            "invalid fixture decoded successfully: {fixture_name}"
        );
    }
}

#[test]
fn malformed_server_fixtures_are_rejected() {
    let fixtures = [
        "server-unknown-tag.json",
        "server-control-invalid-seat.json",
    ];

    for fixture_name in fixtures {
        let result = serde_json::from_str::<ServerEnvelope<FixtureState, FixtureEvent>>(&fixture(
            fixture_name,
        ));
        assert!(
            result.is_err(),
            "invalid fixture decoded successfully: {fixture_name}"
        );
    }
}

#[test]
fn wrong_protocol_version_fixture_is_rejected_by_compatibility_check() {
    let envelope: CommandEnvelope<FixtureCommand> =
        serde_json::from_str(&fixture("compatibility-wrong-version.json"))
            .unwrap_or_else(|error| panic!("compatibility fixture must decode: {error}"));

    assert_eq!(
        envelope.validate_compatibility(Digest32::from_bytes([0xAB; 32])),
        Err(ProtocolCompatibilityError::UnsupportedVersion {
            expected: PROTOCOL_VERSION,
            received: PROTOCOL_VERSION + 1,
        })
    );
}

#[test]
fn wrong_schema_hash_fixture_is_rejected_by_compatibility_check() {
    let envelope: CommandEnvelope<FixtureCommand> =
        serde_json::from_str(&fixture("compatibility-wrong-schema.json"))
            .unwrap_or_else(|error| panic!("compatibility fixture must decode: {error}"));

    assert_eq!(
        envelope.validate_compatibility(Digest32::from_bytes([0xAB; 32])),
        Err(ProtocolCompatibilityError::SchemaHashMismatch)
    );
}
