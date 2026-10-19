# Cycle 085 — live hard vs ships_byfaction on quartet a (Lantids · Ivits · Firaks · Nevlas), 4 rounds

First of the three unmeasured-faction quartets (user, 2026-10-19 "종족별 규칙 넣고 실험 시작", 5a E16).
A = `teacher-a-search4-h1-geodens-cap20.json` — the live-server hard teacher (geodens_guide, 4 comparisons, 20 s).
B = `...-ships-byfaction-cap20.json` — the base stack (guide_r1 + charge3 + lf_more + vm + lf_ts + ships) with the
faction tables on; for these four factions the only faction part is **track_set** (guide track priority, order only):
Lantids Nav · Sci · AI, Ivits Eco · Sci · AI, Firaks Eco · Nav · Gaia, Nevlas Eco · Sci · Nav.
Six new seeds (`find_seeds.py 0 60000 --prefix quartet-a --factions …`: 2470 5565 6481 9831 13449 14043), seat-swapped
pairs, hard budget on both arms, stop at the start of round 4 (063 format), agentmaco, commit 37ff55e,
17:10 → 17:54 (44 min). Result: lab/results/085-quartet-a-hard-vs-byfaction.md.
Pre-registered verdict: charges gained in rounds 1–3 (1 VP = 1.5 charges) **per faction**; a negative faction goes to
replay to find the cause and its `faction-tracks-openings.md` rules become candidates for the faction table.
Read alongside: errors / timeouts / unsearched per faction, rounds 1–3 research per track (`research_counts.py` — did
track_set actually steer research), decision time.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits on any of the four factions. Decisions 662 (A) vs 768 (B); A mean 1.36 s, median 0.37 s, max 15.8 s;
B mean 11.36 s, median 15.51 s, p90 20.32 s, **max 23.2 s** (hard guard 60 s, same as 083's 23.5 s). Unsearched
decisions 442 / 662 (67%) vs 554 / 768 (72%).

## Charges in rounds 1–3 (the verdict)

| Faction | track_set on B | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005) |
|---|---|---:|---:|---:|---|---:|---|
| **Firaks** | Eco · Nav · Gaia | 84.6 | 145.7 | **+61.1** | **[+9.4, +112.7]** | 5 / 6 | +52 · −6 · +68 · +72 · +144 · +37 |
| **Ivits** | Eco · Sci · AI | 123.0 | 178.4 | **+55.4** | **[+11.5, +99.3]** | **6 / 6** | +109 · +57 · +12 · +99 · +13 · +42 |
| Lantids | Nav · Sci · AI | 105.4 | 164.3 | +58.9 | [−22.0, +139.9] | 5 / 6 | +43 · −32 · +28 · **+201** · +46 · +68 |
| Nevlas | Eco · Sci · Nav | 107.2 | 143.9 | +36.7 | [−16.9, +90.3] | 5 / 6 | +58 · +2 · +93 · +15 · −35 · +87 |
| **All (seat mean)** | | | | **+53.0** | **[+21.6, +84.5]** | **6 / 6** | +66 · +6 · +50 · +97 · +42 · +59 |

21 of 24 faction-pairs positive; the three negatives (Firaks −6, Lantids −32, Nevlas −35) are inside the ±50 one-pair
timing drift that 083 measured with the same teacher on both arms. The posted watch replay is `pair-003/game-0-A13`
seat 1 — Lantids A 109 against Lantids B 309 in the other game of the pair (+201, the largest swing of the run and the
reason the Lantids CI is wide).

Size: +53 is the same number as the hard-vs-stack runs on the other quartets (052 +50.5, 063 +52.2, 082 +43.8 on
normal; 081 +30.6 on the live lineup).

**4R-start VP (read alongside, not the verdict).**

