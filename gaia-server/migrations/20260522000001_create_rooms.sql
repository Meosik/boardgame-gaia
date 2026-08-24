CREATE TABLE IF NOT EXISTS rooms (
    code        VARCHAR(8)   PRIMARY KEY,
    seed        VARCHAR(128) NOT NULL,
    host_player SMALLINT     NOT NULL,
    state       VARCHAR(24)  NOT NULL DEFAULT 'lobby',
    revision    BIGINT       NOT NULL DEFAULT 0,
    setup       JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
