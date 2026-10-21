---
name: lab-review
description: Record a finished lab experiment (gaia-rl/lab/results/<name>.md) - cycle document, HANDOFF table row and E-entry, commit, push, then a proposal only. Use for "<name> 결과가 나왔다", a ✅ lab notice, or "결과 정리해".
---

# lab-review <experiment name>

Everything this needs is below; do not read HANDOFF for the procedure (only for the parts named here).

## 1. Get the result (small reads only)
1. `git pull --rebase origin claude/epic-goodall-0ot55w`
2. Read `gaia-rl/lab/results/<name>.md` (3–5 KB). **Never read the `.json`** (hundreds of KB). A missing number:
   `gaia-rl/.venv/bin/python -c "import json;d=json.load(open('gaia-rl/lab/results/<name>.json'));print(d['summary'])"`
   (keys: seeds, summary, timing, final_scores, charges, watch_replay, exit_code; command jobs: metrics).
3. The queue file `gaia-rl/lab/queue/<name>.json` holds the design and the **pre-registered verdict** in `note`.
4. Game data: `~/projects/gaia-lab/gaia-rl/runs/lab-<name>/pair-*/game-*` (readable; never edit under gaia-lab).

## 2. Judge (rules, in this order)
- **Verdict = charges gained in rounds 1–3 by faction** (user 2026-10-07), already in the .md table
  (B−A, 95% CI, pairs B>A). Final VP is never the verdict; for 6R designs it is a pre-registered secondary.
- Readability line **25 charges** (088); same-code drift is **±30 per faction, ±50 per pair** (084/088).
  Below the line = "unreadable", not a result. Count pair signs (n/12) next to the mean.
- Pooled pairs only when the queue note pre-registered them (e.g. 091 + 098 BalTaks).
- Health first: games ok / total, error games, timeouts, fallback-timeout decisions, max decision seconds
  per arm (20 s cap specs run to ~35 s; cap60 to ~80 s). Decision counts A vs B.
- A negative or flat result is explained in HANDOFF 1 order: ① noise ② activation (did the part fire?)
  ③ scope/implementation ④ interaction with other parts or search ⑤ measurement window (gain is 4–6R)
  ⑥ condition mismatch (base game vs Lost Fleet, map, players) ⑦ the source itself. ①–④ fix and re-run,
  ⑤–⑥ narrow and re-run, only ⑦ rejects a source claim.
- Activation evidence (run from the repo root; each tool has `--help`; prefix for engine tools:
  `GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools gaia-rl/.venv/bin/python gaia-rl/tools/<tool>.py <run dir>`):
  `research_counts.py --rounds 1-3` (tracks per faction/arm), `upgrade_counts.py --rounds 1-3` (TS/RL/PI/AC,
  R1 academies), `tile_counts.py` (standard tile ids), `action_counts.py` (faction actions, free actions),
  `plan_labels.py --prefix BGG-R1-` (which plan won, no replay), `charge_rounds.py` (recompute charges),
  `federation_chances.py --by-arm`, `endgame_tech_counts.py`, `endgame_stock.py` (6R stock), `shipmine_hits.py`.
  Pick the two or three that test *this* part; do not run them all.

## 3. Write the cycle document
`gaia-rl/research/strategy/cycles/<name>.md`, shape = `gaia-rl/research/strategy/cycles/TEMPLATE.md` (read that,
not an older cycle). Sections: header (A, B, part, source ids, queue reason, pre-registered verdict, seeds,
budget, host, commit, duration, result path) → Health → Charges table (the verdict) → Activation → Reading
(HANDOFF 1 order) → Proposal (user decision, nothing queued, bot recommendation). Numbers with CI and pair
counts; name the tool behind every count.

## 4. Update HANDOFF (`gaia-rl/lab/HANDOFF.md`)
- Section 2 table: append one row after the last `| NNN |` row, same shape as the row above it:
  `| <number> | **title**(design, parts, source ids) — lineup, seeds, rounds, duration | **health**. verdict numbers
  per faction with CI and n/N, activation footprint | verdict word, code/deploy changes (usually none),
  lab order after this, **다음 제안(큐 안 넣음, 5a E<n>)**: (ㄱ)… 봇 추천 |`
- Section 5a: insert a new `- E<n>(<date time>) **<name> 완료** → 사이클 문서 ...` line **above the current top
  E-entry** (newest first; next number = top number + 1). Same content as the row, plus
  **사용자 답 대기(큐 안 넣음)**: (ㄱ)(ㄴ)… with cost (lab hours or bot turn) and 봇 추천.
- Section 5 "진행 중": update the lab line (what runs now, what is queued, `_`-held items) and the
  "사용자 답 대기" pointers. Keep section 5 a short current-state summary.
- Size rule (section 7): when the table passes 15 rows or 5a passes 15 entries, move the oldest verbatim to
  `gaia-rl/lab/HANDOFF-archive.md` (matching section, note the date and commit).

## 5. Commit and push (one command per call, no `&&`, no newlines)
```
git add gaia-rl/research/strategy/cycles/<name>.md gaia-rl/lab/HANDOFF.md
git commit -m "research: cycle <name> <one-line verdict with numbers>, HANDOFF table + E<n>" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git pull --rebase origin claude/epic-goodall-0ot55w
git push origin HEAD:claude/epic-goodall-0ot55w
```
No model name in the subject line (HANDOFF 7).

## 6. Reply (Korean, phone-short)
Verdict with numbers → what it means (one line per faction that matters) → next experiment **as a proposal
only** (design, seeds, hours) and what the user must decide. Never add a queue file in this turn; config or
deployment changes are proposals. If the result is `failed`, report the log tail and the likely cause instead.
