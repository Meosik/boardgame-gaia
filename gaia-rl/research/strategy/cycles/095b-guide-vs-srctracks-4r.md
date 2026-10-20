# Cycle 095b — ships_byfaction_guide vs ships_byfaction_guide_srctracks, quartet a, 4 rounds (the PG track order alone)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-guide-cap20.json` (093's A arm).
B = `...-ships-byfaction-guide-srctracks-cap20.json`: the same plus `track_steps_src` only (`SOURCE_TRACK_PARTS`,
flag `source_tracks`; opening_only and building_due off). `TRACK_STEPS_SRC` **replaces** the faction's B-blog
`TRACK_STEPS` entry: Nevlas round-1 Science 3 (N1; B-blog had no entry), Lantids Economy 2 first (L1; B-blog
Navigation 2 first), Ivits Science 2 first (I1; B-blog Economy 2 first). Firaks runs the same code on both arms
(drift yardstick). Queued by the user on 2026-10-21 ("그렇게 해", HANDOFF E59 (ㄱ)) after 093, where
track_steps_src was the only source part that fired fully and Nevlas +11.2 (5 of 6) was the only lean.
Pre-registered verdict: charges gained in rounds 1–3 per faction (1 VP = 1.5 charges); Nevlas confirmed if the
12-pair mean is ≥ 25; Lantids L1 alone (no opening list); Ivits; read alongside research_counts 1–3R (activation),
plan_labels (round-1 plans should match across arms), upgrade_counts, decision time, errors; if the sources' gain
is rounds 4–6 (⑤), re-measure the positive factions at 6R.
quartet-a (Lantids · Ivits · Firaks · Nevlas): 093's six seeds (28079 · 28757 · 29744 · 30904 · 36030 · 37776 =
pairs 000–005) + six new (37936 · 51008 · 55834 · 56778 · 57732 · 58786 = pairs 006–011) = 12 seat-swapped pairs,
hard budget (4 comparisons, 20 s), stop at the start of round 4, agentmaco, commit 889c10b, 03:38 → 06:06
(2 h 28 min). Result: lab/results/095b-guide-vs-srctracks-4r.md.

