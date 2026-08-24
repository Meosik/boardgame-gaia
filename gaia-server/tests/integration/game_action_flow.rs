/// Integration tests for game action processing end-to-end.
///
/// Marked #[ignore] — require DATABASE_URL.

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn action_applied_message_broadcast_to_room() {
    // Placeholder — verify that a game action triggers ActionApplied broadcast.
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn invalid_action_returns_error_message() {
    // Placeholder — verify that an out-of-turn action returns Error message.
}
