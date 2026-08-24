CREATE TABLE IF NOT EXISTS game_snapshots (
    id          BIGSERIAL    PRIMARY KEY,
    room_code   VARCHAR(8)   NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
    round       SMALLINT     NOT NULL,
    revision    BIGINT       NOT NULL,
    snapshot    JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (room_code, revision)
);

CREATE INDEX IF NOT EXISTS game_snapshots_room_revision
    ON game_snapshots (room_code, revision DESC);
