# Cycle 113a — BC re-index on the rebuilt engine (records `replay_engine_build_id`), command, no verdict

No A/B: one `command` job, `bc_dataset.py index runs --out runs/bc-1112/manifest.jsonl` (same command and output
path as 113, overwritten). Part under test: 0705be8 — the index now writes the engine build that ran the replay
check (`replay_engine_build_id`) into every manifest line, and export / `iter_samples` refuse a manifest checked on
another engine. The 113 manifest had no such field, so export would refuse it. Queued 2026-11-12 from E130 (ㄱ')
after the owner rebuilt the work-tree engine (E130 (ㄱ)). Pre-registered verdict: none; after the run, check in a
bot turn that `bc_dataset.py stats` shows `replay_engine_build_id` = 36d2e007, then E128 ② (bc_train pipeline test).
All lab runs (1502 games), host agentmaco, commit 2b911bb, 2026-11-12 14:27:39 → 14:31:22 (3 min 43 s).
Result: lab/results/113a-bc-reindex-engine-id.md.

**Health: clean.** Exit code 0, `1502 games indexed`. No review section on the result page (command job).

## Charges in rounds 1–3 (the verdict)

Not applicable — no games were played, no verdict was pre-registered.

## Activation (`bc_dataset.py stats` on the new manifest, run in the work tree, 2026-11-12)

- `current engine build 36d2e007b6f9` — the work tree now runs the same build as lab (it was 045232fa, before
  `@order`, in 113).
- `replay-checked on engine(s): 36d2e007b6f9 1502` — every manifest line carries the field, one engine only.
- Totals unchanged from 113: games 1502, strict replay 1126, 6-round 261, decisions 181,273.
- Per build (games / replay / 6R / decisions): 36d2e007 (current) 70 / 70 / 0 / 4,325; c3e525be 62 / 62 / 0 / 3,835;
  045232fa 263 / 263 / 57 / 43,414; bfb65c38 128 / 128 / 24 / 22,374; 0c2ac810 582 / 454 / 76 / 77,023;
  fd4c2e7c 385 / 139 / 104 / 28,864; 1c2cc2e7 12 / 10 / 0 / 1,438.
- Seat-games per faction unchanged (Xenos 870, Terrans 870, Taklons 780, Geodens 755, base ten 87–112,
  expansion four 37–40).

## Reading

- The part fired as written: the field is present on all 1502 lines and names the lab build, and the work-tree
  engine is that build, so the export gate has nothing to refuse. Export itself was not run in this turn.
- The strict replay count is the same 1126 that 113 found on the older work-tree build 045232fa. The same games
  pass step-count and seat-score checks on 36d2e007, which is what the E130 "legality-equivalent bundle"
  (045232fa → c3e525be → 36d2e007, 395 games, 6R 57) assumed from reading the diffs. It is evidence for that
  assumption at the level the check measures (step counts and final seat scores), not a per-decision comparison
  of legal action lists.
- Replay on the current engine says the recorded moves are still legal and score the same. It says nothing about
  teacher quality: the 1126 games span seven engine builds and many teacher versions, so which builds or
  experiments go into training is a separate choice.
- Health and timing: 3 min 43 s, same as 113.

No code or deployment change. Lab queue is empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) E128 ② pipeline test: `bc_dataset.py export` with a `--build` filter (Sonnet bot turn) and `tools/bc_train.py`
  on the 395-game bundle (policy) and its 57 six-round games (value). A tool check, no strength expected. Bot turns.
- (ㄴ) Collect six-round self-play on the current engine (lab command, four seats same teacher all_tier, 18
  factions, `chosen` recorded): 24 games ≈ 14.5 h by 102, 48 games ≈ 1–1.5 days at cap60, about a third at cap20.
  The owner sets the size and the cap.
- (ㄷ) E124 (ㄱ): the work-tree engine now replays `@order` games, so the 112b turn-position charge table can be
  computed in a bot turn.
Bot recommendation: (ㄱ) first, (ㄴ) queued once the size is set, (ㄷ) when turn order comes up again.