| Faction | A mean | B mean | B−A | 95% CI | Pairs B > A | Per pair |
|---|---:|---:|---:|---|---:|---|
| Firaks | 19.8 | 7.2 | −12.7 | [−22.6, −2.7] | 1 / 6 | −12 · −10 · −17 · −17 · −24 · +4 |
| Ivits | 26.8 | 13.5 | −13.3 | [−23.3, −3.3] | 0 / 6 | −13 · −15 · −4 · −28 · −18 · −2 |
| Lantids | 22.3 | 12.5 | −9.8 | [−21.0, +1.4] | 1 / 6 | −2 · −16 · −12 · +7 · −23 · −13 |
| Nevlas | 24.2 | 8.0 | −16.2 | [−24.1, −8.2] | 0 / 6 | −12 · −17 · −29 · −13 · −7 · −19 |
| All (seat mean) | 23.3 | 10.3 | −13.0 | [−17.0, −9.0] | 0 / 6 | |

The stack's usual "hold charge, bank VP later" shape (052 −6.8, 063 −8.6, 082 −7.7 at the start of round 4; 083 had
2–18 VP on every seat of all twelve factions), but **larger here** — all four factions negative, three of them with the
CI below 0, and B seats at 1–8 VP in nine of 24 seat-games. On the geo and live quartets the gap closed by the end of
round 6 (060 / 081 final VP flat); for these four factions there is no 6R measurement yet.

## What track_set did — rounds 1–3 research per track (`research_counts.py`, six seat-games per arm)

| Faction | Guide tracks | A (live hard) | B (byfaction) | Reading |
|---|---|---|---|---|
| Firaks | Eco · Nav · Gaia | Eco 7 · Sci 6 · Gaia 2 (15) | **Gaia 7 · AI 5 · Nav 4** · Eco 1 · Sci 1 (18) | Nav 4 is the guide; Eco (first, "4 steps first") **7 → 1**; Gaia 7 is third priority but guide says "from R3, late forming"; AI 5 off-guide |
| Ivits | Eco · Sci · AI | Eco 6 · Sci 6 · Gaia 3 · TF 1 (16) | **AI 14** · Sci 3 · Eco 2 · Gaia 1 (20) | AI (third priority, guide "from R4") takes 14 of 20; Eco (first, "2 steps in R1") 6 → 2 — 083's "no research" is gone but the order is inverted |
| Lantids | Nav · Sci · AI | Eco 6 · Sci 5 · Gaia 4 · AI 1 (16) | **AI 14** · Sci 2 · Nav 1 · Eco 1 · Gaia 1 · TF 1 (20) | Same as 083 (AI 2–3, Nav/Sci 0) at six times the sample: Nav (first) 1, Sci (second) 2, AI 14 |
| Nevlas | Eco · Sci · Nav | Eco 13 · Gaia 2 · AI 1 · TF 1 (17) | **Eco 14 · Nav 10** · AI 4 · TF 2 (30) | The guide tracks (Eco first, Nav third); Sci (second) 0 on both arms; research volume 17 → 30 |

Round 1 only: A opens Economy on all four factions (Firaks 5 + Sci 4, Ivits 6, Lantids 6, Nevlas 6 — geodens_guide's
generic first step); B opens **AI** on Ivits (4) and Lantids (5), Gaia on Firaks (5), Economy on Nevlas (8).

So the footprint of track_set is visible on one faction (Nevlas, Eco + Nav), partial on one (Firaks Nav, but Economy
lost), and **absent on two** (Lantids and Ivits research AI 14 of 20 each, their first-priority tracks 1–2 steps).
track_set only swaps the score of the best research move with the best guide-track research move when a guide-track
step exists and no situational rule chose the off-guide step; AI 14 on two factions is therefore either a situational
rule (ships / QIC) winning every time or the rule not firing — the same classification question 083 left for
`explain_ab_decisions.py` (5a E17 ㄱ), now with six seat-games per faction to pick from (Lantids B 309 in
`pair-003/game-1-A02` seat 1 is AI-heavy and the highest seat of the run).

