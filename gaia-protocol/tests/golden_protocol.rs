use std::{fmt::Debug, fs, path::PathBuf};

use gaia_protocol::{
    CommandEnvelope, CommandId, ControlProjection, Digest32, ProtocolRejection, Revision, SeatId,
    ServerEnvelope, PROTOCOL_VERSION,
};
use serde::{de::DeserializeOwned, Deserialize, Serialize};

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
    active_seat: SeatId,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
enum FixtureEvent {
    ResourceChanged { seat: SeatId, ore: i8 },
}

fn schema_hash() -> Digest32 {
    Digest32::from_bytes([0xAB; 32])
}

fn command_id(value: &str) -> CommandId {
    CommandId::parse(value).unwrap_or_else(|error| panic!("invalid fixture command id: {error}"))
}

fn revision(value: u64) -> Revision {
    Revision::new(value).unwrap_or_else(|error| panic!("invalid fixture revision: {error}"))
}

fn seat(value: u8) -> SeatId {
    SeatId::new(value).unwrap_or_else(|error| panic!("invalid fixture seat: {error}"))
}

fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(name)
}

fn assert_golden<T>(fixture_name: &str, value: &T)
where
    T: Debug + DeserializeOwned + PartialEq + Serialize,
{
    let path = fixture_path(fixture_name);
    let expected = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", path.display()));
    let actual = format!(
        "{}\n",
        serde_json::to_string_pretty(value)
            .unwrap_or_else(|error| panic!("failed to serialize {fixture_name}: {error}"))
    );
    assert_eq!(
        actual,
        expected,
        "golden fixture drifted: {}",
        path.display()
    );

    let decoded: T = serde_json::from_str(&expected)
        .unwrap_or_else(|error| panic!("failed to decode {}: {error}", path.display()));
    assert_eq!(
        &decoded,
        value,
        "fixture failed typed round trip: {}",
        path.display()
    );
}

#[test]
fn command_pass_matches_golden() {
    let envelope = CommandEnvelope {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        room_id: "ROOM01".to_string(),
        command_id: command_id("cmd_pass_1"),
        expected_revision: revision(7),
        command: FixtureCommand::Pass,
    };

    assert_golden("command-pass.json", &envelope);
}

#[test]
fn command_with_fields_matches_golden() {
    let envelope = CommandEnvelope {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        room_id: "ROOM01".to_string(),
        command_id: command_id("cmd_rotate_1"),
        expected_revision: revision(8),
        command: FixtureCommand::RotateSector {
            sector_id: 5,
            steps: 2,
        },
    };

    assert_golden("command-rotate-sector.json", &envelope);
}

#[test]
fn command_accepted_matches_golden() {
    let envelope: ServerEnvelope<FixtureState, FixtureEvent> = ServerEnvelope::CommandAccepted {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        command_id: command_id("cmd_pass_1"),
        revision: revision(8),
    };

    assert_golden("server-command-accepted.json", &envelope);
}

#[test]
fn command_rejected_matches_golden() {
    let envelope: ServerEnvelope<FixtureState, FixtureEvent> = ServerEnvelope::CommandRejected {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        command_id: Some(command_id("cmd_rotate_1")),
        revision: revision(8),
        rejection: ProtocolRejection {
            code: "REVISION_CONFLICT".to_string(),
            message_key: "command.revision_conflict".to_string(),
        },
    };

    assert_golden("server-command-rejected.json", &envelope);
}

#[test]
fn snapshot_matches_golden() {
    let envelope: ServerEnvelope<FixtureState, FixtureEvent> = ServerEnvelope::Snapshot {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        revision: revision(8),
        state: FixtureState {
            round: 3,
            active_seat: seat(2),
        },
    };

    assert_golden("server-snapshot.json", &envelope);
}

#[test]
fn events_matches_golden() {
    let envelope: ServerEnvelope<FixtureState, FixtureEvent> = ServerEnvelope::Events {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        from_revision: revision(8),
        to_revision: revision(9),
        events: vec![FixtureEvent::ResourceChanged {
            seat: seat(2),
            ore: -1,
        }],
    };

    assert_golden("server-events.json", &envelope);
}

#[test]
fn control_matches_golden() {
    let envelope: ServerEnvelope<FixtureState, FixtureEvent> = ServerEnvelope::Control {
        protocol_version: PROTOCOL_VERSION,
        schema_hash: schema_hash(),
        control: ControlProjection {
            control_revision: revision(4),
            paused: true,
            recovery_hold: false,
            missing_seats: vec![seat(1), seat(3)],
        },
    };

    assert_golden("server-control.json", &envelope);
}
