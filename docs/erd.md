# ERD Draft

## users

- id
- email
- nickname
- password

## rooms

- id
- title
- max_players
- status

## games

- id
- room_id
- status
- round
- current_player_id

## game_action_logs

- id
- game_id
- player_id
- action_type
- payload_json
- created_at
