# Cycle 086 — live hard vs ships_byfaction on quartet b (BalTaks · Bescods · Gleens · Itars), 4 rounds

Second of the three unmeasured-faction quartets (user, 2026-10-19 "종족별 규칙 넣고 실험 시작", 5a E16).
A = `teacher-a-search4-h1-geodens-cap20.json` — the live-server hard teacher (geodens_guide, 4 comparisons, 20 s).
B = `...-ships-byfaction-cap20.json` — the base stack (guide_r1 + charge3 + lf_more + vm + lf_ts + ships) with the
faction tables on; for these four factions the only faction part is **track_set** (guide track priority, order only):
BalTaks Gaia · Eco · TF · AI, Bescods Sci · Eco · Nav, Gleens Nav · Gaia, Itars Gaia · Eco · TF.
Six new seeds (`seeds-quartet-b.txt` lines 2–7: 5744 6886 7905 10311 10743 12087; 083 used 5187), seat-swapped
pairs, hard budget on both arms, stop at the start of round 4 (063 format), agentmaco, commit 1f8dafe,
17:54 → 18:36 (42 min). Result: lab/results/086-quartet-b-hard-vs-byfaction.md.
Pre-registered verdict: charges gained in rounds 1–3 (1 VP = 1.5 charges) **per faction**; a negative faction goes to
replay to find the cause and its `faction-tracks-openings.md` rules (BalTaks Gaia 4 in R1, Gleens two tracks only, …)
become candidates for the faction table. Read alongside: errors / timeouts / unsearched per faction, rounds 1–3
research per track (`research_counts.py`), decision time, and the 083 question whether Itars' 51–52 charges were a
defect.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits on any of the four factions. Decisions 581 (A) vs 799 (B); A mean 1.08 s, median 0.45 s, max 7.4 s;
B mean 11.22 s, median 13.16 s, p90 20.20 s, **max 38.9 s** — the highest B maximum of the byfaction series (083
23.5 s, 085 23.2 s, 084 30.3 s on 6R), still inside the hard guard of 60 s. Unsearched decisions 414 / 581 (71%)
vs 614 / 799 (77%).

## Charges in rounds 1–3 (the verdict)

| Faction | track_set on B | A | B | B−A | 95% CI | Pairs B > A | Per pair (p000 … p005) |
|---|---|---:|---:|---:|---|---:|---|
| **BalTaks** | Gaia · Eco · TF · AI | 94.5 | 148.7 | **+54.2** | **[+24.0, +84.3]** | **6 / 6** | +16 · +45 · +54 · +47 · +104 · +58 |
| **Bescods** | Sci · Eco · Nav | 128.0 | 207.1 | **+79.0** | **[+51.9, +106.2]** | **6 / 6** | +74 · +72 · +42 · **+110** · +107 · +69 |
| **Gleens** | Nav · Gaia | 100.0 | 169.9 | **+69.9** | **[+28.9, +110.9]** | 5 / 6 | +79 · +100 · +73 · +87 · +87 · −7 |
| **Itars** | Gaia · Eco · TF | 127.9 | 179.9 | **+52.0** | **[+25.3, +78.7]** | **6 / 6** | +33 · +69 · +54 · +35 · +93 · +27 |
| **All (seat mean)** | | | | **+63.8** | **[+41.6, +86.0]** | **6 / 6** | +51 · +72 · +56 · +70 · +98 · +37 |

**All four factions clear 0 on their own CI** — the first quartet where that happens (085: two of four). 23 of 24
faction-pairs positive; the one negative (Gleens p005 −7) is well inside the ±50 one-pair timing drift that 083
measured with the same teacher on both arms. The posted watch replay is `pair-003/game-1-A02` seat 0 — Bescods A 117
against Bescods B 227 in the other game of the pair (+110, the largest Bescods swing).

