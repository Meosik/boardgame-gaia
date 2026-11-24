# Cycle 133 — fixed-seed ladder, stage 1 baseline (map `quartet-e-88365`, 12 faction sets × 1 game, 6R), command, no verdict

No A/B: one `command` job, `teacher_ab.py run --single` (one game per seed) with the same teacher in all four
seats — `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(`ships_menu1_all_tier`, cap60-p2, 4 comparisons; `pass_last` · `shipnow` · `charge_phase` off, they have no A/B yet),
the 114 · 119 · 123 environment (`GAIA_ENGINE_FIXES_2=1`, `GAIA_FEDERATION_ONE_ROUTE` off). Queued 2026-11-24 by the
user's 「그냥 모든 종족이 3연방이라도 일단 하게 목표를 잡아야할거 같은데」 after a clean Codex round (HANDOFF E297); the
ladder itself is E177 · E178 · E180 · E181.
Pre-registered verdict: none (baseline). Ladder criterion (user E180, read as an exception to the rounds 1–3 charge
rule): **every seat of all 12 games forms 3 or more federations and the seat mean final VP is 120 or more** → stage 2
(rotating tiles). This run measures the distance to it. Read alongside: games complete, fallbacks, decision time,
federations per seat (FormFederation choices in the decision log; tokens from other routes separately), rounds of the
first and second federation, seat mean VP; per-faction values are written down, not read (2–3 seats each).
Map and tiles fixed (`quartet-e-88365`), 12 faction sets = `lab/fixed-seed-factions-quartet-e-88365.json` (18 factions,
2–3 seats each), turn order `@order` from `faction_strength.py`, the 12 seed lines =
`lab/seeds-fixed-ladder-quartet-e-88365.txt` (the same lines are used after every teacher change), 6 rounds,
agentmaco, lab commit bdd2fec, engine build 49318fef, 2026-11-24 16:39 → 20:32 (3 h 52 min).
Result: lab/results/133-fixed-seed-ladder-baseline-12.md (no second-model review section — command job).

**Health: clean.** 12 / 12 games complete, exit code 0, no failure, 0 error games, 0 timeout games, 0 fallback-timeout
decisions, 0 federation-limit hits. 3,500 decisions: seconds mean 13.7 · median 7.7 · p90 37.1 · p99 60.0 · max 62.5;
over 60 s 128 (3.66%), over 80 s 0 (`lab/scratch_123_stats.py`). 2,827 of 3,500 decisions had more candidates than the
4 comparisons (result table "비교 미탐색 결정" 1,379 + 1,448) — the budget, not a fault. All 12 games replay to the end
with the lab build 49318fef; the work tree build (67eaa893) does not (candidate index out of bounds in the first game),
so every replay count below preloads `~/projects/gaia-lab/gaia-rl/python`.

## Distance to the ladder criterion (not a verdict)

| | this run | criterion |
|---|---:|---:|
| Games where every seat formed 3+ federations | **0 / 12** | 12 / 12 |
| Seats with 3+ federations formed | **2 / 48** (both Xenos) | 48 / 48 |
| Seats holding 3+ federation tokens at the end | 4 / 48 | — |
| Seat mean final VP | **101.6** (min 70, max 140; winner mean 116.8) | 120 |
| Seats at 120 VP or more | 6 / 48 (100 or more: 25) | — |

Federations formed per seat (FormFederation choices, `lab/scratch_123_stats.py`, same numbers from the replay in
`lab/scratch_fed_third.py`): 0 = 0 seats, 1 = 32 (67%), 2 = 14 (29%), 3 = 2 (4%); mean 1.38. The lowest seat of every
game formed exactly 1 (12 / 12 games); federations per game 4 × 1, 5 × 5, 6 × 5, 7 × 1 game.
Tokens held at the end (`lab/scratch_133_review.py`, green + gray): 1 = 29, 2 = 15, 3 = 4, mean 1.48. The five seats
holding one more than they formed all stand on terraforming level 5 (the track's token): Ivits pair-000, Geodens
pair-004, Tinkeroids pair-005 and pair-010, HadschHallas pair-011. No artifact or alliance route.

Rounds (`lab/scratch_fed_third.py`): first federation R2 8 · R3 30 · R4 8 · R5 2 seats; second (16 seats) R4 2 ·
R5 2 · R6 12; third (2 seats) R6 2.
Final VP by federations formed (description, not an effect): 1 → 96.4 (32 seats), 2 → 109.7 (14), 3 → 129.0 (2).

Reference only, other maps (114 · 119 · 123 collections): 114 seat mean 100.1 VP · 1.50 federations, 119 99.0 · 1.52;
93 games, 372 seats: 1 federation 201 (54%), 2 146 (39%), 3 23 (6%) (E174). This map sits in the same place.

Per faction (2–3 seats each, written down only — not read as differences):

| Faction | Seats | VP | Federations formed |
|---|---:|---:|---:|
| Xenos | 3 | 126.7 | 2.67 |
| Darkanians | 3 | 113.3 | 1.33 |
| Lantids | 3 | 110.0 | 1.33 |
| Bescods | 3 | 108.0 | 1.67 |
| Taklons | 3 | 108.0 | 1.33 |
| Terrans | 3 | 107.7 | 1.33 |
| HadschHallas | 2 | 107.0 | 1.50 |
| Gleens | 2 | 106.0 | 1.50 |
| Nevlas | 3 | 102.3 | 1.00 |
| BalTaks | 3 | 100.7 | 1.00 |
| Ivits | 2 | 100.0 | 2.00 |
| Tinkeroids | 3 | 100.0 | 1.00 |
| Ambas | 2 | 97.0 | 1.50 |
| Firaks | 3 | 95.3 | 1.33 |
| Geodens | 3 | 91.0 | 1.00 |
| Moweyds | 2 | 86.0 | 1.50 |
| Itars | 2 | 82.0 | 1.00 |
| SpaceGiants | 3 | 77.7 | 1.00 |

## Where the seats stop (replay counts, lab build)

`lab/scratch_fed_third.py` (stage k = the seat has formed k federations; "legal" = a FormFederation candidate at one of
the seat's main-turn decisions):

| Stage | Seats | Formed | Legal but left / lost | Never legal |
|---|---:|---:|---:|---:|
| 0 → 1 | 48 | 48 | 0 / 0 | 0 |
| 1 → 2 | 48 | 16 | 0 / 0 | **32** |
| 2 → 3 | 16 | 2 | 0 / 0 | **14** |

Every federation was formed in the round it first became legal (48 / 48, 16 / 16, 2 / 2). No seat ever ended with a
legal federation unformed.

`lab/scratch_fed_why.py` (power value of the seat's buildings outside its federations against the engine's need; engine
checks A 0 of 79 decisions, B 0 of 66 actions):

| Stopped at | Seats | Power short | Enough power, cause unconfirmed | At the last main turn of R6: power outside / need | Buildings outside | Power inside | Short by 0 / 1 / 2 / 3 / 4 / 5+ |
|---|---:|---:|---:|---|---:|---:|---|
| 1 federation | 32 | 29 | 3 | 3.88 / 7.0 | 2.78 | 10.72 | 3 / 3 / 1 / 12 / 4 / 9 |
| 2 federations | 14 | 13 | 1 (Ivits, satellite funds 0) | 2.29 / 8.93 | 1.57 | 16.21 | 1 / 1 / 1 / 1 / 2 / 8 |

One-federation seats by round (last main turn): R4 power outside 1.94 · inside 8.16 · buildings outside 1.81 (31
seats); R5 2.50 · 8.91 · 2.34; R6 3.88 · 10.72 · 2.78. Satellite funds mean 6.3 in R4–R5, 3.6 in R6.

## Reading

- **The criterion is far, and the pattern is the one E174–E176 found on other maps.** 0 of 12 games, 2 of 48 seats
  (4 by tokens held), 101.6 VP against 120. The seats do not skip a federation they can form (0 left, 0 lost); the next
  one never becomes legal — 32 of 48 for the second, 14 of 16 for the third — and in 42 of those 46 the building power
  outside the existing federations is short.
- **Mostly short by a lot, not by 1–2.** At the last main turn of round 6, 6 of the 46 stopped seats are 1–2 short
  (4 of 32 and 2 of 14), 36 are 3 or more short (25 and 11), 4 have the power and no candidate (cause unconfirmed).
  The pre-registered first fix candidate E179 (ㄱ) (in R5–6, when the power outside is 2 or less short, a
  power-raising root inside the four comparisons) aims at that 1–2 group: 6 of the 46 stopped seats at the end.
  Recount after the debate (Codex 1/1, accepted — the earlier "at most 6 of 46" is withdrawn as a bound on the fix):
  the smallest shortfall over every main-turn decision of the final stage (`best_gap` in the `scratch_fed_why.py`
  output) falls in the same 0 / 1 / 2 / 3 / 4 / 5+ cell as the round-6 last-turn shortfall for all 46 seats, so none
  of the 36 seats that ended 3 or more short was within 2 at any decision of that stage. Not counted, and therefore
  no maximum reach is stated: the 4 seats that reached enough power without a candidate, the stages that were formed
  (12 of the 16 second federations came in round 6 — the fix could bring such a federation forward and leave time
  for the next), and whether a filling move existed and could be paid at those decisions.
- **The volume outside the first federation is the gap, and it opens before round 5.** A one-federation seat ends
  round 4 with 1.81 buildings (power 1.94) outside its federation; over R5–R6 the power inside the existing federation
  grows by 2.56 (8.16 → 10.72) and outside by 1.94 (1.94 → 3.88). Total building power at the end: 14.6 for
  one-federation seats and 18.5 for two-federation seats, against 14 for two federations and 21 for three (E175 on
  93 games: 14.2 and 17.9). Why the growth lands inside the federation (cheaper sites next to it, range, or the
  ranking) is not measured here.
- **VP.** 101.6 is at the level of 114 (100.1) and 119 (99.0). The VP by federations formed (96.4 / 109.7 / 129.0) is
  a description of these seats, not the effect of a federation.
- **Limits.** One map, 12 games, 48 seats; the same-code rerun spread is not measured, so a later difference on the
  same 12 lines has no noise reference yet. Per-faction values are 2–3 seats. Federations are counted as
  FormFederation choices; tokens from the terraforming track are listed separately.
- Health and timing: nothing to fix; decision time stays under the cap60 envelope (max 62.5 s).

No code or deployment change. Lab queue is empty after this cycle. Note for tools: the work tree venv build differs
from the lab build (67eaa893 against 49318fef), replay tools run in the work tree need the lab module.

## Proposal (user decision, nothing queued)

- (ㄱ) Bot turn, read-only (a few minutes): the pre-registered count on these 12 games — "could build and passed"
  (E296: building site × target building kind, deduplicated; denominator = all passes), split by round and by
  federations formed, and whether the buildable target lies outside the seat's federation. Added in the debate: over
  all R5–6 main-turn decisions (formed stages included), the seats that met the E179 (ㄱ) condition (1–2 short) at
  least once and the number of payable power-raising moves at those decisions.
- (ㄴ) Same 12 lines, same teacher, once more (lab ≈ 4 h, command, no verdict): the same-code rerun spread of
  federations per seat and seat mean VP — the noise reference every later fix on these lines is read against.
- (ㄷ) Federation plan design stages 1–3 (`research/strategy/federation-plan-design.md`, `fed_plan` flag; E179 (ㄱ) is
  its front-slot part) and its measurement on the same 12 lines (lab ≈ 4 h): waits for the user's approval and
  numbers (short value 2, verdict criterion, number of games). 36 of the 46 stopped seats end 3 or more short, which
  is the part design (다) (mine sites in R1–5) is about; the reach of the front-slot part is open until (ㄱ).
Bot recommendation: (ㄱ) and (ㄴ) now (the lab is idle), (ㄷ) after (ㄱ) shows whether the missing buildings were
affordable.
