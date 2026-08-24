CREATE TABLE IF NOT EXISTS game_events (
    id          BIGSERIAL    PRIMARY KEY,
    room_code   VARCHAR(8)   NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
    round       SMALLINT     NOT NULL,
    revision    BIGINT,
    player_id   SMALLINT,
    event_type  VARCHAR(64)  NOT NULL,
    payload     JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS game_events_room_id
    ON game_events (room_code, id);
