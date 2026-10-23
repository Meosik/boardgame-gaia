# Cycle 105 — ships vs ships_menu1 — plan_menu front slot 1 (was 3), 4R start

A = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap60-p2.json` (ships stack, dedup code 588c076).
B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-cap60-p2.json`: A + 103's plan_menu ≈80%
with only **one** front slot (`_guide['menu_first']=1`, 4962c6e) instead of p1–p3 — 103 showed the three front slots pushed
root·upgrade candidates out of the 4 comparisons (root entries 2540 → 413). Queued 2026-10-23 by the user ("ㄱ으로 ㄱㄱ", E93 (ㄱ) = E89 (ㄷ)).
Pre-registered verdict: budget validity first (1–3R decisions; (가) error games > 2, (다) completed comparisons/decision differ > 10%,
(라) >60 s share differs ≥ 1 %p, (마) >100 s > 0.5% or any >300 s → held); health: exact (goal, spec, first) duplicates 0.
If valid, 1–3R charges all (seat mean) 95% CI: non-inferiority lower > −15 → "해 없음"; direction lower > 0 "개선", upper < 0 "손해", else "방향 없음".
Read alongside: per-faction charges and pair signs, 4R-start VP, basics table, family entries/selections vs 103.
geo-quartet (Geodens·Taklons·Terrans·Xenos), the same 24 seeds as 103, seat-swapped pairs, comparisons 4, both arms cap60-p2,
stop at the start of round 4, agentmaco, commit 70ebff9, 2026-10-23 21:50 → 10-24 07:00 (9 h 10 min, est. 8.5 h).
Result: lab/results/105-ships-vs-menu1-4r.md.

**Health: clean.** 48/48 games, errors 0, timeouts 0, fallback-timeout 0, federation-limit misses 0. Decisions A 3650 · B 3699;
time A mean 16.6 · median 14.3 · p90 40.9 · max 70.2 s, B 17.3 · 14.7 · 43.8 · 70.0 s. Unsearched A 2643 / B 2663.
Budget validity (decisions.jsonl.gz direct count, all decisions are 1–3R): (가) 0 / 0 pass; (다) completed comparisons/decision
A 2.819 · B 2.791 (1.0%) pass; (라) >60 s A 122/3650 = 3.34% · B 157/3699 = 4.24%, gap 0.90 %p < 1 pass (close);
(마) >100 s 0 / 0 pass. Exact duplicates in `compared` A 0 · B 0 pass. **Budget valid.**

## Charges in rounds 1–3 (the verdict)

| Faction | B parts | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| Geodens | menu 1 slot | 189.6 | 190.5 | +0.9 | [−12.8, +14.6] | 10/24 | min −107 (pair-014), max +49 |
| Taklons | menu 1 slot | 181.9 | 184.4 | +2.5 | [−16.7, +21.6] | 9/24 | −59 … +120 (pair-019); 7 pairs beyond ±50 |
| Terrans | menu 1 slot | 175.8 | 181.2 | +5.4 | [−6.7, +17.4] | 16/24 | −76 (pair-001) … +50 |
| Xenos | menu 1 slot | 187.1 | 190.4 | +3.4 | [−12.0, +18.7] | 12/24 | −56 … +76; 5 pairs beyond ±50 |
| **All (seat mean)** | | | | **+3.0** | **[−4.8, +10.8]** | 14/24 | 24 pairs, −33.5 … +37.6 |

(pair signs and extremes: short python over `charges.seats` of the result json.)
Posted watch replay: `pair-019/game-1-A01` seat 0 — Taklons A 161 vs B 281.
VP at the start of round 4 (not the verdict): all +0.8 [−0.5, +2.1]; Taklons +2.1 [−0.6, +4.8].

Pre-registered reading: non-inferiority lower −4.8 > −15 → **"해 없음"**; direction CI contains 0 → **"방향 없음"**.
No faction reaches the 25-charge readability line (largest Terrans +5.4, 16/24); all inside the ±30 drift band.
Same seeds as 103 (reference −9.7 [−16.2, −3.3], 7/24) now +3.0, 14/24 — but A's code differs (dedup), so not pooled.

## Activation (rounds 1–3, A → B)

