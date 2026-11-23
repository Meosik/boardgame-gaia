# Cycle 129 — room handover 98ADBD — the teacher plays the user's room on from the round 1, 4, 5 and 6 starts, one game each, command

No A/B. One teacher, `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(factory `guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier`, 4 comparisons, 60 s cap, parallel 2), sits in all four
seats and plays the user's live room 98ADBD (Ivits = user, 187 points; Space Giants, Tinkeroids, Itars = live-server AI) on
from the first action decision of rounds 1, 4, 5 and 6 (snapshot revisions 11, 130, 191, 280) to the end of the game.
Part under test: none of the teacher's — this is the diagnostic the tool `tools/room_handover.py` was written for (E258,
E259; smoke = cycle 128). Queued 2026-11-23 by the user's 「내 플레이로 하이브 교사의 실력을 높일 수 있나? 테스트 해봐」 → 「ㄱ」 →
「진행해」 (E258·E259·E261 (ㄱ)·E262).
Pre-registered (queue note): exploratory diagnostic, **no verdict**, not a proof of strength. Control = the round-1 start
(same map, factions, seats; the teacher starts from the setup of the user and the live AI). Reading = Ivits final score
(round 4, 5, 6 start) − control = the value of the room position at that round, opponents' positions included — not the
user's opening alone; a low finish does not prove late-game play at fault. Purpose: choose which stretch to look at with
explain. Not compared: the room's 187 (different engine: E252, E257; different opponents) and the teacher's mean on other
maps (≈ 97). Health = 4/4 games finished, `failures` empty, errors 0, fallback timeouts 0. Read alongside: decisions cut
by the 60 s cap per arm, maximum decision time, decisions over 100 s, opponents' finals per arm, federation actions per
seat, and the round-6 arm reproducing 128 (185/69/93/121).
One game per start, four arms at once (`--jobs 4`), no seed (map and game up to the start are the room record
`~/gaia-media/rooms/98ADBD-snapshots.jsonl`), `GAIA_ENGINE_FIXES_2=1`, engine = lab HEAD build. agentmaco, commit a388cb2,
2026-11-23 13:04:26 → 13:57:50 (53 min 24 s; estimate was 1–1.5 h). Result: lab/results/129-room-handover-98ADBD.md.

**Health: clean.** Exit code 0, 4/4 games finished (`games_complete` 4, `failures` empty), errors 0, fallback timeouts 0,
decisions over 100 s 0, expired before search 0. The result page has no review section (command job).

| Arm (start) | Decisions | Mean · median · p90 · max (s) | Cut by the 60 s cap | Over 30 s | Searched / 4 of 4 comparisons |
|---|---:|---|---:|---:|---|
| Round 1 | 249 | 12.85 · 7.01 · 36.71 · 60.06 | 11 | 34 | 213 / 201 |
| Round 4 | 187 | 9.76 · 5.21 · 25.98 · 60.03 | 2 | 10 | 160 / 158 |
| Round 5 | 139 | 15.35 · 7.35 · 47.78 · 60.07 | 9 | 27 | 114 / 104 |
| Round 6 | 76 | 8.60 · 5.54 · 20.95 · 57.24 | 0 | 3 | 65 / 63 |

(One-line Python count over each arm's `decisions.jsonl.gz`: `seconds`, `timing.time_capped`, `compared`,
`completed_comparisons`. The cap counts equal `at_or_over_60_seconds` in `metrics.json`.)

## Scores (reference values, no verdict)

No charges table: no A/B, one room, one game per start. The pre-registered reading is the Ivits final score minus the
round-1 control.

| Arm (start) | Ivits VP at the start | Ivits final | − control | Ivits rank | Space Giants | Tinkeroids | Itars |
|---|---:|---:|---:|---:|---:|---:|---:|
| Round 1 (control) | 10 | 103 | 0 | 3 | 104 | 86 | 106 |
| Round 4 | 11 | 134 | **+31** | 1 | 74 | 84 | 118 |
| Round 5 | 27 | 155 | **+52** | 1 | 66 | 85 | 114 |
| Round 6 | 64 | 185 | **+82** | 1 | 69 | 93 | 121 |
| Room itself (user + live AI, live engine; not compared) | — | 187 | — | 1 | 71 | 88 | 103 |

The later the teacher takes the seat over, the higher Ivits finishes: every stretch the user played adds to what the
teacher ends with. No replay posted (queue note).

## Activation (did the design run as written)

- **Start positions** (`manifest.json` `starts`, `states/round-N.json`): revisions 11 / 130 / 191 / 280; Ivits VP
  10 / 11 / 27 / 64 (same as the bot-turn check, E262), structures 1 / 9 / 11 / 15, technology tiles 0 / 3 / 5 / 7,
  federation tokens held 0 / 1 / 2 / 3. `snapshots_skipped` 5.
- **Round-6 arm reproduces 128**: 185/69/93/121 again, 76 decisions with the same split per seat (34/7/20/15), 65 searched
  and 63 with 4 of 4 comparisons, 0 decisions cut by the cap — as in 128. Only the time moved, because four arms ran at
  once: mean 6.59 → 8.60 s, maximum 44.80 → 57.24 s. So the E259 code reading holds for this position: with no decision
  cut by the cap, the same start gives the same game.
- **Decisions cut by the cap** (`timing.time_capped` by seat and round): 22 of 651. Round-1 arm 11 (Ivits: round 1 two,
  round 5 five, round 6 four), round-4 arm 2 (Ivits round 5), round-5 arm 9 (Ivits round 5 six, Ivits round 6 one, Space
  Giants round 5 two), round-6 arm 0. 20 of the 22 are Ivits decisions and 13 are Ivits decisions in round 5.
  These three arms are therefore not fixed values: a rerun can differ at those decisions.
- **Federations** (`metrics.json` `federations_formed`, seats Ivits/Space Giants/Tinkeroids/Itars): round-1 arm 3/1/1/1,
  round-4 arm 2/1/0/1, round-5 arm 1/0/0/0, round-6 arm 1/0/0/1. Ivits `FormFederation` by round (decision log): round-1
  arm in rounds 3, 5, 6; round-4 arm in rounds 4, 6; round-5 arm in round 5; round-6 arm in round 6. With the tokens held
  at the start (0/1/2/3) Ivits ends with 3 / 3 / 3 / 4 — the count of federations barely differs between arms.
- Decisions per seat: round-1 arm 70/61/71/47, round-4 arm 56/38/43/50, round-5 arm 40/30/33/36, round-6 arm 34/7/20/15.

## Reading (HANDOFF 1 order)

- **Pre-registered reading**: the room position is worth +31 at the round-4 start, +52 at the round-5 start and +82 at the
  round-6 start over the teacher playing the whole game from the same setup. It grows at every start.
- **Per stretch (a subtraction made after seeing the result, not pre-registered)**: rounds 1–3 +31, round 4 +21
  (134 → 155), round 5 +30 (155 → 185); round 6 is 185 against the room's 187, which is not compared. No stretch stands
  out as the only gap, and round 6 alone shows none worth a look.
- ① Noise: one game per arm. The round-6 arm is a fixed value (reproduced exactly, no capped decision); the other three
  hold 11, 2 and 9 capped decisions, so their spread on a rerun is not measured. The differences (21–31 per stretch) are
  leads, not measurements.
- ② Activation: all four starts loaded and played to the end; the reproduction check passed.
- ③ Scope: the rounds 1–3 stretch is the most confounded. In the round-1 arm the teacher also plays the three opponents'
  openings, and Space Giants finishes 104 there against 66–74 in the arms that start from the live AI's position
  (Tinkeroids 84–93 and Itars 106–121 move less). So +31 mixes "the user's opening" with "weaker opponents' openings" —
  as pre-registered, it is not the value of the user's opening alone.
- ④ Interaction with search: the cap bites where Ivits is biggest. 13 of the 22 capped decisions are Ivits decisions in
  round 5, in three different arms; part of that is the load of four arms at once (the round-6 arm ran 30% slower than
  alone in 128). Whether the round-5 loss comes from those cut comparisons or from what the teacher prefers is not known.
- ⑤ Cleanest pair: round-5 arm against round-6 arm. Both come from the same round-5 start; the only difference is who
  played round 5 (teacher in all seats: Ivits ends 155; user and live AI: Ivits ends 185 with the same teacher playing
  round 6). The user's round 5 took Ivits from 27 to 64 VP, 11 to 15 structures, 5 to 7 technology tiles, 2 to 3
  federation tokens. Round-4 arm against round-5 arm is the same kind of pair for round 4 (+21).
- ⑥ Condition: one room = one map, one lineup, live-AI opponents up to each start. Nothing here generalises to the
  teacher's Ivits on other maps.
- Health and timing: clean; 53 min for the four arms at once, the round-1 arm (3,199 s of decisions) sets the length.

No code or deployment change. Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Round-5 stretch side by side — bot turn 1–2, no lab. Replay the round-5 arm's Ivits moves of round 5 from
  `states/round-5.json` and the user's round 5 from the room record (revisions 191–280); put the two round-6 start states
  next to each other (VP, structures, technology tiles, federations, resources) and explain the first two or three teacher
  decisions that part from the user's line, the capped ones first. Decides: what the teacher does not do in round 5 that
  the user did.
- (ㄴ) Measure the spread: the same command with `--repeats N` (lab ≈ 1 h per repeat of the four starts). N is the user's
  number.
- (ㄷ) The same experiment on another room of the user's (another map), once a room export exists.
- (ㄹ) Rerun the arms one at a time (`--jobs 1`, ≈ 2 h) to remove the capped decisions caused by load. Low priority.

Bot recommendation: (ㄱ) first — it is what this diagnostic was for; (ㄴ) only if the user wants the differences as numbers.
