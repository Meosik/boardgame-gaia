# Cycle 128 — room handover smoke — the teacher plays the user's room 98ADBD on from the round-6 start, one game, command

No A/B. One teacher, `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(factory `guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier`, 4 comparisons, 60 s cap, parallel 2), sits in all four
seats and plays the user's live room 98ADBD (Ivits = user, 187 points; Space Giants, Tinkeroids, Itars = live-server AI) on
from the first action decision of round 6 (snapshot revision 280, after income and the Gaia phase) to the end of the game.
Part under test: the tool `tools/room_handover.py` and the start-state path in `teacher_ab.play` (a2ca5b1, E259), not a
teacher part. Queued 2026-11-23 by the user's 「내 플레이로 하이브 교사의 실력을 높일 수 있나? 테스트 해봐」 → 「ㄱ」(E258·E259·E260).
Pre-registered: no verdict. Pass = ① 1/1 game reaches the end of the game (`metrics.json` `games_complete` 1, `failures`
empty, four final scores) ② errors and timeouts 0. Read alongside: maximum decision time, decisions at or over 60 s and
over 100 s, fallback timeouts, federation actions per seat. The Ivits final score is a reference value only.
Map, factions, seats and the game up to revision 280 are the room record (`~/gaia-media/rooms/98ADBD-snapshots.jsonl`); no
seed. Environment as in 114·119·123 (`GAIA_ENGINE_FIXES_2=1`). Engine = lab HEAD build, which differs from the live engine
that played the room (E252 Ivits federation absorption, E257 conversion at game end). agentmaco, commit 9122315,
2026-11-23 12:45:57 → 12:54:21 (8 min 24 s). Result: lab/results/128-room-handover-smoke.md.

**Health: clean, both pass criteria met.** Exit code 0, 1/1 game complete, `failures` empty, four final scores, 76/76
decisions all in round 6, errors 0, fallback timeouts 0, decisions cut by the 60 s cap 0 (`timing.time_capped`), expired
before search 0. Decision time (one arm): mean 6.59 · median 4.51 · p90 15.29 · max 44.80 s; over 30 s 2/76, at or over
60 s 0, over 100 s 0. No review section on the result page (command job).

## Result (no verdict — tool check)

| Seat | Faction | VP at the round-6 start | Room final (live engine; user / live AI) | Teacher final (lab HEAD engine) | Decisions | Federation actions |
|---|---|---:|---:|---:|---:|---:|
| 0 | Ivits (user's seat) | 64 | 187 (+123) | 185 (+121) | 34 | 1 |
| 1 | Space Giants | 20 | 71 (+51) | 69 (+49) | 7 | 0 |
| 2 | Tinkeroids | 28 | 88 (+60) | 93 (+65) | 20 | 0 |
| 3 | Itars | 25 | 103 (+78) | 121 (+96) | 15 | 1 |

Source: `metrics.json` (`scores`, `federations_formed`, `room_final_scores`), `manifest.json` (`starts.6.vp`),
`result.json` counters. The start VP 64 equals the E258 recount of the room (round-6 start VP 64). No replay posted.

The two score columns are not compared as a result: the engines differ (E252, E257), the three opponents differ (teacher
against teacher here, the user against the live AI in the room), and it is one game. What the row does say: the tool
loaded the exported position, the teacher played a legal round 6 to the end, and Ivits did not collapse from that position.

## Activation (did the tool do what the note says)

- Start: `manifest.json` `starts.6` = revision 280, first decision by seat 2 (Tinkeroids `SelectTinkeringTile`), VP
  64/20/28/25. `snapshots_skipped` 5 = snapshots the lab engine refuses (transient phases) up to revision 280; E258
  counted 6 over the whole file — the tool stops loading once every requested start is found (`room_handover.py:46`), so
  the two counts agree.
- Decision log (`round-6/game-0/decisions.jsonl.gz`, one-line python count): 76 rows, all round 6; 65 searched, 63 of
  them finished 4/4 comparisons and stopped on the comparison budget (`budget_stopped`), 2 finished 3 (not time-capped),
  11 without search (≤ 0.05 s). Sum of decision seconds 500.8 = the whole wall time (one game, nothing else in the run).
- Slowest decision: step 4, Ivits, `TwilightReplayFederationToken` (Twilight's 3-QIC action: repeat the immediate effect of an owned
  federation token), 44.8 s, 4/4 comparisons.
- Federation actions: Ivits 1, Itars 1 (`FormFederation` rows match `federations_formed` [1, 0, 0, 1]).

## Reading

- Tool: works on a real exported room from a late start. Both pre-registered criteria met.
- Reproducibility: no decision hit the 60 s cap, so by the E259 code reading (teacher randomness comes from
  `decision_id` only) the same start should give the same game. That is a prediction, not yet observed — the round-6 arm
  of the main experiment runs the same position again and should end 185 / 69 / 93 / 121. If it does not, a single game
  per start is not a fixed value and the reading of the main experiment has to say so.
- Timing: the note's estimate for the main experiment (≈ 50 min) is too low. Round 6 alone took 8.4 min as the only game
  on the machine. The round-1 arm is a whole six-round game: lab 123 ran 48 such games (same teacher, four at a time) in
  15 h 11 min ≈ 76 min per game. The four arms run together (`--jobs 4`), so the run is as long as the round-1 arm:
  ≈ 1–1.5 h. The lineup is different from 123 (Lost Fleet factions), so this is an estimate.
- Condition: the reference scores carry the engine difference (E252, E257) and different opponents; nothing is read from
  185 against 187.

No code or deployment change. Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Main experiment as agreed in E258–E260: queue `129-room-handover-98ADBD` — same room, starts at rounds 1·4·5·6,
  one game each, same teacher and command (`--rounds 1 4 5 6`), lab ≈ 1–1.5 h (timeout 3 h). Exploratory diagnosis, not
  proof of strength: Ivits final by start round minus the round-1 control (same map, factions, seats; the teacher plays
  from the user's and the live AI's setup). Read with: 4/4 complete, errors 0, decisions cut by the cap per arm (those are
  the only non-repeatable ones), opponents' finals per arm, and the round-6 arm reproducing 185 / 69 / 93 / 121.
- (ㄴ) Nothing else to run before (ㄱ).
Bot recommendation: (ㄱ), after a clean Codex round.
