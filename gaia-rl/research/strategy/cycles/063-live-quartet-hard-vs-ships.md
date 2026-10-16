# Cycle 063 — live hard vs vm_lf_ts_ships on the live bot lineup (Terrans, Xenos, Taklons, Hadsch Hallas)

A: `teacher-a-search4-h1-geodens-cap20.json` (geodens_guide, 4 comparisons, 20 s cap — the live hard teacher).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (vm_lf_ts_ships, the base stack, same
search budget) plus the 14-faction uiqoo opening order added on 2026-10-16 (`UIQOO_OPENINGS`; Hadsch Hallas from
B17: RL + 4 mines, then AC + mine). No other code differs from 062.
Question (user, 2026-10-16 "자료대로 해. 그 외 다 해"): first step of the all-faction teacher. The live server's bot
pool (`dev_game.rs dev_bot_factions`) always draws its three bots from Terrans, Xenos, Taklons and Hadsch Hallas, so
this is the lineup the live hard teacher actually plays. Hadsch Hallas had never been played by the B stack. Does the
052 result (hard vs vm_lf_ts on the geo-quartet, +50.5) hold on the live lineup, and does the stack run without errors
on a faction it has no faction code for?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges. Also look at Hadsch Hallas errors and
unsearched decisions, and decision time. If significantly positive, propose replacing the live teacher (deployment
is the user's call).
12 seeds from `lab/seeds-live-quartet.txt` (live-quartet-801319 … 818705, found with `find_seeds.py` 800000–830000,
kept apart from `seeds.txt`) × 2 seat-swapped games, agentmaco, commit c3df952, stop_round 3 (ends at the start of
round 4). 1 h 42 min wall time.
Result: lab/results/063-live-quartet-hard-vs-ships.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Hadsch Hallas | 12 | 102.3 | 151.6 | +49.3 | [+28.9, +69.8] |
| Taklons | 12 | 107.5 | 159.3 | +51.8 | [+33.0, +70.6] |
| Terrans | 12 | 113.6 | 178.7 | +65.1 | [+31.5, +98.6] |
| Xenos | 12 | 102.6 | 145.3 | +42.7 | [+19.8, +65.6] |
| **All** | 12 | | | **+52.2** | [+41.3, +63.2] |

Significant for every faction and overall. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 | p006 | p007 | p008 | p009 | p010 | p011 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hadsch Hallas | +114 | +56 | +49 | +18 | +77 | +76 | +46 | +31 | +4 | +78 | +16 | +29 |
| Taklons | +60 | +60 | +28 | +57 | +36 | −5 | +44 | +114 | +31 | +47 | +80 | +71 |
| Terrans | +39 | +160 | −4 | +73 | +159 | +85 | +55 | +27 | +75 | +1 | +34 | +77 |
| Xenos | −19 | +96 | +75 | +65 | +47 | −6 | +15 | +42 | +44 | +91 | +43 | +18 |
| Pair mean | +48.5 | +93.0 | +37.0 | +53.3 | +80.0 | +37.5 | +40.0 | +53.5 | +38.6 | +54.2 | +43.1 | +48.8 |

All 12 pair means are positive (smallest +37). 44 of the 48 faction-pair differences are positive; the four negative
ones are small (−4 to −19). This is the same size as 052 on the geo-quartet (+50.5 [+35.1, +65.8]) with a new seed
set, a new lineup and one faction (Hadsch Hallas) the stack had never seen: the gain is not specific to Geodens,
which carried 052 (+121). The published watch replay is pair-001/game-1-A01 seat 1, Terrans on the A arm, 93 charges
against 252 for the B-arm Terrans in the other game.

Hadsch Hallas: 0 errors, 0 timeouts, 0 fallback decisions, unsearched decisions 304 (A) vs 334 (B), in line with
the other three factions. The stack's only Hadsch-specific input is the B17 opening order; the shared rules
(guide_r1, LF prices, value_max, ts_chain, ships) carry the rest.

Reference VP at the start of round 4 (not the verdict): All −8.6 [−12.3, −5.0]; Hadsch Hallas −4.9, Xenos −7.0,
Taklons −10.5, Terrans −12.2. Wider than 052 (−6.8). The B-arm Terrans sit at 0–2 VP at the start of round 4 in six
of twelve games (A: 4–36). This is the known shape of the stack — charges go into buildings, power and research rather
than early points — but no hard-vs-stack game has been played to round 6 yet, so the final-VP consequence on this
lineup is unmeasured.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1567 | 1.87 s | 0.49 s | 5.56 s | 20.2 s |
| B vm_lf_ts_ships | 1845 | 11.36 s | 15.93 s | 20.25 s | 25.5 s |

No errors, timeouts or fallback decisions on either arm. B makes 18% more decisions and is 6× slower on average
(median 33×); its maximum of 25.5 s is inside the live hard wait limit of 60 s. Unsearched decisions 1109 (A) vs 1321
(B), about 71% of decisions on both arms.

Reading: the pre-set condition is met. On the lineup the live server actually plays, vm_lf_ts_ships gains about +52
charges per seat in rounds 1–3 over the live hard teacher, significant for all four factions, with no faction-code
dependence for Hadsch Hallas. The proposal to replace the live teacher goes to the user; no change was made in this
cycle. What a replacement would involve (not done):

- `tools/ai_worker.py` imports `geodens_guide` as its factory for every level; it would import
  `guide_r1_charge3_lf_more_vm_lf_ts_ships` instead (the spec files are not read by the live worker).
- `gaia-server/Dockerfile` copies a fixed list of tool modules; `guide_value.py` (used by the stack) is not in it and
  would be added, and the build checked for any other module the factory imports.
- The factory is shared by easy, normal and hard. Only hard (4 comparisons, 20 s) has been measured on this stack;
  normal is 2 comparisons with a 5 s cap, where the B median of 15.9 s means most decisions would stop at the cap.
  Normal and easy with the stack are untested.
- Open points carried from 052: rounds 4–6 unseen against hard, and the reference VP gap at the start of round 4.

Candidate follow-ups (user decision pending, not queued): a full-length (stop_round 0) hard vs ships run on the
live-quartet seeds to see the final-VP side before deploying; or a normal-level (2 comparisons, 5 s) hard vs ships
A/B, since that is the default live level. Four live-quartet seeds remain (822328 … 826028); more come from
`find_seeds.py 830000 860000 --prefix live-quartet --factions Terrans,Xenos,Taklons,HadschHallas`.
