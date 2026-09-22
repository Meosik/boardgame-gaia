# Four-seat approval coaching

Local-only, separate from normal multiplayer and existing live spectators. The
same quartet seed and current A/B assignment are reused: HadschHallas/Taklons B,
Xenos/Terrans A. This is a coaching session, **not an A/B strength result**.

From the repository root:

```sh
PYTHONPATH=gaia-rl/python:gaia-rl/experiments:gaia-rl/tools \
  gaia-rl/.venv/bin/python -m coaching.launch \
  --output gaia-rl/runs/my-coaching-session
```

Open `http://localhost:5174/?aiCoach=1`. The launcher freezes the teacher/native
sources and uses ports 5174/8789, leaving existing matches/5173 alone. Closing the
browser does not play a move. Ctrl-C stops these local services; to recover:

```sh
PYTHONPATH=gaia-rl/python:gaia-rl/experiments:gaia-rl/tools \
  gaia-rl/.venv/bin/python -m coaching.launch \
  --output gaia-rl/runs/my-coaching-session --resume
```

Every native decision (including setup, power responses and free actions) waits
for explicit approval. New coaching sessions use a maximum 10-second recommendation budget with no automatic extension. Historical clock metadata and pending recommendations remain intact when an explicitly recorded runtime clock amendment is applied.
The side panel shows its final recommendation separately from genuine root
scores. Scores are heuristic values, **not predicted final VP**. All native legal
candidates remain selectable, including moves excluded by teacher policy; search
and coordinate labels help locate them. Choosing does not execute. Nonrecommended
choices require both a reason and a next plan before the execution button enables.
A rejected plan is not forced onto the subsequent human-corrected state.

Technology-granting actions are grouped by their base action. Select the action,
then explicitly select its technology, then its research track when freely chosen.
Fixed aligned tracks are displayed rather than silently inferred by the UI.
There is no preselected technology, including when accepting the AI's recommendation.
Bonus destinations require an explicit choice when multiple native variants exist.
The API also requires `technology_confirmed: true` for technology acquisition;
the selected native candidate and confirmation are recorded together.

Undo preserves the original journal: `coaching.branch.branch_session` copies a
prefix into a new directory, replays it natively, and checks the exact pre-action
state. `game/branch.json` records source hashes and the retained action count.
Later actions stay in the original run; they are never reapplied to the new state.
Branch session IDs differ, so the viewer can accept an earlier decision safely.

## Record and safety boundary

- `game/session.json`: initial state, native versions, sources, seed/policy.
- `game/suggestions/`: pending and past recommendations, original scores/audit,
  pre/post-search teacher memory. Reload/restart keeps a pending recommendation.
- `game/decisions/`: atomic append-only files with complete before/after state,
  actual legal action, recommendation, explanation, plan, and controller provenance.
- `GET /coach-api/record`: downloadable complete or partial coaching record.
- Human acceptance of an AI recommendation is `ai_accepted_by_human`, **not an
  independent human demonstration**. A correction is `human_override`, not proof
  that the choice is optimal. Tests/diagnostics must not be passed off as expertise.
- No online weight change, PPO/BC, promotion, automatic pass or auto-approval.
  Partial coaching records are **not yet consumed by the complete-game BC loader**.
- Duplicate/stale approvals are rejected. Disk write failure does not advance the
  parent game. Restart replays every saved action natively and checks exact states.
- Only localhost access is supported. Mutation requires same local origin and an
  API token. A file lock prevents two API processes owning the same journal.
- The coaching board is selection-only: buildings/planets, technologies/tracks,
  power/personal/ship actions and boosters route to the current native candidates.
  All grouped legal actions are also available as clickable buttons in the panel;
  the text list remains an optional fallback. Yellow marks the AI recommendation,
  not the human selection. A complete alternative opens a reason/next-plan dialog.
  Closing or completing that dialog never executes; final approval is still required.
  Normal game WebSockets, multiplayer permissions, prior replays and BGS code are untouched.

Checks: `python -m unittest coaching.test_session coaching.test_server` with the
PYTHONPATH above; frontend `vitest run src/tests/AiCoach.test.tsx`. Real teacher
inference and browser validation are additional to these deterministic tests.
