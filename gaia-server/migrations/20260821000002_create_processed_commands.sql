CREATE TABLE IF NOT EXISTS processed_commands (
    room_code   VARCHAR(8)   NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
    command_id  VARCHAR(64)  NOT NULL,
    revision    BIGINT       NOT NULL,
    result      JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (room_code, command_id)
);
