CREATE TABLE IF NOT EXISTS sessions (
    token_hash   CHAR(64)     PRIMARY KEY,
    room_code    VARCHAR(8)   NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
    player_id    SMALLINT     NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sessions_room_player
    ON sessions (room_code, player_id);
