use std::{fmt, str::FromStr};

use serde::{de, Deserialize, Deserializer, Serialize, Serializer};
use thiserror::Error;

pub const PROTOCOL_VERSION: u16 = 1;
pub const MAX_SAFE_INTEGER: u64 = 9_007_199_254_740_991;
const MAX_COMMAND_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum ProtocolTypeError {
    #[error("command id must contain 1 to {MAX_COMMAND_ID_LEN} ASCII letters, digits, '-' or '_'")]
    InvalidCommandId,
    #[error("revision exceeds the JavaScript-safe integer range")]
    InvalidRevision,
    #[error("seat id must be between 0 and 3")]
    InvalidSeatId,
    #[error("digest must contain exactly 64 hexadecimal characters")]
    InvalidDigest,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CommandId(String);

impl CommandId {
    pub fn parse(value: &str) -> Result<Self, ProtocolTypeError> {
        let valid = !value.is_empty()
            && value.len() <= MAX_COMMAND_ID_LEN
            && value
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_'));
        if !valid {
            return Err(ProtocolTypeError::InvalidCommandId);
        }
        Ok(Self(value.to_owned()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for CommandId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl Serialize for CommandId {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for CommandId {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Self::parse(&value).map_err(de::Error::custom)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Revision(u64);

impl Revision {
    pub const ZERO: Self = Self(0);

    pub fn new(value: u64) -> Result<Self, ProtocolTypeError> {
        if value > MAX_SAFE_INTEGER {
            return Err(ProtocolTypeError::InvalidRevision);
        }
        Ok(Self(value))
    }

    pub const fn get(self) -> u64 {
        self.0
    }

    pub fn checked_next(self) -> Result<Self, ProtocolTypeError> {
        let next = self
            .0
            .checked_add(1)
            .ok_or(ProtocolTypeError::InvalidRevision)?;
        Self::new(next)
    }
}

impl Serialize for Revision {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_u64(self.0)
    }
}

impl<'de> Deserialize<'de> for Revision {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = u64::deserialize(deserializer)?;
        Self::new(value).map_err(de::Error::custom)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SeatId(u8);

impl SeatId {
    pub fn new(value: u8) -> Result<Self, ProtocolTypeError> {
        if value > 3 {
            return Err(ProtocolTypeError::InvalidSeatId);
        }
        Ok(Self(value))
    }

    pub const fn get(self) -> u8 {
        self.0
    }
}

impl Serialize for SeatId {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_u8(self.0)
    }
}

impl<'de> Deserialize<'de> for SeatId {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = u8::deserialize(deserializer)?;
        Self::new(value).map_err(de::Error::custom)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Digest32([u8; 32]);

impl Digest32 {
    pub const fn from_bytes(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl fmt::Display for Digest32 {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        for byte in self.0 {
            write!(formatter, "{byte:02x}")?;
        }
        Ok(())
    }
}

impl FromStr for Digest32 {
    type Err = ProtocolTypeError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        if value.len() != 64 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err(ProtocolTypeError::InvalidDigest);
        }

        let mut bytes = [0_u8; 32];
        for (index, pair) in value.as_bytes().chunks_exact(2).enumerate() {
            let high = decode_hex(pair[0]).ok_or(ProtocolTypeError::InvalidDigest)?;
            let low = decode_hex(pair[1]).ok_or(ProtocolTypeError::InvalidDigest)?;
            bytes[index] = (high << 4) | low;
        }
        Ok(Self(bytes))
    }
}

impl Serialize for Digest32 {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for Digest32 {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        value.parse().map_err(de::Error::custom)
    }
}

fn decode_hex(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandEnvelope<C> {
    pub protocol_version: u16,
    pub schema_hash: Digest32,
    pub room_id: String,
    pub command_id: CommandId,
    pub expected_revision: Revision,
    pub command: C,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProtocolRejection {
    pub code: String,
    pub message_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ControlProjection {
    pub control_revision: Revision,
    pub paused: bool,
    pub recovery_hold: bool,
    pub missing_seats: Vec<SeatId>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum ServerEnvelope<S, E> {
    CommandAccepted {
        protocol_version: u16,
        schema_hash: Digest32,
        command_id: CommandId,
        revision: Revision,
    },
    CommandRejected {
        protocol_version: u16,
        schema_hash: Digest32,
        command_id: Option<CommandId>,
        revision: Revision,
        rejection: ProtocolRejection,
    },
    Snapshot {
        protocol_version: u16,
        schema_hash: Digest32,
        revision: Revision,
        state: S,
    },
    Events {
        protocol_version: u16,
        schema_hash: Digest32,
        from_revision: Revision,
        to_revision: Revision,
        events: Vec<E>,
    },
    Control {
        protocol_version: u16,
        schema_hash: Digest32,
        control: ControlProjection,
    },
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::{Deserialize, Serialize};
    use serde_json::json;

    #[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
    #[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
    enum TestCommand {
        Pass,
        RotateSector { sector_id: u8, steps: u8 },
    }

    fn schema_hash() -> Digest32 {
        Digest32::from_bytes([0xAB; 32])
    }

    #[test]
    fn command_envelope_rejects_unknown_fields() {
        let value = json!({
            "protocol_version": PROTOCOL_VERSION,
            "schema_hash": schema_hash().to_string(),
            "room_id": "ROOM01",
            "command_id": "cmd_1",
            "expected_revision": 0,
            "command": { "type": "pass" },
            "unexpected": true
        });

        let result = serde_json::from_value::<CommandEnvelope<TestCommand>>(value);
        assert!(result.is_err());
    }

    #[test]
    fn command_variant_is_strict_and_snake_case() {
        let value = json!({
            "protocol_version": PROTOCOL_VERSION,
            "schema_hash": schema_hash().to_string(),
            "room_id": "ROOM01",
            "command_id": "cmd_1",
            "expected_revision": 7,
            "command": { "type": "rotate_sector", "sector_id": 5, "steps": 2 }
        });

        let envelope: CommandEnvelope<TestCommand> = serde_json::from_value(value)
            .unwrap_or_else(|error| panic!("valid envelope failed: {error}"));
        assert_eq!(envelope.expected_revision.get(), 7);
        assert_eq!(
            envelope.command,
            TestCommand::RotateSector {
                sector_id: 5,
                steps: 2
            }
        );
    }

    #[test]
    fn revision_rejects_values_outside_javascript_safe_range() {
        let value = json!(MAX_SAFE_INTEGER + 1);
        let result = serde_json::from_value::<Revision>(value);
        assert!(result.is_err());
    }

    #[test]
    fn digest_round_trips_as_lowercase_hex() {
        let digest = Digest32::from_bytes([0xAB; 32]);
        let encoded = digest.to_string();
        let decoded = encoded
            .parse::<Digest32>()
            .unwrap_or_else(|error| panic!("digest failed: {error}"));
        assert_eq!(decoded, digest);
        assert!(encoded.bytes().all(|byte| !byte.is_ascii_uppercase()));
    }

    #[test]
    fn command_id_validation_is_closed() {
        assert!(CommandId::parse("abc-123_DEF").is_ok());
        assert!(CommandId::parse("").is_err());
        assert!(CommandId::parse("contains spaces").is_err());
        assert!(CommandId::parse(&"x".repeat(MAX_COMMAND_ID_LEN + 1)).is_err());
    }
}
