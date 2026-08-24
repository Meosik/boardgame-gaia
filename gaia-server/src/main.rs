use std::net::SocketAddr;

use gaia_server::router;
use gaia_server::state::AppState;

#[tokio::main]
async fn main() {
    // Load .env (ignore error if file absent — env vars may be set externally)
    let _ = dotenvy::dotenv();

    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8080);

    let pool = sqlx::PgPool::connect(&database_url)
        .await
        .expect("failed to connect to PostgreSQL");

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("failed to run database migrations");

    log::info!("migrations applied");

    let app_state = AppState::new(pool);
    let app = router::build_router(app_state);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    log::info!("gaia-server listening on {addr}");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind TCP listener");

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("server error");
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c()
        .await
        .expect("failed to install CTRL+C handler");
    log::info!("shutdown signal received");
}