Charge levels of B: Ivits 178 (083: 130–142), Lantids 164 (083: 162–214), Firaks 146 (083: 225–261 on one seed),
Nevlas 144 (083: 137). B takes more decisions than A on every faction (Firaks 128 → 177, Lantids 153 → 185, Nevlas
189 → 214, Ivits 192 → 192 — more actions per round, as on the other quartets).

## Reading

- **Verdict rule: no negative faction.** All four are positive on the point estimate, 21 of 24 pairs, run total +53.0
  [+21.6, +84.5] with every pair positive; Firaks and Ivits clear 0 on their own CI, Lantids and Nevlas are 5/6 with
  CIs through 0 (one ±50 drift pair each, 083 yardstick). The "negative faction → replay → faction-table candidate"
  branch does not trigger for quartet a.
- **What the +53 is.** A is the live hard teacher and B is the whole stack plus track_set, so this is the stack's
  known hard-vs-stack gain (052 / 063 / 082: +44 to +52) extended to four more factions — the twelfth, thirteenth,
  fourteenth and fifteenth faction-level measurements against the live teacher, all positive on charges. It is **not**
  a measurement of track_set: that needs ships vs ships_byfaction on these seeds (as 084 did for the measured quartet).
- **track_set itself is unconfirmed on quartet a.** The research footprint matches the guide on Nevlas only; Lantids
  and Ivits play AI 14 / 20 in rounds 1–3 against guide orders that put AI third. The gain exists with that footprint,
  so whatever is choosing AI is not hurting charges in three rounds — but it is not the rule the user asked to
  measure, and the 4R-start VP gap (−13, larger than before) is the thing a 6R run would have to settle.
- **D1 bearing.** For these four factions the D1 deployment teacher (`ships`) is B minus track_set, so this run says
  the stack is safe to deploy on them (no errors, no timeouts, max 23.2 s, charges up on all four), with the same
  caveat as 081: charges at the start of round 4 are not final VP.

No code was changed and nothing was deployed. 086 (quartet b: BalTaks · Bescods · Gleens · Itars) started from the
queue at ≈ 17:55, 087 (quartet c) follows; 085 changes nothing in them.

## Proposal (user decision, nothing queued)

- (ㄱ) **Lab time 0, now**: `explain_ab_decisions.py` on the 085 folders for the AI-heavy B seats — Lantids
  `pair-003/game-1-A02` seat 1 (charges 309, AI research) and one Ivits B seat (e.g. `pair-001/game-0-A23` seat 1,
  223) — to classify each early AI step as "guide track unavailable / unaffordable", "situational rule chose it" or
  "track_set did not fire". This is 083's E17 (ㄱ) with better material; it decides whether track_set on Lantids and
  Ivits is a no-op that should be rewritten or a rule that is being overridden on purpose.
- (ㄴ) **Keep the queue** 086 → 087 as it is; read each quartet the same way (per-faction sign over six pairs, one
  pair ±50 is noise).
- (ㄷ) **Measure track_set itself on quartet a: ships vs ships_byfaction**, same six seeds or the next six from
  `seeds-quartet-a.txt` (18334 19444 21268 21567 21686 21831), hard budget both arms, 4R stop (≈ 45 min; 6R ≈ 2.5 h
  if the 4R-start VP gap should be followed to the end). A and B then differ only by track_set on these four
  factions, which is the measurement E16 set out to make. Slot after 087; the same design applies to quartets b and
  c if their hard-vs-byfaction runs also come out positive.
- (ㄹ) **6R check of the VP gap** (lower priority): hard vs byfaction on quartet a to round 6, new six seeds, to see
  whether −13 at the start of round 4 closes as it did on the geo and live quartets (060 / 081).

Bot recommendation: (ㄱ) now, (ㄴ) as is, (ㄷ) as the first slot after 087; (ㄹ) only if (ㄷ) is positive and the
user wants the deployment question settled on final VP for these factions.
