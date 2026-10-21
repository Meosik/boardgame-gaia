---
name: explain
description: Explain one teacher decision from a lab game ("왜 그 수를 뒀나", "이 수 이상한데", replay frame N) with explain_decision / explain_ab_decisions / list_decisions, publish a replay, and record the finding in known-bad-decisions.md. Use when the user points at a move or asks why the AI did something.
---

# explain

The user cannot read moves deeply (2026-10-20). Before running anything, make sure you have the four facts;
ask for the missing ones in one short message, the rest can wait:
1. which experiment / pair / game (or replay title `<pair> / game-Y-AZZ`), 2. the frame or decision number,
3. what looked wrong (resources piling up, a scoring move skipped, a federation left unformed, a token not
flipped, a plan that makes no sense), 4. the expected move. Round, opponents and map matter too.
If the user gives a replay title only, the folder is `~/projects/gaia-lab/gaia-rl/runs/lab-<experiment>/<pair>/<game>`.

## Commands (repo root, one per call; the python prefix is in the bot allow list)
Prefix `<P>` = `GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools gaia-rl/.venv/bin/python` — write it out in full every time, never a shell variable.
- List decisions of a game (step = 0-based = replay frame − 1; all four seats are counted):
  `<P> gaia-rl/tools/list_decisions.py <game dir> --seat <n>` (filters per `--help`).
- Replay one decision without plan memory (actual move, re-chosen move, default ranking with scores and
  reasons, compared plans with predicted values):
  `<P> gaia-rl/tools/explain_decision.py <game dir> --step N` (`--spec <teacher spec>` to ask another stack).
- Replay with the arm's plan memory (the teacher re-chooses that seat from the start; slower, exact):
  `<P> gaia-rl/tools/explain_ab_decisions.py <game dir> --arm A|B --steps N [N ...]`.
- First decision where the two arms of a pair diverge: `shipmine_hits.py --first-split <run dir>` for that
  part; otherwise compare `list_decisions.py` of the two games of the pair.
- Replay for the user (phone): export + publish, visible on the site without a deployment:
  `<P> gaia-rl/tools/ab_replays.py export <game dir> --output /tmp/ab-<name> --focus <seat|A|B|best>`
  `gaia-rl/.venv/bin/python gaia-rl/tools/publish_replays.py --source /tmp/ab-<name> --destination ~/gaia-media/ai-replays`
  Title = `<pair> / <game folder>` only (the site adds "· 초점 <faction> <VP>"); no experiment name or arm.
- Anything over ~5 minutes (many steps, whole-run scans) goes to the lab queue as a command job instead.

## Reading the output
- `selected` = what was played; `via` = the plan that proposed it (`BGG-R1-…` opening lists, `federation-…`,
  `track-plan-…`, `colony@x,y`, `local-baseline`, `current-choice`, `fallback-…` = a forecast that did not finish).
- Comparisons: at most 4 plans per decision under the 20 s cap (`comparisons 4/4` = all finished; fewer = host
  load changed the decision, i.e. timing noise, not a rule).
- Ties at the same value fall back to the default ranking (research AI/QIC first on the LF value table).
- Separate: value error (a resource priced wrong — the kind indicators never show), ordering (a plan not
  in the comparison set), horizon (one-income rollout cannot see a gain two rounds out), noise.

## Record
Append to `gaia-rl/research/strategy/known-bad-decisions.md`: experiment, game, step/frame, faction, round,
what was played, what was expected, the explain reading (value / order / horizon / noise), and the re-question
command. This file is the regression set: after a value or search change, re-run the listed commands and note
what moved. Commit: `git add <file>` / `git commit -m "research: explain <experiment> <game> step N (<reading>)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"` / `git pull --rebase origin claude/epic-goodall-0ot55w` / `git push origin HEAD:claude/epic-goodall-0ot55w`.

Reply in Korean, short: what was played and why (the teacher's own numbers), whether it is a value, order,
horizon or noise issue, and the one fix candidate with its cost. A rule change is a proposal; the user decides.
