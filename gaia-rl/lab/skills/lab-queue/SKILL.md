---
name: lab-queue
description: Write a lab experiment queue file (gaia-rl/lab/queue/<name>.json, kind ab or command) with the pre-registered verdict, seeds and time estimate, then commit and push. Use when the user confirms an experiment ("큐에 넣어", "돌려", "그렇게 해").
---

# lab-queue

Only after the user confirmed the experiment (a proposal in a review turn is not a confirmation).

## 1. Name and number
- `NNN-<a>-vs-<b>-<4r|full>` for A/B, `NNN-<what>` for commands. NNN = highest number in
  `gaia-rl/lab/queue/` (including `_`-held) and `gaia-rl/lab/results/` + 1. Sub-letters (098a, 098b) only
  for smokes attached to a numbered design.
- `_` prefix = held (lab skips it). Lab runs queue files in name order, one at a time.

## 2. Teacher specs (A/B)
- Files: `gaia-rl/tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-<stack>-cap20.json`.
  `ships` = the deployment stack (A arm of most designs); `ships_byfaction`, `ships_byfaction_guide`,
  `ships_menu`, `ships_endgame`, … = one part on top. Budget variants: `cap20` (20 s, comparisons 4, hard),
  `cap60-p2` / `cap60-p4` (60 s with 2 / 4 parallel rollouts: same decisions, fewer host-load effects; use
  for 6R designs). A new factory needs the flag in `teacher_patches.py` + a spec file + the factory test first.
- Both arms must differ by exactly the part under test. Check with `grep -n "<flag>" gaia-rl/tools/teacher_patches.py`.

## 3. Seeds
- geo-quartet (Xenos / Taklons / Terrans / Geodens): omit `seeds`, give `pairs`; lab takes fresh seeds from
  `lab/seeds.txt` and scans for more when short (lab.py `ensure_seeds`).
- Fixed lineups: give `seeds` explicitly from `lab/seeds-quartet-{a,b,c,d,e}.txt` / `lab/seeds-live-quartet.txt`
  (a Firaks·Ivits·Lantids·Nevlas, b BalTaks·Bescods·Gleens·Itars, c Ambas·HadschHallas·Terrans·Xenos,
  d Geodens·Moweyds·Taklons·Tinkeroids, e Darkanians·SpaceGiants·Terrans·Xenos, live HadschHallas·Taklons·Terrans·Xenos).
  Unused seeds of a file (change the file name):
  `gaia-rl/.venv/bin/python -c "import json,glob;u={s for p in glob.glob('gaia-rl/lab/results/*.json')+glob.glob('gaia-rl/lab/queue/*.json') for s in (json.load(open(p)).get('seeds') or [])};print([l.strip() for l in open('gaia-rl/lab/seeds-quartet-b.txt') if l.strip() and l.strip() not in u][:12])"`
  Re-using seeds is only for pre-registered pools (say so in the note).

## 4. The file
```json
{
  "kind": "ab",
  "note": "사용자(<date> \"<quote>\"; HANDOFF E<n> (ㄱ)): A = <stack>, B = A + <part> (<source ids>). <design: lineup, seeds, rounds, budget>. 판정: 1–3R 충전 종족별 — <which faction decides, pooled pairs if any>. 함께 볼 것: <counts>.",
  "teacher_a": "tools/teacher-a-...-ships-cap20.json",
  "teacher_b": "tools/teacher-a-...-ships-<part>-cap20.json",
  "pairs": 6,
  "comparisons": 4,
  "stop_round": 3
}
```
- `stop_round` 3 = games end when round 4 starts (verdict window 1–3R; ≈ 1.5 h for 6 pairs, ≈ 2 h 50 for 12).
  `0` = full 6 rounds (≈ 3 h for 6 pairs, ≈ 6 h for 12; needed when the pre-registered secondary is final VP).
- `vp_rate`: leave out (1.5 charges per VP held). `seeds`: explicit list for fixed lineups.
- Command jobs: `{"kind": "command", "note": "...", "run": ["{python}", "tools/x.py", "--jobs", "{jobs}", "--out", "runs/x/metrics.json"], "metrics": "runs/x/metrics.json", "timeout_hours": 4}`.
  A command that edits tracked files (seed scans) is fine since 2026-10-21 (lab stages `lab/seeds*.txt`).
- The note is the pre-registration: what decides, which pairs pool, what to read alongside. Write it so the
  review turn can judge without asking.

## 5. Commit, push, reply
```
git add gaia-rl/lab/queue/<name>.json
git commit -m "lab: queue <name> (<A> vs <B>, <lineup> <n> pairs <4R|6R>)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git pull --rebase origin claude/epic-goodall-0ot55w
git push origin HEAD:claude/epic-goodall-0ot55w
```
Then add one line to HANDOFF section 5 (lab order) if the order changed, and reply with name, hours, and the
expected notices: lab posts 📋 when it sees the file, 🧪 at start, ✅ at the end (the ✅ starts the review turn).
Never run the experiment in the bot turn (5-minute limit).