**Health: clean.** 24 of 24 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1733 vs 1725; A mean 10.06 s, median 10.47 s, p90 20.12 s, max 22.9 s; B mean 9.66 s, median
9.44 s, p90 20.11 s, max 23.3 s. Unsearched 1217 vs 1153. No pair is identical across arms (the part changes
every seat's game). The part costs no time.

## Charges in rounds 1–3 (the verdict)

| Faction | B part | A | B | B−A | 95% CI | Pairs B > A | Per pair (000–005 = 093 seeds · 006–011 new) |
|---|---|---:|---:|---:|---|---:|---|
| **Nevlas** | Science 3 in R1 (N1) | 155.6 | 169.6 | **+14.0** | **[+0.2, +27.9]** | **9 / 12** | +20 · +48 · +1 · +50 · +0 · −5 · −13 · +2 · −7 · +22 · +39 · +10 |
| **Lantids** | Economy 2 first (L1) | 185.2 | 184.8 | −0.4 | [−26.9, +26.0] | 6 / 12 | +6 · −50 · −13 · +11 · +52 · −27 · −39 · +76 · +31 · +26 · −18 · −60 |
| **Ivits** | Science 2 first (I1) | 171.8 | 150.2 | **−21.6** | [−48.2, +5.0] | 4 / 12 | −31 · −63 · +28 · +22 · −97 · −55 · −31 · −45 · −42 · −2 · +30 · +26 |
| Firaks (same code) | — | 151.3 | 150.7 | −0.6 | [−17.1, +15.8] | 6 / 12 | +32 · +0 · −20 · +40 · +18 · +3 · −22 · −7 · −49 · −24 · +22 · −0 |
| **All (seat mean)** | | | | **−2.2** | [−12.8, +8.5] | | 12 pairs |

- **Nevlas +14.0, CI just above 0, 9 of 12 pairs positive**; 093's six seeds give +19 (5 of 6), the six new
  seeds +9 (4 of 6). Pair by pair 093 is not reproduced (093: −26 · +39 · +10 · +11 · +27 · +6 vs now +20 · +48
  · +1 · +50 · +0 · −5 — timing noise), the sign is. 093 + 095b = **18 pairs, mean ≈ +13, 14 of 18 positive**.
  **Below the pre-registered 25-charge line → not confirmed** by the rule; the same-code Firaks CI (±16 on 12
  pairs) says +14 sits at the edge of drift, so it is a consistent lean, not a result.
- **Ivits −21.6, 8 of 12 negative** (093: −2.0 on the same six seeds, now −33 on them, −11 on the new six; 18 pairs
  ≈ −15, 6 of 18 positive). Under the line, CI covers 0, but the lean is negative on both runs.
- **Lantids −0.4**, ±60 pairs, unreadable; VP at the start of round 4 leans positive again (+5.8 [−1.1, +12.7],
  8.2 → 14.0; 093 +6.7). Nevlas VP −1.1, Ivits −3.2, Firaks −2.6; all −0.3 [−3.0, +2.5] (not the verdict).

Posted watch replay: `pair-004/game-0-A01` seat 2 — Ivits **B** 140 vs Ivits A 237 in the other game (the −97 pair).

## Activation (A → B)

**Research, rounds 1–3** (`research_counts.py --rounds 1-3`, TF / Nav / AI / Gaia / Eco / Sci) — **all three
entries fired as written**, in round 1:

| Faction | A 1–3R | B 1–3R | A round 1 | B round 1 |
|---|---|---|---|---|
| Nevlas | 2 / 8 / 21 / 1 / **36** / **0** | 4 / 11 / 20 / 0 / **19** / **23** | 0 / 3 / 2 / 0 / 21 / 0 | 1 / 1 / 1 / 0 / 8 / **20** |
| Lantids | 2 / **23** / 15 / 1 / **1** / 2 | 3 / **1** / 15 / 2 / **21** / 4 | 1 / 9 / 2 / 0 / 0 / 1 | 2 / 0 / 0 / 0 / **12** / 3 |
| Ivits | 1 / 1 / 11 / 2 / **23** / 2 | 5 / 6 / 4 / 1 / **1** / **19** | 0 / 1 / 0 / 0 / 12 / 0 | 0 / 3 / 0 / 0 / 1 / **8** |
| Firaks (same code) | 3 / 6 / 9 / 0 / 36 / 3 | 4 / 6 / 5 / 0 / 35 / 0 | 0 / 1 / 0 / 0 / 13 / 1 | 1 / 0 / 0 / 0 / 13 / 0 |

Nevlas trades half its Economy for Science 23 (≈ 2 steps a seat by round 3); Lantids drops Navigation to 1 and
plays Economy 21; **Ivits drops Economy from 23 to 1 for three rounds** — the entry `((1, 'science', 2),)` replaces
the B-blog `((1, 'economy', 2),)` instead of preceding it, so once Science 2 is reached nothing steers and the
value-driven picks (TF 5, Nav 6, AI 4) never return to Economy: "science first" became "no economy".

**Round-1 BGG plans** (`plan_labels.py --prefix BGG-R1-`, A / B): Nevlas 73 / 81 picks, same shape (1RL+2M 45 /
42, 1RL+1TS+1M 11 / 23, 1RL+1TS+2M 10 / 9, 1PI+1RL+1M 7 / 4); Ivits 71 / 78, same shape (1PI+1RL+1M 17 / 23,
1PI+2M 16 / 20, 1PI+3M 7 / 10); Firaks 56 / 41 (1RL+2M 26 / 18, 1PI+1TS 24 / 18). **Lantids differs**: A 1PI+2M
×33 · 1RL+3M 14 · 1RL+4M 8 · 1RL+2M 6 · 1PI+3M 2 → B **1RL+2M 21 · 1RL+3M 17 · 1RL+4M 14** · 1PI+2M 6 · 1RL+1TS+2M 5
— institute openings 35 → 6.

**Upgrades, rounds 1–3** (`upgrade_counts.py --rounds 1-3`, TS / RL / PI / AC): Nevlas 21 / 20 / 0 / 11 → 19 / 16 /
0 / 12; Ivits 14 / 12 / 0 / 4 → 12 / 11 / 0 / 5; **Lantids 15 / 10 / 6 / 4 → 19 / 18 / 1 / 8** (institutes 6 → 1,
labs 10 → 18, academies 4 → 8); Firaks 24 / 29 / 7 / 3 → 26 / 26 / 9 / 2.

## Reading (HANDOFF 1 order)

- **Nevlas N1 (round-1 Science 3): ② fired; +14.0 [+0.2, +27.9], 9 of 12; 18 pairs over two runs ≈ +13, 14 of 18
  positive.** Below the 25 line → **not adopted by the rule**; it is the only consistent positive lean among the
  source parts so far, and the only one whose CI excludes 0. The sources (PG10-S18·S19) claim the gain in rounds
  4–6 (Science → knowledge → institute/academy economy), which a 4R run does not see (⑤) — the pre-registered
  follow-up is the 6R re-measure of the positive faction.
- **Ivits I1 (Science 2 first): ② fired; −21.6 [−48.2, +5.0], 8 of 12 negative; ③ scope.** The entry does not
  put Science before Economy, it removes Economy (23 → 1 in 1–3R). On the 1–3R charge metric an Economy step is
  direct income while a Science step is knowledge, so the drop is partly the metric (⑤) — but the implemented
  order is not what the source says either. Not adopted; fix the scope first (`((1, 'science', 2), (1, 'economy',
  2))` — science, then the B-blog economy step; order only, no values), then re-measure.
- **Lantids L1 (Economy 2 first): ② fired (Nav 23 → 1, Eco 1 → 21); charges flat (−0.4, ±60); ④ side effect on
  the opening.** With Economy first the round-1 catalog moves off the institute (PI+2M 33 → 6; institutes 6 → 1,
  labs 10 → 18, academies 4 → 8 by round 3). The source's own Lantids opening is the institute (093's opening list
  PI+3M … PI+6M), so L1 as implemented contradicts the source's opening; **093's reading that the opening list
  lowered round-1 institutes (4 → 2) is revised — the track order alone does it.** VP leans positive on both
  runs (+5.8, +6.7) while charges are flat: the lab-heavy line scores earlier but does not out-earn. Nothing to
  adopt; if L1 stays, it should start after the round-1 opening (from round 2 or once a big building stands —
  range only), and the Lantids read then needs a playable institute opening.
