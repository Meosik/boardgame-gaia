# Cycle 087 — live hard vs ships_byfaction on quartet c (Ambas · HadschHallas · Terrans · Xenos), 4 rounds

Third and last of the unmeasured-faction quartets (user, 2026-10-19 "종족별 규칙 넣고 실험 시작", 5a E16).
A = `teacher-a-search4-h1-geodens-cap20.json` — the live-server hard teacher (geodens_guide, 4 comparisons, 20 s).
B = `...-ships-byfaction-cap20.json` — the base stack (guide_r1 + charge3 + lf_more + vm + lf_ts + ships) with the
faction tables on. Faction parts on B: Ambas **track_set** TF · Eco · Sci, HadschHallas **track_set** Eco · Nav · Sci
(third sample after 063 +49.3 and 081 −21.1), Terrans **track_income** (084), Xenos none (= the `ships` stack).
Six new seeds (`seeds-quartet-c.txt` lines 2–7: 1433 4489 5963 9166 9171 11075; 083 used 60), seat-swapped pairs, hard
budget on both arms, stop at the start of round 4 (063 format), agentmaco, commit e4d6d9e, 18:36 → 19:27 (51 min).
Result: lab/results/087-quartet-c-hard-vs-byfaction.md.
Pre-registered verdict: charges gained in rounds 1–3 (1 VP = 1.5 charges) **per faction**; Ambas and HadschHallas are
the main targets; a negative faction goes to replay and its `faction-tracks-openings.md` rules become faction-table
candidates. Read alongside: errors / timeouts / unsearched per faction, rounds 1–3 research per track
(`research_counts.py`), decision time.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 855 (A) vs 928 (B); A mean 1.63 s, median 0.33 s, max 18.5 s; B mean 10.97 s, median 14.17 s,
p90 20.2 s, max 32.0 s (inside the 60 s guard). Unsearched decisions 571 / 855 (67%) vs 663 / 928 (71%).

## Charges in rounds 1–3 (the verdict)

| Faction | Faction part on B | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005) |
|---|---|---:|---:|---:|---|---:|---|
| **Ambas** | track_set TF · Eco · Sci | 83.0 | 166.0 | **+83.0** | **[+34.5, +131.5]** | **6 / 6** | +93 · **+161** · +38 · +62 · +43 · +102 |
| HadschHallas | track_set Eco · Nav · Sci | 116.5 | 152.1 | +35.6 | [−12.3, +83.5] | 4 / 6 | +53 · +8 · −6 · −12 · +101 · +69 |
| Terrans | track_income | 127.0 | 158.3 | +31.2 | [−7.2, +69.7] | 5 / 6 | +11 · +34 · +17 · +50 · +91 · −15 |
| Xenos | none (`ships`) | 124.6 | 140.7 | +16.1 | [−41.8, +73.9] | 4 / 6 | +21 · −62 · +3 · −14 · +49 · +99 |
| **All (seat mean)** | | | | **+41.5** | **[+17.3, +65.7]** | **6 / 6** | +44 · +35 · +13 · +21 · +71 · +64 |

No faction is negative. 19 of 24 faction-pairs positive; the five negatives (−6, −12, −15, −14, −62) are inside the
±50 one-pair timing drift that 083 measured, except Xenos p001 −62 (A 160 vs B 98), on the faction whose code is the
plain `ships` stack. The posted watch replay is `pair-001/game-0-A23` seat 3 — Ambas A 58 against Ambas B 219 in the
other game of the pair (+161, the largest swing of the run).

Size: +41.5 is the smallest of the three unmeasured quartets (085 +53.0, 086 +63.8) but in the usual band of
hard-vs-stack runs (052 +50.5, 063 +52.2, 082 +43.8; 081 +30.6 on the live lineup). Only Ambas clears 0 on its own CI.
**Ambas' gain is mostly a weak A**: live hard Ambas earns 83 charges, below every A faction mean of 086 (94–128), with
three A seats at 57–71.

**HadschHallas, third sample.** 063 +49.3, 081 −21.1 (significant), 087 +35.6 (4 / 6). Two of three positive, simple
mean of the three ≈ +21; the arms are not identical across the three (063 / 081 B = `ships`, 087 B = `ships` +
track_set), so this is the stack's sign on HadschHallas, not track_set's.

**Terrans.** +31.2 here is the stack plus track_income against **live hard**; 084's +31.3 was track_income against
`ships`. Same number, different comparison, so they are not pooled as "12 pairs of track_income"; 087 only says the
Terrans with track_income still beat live hard on charges (5 / 6).

**Xenos** run the plain stack: +16.1 with a wide CI (4 / 6, p005 +99 and p001 −62), consistent with hard 052 / 063 / 081
positive; 082's −57 was normal level.

**4R-start VP (read alongside, not the verdict).**

| Faction | A mean | B mean | B−A | 95% CI |
|---|---:|---:|---:|---|
| Ambas | 14.2 | 14.5 | +0.3 | [−5.8, +6.5] |
| HadschHallas | 16.8 | 8.7 | −8.2 | [−17.6, +1.3] |
| **Terrans** | 24.0 | 9.8 | **−14.2** | **[−25.4, −3.0]** |
| Xenos | 14.2 | 13.8 | −0.3 | [−12.9, +12.2] |
| All (seat mean) | | | −5.6 | [−10.7, −0.4] |

