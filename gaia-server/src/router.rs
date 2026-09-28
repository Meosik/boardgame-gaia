use std::sync::Arc;

use axum::{
    http::{header, HeaderValue},
    routing::{get, post},
    Router,
};
use tower_governor::{governor::GovernorConfigBuilder, GovernorLayer};
use tower_http::{
    services::{ServeDir, ServeFile},
    set_header::SetResponseHeaderLayer,
    trace::TraceLayer,
};

use crate::{
    handlers::{dev_tools, rest, websocket},
    rate_limit::ClientIpKeyExtractor,
    site_gate::{self, SiteGate},
    state::AppState,
};

pub fn build_router(state: AppState) -> Router {
    let gate = SiteGate::from_env();

    // A few requests per second with a small burst — generous for a human clicking
    // "만들기"/"참가" a couple of times, hostile to a script trying every room code.
    // NOTE: this also covers /ws, since a mobile client bouncing between wifi and
    // LTE reconnects the socket repeatedly — that churn shares this same bucket,
    // so it must stay generous enough to not starve normal reconnects.
    let rate_limit_config = Arc::new(
        GovernorConfigBuilder::default()
            .per_second(2)
            .burst_size(8)
            .key_extractor(ClientIpKeyExtractor)
            .finish()
            .expect("rate limit config is valid"),
    );
    let rate_limited = GovernorLayer {
        config: rate_limit_config,
    };

    // The site password gets its own bucket, separate from /api and /ws — it must
    // not be starved by a flaky mobile connection's websocket-reconnect churn, and
    // Cf-Connecting-Ip means everyone behind the same carrier NAT/public wifi
    // shares one bucket, so this stays deliberately more generous than the API one.
    let gate_rate_limit_config = Arc::new(
        GovernorConfigBuilder::default()
            .per_second(1)
            .burst_size(20)
            .key_extractor(ClientIpKeyExtractor)
            .finish()
            .expect("gate rate limit config is valid"),
    );
    let gate_rate_limited = GovernorLayer {
        config: gate_rate_limit_config,
    };

    let api = Router::new()
        .route("/rooms", post(rest::create_room).get(rest::list_rooms))
        .route("/dev-games", post(rest::create_dev_game))
        .route("/rooms/:code/dev-refill", post(dev_tools::refill))
        .route("/rooms/:code/dev-delete", post(dev_tools::delete))
        .route("/rooms/:code/join", post(rest::join_room))
        .route("/rooms/:code", get(rest::get_room))
        .route("/rooms/:code/regenerate", post(rest::regenerate_setup))
        .route("/rooms/:code/preview_board", get(rest::preview_board));

    // The WS handshake is a plain HTTP GET (Upgrade request), so it shares the
    // same governor as the REST API — otherwise a script could open unlimited
    // connections against the one route the limiter above never covered.
    let ws = Router::new().route("/ws/:room_code", get(websocket::ws_handler));

    let rate_limited_routes = Router::new()
        .nest("/api", api)
        .merge(ws)
        .layer(rate_limited);

    let gate_routes = site_gate::routes(gate.clone()).layer(gate_rate_limited);

    let frontend_dir =
        std::env::var("FRONTEND_DIR").unwrap_or_else(|_| "gaia-frontend/dist".to_string());
    let spa_fallback = ServeFile::new(format!("{frontend_dir}/index.html"));

    // The frontend is always served by this same origin — production gets it from
    // ServeDir above, and local dev proxies /api and /ws through Vite's own dev
    // server (see gaia-frontend/vite.config.ts) — so every legitimate request is
    // same-origin already. No CorsLayer is added: without one, axum sends no
    // Access-Control-Allow-Origin header, so browsers refuse cross-site reads of
    // API responses (e.g. the public room list) for any third-party page that
    // still holds a visitor's gate cookie.
    Router::new()
        .merge(rate_limited_routes)
        .merge(gate_routes)
        .route("/health", get(rest::health))
        .nest_service("/", ServeDir::new(frontend_dir).fallback(spa_fallback))
        .layer(axum::middleware::from_fn(move |req, next| {
            let gate = gate.clone();
            async move { site_gate::require_password(gate, req, next).await }
        }))
        // Basic hardening headers: no MIME-sniffing, no framing (the /gate password
        // form is the concrete clickjacking target), and no referrer leakage to
        // whatever page a room-invite link was pasted into.
        .layer(SetResponseHeaderLayer::overriding(
            header::X_CONTENT_TYPE_OPTIONS,
            HeaderValue::from_static("nosniff"),
        ))
        .layer(SetResponseHeaderLayer::overriding(
            header::HeaderName::from_static("x-frame-options"),
            HeaderValue::from_static("DENY"),
        ))
        .layer(SetResponseHeaderLayer::overriding(
            header::REFERRER_POLICY,
            HeaderValue::from_static("no-referrer"),
        ))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