- **Firaks (same code): −0.6 [−17.1, +15.8], pairs ±50** — the drift scale for 12 pairs is a ±16 CI; single
  pairs of ±50 mean nothing.
- The run's "all −2.2 [−12.8, +8.5]" and VP −0.3 are flat; the parts cost no time.

Nothing changed in code or deployment. Side result (095a, `098a-src-cap60-opening-smoke`, 3 pairs stop at round
2, cap60 + 2 comparison processes): the opening lists **still do not fire at 60 s** — B-arm round-1 BGG picks Ambas
0, Bescods 0, Nevlas 0, Lantids 0, Gleens 1 (A arm 6 · 5 · 6 · 3 · 13); decisions max 73.7 / 81.3 s. The
big-mine / two-building forecasts are not a time-cap problem; the lists need the coach path (fixed-opening
enforcement) or deletion — user decision (E59 (ㄴ) answered).

## Proposal (user decision, nothing queued)

- (ㄱ) **Nevlas 6R re-measure (the pre-registered ⑤ follow-up).** A factory that carries track_steps_src for
  Nevlas only (`source_tracks` restricted to a faction set — flag only, no new values; Lantids and Ivits off so
  their side effects do not move the other seats) vs guide, quartet a, the same 12 seeds, 6 rounds (≈ 6–7 h;
  six seeds ≈ 3.5 h). Verdict stays 1–3R charges (now 30 pairs with 093); pre-registered side metrics: final VP,
  charges in rounds 4–6, research_counts 1–6, academies/institutes. Adopting N1 now on 18 pairs (+13) is below
  the line — the bot does not recommend it.
- (ㄴ) **Ivits: scope fix then explain, lab 0 first.** `explain_ab_decisions.py` on the posted replay
  (`pair-004/game-0-A01` seat 2, B 140 vs A 237) to see where the charges went after Science 2, then change the
  entry to science-then-economy; re-measure only with (ㄱ) or later.
- (ㄷ) **Lantids: L1 range** — start the Economy step after the round-1 opening (round 2 or first big building).
  No re-measure until the institute opening is playable (095a: cap60 does not help → coach path or drop the
  lists; user decision).
- (ㄹ) 094 (src vs res) stays on hold; science_when for Nevlas / Ivits only makes sense after (ㄱ)/(ㄴ).

Bot recommendation: (ㄴ) explain now as a bot turn, (ㄱ) as the next lab slot after 096 / 098, (ㄷ) with (ㄱ)'s
factory change if the user keeps L1.