Run total −5.6, the smallest 4R gap of the three quartets (085 −13.0, 086 −7.4). **Terrans −14.2 is the only faction
CI below 0**, with all six B seats at 0–13 VP against A at 15–34. This is the track_income shape: on 084 Terrans B went
Eco 5 → 12 and banked VP later (final VP +20.3 on 6R, 3 cycles 18 pairs 15 positive on VP); live hard Terrans here
play Gaia 12 in rounds 1–3 and score Gaia VP early. A 6R run would be needed to say the same holds against live hard.

## What the faction parts did — rounds 1–3 research per track (`research_counts.py`, six seat-games per arm)

| Faction | Guide / part | A (live hard) | B (byfaction) | Reading |
|---|---|---|---|---|
| Ambas | TF · Eco · Sci | Sci 5 · Gaia 4 · Eco 3 · TF 1 · AI 1 (14) | **TF 9** · Eco 5 · AI 4 · Nav 3 · Sci 3 · Gaia 2 (26) | TF 1 → 9 is the rule; 17 / 26 on guide tracks. R1: A Sci 3 · Eco 2 · Gaia 1, B Eco 4 · Sci 2 · TF 1 |
| HadschHallas | Eco · Nav · Sci | Eco 12 · Nav 5 · TF 3 · AI 2 · Sci 1 (23) | **Nav 17** · Eco 10 · TF 4 (31) | Nav 5 → 17, 27 / 31 on guide; Sci 0 (third priority) |
| Terrans | track_income | **Gaia 12** · Eco 3 · Sci 2 · TF 2 (19) | **Eco 12 · AI 10** · Gaia 2 · TF / Nav / Sci 1 (27) | Eco 3 → 12 as on 084 (5 → 12); Gaia 12 → 2; **AI 0 → 10 is new** (084 did not show it). R1: A Gaia 7, B Eco 11 |
| Xenos | none | Eco 12 · Nav 7 · TF / AI 2 (23) | **Nav 12 · TF 6** · Eco 3 · AI 3 (24) | the `ships` stack's own Nav / TF shift (same as on the geo quartet) |

Research volume 79 → 108 steps. The footprint is **clear on both main targets** (Ambas TF, HadschHallas Nav) — like
quartet b, unlike quartet a. Decisions per faction A → B: Ambas 164 → 199, HadschHallas 242 → 247, Terrans 203 → 218,
Xenos 246 → 264.

## Reading

- **Verdict rule: no negative faction.** All four positive on charges, run total +41.5 [+17.3, +65.7] with every pair
  positive. The "negative faction → replay → faction-table candidate" branch does not trigger for quartet c, as for a
  and b. No candidate rule from `faction-tracks-openings.md` is promoted.
- **The E16 series is complete.** 085–087 measured the stack (with track_set) against the live hard teacher on all
  ten unmeasured base-game factions plus Terrans and Xenos again: 12 of 12 faction means positive on charges, 7
  of 12 with CI above 0, all three run totals significant with every pair positive (18 / 18 pairs). Lost Fleet
  factions are still out (no track table).
- **What it is not.** As in 085 / 086 this is the whole stack against live hard, not a measurement of track_set. The
  4R VP gap is negative in all three quartets (−13.0, −7.4, −5.6); only geo and live quartets have a 6R check
  (060 / 081 flat).
- **D1 bearing.** For Ambas and HadschHallas the D1 deployment teacher (`ships`) is B minus track_set; for Terrans it
  is B minus track_income; for Xenos it is B. Safe on all four (no errors, no timeouts, max 32.0 s), charges up.

No code was changed and nothing was deployed. The queue is empty after 087.

## Proposal (user decision, nothing queued)

- (ㄱ) **Lab time 0, now**: `explain_ab_decisions.py` on the 087 folders — one Ambas A seat at 57–58 charges
  (`pair-001/game-0-A23` seat 3 or `pair-003/game-0-A13` seat 1) to see why live hard Ambas is so low (setup, PI swap,
  or no early mines), and one Terrans B seat for the round 1–3 AI research (084 had none).
- (ㄴ) **Measure the faction parts themselves on quartet c: ships vs ships_byfaction**, next six seeds from
  `seeds-quartet-c.txt` (11429 14468 21485 21807 24649 25940), hard budget both arms. A and B differ by track_set on
  Ambas / HadschHallas and by track_income on Terrans; **Xenos runs the same code on both arms, a built-in drift
  yardstick** (the 084 design), and Terrans becomes the second track_income vs `ships` sample (12 pairs with 084,
  the E18 question). 6R ≈ 2.5 h so final VP is read too (Terrans' 4R −14.2), or 4R ≈ 45 min.
- (ㄷ) **The same on quartet b** (E20 ㄷ, seeds 16679 19271 20210 20853 21625 21684, 4R ≈ 45 min) — clear footprint on
  three factions, but no same-code faction for drift.
- (ㄹ) 6R check of the 4R VP gap for the new factions (lower priority; folded into (ㄴ) if run to 6R).

Bot recommendation: (ㄱ) now; (ㄴ) at 6R as the next lab slot, because it is the only quartet with both a clear
footprint and a drift yardstick, and it answers E18 for Terrans at the same time; (ㄷ) after it.
