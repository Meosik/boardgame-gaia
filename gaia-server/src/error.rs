use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use gaia_engine::SetupError;
use serde_json::json;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ServerError {
    #[error("room not found: {0}")]
    RoomNotFound(String),

    #[error("room is full")]
    RoomFull,

    #[error("room already started")]
    RoomAlreadyStarted,

    #[error("player not found")]
    PlayerNotFound,

    #[error("not your turn")]
    NotYourTurn,

    #[error("invalid action: {0}")]
    InvalidAction(String),

    #[error("not authorised")]
    Unauthorised,

    #[error("session invalid or expired")]
    InvalidSession,

    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("serialisation error: {0}")]
    Serialise(#[from] serde_json::Error),

    #[error("internal error: {0}")]
    Internal(String),

    #[error("invalid seed: {0}")]
    InvalidSeed(String),
}

impl From<SetupError> for ServerError {
    fn from(e: SetupError) -> Self {
        match e {
            SetupError::InvalidSeed(msg) => Self::InvalidSeed(msg),
        }
    }
}

impl IntoResponse for ServerError {
    fn into_response(self) -> Response {
        let (status, code) = match &self {
            ServerError::RoomNotFound(_) => (StatusCode::NOT_FOUND, "ROOM_NOT_FOUND"),
            ServerError::RoomFull => (StatusCode::CONFLICT, "ROOM_FULL"),
            ServerError::RoomAlreadyStarted => (StatusCode::CONFLICT, "ALREADY_STARTED"),
            ServerError::PlayerNotFound => (StatusCode::NOT_FOUND, "PLAYER_NOT_FOUND"),
            ServerError::NotYourTurn => (StatusCode::FORBIDDEN, "NOT_YOUR_TURN"),
            ServerError::InvalidAction(_) => (StatusCode::UNPROCESSABLE_ENTITY, "INVALID_ACTION"),
            ServerError::Unauthorised => (StatusCode::FORBIDDEN, "UNAUTHORISED"),
            ServerError::InvalidSession => (StatusCode::UNAUTHORIZED, "INVALID_SESSION"),
            ServerError::Database(_) => (StatusCode::INTERNAL_SERVER_ERROR, "DB_ERROR"),
            ServerError::Serialise(_) => (StatusCode::INTERNAL_SERVER_ERROR, "SERIALISE_ERROR"),
            ServerError::Internal(_) => (StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL_ERROR"),
            ServerError::InvalidSeed(_) => (StatusCode::BAD_REQUEST, "INVALID_SEED"),
        };
        let body = Json(json!({ "error": code, "message": self.to_string() }));
        (status, body).into_response()
    }
}

pub type ServerResult<T> = Result<T, ServerError>;
