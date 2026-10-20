# Cycle 090 — ships vs ships_tokens on the measured quartet, 6 rounds (token compare + track race + race prune)

A = `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` (deployment teacher).
B = `...-ships-tokens-cap20.json`: the same stack plus **token_compare** (with a green token, the best legal move that
flips it — a level-5 advance or an upgrade taking an Advanced tile — is compared first as a root goal; the rollout
decides), **track_race** (when a rival is also at level 4 on a track with a green token and can pay the step soon, our
level-5 advance there leads the research moves, and the Advanced tile above that track leads one upgrade's tile
choices) and **race_prune** (a level-5 or Advanced-tile goal on a track already lost — level 5 taken, or a rival at 4
with a token while we are at 3 or below — leaves the compared goals). All factions. Queued by the user on 2026-10-20
("그렇게 해", 5a E26) on the 060–084 evidence: 0.45 green tokens a seat never flipped, 0.40 of them with a free use left
(`endgame_tech_counts` missed); user: "밀리는 것을 미리 인지하면 … 다른 곳에 투자".
Pre-registered verdict: charges gained in rounds 1–3 (1 VP = 1.5 charges). Read alongside (not the verdict, PPO gate):
level 5 / Advanced tiles / green tokens left / missed, federations, final VP, decision time.
geo-quartet, six new seeds, seat-swapped pairs, hard budget (4 comparisons, 20 s), full 6 rounds, agentmaco, commit
ddfe36a, 10:52 → 14:04 (3 h 12 min). Result: lab/results/090-ships-vs-tokens-full.md.

**Health: clean.** 12 of 12 games, 0 error games, 0 timeouts, 0 fallback-timeout decisions, 0 federation-candidate
limit hits. Decisions 1827 vs 1926; A mean 11.84 s, median 17.04 s, max 22.3 s; B mean 11.90 s, median 17.26 s,
max 24.4 s. Unsearched decisions 1383 vs 1474. The extra root goal costs no time.

## Charges in rounds 1–3 (the verdict)

| Faction | A | B | B−A | 95% CI | Pairs B ≠ A | Per pair (p000 … p005) |
|---|---:|---:|---:|---|---:|---|
| Geodens | 164.9 | 166.8 | +1.8 | [−2.9, +6.5] | 1 / 6 | 0 · 0 · 0 · 0 · +10.9 · 0 |
| Taklons | 170.3 | 171.4 | +1.2 | [−1.4, +3.8] | 2 / 6 | 0 · 0 · 0 · 0 · +6.1 · +1.0 |
| Terrans | 170.1 | 175.2 | +5.1 | [−8.0, +18.2] | 1 / 6 | 0 · 0 · 0 · 0 · +30.5 · 0 |
| Xenos | 157.5 | 164.7 | +7.3 | [−11.4, +25.9] | 1 / 6 | 0 · 0 · 0 · 0 · +43.6 · 0 |
| **All (seat mean)** | | | **+3.8** | [−5.9, +13.6] | | |

**Rounds 1–3 were move-for-move identical in both games of p000–p003 and p005** (p005: one Taklons charge). Every
non-zero number above comes from p004, and p004 split at step 11 (round 1, Xenos): both arms chose the same opening
(1RL+1TS+2M), but A completed 1 comparison and B 2 inside the 20 s cap, so the plan behind the opening differed; at step
82 (Taklons) 3 vs 2 comparisons. **That is the 20 s cap's same-code drift, not a token rule**: no token rule has a
trigger before a green token exists or a rival stands at level 4, i.e. nothing before round 3–4. The verdict window
cannot see these parts at all.

**p000 and p001 were identical for all six rounds** (same four final scores, same step count 332 / 327; the only
differing label is `local-baseline` vs `current-choice` for the same move). p002 and p003 split in round 4, both at a
Xenos B flip decision (below).

Posted watch replay: `pair-004/game-0-A01` seat 1 — Xenos A 132 vs Xenos B 175 in the other game of the pair (the
drift pair).

## What the parts did (B decisions, `decisions.jsonl.gz` selected labels)

The token_compare root goal (`flip-N`) won the comparison **4 times, all Xenos B, all Advanced tiles through an
upgrade, none a level-5 advance**:

| Game | Step | Round | Move |
|---|---:|---:|---|
| p002 `game-0-A03` seat 2 | 172 | 4 | Science academy + Advanced tile (Terraforming) |
| p003 `game-1-A02` seat 3 | 164 | 4 | Twilight free lab + Lost Fleet Advanced tile |
| p003 `game-1-A02` seat 3 | 294 | 6 | QIC academy + Advanced tile (AI), VP 21 → 42 in the log |
| p004 `game-1-A23` seat 1 | 224 | 5 | Lab upgrade + Advanced tile (AI) |

Geodens, Taklons and Terrans B never selected a flip plan. track_race swaps and race_prune removals are not written to
the decision log (only the selected label is), so they are not counted here.

**End state by arm (`endgame_tech_counts.py --glob 'lab-090-*'`, 6 seat-games per cell, A → B):**

