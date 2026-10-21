# Cycle 099 — seed scan for the six fixed lineups (lab command, no A/B)

Not a measurement. The lab's A/B runs on fixed four-faction lineups, and a lineup is only reproducible through a
seed string whose faction draw happens to give those four factions (`quartet-a-N`, `quartet-b-N`, …, about one hit
in 2000). The lineup files `lab/seeds-quartet-{a,b,c,d,e}.txt` and `lab/seeds-live-quartet.txt` were running dry —
098 had to reuse six quartet-b seeds from 083 / 086 / 088 because only one unused seed was left (HANDOFF E39), and
096 stalled the service for an hour on 2026-10-21 when `seeds.txt` ran out (E62). User 2026-10-20 "시드 미리 많이
만들어둬" → `tools/scan_seeds.py` (E39 ②): reads each file's lineup from its first seed, scans the seed numbers
60000–259999 under that file's prefix in 2000-seed chunks on a process pool, and appends the hits that are not
already in the file. Queued as lab `command` 099 (jobs 4, timeout 4 h).

Run: agentmaco, commit f861ff7, 2026-10-21 12:05:50 → 12:30:10 (**24 min 20 s**, exit code 0). Result:
lab/results/099-scan-seeds.md (see the lab-state note below: the result commit is still local on the lab checkout).

## What was added

| File | Lineup | Lines before | Added | Lines after | Hit rate |
|---|---|---:|---:|---:|---|
| seeds-quartet-a.txt | Firaks, Ivits, Lantids, Nevlas | 35 | **+120** | 155 | 1 in 1667 |
| seeds-quartet-b.txt | BalTaks, Bescods, Gleens, Itars | 37 | **+108** | 145 | 1 in 1852 |
| seeds-quartet-c.txt | Ambas, HadschHallas, Terrans, Xenos | 29 | **+108** | 137 | 1 in 1852 |
| seeds-quartet-d.txt | Geodens, Moweyds, Taklons, Tinkeroids | 11 | **+110** | 121 | 1 in 1818 |
| seeds-quartet-e.txt | Darkanians, SpaceGiants, Terrans, Xenos | 9 | **+101** | 110 | 1 in 1980 |
| seeds-live-quartet.txt | HadschHallas, Taklons, Terrans, Xenos | 45 | **+101** | 146 | 1 in 1980 |
| **Total** | | 166 | **+648** | 814 | 1 in 1852 (1.2 M draws) |

- Throughput: 1.2 M lineup draws in 1460 s on 4 processes ≈ 820 draws/s ≈ 4.9 ms a draw a process — the 5 ms
  estimate of E39 held, so a 200 000-seed window costs ≈ 4 min a file at jobs 4 (≈ 25 min for all six).
- The five quartet-b seeds of the E39 smoke (60000–66000) were already in the file and were skipped by the
  `known` check (the first new quartet-b line is 61243 after the smoke's 60000–61000 hits); no duplicates added.
- `seeds.txt` (geo-quartet, used by `pairs` allocation) was not in the scan; it has the 14 seeds E62 added and
  101 will take 12 of them. A `--files lab/seeds.txt` scan is the same tool when it runs low.
- Every lineup now has 100+ fresh seeds, so quartet-b 12-pair designs (098 style), quartet-a 6R designs (E62
  (ㄱ) Nevlas), and quartet-d / -e (the Lost Fleet factions, 9–11 seeds before) can all draw unused seeds. The
  ± 30-charge same-code drift of 084 / 088 does not change: more seeds buy pairs, not narrower pairs.

## Lab state after the run — the result commit is stuck (owner action)

`scan_seeds.py` appends to **tracked** files, but `lab.py` `publish()` stages only the result files. On the lab
checkout (`~/projects/gaia-lab`) the six seed files are now modified and uncommitted, so the lab's
`git pull --rebase` refuses ("unstaged changes") and the push of its result commit `021eb81 lab: 099-scan-seeds done`
failed five times (journal 12:31:16 "git push failed 5 times; results are committed locally"; the checkout is
ahead 1 / behind 1 of the branch). Until the seed files are committed there, every 300 s watch loop fails at
`pull()` with a ⚠️ notice and **101 does not start**. The bot does not touch `~/projects/gaia-lab` (HANDOFF 4),
so the owner runs, on the lab checkout:

```sh
cd ~/projects/gaia-lab
git add gaia-rl/lab/seeds-quartet-a.txt gaia-rl/lab/seeds-quartet-b.txt gaia-rl/lab/seeds-quartet-c.txt gaia-rl/lab/seeds-quartet-d.txt gaia-rl/lab/seeds-quartet-e.txt gaia-rl/lab/seeds-live-quartet.txt
git commit -m "lab: 099 scan seeds (+648 quartet seeds)"
git pull --rebase origin claude/epic-goodall-0ot55w
git push origin HEAD:claude/epic-goodall-0ot55w
```

This cycle document and the HANDOFF update were pushed from the work tree first; the owner's rebase puts the two
lab commits (results + seeds) on top of them without conflict (different files). The lab's next loop then pulls
cleanly and starts 101 (≈ 6 h).

Tooling gap (proposal, not applied): a `command` job that edits tracked files outside `lab/results/` leaves the lab
checkout dirty. Smallest fix in `lab.py`: have `pull()` / `publish()` also stage `lab/seeds*.txt` (the only tracked
files a lab command is meant to write), or give `scan_seeds.py` a `--out` that writes the hits to a new file under
`runs/` and let the bot commit them from the work tree. `lab.py` re-execs itself when a pull changes it, so the fix
needs no service restart. Owner's decision; E62's hand-run of `scan_seeds.py` from the work tree had no such problem.

## Reading

- The scan did what it was queued for: +648 seeds, no file lost a line, no duplicates, 5 ms a draw as estimated.
- No teacher, value, or deployment change. Nothing to judge by charges.
- Operational finding: lab commands that write tracked files need their output staged, or the lab stalls silently
  (only the ⚠️ pull notices show it). Recorded in HANDOFF 4 / 5a E66.

## Proposal (user decision, nothing queued)

- Lab order after the owner's commit: **101** (ships vs ships_menu, geo 12 pairs 6R, ≈ 6 h) starts by itself.
- Next queue entry (recommended, after 101): **102 quartet-b six new seeds, byfaction vs byfaction_guide, 4R**
  (≈ 1 h 25 min) — settles BalTaks on 18 pre-registered pairs (12 pairs +25.3 [+7.6, +43.0] 10 / 12 now) and gives
  Bescods a third sample **after** the E65 (ㄴ)+(ㄷ) explain turn (lab 0) has said whether the Navigation cap is
  ④ or ⑤; if the user prefers "integrate, then fix by replay" for BalTaks (E65 (ㄱ)), skip 102 and give the slot
  to E62 (ㄱ) Nevlas 6R on quartet-a (now 120 fresh seeds, ≈ 6–7 h for 12 pairs).
- `lab.py` seed staging fix: owner's call (one bot turn, no measurement).
