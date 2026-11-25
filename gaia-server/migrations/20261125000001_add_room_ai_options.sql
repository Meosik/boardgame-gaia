-- What the member of an AI game chose for it beside the game itself: {"all_seats": bool,
-- "review": bool} (gaia-server `room::manager::AiOptions`). Rooms created before this column
-- read as '{}' = both off, which is how they ran.
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS ai_options JSONB NOT NULL DEFAULT '{}'::jsonb;