Size: +63.8 is the largest hard-vs-stack number so far (052 +50.5, 063 +52.2, 082 +43.8, 085 +53.0; 081 +30.6 on the
live lineup). Bescods at B 207 and Itars at B 180 are the two highest B faction means of any quartet (085 best:
Ivits 178).

**Itars are not a defect.** 083 had Itars at 51–52 charges on its one quartet-b seed and left "faction or defect" to
this run; on six seeds Itars earn 128 (A) and 180 (B), mid-to-high for the run. The 083 number was that seed, so the
replay question is closed without a replay.

**4R-start VP (read alongside, not the verdict).**

| Faction | A mean | B mean | B−A | 95% CI | Pairs B > A | Per pair |
|---|---:|---:|---:|---|---:|---|
| BalTaks | 17.5 | 10.7 | −6.8 | [−15.9, +2.2] | 1 / 6 | +10 · −7 · −10 · −8 · −14 · −12 |
| Bescods | 22.2 | 15.3 | −6.8 | [−17.3, +3.6] | 1 / 6 | −21 · +6 · −5 · −4 · −1 · −16 |
| Gleens | 21.2 | 16.3 | −4.8 | [−16.4, +6.8] | 1 / 6 | −24 · −4 · −3 · −1 · +10 · −7 |
| Itars | 21.7 | 10.7 | −11.0 | [−25.4, +3.4] | 2 / 6 | +11 · −19 · −19 · −23 · −17 · +1 |
| All (seat mean) | 20.6 | 13.3 | −7.4 | [−9.2, −5.6] | 0 / 6 | |

The stack's usual "hold charge, bank VP later" shape, and this time the same size as before (052 −6.8, 063 −8.6, 082
−7.7) rather than 085's −13.0; no faction's CI is below 0 on its own. On the geo and live quartets the gap closed by
the end of round 6 (060 / 081 final VP flat); for these four factions there is no 6R measurement.

## What track_set did — rounds 1–3 research per track (`research_counts.py`, six seat-games per arm)

| Faction | Guide tracks | A (live hard) | B (byfaction) | On-guide share of B | Reading |
|---|---|---|---|---:|---|
| BalTaks | Gaia · Eco · TF · AI | Eco 5 · Sci 6 · TF 2 (13) | **Gaia 9 · AI 8** · TF 4 · Eco 4 · Sci 2 (27) | 25 / 27 | Gaia 0 → 9 and Sci 6 → 2 are the rule; but the guide's "Gaia 4 in R1" is not reached — B plays **Gaia 1 in R1 on five of six seats** (A: Gaia 0); AI 8 is the fourth priority ("up to 4") |
| Bescods | Sci · Eco · Nav | Eco 4 (4) | **Nav 10** · Eco 4 · AI 4 · Sci 1 (19) | 15 / 19 | Nav (third, guide "R3 to 2") carries the increase; **Sci (first, "R1 2–3") 1** — same as 083's Sci 0 (the free lowest-track step is a different move type and is not counted here); AI 4 off-guide |
| Gleens | Nav · Gaia | Eco 6 · Sci 4 · TF 2 (12) | **Gaia 15 · Nav 4** · TF 1 · Eco 1 (21) | 19 / 21 | The two-track shape the guide asks for; A plays none of the guide tracks at all. Order inside the guide differs: B opens **Gaia 2 in R1 on four seats**, Nav 1 on one (guide: Nav 2 first) |
| Itars | Gaia · Eco · TF | Gaia 5 · Eco 5 · Sci 6 (16) | **Gaia 15 · TF 5** · Eco 4 · AI 2 · Nav 1 · Sci 1 (28) | 24 / 28 | Gaia 5 → 15, TF 0 → 5, Sci 6 → 1 — the rule as written |

Research volume 45 → 95 steps over the six seat-games per arm. Round 1 only: A opens Economy (plus Science on three
factions) everywhere — geodens_guide's generic first step; B opens Gaia on BalTaks (5), Gleens (10) and Itars (6),
Economy on Bescods (4).

