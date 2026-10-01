# Geodens — B14 read in full, mapped to the teacher scope

Source: uiqoo, "어잌후의 가이아 프로젝트 분석/공략 (14) - 기오덴" (2020-05-29, 9 saved pages),
read in full on 2026-10-01 from the user's upload; cross-checked with B19 (2023-09-04, Geodens
section), LF03/LF04 and SH04. Only paraphrased claims are kept here, not the article text.

Scope rule (agreed 2026-10-01): **facts** are computed exactly; **within-horizon outcomes**
are left to search; **judgments** (values, priorities, prohibitions) are not hand-coded as
coefficients or bans — a guide may only *order proposals* that search then verifies.

| # | Claim (source) | Kind | Teacher use |
|---|---|---|---|
| 1 | PI: +3 knowledge per new planet type; realistic total ≈18 (6 types; an opponent's home colour is the hardest, not the 3-step colours) (B14 §1) | fact (engine) / judgment (≈18) | engine already applies it; future-value left to learning |
| 2 | A new type taken **before** the PI forfeits its 3 knowledge for good, and the next 3 must come from a costlier colour (B14 §1) | fact | visible to search only if both routes reach the PI payoff → Geodens look-ahead = 2 incomes |
| 3 | Plan knowledge so that this round's new types ×3 + stock is a multiple of 4 (B14 §1) | judgment | none |
| 4 | Keep 1–2 labs or one academy; spend the rest on mines — expansion supplies knowledge (B14 §1) | judgment | none |
| 5 | R1 economy or science; T3 and N2 exactly when terraforming starts; stop eco/sci early if knowledge is short; then N3 + AI for QIC actions (B14 §2, §3; B19 "테3항2") | judgment → order | after the PI, propose Terraforming-3 and Navigation-2 first |
| 6 | Keep ≥1 step ahead on terraforming and form a federation by R4 to defend terraforming 5 (B14 §2, §3.1; B19 "테꼭 수비") | judgment | none (generic terraforming goals remain) |
| 7 | T3/N2 deadlock: with a QIC raise terraforming first, with spare ore navigation first; 2-step power action before 1-step targets can save ore (B14 §2) | judgment | none; both are legal candidates |
| 8 | Exactly one Gaia planet, using the navigation-1 QIC (B14 §2, §3.2) | judgment | none |
| 9 | From R4, a QIC action every round; R5–6 the 2-QIC action scores most (B14 §2, §3.3; B19 "정큐액션 3번") | judgment → order | from round 4, propose the next AI level |
| 10 | Power actions: 1-/2-terraform (before T3), then 2 ore or 7 credits, then 2 knowledge; federation tokens: ore/credits (B14 §2) | judgment | none; candidates already ranked by the evaluator |
| 11 | Gaia track: avoid; if knowledge overflows, take two steps at once in R5 (B14 §2, §3.4) | judgment | none |
| 12 | Boosters: QIC or range > terraform; without the terraform booster burn 3 power for the shared 1-terraform action (B14 §2; LF04) | judgment | none |
| 13 | Tech: 4-charge early; knowledge-per-planet-type late (≈7 knowledge in R6) (B14 §2) | judgment | none |
| 14 | Openings: AC+M+M with a home planet at range 3; PI+TS+M+M without home planets; RL+TS+M+M with two (B14 §4; B19 "의광광 / 아광 / 연교광광") | judgment | already in the BGG R1 catalog (1AC+2M, 1PI+1TS+2M, 1RL+1TS+2M) |
| 15 | Ships: TF Mars (3 credits → 1 terraform), Eclipse (2 QIC per planet type) suit Geodens (LF03, d78da53f) | judgment | none; ship goals exist generically |

Implemented in `tools/teacher_patches.py` `geodens_guide` (opt-in): rows 2, 5, 9, plus
new-type colony proposals cheapest first (terraform steps + QIC). Everything else stays a
candidate the search and, later, the learned value decide on.
