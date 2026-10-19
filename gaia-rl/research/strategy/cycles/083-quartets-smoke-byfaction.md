# Cycle 083 — ships_byfaction smoke on the three unmeasured-faction quartets (A = B)

A = B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-cap20.json` — the base stack plus the
faction table: Terrans track_income, Geodens former_use, Taklons opening_budget + budget_guard + opening_release
(`CANDIDATE_FACTION_PARTS`), and **track_set** (guide track priority, order only, `FACTION_TRACKS`) for the ten base
factions that no cycle has measured yet. Queued by the user on 2026-10-19 ("종족별 규칙 넣고 실험 시작", E16).
Purpose: not an A/B. The special-rule factions (Ivits space station, Lantids parasite mines, BalTaks former
conversion, Nevlas power) play inside the stack for the first time; the question is only whether the stack runs clean
on them — errors, timeouts, fallback decisions, unsearched comparisons, decision time — so that 085–087 (live hard vs
byfaction per quartet) are valid.
3 quartets × 1 seed × 2 seat-swapped games = 6 games, hard budget (4 comparisons, 20 s), stop at the start of round 4,
agentmaco, commit e649bf4, 57 min wall time. Result: lab/results/083-quartets-smoke-byfaction.md.

| Pair | Seed | Quartet |
|---|---|---|
| p000 | quartet-a-2470 | Lantids · Ivits · Firaks · Nevlas |
| p001 | quartet-b-5187 | BalTaks · Bescods · Gleens · Itars |
| p002 | quartet-c-60 | Ambas · HadschHallas · Terrans · Xenos |

**Health (the point of the cycle): clean.** 6 of 6 games complete, exit code 0, 0 error games, 0 timeout games,
0 fallback-timeout decisions, 0 federation-candidate limit hits on either arm. Decision time is the usual hard-budget
shape: A n = 450, mean 11.40 s, median 16.44 s, p90 20.20 s, max 23.5 s; B n = 454, mean 11.26 s, median 16.76 s,
p90 20.25 s, max 23.4 s (081 B on the live lineup: max 25.3 s; hard server guard 60 s). Unsearched decisions 312 / 450
(69%) vs 308 / 454 (68%), the same fraction as every 4-comparison hard run. Decisions per faction in three rounds:
Xenos 55, HadschHallas 46, Nevlas 41–46, Firaks 43–44, Ivits 38–45, Lantids 27–38, Gleens 36–37, Bescods 35–37,
Ambas 32, Terrans 30, Itars 29–30, BalTaks 25–27. 085–087 are valid as queued.

**Charges in rounds 1–3 (not a verdict — both arms are the same teacher).**

| Faction | A | B | B−A | | Faction | A | B | B−A |
|---|---:|---:|---:|---|---|---:|---:|---:|
| Ambas | 127.9 | 127.9 | 0.0 | | Itars | 52.3 | 51.1 | −1.2 |
| BalTaks | 147.4 | 153.4 | +6.0 | | Ivits | 130.0 | 142.0 | +12.0 |
| Bescods | 256.5 | 263.0 | +6.5 | | Lantids | 213.9 | 162.1 | **−51.8** |
| Firaks | 225.2 | 261.3 | **+36.1** | | Nevlas | 137.2 | 138.5 | +1.3 |
| Gleens | 242.7 | 241.8 | −0.9 | | Terrans | 140.9 | 140.9 | 0.0 |
| HadschHallas | 169.7 | 169.7 | 0.0 | | Xenos | 171.1 | 171.1 | 0.0 |
| **All (seat mean)** | | | **+0.7 [−3.5, +4.9]** | | | | | |

Two readings come out of an A = B run.

1. **Noise floor of one pair at the hard budget.** p002 (quartet c) is identical to the decimal on both arms — same
   charges, same decision counts, same unsearched comparisons (3575 / 3575, 5595 / 5595, 8222 / 8222) — so the stack is
   deterministic when the 20 s cap cuts the same comparisons. p000 and p001 drifted: the cap is wall-clock and four
   games ran in parallel, so the arms searched different comparison counts (BalTaks 2205 vs 2420, Lantids 5393 vs
   3400, Lantids decisions 38 vs 27) and the games diverged. The resulting per-faction, single-pair differences —
   Lantids −51.8, Firaks +36.1, Ivits +12.0 — are **pure timing noise**. 078 saw the same thing (three pairs identical
   through round 3, drift from round 4). For 085–087 (6 pairs each, 4R) this is the yardstick: a per-faction swing of
   ±40–50 in one pair means nothing, and per-faction verdicts need the sign across six pairs, not the mean of one.
   The posted watch replay (pair-000/game-0-A02 seat 3, Lantids B 162 vs A 214 in the other game) is one side of
   such a drift, not a rule effect.
2. **Charge levels by faction** (same teacher, so these are the stack's own levels): Bescods 256–263, Gleens 242,
   Firaks 225–261 and Lantids 162–214 earn as much as or more than the measured quartet's best (082 B Geodens 196);
   Ambas 128, Ivits 130–142, Nevlas 137, BalTaks 147–153 and HadschHallas 170 are mid; **Itars 51–52** is by far the
   lowest seat in the run (Itars burn power tokens in the Gaia area for tech tiles, so a low charge count may be the
   faction, not a defect — the 086 replay will say). 4R-start VP are 2–18 per seat on all twelve factions, the
   stack's usual "hold charge, bank VP later" shape.

**Research footprint of track_set, rounds 1–3 (`research_counts.py`, one seat-game per arm).** `FACTION_TRACKS`
priority in the second column; counts are ResearchAdvance moves (Bescods' free lowest-track step is a different move
type and is not counted).

| Faction | Guide tracks | A | B | Off-guide |
|---|---|---|---|---|
| Ambas | TF · Eco · Sci | TF 2 · AI 1 · Sci 1 | same | AI 1 |
| BalTaks | Gaia · Eco · TF · AI | Gaia 1 · Eco 1 · Sci 1 | same | Sci 1; guide "Gaia 4 in R1" not reached (Gaia 1) |
| Bescods | Sci · Eco · Nav | Nav 1 · Eco 1 | Nav 2 · Eco 1 | none, but **Sci 0** (first-priority track) |
| Firaks | Eco · Nav · Gaia | Nav 2 · AI 1 · Gaia 1 | Nav 3 · AI 1 · Eco 1 | AI 1 both arms; Eco (first) 0 / 1 |
| Gleens | Nav · Gaia | Nav 2 · Gaia 4 · Eco 1 | same | Eco 1 (guide: two tracks only) |
| HadschHallas | Eco · Nav · Sci | TF 1 · Nav 2 · Eco 1 | same | TF 1 |
| Itars | Gaia · Eco · TF | TF 1 · Eco 1 | TF 1 · Gaia 1 | none |
| Ivits | Eco · Sci · AI | — | — | **no research at all in three rounds** (guide: Eco 2 in R1) |
| Lantids | Nav · Sci · AI | TF 1 · AI 3 | AI 2 | TF 1 (A); Nav and Sci (first two) 0 |
| Nevlas | Eco · Sci · Nav | TF 1 · Nav 2 · Eco 3 | Nav 4 · Eco 3 | TF 1 (A) |
| Terrans (not track_set) | Nav · Gaia · Eco | AI 2 · Sci 1 | same | base stack, terrans_gaia_late |
| Xenos (not track_set) | Gaia · Nav · Eco | TF 2 · Nav 2 · AI 2 | same | base stack |

Of the ten track_set factions, seven research mostly on their guide tracks (Gleens Nav 2 / Gaia 4, Nevlas Eco 3 / Nav,
Itars, HadschHallas, Ambas, BalTaks, Bescods) and six seat-games hold one off-guide step each (Ambas AI, BalTaks Sci,
Firaks AI ×2, HadschHallas TF, Lantids TF, Nevlas TF, Gleens Eco). The rule swaps the best research move's score with
the best guide-track research move only when a guide-track step is available and no situational rule chose the
off-guide step, so each of these is either "guide track blocked / unaffordable at that decision" or "rule did not
fire" — the HANDOFF already lists this as the thing to check with `explain_ab_decisions.py` on the 083 game folders
(Bescods R2 AI and R3 Gaia, Itars R4 Nav were seen in the pre-queue smoke; here it is Firaks AI, Lantids TF, Ambas AI).
Two footprints are larger than a single step: **Lantids** never touch Nav or Sci (their first two guide tracks) and
put 2–3 steps into AI (third), and **Ivits** make no research move at all, against a guide that opens Economy 2 in
round 1. Both are quartet a (085).

**Reading.** On the only question the cycle asks — does the stack run clean on the ten unmeasured factions — the
answer is yes: no errors, no timeouts, no fallbacks, decision time inside the hard guard, unsearched fraction
unchanged. 084 (ships vs byfaction, geo-quartet, 6R) started at 14:06 and 085–087 follow as queued; nothing in 083
changes them. The two things 083 adds are (a) the per-pair noise yardstick for reading 085–087 and (b) a short list of
decisions to explain before those results arrive, so that a negative faction in 085–087 can be split into "rule fired
and hurt" vs "rule never fired". No code change, no deployment, base stack unchanged.

**Proposal (user decision, nothing queued).**

- (ㄱ) **Lab time 0, bot work**: `explain_ab_decisions.py` on the 083 folders — Ivits (p000, both games: why no
  research in three rounds; whether Economy was available and what outranked it), Lantids (p000 game-1-A13 seat 3
  and game-0-A02 seat 3: AI over Nav/Sci), and one off-guide step each for Firaks AI, Bescods (Sci 0) and BalTaks Sci.
  Output: for each, "guide track unavailable" or "track_set did not fire" — the reading key for 085–087. Can run while
  084 plays (only CPU contention; 079's 111 s decisions came from that, so prefer the gap between runs).
- (ㄴ) Queue unchanged: 084 → 085 → 086 → 087 as listed in 5a E16 (≈ 3 h 20 min + 3 × 1.5 h). Read each quartet by the
  sign across six pairs and the pooled quartet mean; a faction with a per-pair swing inside ±50 and a mixed sign is
  "not measured", not "negative".
- (ㄷ) Repeats: the a/b/c seed lists hold 29–32 unused seeds each. If a quartet comes back with a faction at 4–5 of 6
  pairs on one sign but a CI through 0, the next slot is the 6-seed repeat of that quartet (12 pairs pooled, as
  074 + 076). Decide per quartet after its result, not now.

Bot recommendation: (ㄱ) now, (ㄴ) as queued, (ㄷ) case by case.
