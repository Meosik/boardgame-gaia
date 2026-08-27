use axum::{
    routing::{get, post},
    Router,
};
use tower_http::{
    cors::CorsLayer,
    services::{ServeDir, ServeFile},
    trace::TraceLayer,
};

use crate::{
    handlers::{rest, websocket},
    state::AppState,
};

pub fn build_router(state: AppState) -> Router {
    let api = Router::new()
        .route("/rooms", post(rest::create_room))
        .route("/rooms/:code/join", post(rest::join_room))
        .route("/rooms/:code", get(rest::get_room))
        .route("/rooms/:code/regenerate", post(rest::regenerate_setup))
        .route("/rooms/:code/preview_board", get(rest::preview_board));

    let frontend_dir =
        std::env::var("FRONTEND_DIR").unwrap_or_else(|_| "gaia-frontend/dist".to_string());
    let spa_fallback = ServeFile::new(format!("{frontend_dir}/index.html"));

    Router::new()
        .nest("/api", api)
        .route("/ws/:room_code", get(websocket::ws_handler))
        .route("/health", get(rest::health))
        .nest_service("/", ServeDir::new(frontend_dir).fallback(spa_fallback))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