So on quartet b the footprint of track_set is **clear on three factions** (Gleens, Itars, BalTaks — 25 / 27, 19 / 21
and 24 / 28 of B's research on guide tracks) and **partial on Bescods** (Nav yes, Sci no). This is the opposite of
quartet a, where two of four factions (Lantids, Ivits) showed no footprint and played AI 14 / 20. Two details are
below the guide: BalTaks' Gaia 4 in round 1 (B gets to 1) and Bescods' Science first (B gets to 1 in three rounds) —
track_set is order only, so neither is the rule failing, but both are places where the guide says a *step count*
matters and the rule cannot express it.

Charge levels of B: Bescods 207 (083: 256–263 on one seed), Itars 180 (083: 51–52), Gleens 170 (083: 242), BalTaks
149 (083: 147–153). B takes more decisions than A on every faction (BalTaks 135 → 186, Bescods 151 → 220, Gleens
139 → 200, Itars 156 → 193).

## Reading

- **Verdict rule: no negative faction.** All four positive, all four CIs above 0, 23 of 24 pairs, run total +63.8
  [+41.6, +86.0] with every pair positive. The "negative faction → replay → faction-table candidate" branch does not
  trigger for quartet b, as it did not for quartet a. No candidate rule from `faction-tracks-openings.md` is promoted.
- **What the +63.8 is.** As in 085: A is the live hard teacher and B is the whole stack plus track_set, so this is
  the stack's hard-vs-stack gain extended to four more factions — faction-level measurements against the live teacher
  now 16 → 20, all positive on charges. It is **not** a measurement of track_set; that needs ships vs ships_byfaction
  on these seeds (084 design).
- **track_set is visible here.** Unlike quartet a, the research footprint matches the guide on three of four factions
  and partly on the fourth. That makes quartet b the better place to measure track_set on its own: if the rule has an
  effect anywhere, it should show on factions where it demonstrably steers research.
- **D1 bearing.** For these four factions the D1 deployment teacher (`ships`) is B minus track_set; this run says the
  stack is safe on them (no errors, no timeouts, max 38.9 s under the 60 s guard, charges up on all four), with the
  081 caveat that charges at the start of round 4 are not final VP (−7.4 here, the usual size).

No code was changed and nothing was deployed. 087 (quartet c: Ambas · HadschHallas · Terrans · Xenos) started from
the queue at 18:36 (pairs 0–1 running at the time of writing); 086 changes nothing in it.

## Proposal (user decision, nothing queued)

- (ㄱ) **Lab time 0, now**: `explain_ab_decisions.py` on the 086 folders for the two below-guide spots — one Bescods
  B seat (e.g. `pair-003/game-0-A13` seat 0, charges 227) for why Science (first priority) is not researched in rounds
  1–2, and one BalTaks B seat for why Gaia stops at 1 in round 1 — classified as "guide track unavailable /
  unaffordable", "situational rule chose it" or "track_set did not fire". Pairs with 085's E19 (ㄱ) on Lantids /
  Ivits; together they say whether the no-footprint cases are the rule or the situation.
- (ㄴ) **Keep the queue**: 087 runs to the end, read the same way.
- (ㄷ) **Measure track_set itself: ships vs ships_byfaction on quartet b**, next six seeds from `seeds-quartet-b.txt`
  (16679 19271 20210 20853 21625 21684), hard budget both arms, 4R stop (≈ 45 min; 6R ≈ 2.5 h). A and B then differ
  only by track_set on these four factions. **Quartet b before quartet a**: the footprint is clear here, so a null
  result would mean "the rule steers research but does not help", while on quartet a a null result could just mean
  the rule did not fire.
- (ㄹ) **6R check of the VP gap** (lower priority): −7.4 is the usual size, so this is less pressing than 085's −13.

Bot recommendation: (ㄱ) now, (ㄴ) as is, (ㄷ) as the first slot after 087 (quartet b first, quartet a after if b is
positive); (ㄹ) only if the user wants the deployment question settled on final VP for these factions.