| Faction | adv | lvl5 | lvl4+ | feds | green left | missed | VP before final scoring |
|---|---|---|---|---|---|---|---|
| Geodens | 0 → 0 | 0.50 → 0.33 | 1.33 → 1.67 | 1.00 → 0.83 | 0.50 → 0.50 | 0.17 → 0.33 | 18.2 → 16.5 |
| Taklons | 0 → 0 | 0.50 → 0.67 | 1.50 → 1.50 | 0.83 → 0.67 | 0.33 → 0 | 0.17 → 0 | 31.0 → 37.2 |
| Terrans | 0.17 → 0.33 | 0.83 → 0.67 | 2.33 → 2.50 | 1.00 → 1.00 | 0 → 0 | 0 → 0 | 30.7 → 36.8 |
| Xenos | 0.33 → 0.83 | 1.17 → 1.17 | 2.00 → 2.17 | 2.67 → 2.67 | 1.17 → 0.67 | 1.17 → 0.67 | 56.2 → 68.7 |
| Seat mean | 0.13 → 0.29 | 0.75 → 0.71 | | 1.38 → 1.29 | 0.50 → 0.29 | 0.38 → 0.25 | 34.0 → 39.8 |

Xenos is the only faction that holds tokens early enough for the rules to act (2.67 federations a game); its unflipped
tokens fell 1.17 → 0.67 and Advanced tiles rose 0.33 → 0.83. Taklons' "green 0" comes with fewer federations
(0.83 → 0.67), not more flipping. Geodens kept 0.50 unflipped and lost a level 5.

**Federations by arm (`federation_chances.py --by-arm`, formed per seat-game, A → B):** Geodens 1.00 → 0.83, Taklons
0.83 → 0.67, Terrans 1.00 → 1.00 (satellites 4.2 → 3.3), Xenos 2.17 → 2.17 (13 formed each, satellites 5.2 → 4.8).
Taklons B sat on more legal federations late (round 5–6 legal decisions 1.0 + 1.7 → 2.2 + 3.2, formed 0): its moves
while a federation was legal were ResearchAdvance 18, PowerAction 15. Passes while legal: Taklons 6 → 8, Terrans 2 → 1.

**Final VP (read alongside).**

| Faction | A mean | B mean | B−A | 95% CI | Per pair (p000 … p005) |
|---|---:|---:|---:|---|---|
| Geodens | 60.7 | 55.7 | −5.0 | [−14.9, +4.9] | 0 · 0 · −21 · −11 · +5 · −3 |
| Taklons | 70.7 | 82.0 | +11.3 | [−20.0, +42.7] | 0 · 0 · +10 · −15 · **+70** · +3 |
| Terrans | 78.5 | 88.5 | +10.0 | [−9.7, +29.7] | 0 · 0 · +2 · +5 · +48 · +5 |
| Xenos | 106.3 | 118.0 | +11.7 | [−4.0, +27.4] | 0 · 0 · +15 · +22 · +35 · −2 |
| All (seat mean) | 79.0 | 86.0 | +7.0 | [−9.7, +23.7] | |

Taklons +70 and Terrans +48 are p004, the drift pair. Without p004: Xenos +8.8 (3 of 4 split pairs positive),
Geodens −8.8, Taklons −0.5, Terrans +3.0.

## Reading

- **Verdict (pre-registered, rounds 1–3 charges): not shown, and not showable.** +3.8 [−5.9, +13.6]; the only pair
  that differs in rounds 1–3 differs by comparison count at the cap. The rules have no trigger in the verdict window.
  The window confirms "no early harm" only in the trivial sense that the code does not run there.
- **The parts fire, but only where tokens exist**: 4 flips in 24 B seat-games, all Xenos, all Advanced tiles in rounds
  4–6; no level-5 flip at all (level 5 needs 4 knowledge and a level-4 track; the rollout never preferred it).
  Xenos: fewer tokens left (1.17 → 0.67), more Advanced tiles (0.33 → 0.83), VP +11.7 (CI touching 0).
- **Geodens leans negative** (VP −5.0, 4 of 4 split pairs ≤ +5, level 5 0.50 → 0.33, missed up) with no flip ever
  selected — the race_prune / track_race order changes are the only parts that can have acted; worth one explain.
- **PPO gate unchanged**: a token rule can only flip tokens that exist. Three factions form 0.67–1.0 federations a
  game, so they hold at most one token, usually taken in round 4–6. The ceiling is federations (089's conclusion),
  i.e. placement.
- The 20 s cap splits same-code mirror games by one completed comparison (p004 step 11: 1 vs 2). That is the ±30
  drift the 084 yardstick measures; here it produced the whole "signal".

Nothing changed in code or deployment. 091–094 stay queued as they are.

## Proposal (user decision, nothing queued)

- (ㄱ) **Verdict rule for late-game parts.** fed (089) and tokens (090) cannot act before round 3–4, so rounds 1–3
  charges only measure drift for them. Proposal: for such parts the verdict is the PPO-gate counts (federations a
  seat, green left, missed) plus final VP, with rounds 1–3 charges kept as the no-harm check. Needs the user's yes;
  the charge rule stays for everything that acts early.
- (ㄴ) **Bundle, one measurement**: `ships_fed_tokens` (089 fed_compare + fed_cluster, 090 token parts) vs `ships`,
  six new geo-quartet seeds, 6 rounds (≈ 3 h, after 094). Both bundles were harmless in rounds 1–3; measured by (ㄱ).
  If positive on tokens/feds, add six more seeds (12-pair pool) before touching the deployment stack.
- (ㄷ) Lab time 0, bot turn: explain Geodens B (which rule moved it; level 5 lost, no flip) and Taklons B round 6
  (3.2 legal federations a seat-game, 0 formed, ResearchAdvance played instead) with `explain_ab_decisions.py`.

Bot recommendation: (ㄷ) now in a bot turn, (ㄱ) decided by the user, then (ㄴ).
