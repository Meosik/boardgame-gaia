//! Per-client rate limiting for room-mutating endpoints (create/join), the ones an
//! automated script could hammer to spam rooms or brute-force a 6-hex-digit room code.
//!
//! The server sits behind a Cloudflare Tunnel, so the TCP peer seen by axum is always
//! the `cloudflared` container — the default peer-IP extractor would bucket every real
//! visitor together. Cloudflare adds `Cf-Connecting-Ip` on every proxied request, so this
//! keys on that header instead, falling back to a shared bucket only if it's absent
//! (plain local/dev runs without the tunnel in front).

use axum::http::Request;
use tower_governor::{key_extractor::KeyExtractor, GovernorError};

#[derive(Clone)]
pub struct ClientIpKeyExtractor;

impl KeyExtractor for ClientIpKeyExtractor {
    type Key = String;

    fn extract<B>(&self, req: &Request<B>) -> Result<Self::Key, GovernorError> {
        let key = req
            .headers()
            .get("cf-connecting-ip")
            .and_then(|value| value.to_str().ok())
            .map(str::to_string)
            .unwrap_or_else(|| "no-cf-connecting-ip".to_string());
        Ok(key)
    }
}