decisions.jsonl.gz direct count (`compared` families and `selected` goal; same method as 103):
- B decisions with a non-empty menu 3365/3699 (91%), A 0. `menu_forgot` 0 (as in 103).
- Completed-comparison entries by family, A → B (103 B in brackets): root 2541 → **2644** [413], upgrade 990 → 475 [297],
  research 949 → 298 [500], sequence 1375 → 407 [1071], ordered 497 → 1316 [3265], colony 281 → 1367 [920],
  federations 7 → 125 [73]; bgg-opening 1007 → 1031, current 2641 → 2662.
- Selected by family, A → B: root 265 → **268** [18], upgrade 153 → 86 [29], current 1037 → 371, sequence 112 → 13,
  research 40 → 4, ordered 29 → 146, colony 9 → 28, federations 3 → 1; not in `compared` (tie/memory) 1297 → 2133.
= The one front slot gave root back fully (entries and wins at A level); the menu now displaces the later research·sequence·upgrade
slots instead. Federation plans enter 125 times, win once.
- Basics table: Xenos 1–3R credit income 16.0 → 18.1, 4R credits 7.0 → 8.0; Taklons ore income 12.0 → 12.9; others flat.

## Reading (HANDOFF 1 order)

- All: ① the +3.0 sits well inside noise (CI spans 0, 14/24, ±30 drift band) — no gain, no harm. ② the part fired (menu 91%)
  and the 103 interaction is gone: root entries/wins back to A level (2644/268 vs 2541/265) and the 103 loss direction
  (−9.7) does not appear on the same seeds. So 103's loss is best explained by ④ the three front slots pushing root out, not by
  the menu plans themselves — with the caveat that A's code also changed (dedup), so 103 → 105 is not a clean comparison.
- What the menu buys in 1–3R is nothing measurable: federation plans enter (125) but win once, `ordered`/`colony` win 146/28
  mostly in place of `current`. ⑤ **hypothesis, untested** (debate 1/1): the menu's targets (federations, track plans, round tiles)
  may pay off in 4–6R; this run stopped at the 4R start, and CI [−4.8, +10.8] means "gain not shown", not "no gain". A late effect vs
  plain non-firing can only be separated by a 6R run with pre-registered late metrics (Proposal (ㄹ)). The 6R question needs the
  645 s path (E82 (ㄷ)) closed first — 102 p2 6R still ran to 757 s.
- Taklons: 9/24 signs but mean +2.5 — 7 pairs beyond ±50 both ways (pair-019 +120, pair-004·005 +80/+77) = ① spread, not a direction.
  Geodens pair-014 −107 (114 vs 221) is the single large loss — explain candidate (101/102 had −97/−98 Geodens pairs too).
- Health clean; >60 s gap 0.90 %p sits just under the 1 %p bound (B slightly slower, 17.3 vs 16.6 s mean).
- Review: the result page has no `## 검수` section (no second-model review attached) — noted.

No code or deployment change. Lab queue empty (097·100 held `_`).

## Proposal (user decision, nothing queued)

- (ㄱ) Record: `ships_menu1` = "해 없음, 방향 없음" in 1–3R; keep it as the menu candidate (103's p1–p3 layout retired). No adoption into
  the baseline yet — no gain shown. Bot turn, now.
- (ㄴ) explain bot turn (lab 0): Geodens pair-014 (B `pair-014/game-0-A03` 114 vs A `game-1-A12` 221) first divergence, and
  whether a menu plan won there.
- (ㄷ) Before any 6R menu run: E82 (ㄷ) find the cap60 path that ran to 645–757 s in 102 (bot turn, code reading + the 102 decisions).
- (ㄹ) Then 6R ships vs ships_menu1, 12–24 seeds cap60-p2, final VP as pre-registered secondary (≈ 8–15 h lab). Verdict stays
  1–3R charges; pre-register late metrics with success lines before the run (debate 1/1): 4–6R charges by faction (`charge_rounds.py`
  window 4–6), federations per seat and green-token flips (`federation_chances.py --by-arm`, `endgame_stock.py`), menu federation/track
  plans entered → selected → completed (`plan_labels.py --families`). "Late effect" only if B's menu plans are selected and completed
  more AND 4–6R charges or final VP move the same way; selected but no outcome change = fired without effect; not selected = non-firing.
Bot recommendation: (ㄱ) now, (ㄴ) and (ㄷ) as bot turns, then (ㄹ).
