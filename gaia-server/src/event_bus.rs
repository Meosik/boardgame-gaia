use std::collections::HashMap;
use tokio::sync::{broadcast, RwLock};

use crate::messages::OutboundMessage;

const CHANNEL_CAPACITY: usize = 128;

pub struct EventBus {
    channels: RwLock<HashMap<String, broadcast::Sender<OutboundMessage>>>,
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}

impl EventBus {
    pub fn new() -> Self {
        Self {
            channels: RwLock::new(HashMap::new()),
        }
    }

    /// Returns the sender for `room_code`, creating a new channel if needed.
    pub async fn get_or_create(&self, room_code: &str) -> broadcast::Sender<OutboundMessage> {
        {
            let channels = self.channels.read().await;
            if let Some(tx) = channels.get(room_code) {
                return tx.clone();
            }
        }
        let mut channels = self.channels.write().await;
        let (tx, _) = broadcast::channel(CHANNEL_CAPACITY);
        channels.insert(room_code.to_string(), tx.clone());
        tx
    }

    /// Broadcast `msg` to every subscriber of `room_code`.
    pub async fn broadcast(&self, room_code: &str, msg: impl Into<OutboundMessage>) {
        let channels = self.channels.read().await;
        if let Some(tx) = channels.get(room_code) {
            let _ = tx.send(msg.into());
        }
    }

    /// Subscribe to messages for `room_code`.
    pub async fn subscribe(&self, room_code: &str) -> broadcast::Receiver<OutboundMessage> {
        self.get_or_create(room_code).await.subscribe()
    }

    /// Remove the channel for `room_code` (called when room ends).
    pub async fn remove(&self, room_code: &str) {
        self.channels.write().await.remove(room_code);
    }
}
