# Cycle 138 — setup-only placement simulation, 20 maps — where the teacher puts starting buildings, setup only

A = B = `ships_menu1_all_tier` cap60-p2 in all four seats (same teacher as 133 · 134); no part under test. Games stop after the
starting placement, before boosters (`teacher_ab run --single --stop-after-setup`, 5896e92), each saving `setup_state.json`.
Queued 2026-11-26 by the user (「배치 시뮬레이션 + 초반에 건설할 만한 땅 찝어주기까지는 될듯? … 거기서 너가 패턴을 찾아봐」 →
「그렇게 해」, the only exception to the experiment hold of E341). Pre-registered verdict: **none** (observation). Read: ① own
building distances ② planets the second mine adds ③ nearest opponent building ④ step mix of the top 5 early sites ⑤ ① vs ②.
Quartets a–e, 4 unused seeds each = 20 maps, 1 game per map, setup only, agentmaco, commit 6c69d96,
11:34 → 12:00 (26 min; estimate was 1–3 h). Result: lab/results/138-setup-placement-sim-20.md.

**Health: clean.** 20/20 games complete (pair-000 … 019, 20 `setup_state.json`), errors 0, timeouts 0, fallback-timeout
decisions 0. Unsearched-comparison decisions 53 (Geodens 209 + 67 comparisons, Gleens 22 + 65) — placement decisions with many
open sites; not read further (no verdict). All 80 seats have reach 1 (navigation 0). Building counts match the rules:
2 mines for base factions, Xenos 3, Ivits 1 (PI), Lost Fleet Darkanians · Moweyds · SpaceGiants · Tinkeroids 1
(reverse pass only, as in cycle 112 / `engine.rs` `starting_placement_queue`).

## Charges in rounds 1–3 (the verdict)

None — the games stop before round 1. No replay posted here (`138r-setup-replays` is queued separately).

## Activation / counts (setup only)

Tool: `tools/setup_report.py` functions imported in memory by `lab/scratch_138_patterns.py` and two one-line snippets (the script
itself writes into the run dir under gaia-lab, which bot turns must not edit; `setup_report.md` was therefore not written).

- ① Own building distance (pairs of own buildings, 76): 2:1 · 3:1 · 4:4 · 5:15 · 6:11 · 7:9 · 8:10 · 9:7 · 10:4 · 11:6 · 12:3 ·
  13–15:5. 74/76 are ≥ 4 apart, median ≈ 7. By faction (mean, 4 seats each, Terrans · Xenos 8): Gleens 4.5, Geodens 5.0,
  Terrans 5.9, Lantids 6.8, Ambas · BalTaks 7.2, Nevlas 7.5, Bescods · HadschHallas 8.0, Taklons 8.2, Firaks · Itars 8.5, Xenos 9.0.
- ② Planets the second mine adds over the first: at reach 1 (the tool's metric) 0:13 · 1:33 · 2:9 · 3:5 — **but this is not
  overlap**: the first mine alone has 1.1 free planets within distance 1 on average, and mines ≥ 4 apart cannot share any. At
  reach 3 (reach 1 + 2 QIC range, recount snippet): each mine sees 9.1 free planets; the second adds 3–14 (mean ≈ 8.4), and
  37/60 seats share **zero** planets, 6 share 1, 17 share 2–5.
- ③ Nearest opponent building (80 seats): 1:31 · 2:36 · 3:6 · 4:4 · 5–7:3 → 67/80 (84 %) within 2. Moweyds the exception (mean 5.0).
- ④ Top 5 early sites per seat (399 sites): 237 (59 %) need a QIC, 199 (50 %) next to an opponent. Steps from home (ring factions):
  0:37 · 1:136 · 2:40 · 3:49; off-ring 137 (Transdim 39, Gaia 8, and all sites of factions whose home is off the ring — Lost Fleet,
  so their steps are blank). Sites reachable without QIC per seat: 0:6 · 1:22 · 2:28 · 3:14 · 4+:10 → 56/80 (70 %) have ≤ 2.
  Non-QIC sites at ≤ 1 step: 0 for 49/80 seats (includes the off-ring seats).
- ⑤ Mine distance vs ② (reach 1): flat, 0.5–1.5 at every distance — expected, since at reach 1 ② is just sparsity.

## Reading (HANDOFF 1 order)

- Pattern 1 — **spread, not clustered**: the teacher puts its two mines ~7 apart, so at QIC range they open two separate
  ~9-planet areas with little overlap. Gleens · Geodens · Terrans sit closer (4.5–5.9), Xenos · Firaks · Itars farthest.
- Pattern 2 — **next to opponents**: 84 % of seats have a building within 2 of an opponent (charge-seeking placement).
- Pattern 3 — **few free planets inside base reach**: 70 % of seats have at most 2 free planets within reach 1, and most ring
  factions have no 0–1-step planet within reach 1. **Hypothesis only** (Codex debate 1/1, accepted): `setup_report.py` marks
  `qic` as `distance > reach` and checks neither buildability, resources, terraform cost nor boosters (range / terraform
  booster), so "59 % need a QIC" means "59 % lie outside base reach", not a measured round-1 cost. Whether the first-round
  mine really needs a QIC, terraforming or navigation is not shown by this data.
- ① noise: 4 seats per faction — faction means are only indicative. ③ scope: ② at reach 1 measures sparsity, not overlap
  (the reach-3 recount replaces it); ④'s ranking is a heuristic (no federation split, no satellites, current navigation only).
  ⑥ condition: one game per map, the teacher's own placement — this shows what the teacher does, not whether it is good.
- Health and timing: clean, 26 min for 20 setup-only games.

No code or deployment change. Lab: `138r-setup-replays` queued (replays of these setups). Experiment hold (E341) stays.

## Proposal (user decision, nothing queued)

- (ㄱ) `setup_report.py`: output-dir option (so bot turns can write the report outside gaia-lab) and ② at reach + QIC range —
  bot turn, Sonnet subagent, minutes.
  Done 2790b80 (`--out`, `added_planets_qic`, Summary section); the distance-only QIC label is renamed in the follow-up commit.
- (ㄴ) Theory: pattern 3 enters the E345 design only as a hypothesis (outside base reach ≠ measured cost); a real cost
  check (ore/credits/QIC/booster at the first main turn) would be a later tool change — discussion, no experiment.
Bot recommendation: (ㄱ) done; (ㄴ) as a hypothesis only; no new experiment while the hold stands.
