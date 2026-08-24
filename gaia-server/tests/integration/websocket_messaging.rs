/// WebSocket connection and message routing tests.
///
/// Marked #[ignore] — require a live server with DATABASE_URL set.

#[tokio::test]
#[ignore = "requires DATABASE_URL and live server"]
async fn ws_join_room_receives_room_joined_message() {
    // Full WS tests require a running server.
    // Placeholder — implement with tokio-tungstenite once server is deployed.
}

#[tokio::test]
#[ignore = "requires DATABASE_URL and live server"]
async fn ws_broadcast_reaches_all_room_members() {
    // Placeholder
}
