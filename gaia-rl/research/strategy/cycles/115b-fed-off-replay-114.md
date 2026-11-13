# Cycle 115b — the 46 games of 114 replayed on the engine after 966e9ea (flag off), command, no games

A = the engine that played 114 (build `36d2e007b6f9`). B = the lab engine rebuilt after 966e9ea
(`gaia-engine/src/rules/ai_federation.rs`: a federation shape is validated once with a plain token before its
tokens and bonuses, both modes; HANDOFF E137). `GAIA_FEDERATION_ONE_ROUTE` is not set, so this is the flag-off
path every recorded game used. Queued 2026-11-13 by the owner's 「진행해」 (E137). No A/B, no games, no charge
verdict.
Pre-registered pass criteria (queue note): `bc_dataset.py stats` in the bot turn shows all 46 games pass the
strict replay (step count, per-seat scores, and the `chosen` content of every decision), 46 six-round games,
13,841 decisions (the E133 numbers), and the engine that ran the replay check is a new build, not `36d2e007`.
Any `chosen differs`, step or score mismatch = old games no longer replay → fix or revert the engine change.
Scope fixed in the note (debate 1/1): the replay compares only the chosen action at the recorded index, so this
is **replay compatibility**, not identity of the whole candidate list — that is 115c.
Command: `bc_dataset.py index runs --glob lab-114-all-tier-selfplay-18f-full --out runs/bc-115b/manifest.jsonl`,
agentmaco, commit 92fc0e7, 2026-11-13 13:18:09 → 13:18:29 (20 s). Result: lab/results/115b-fed-off-replay-114.md.

**Health: clean.** Exit code 0, `46 games indexed`, no review section (command job).

## Charges in rounds 1–3 (the verdict)

None — no games were played. The pass criteria above are the outcome.

## Activation (what the manifest shows)

`gaia-rl/.venv/bin/python gaia-rl/tools/bc_dataset.py stats ~/projects/gaia-lab/gaia-rl/runs/bc-115b/manifest.jsonl`
(bot turn; `stats` only reads the manifest, it replays nothing):

| Item | 114 (E133, engine 36d2e007) | 115b (lab engine after 966e9ea) |
|---|---:|---:|
| games indexed | 46 | 46 |
| strict replay passes | 46 | **46** |
| six-round games | 46 | 46 |
| decisions | 13,841 | **13,841** |
| engine that played the games | 36d2e007b6f9 | 36d2e007b6f9 |
| engine that ran the replay check | 36d2e007b6f9 | **fc19671c4278** |

Seat-games per faction are those of 114 (Xenos 19, Terrans 19, Taklons/Geodens/Lantids/Firaks/Nevlas/Ivits 10,
BalTaks/Bescods/Gleens/Itars/Ambas/HadschHallas 9, Tinkeroids/Moweyds/SpaceGiants/Darkanians 8).

Which source `fc19671c4278` is: the build id is a SHA-256 over the engine sources (`gaia-rl/build.rs:23–55`:
`gaia-engine/src`, `gaia-engine/data`, both crates' manifests, `gaia-rl/src`, `Cargo.lock`, `rust-toolchain.toml`).
Recomputed in the bot turn with the same formula over the work tree at HEAD (47 files, engine paths clean in
`git status`, last engine commit 966e9ea): **`fc19671c4278`**. So the lab replay ran on exactly the 966e9ea
source — the direct build evidence the 115a page did not carry.

## Reading (HANDOFF 1 order)

- All four pre-registered items pass: 46/46 strict replays, 46 six-round, 13,841 decisions, replay engine
  `fc19671c4278` ≠ `36d2e007`. The 114 data stay usable on the new engine (BC export, PPO initial data).
- ③ Scope, as registered: one chosen action per decision is compared. A change that reorders or alters other
  candidates while leaving the chosen one at its index would pass here. Identity of the flag-off candidate lists
  rests on 115c (golden compare of the full lists, old build vs new), which has no result yet.
- ③ Coverage: `index` takes complete games only, so the two crash games of 114 (pair-012, pair-037;
  14,176 − 13,841 = 335 decisions) are not replayed here. The crash state with the 17,318-candidate lists is
  in 115a (counts) and 115c (contents), not in this job.
- The manifest is checked on `fc19671c4278`; the work tree engine is still `36d2e007`, so `export` /
  `iter_samples` on this manifest from the work tree are refused until the work tree is rebuilt (owner command)
  (a manifest is valid only on the engine that checked it; E131).
- Timing: 20 s for 46 replays; nothing to read.

No code or deployment change. The flag stays off by default and no spec turns it on. Lab queue after this:
115c-fed-off-golden-114 (queued, no result page yet).

## Proposal (user decision, nothing queued)

- (ㄱ) Wait for 115c (already queued, minutes, no decision needed). A mismatch there → fix or revert 966e9ea in
  a bot turn.
- (ㄴ) After 115c passes: a new all_tier spec with the flag in `env` (one bot turn). More collection itself
  stays on hold (E134 「ㄷ은 대기」).
- (ㄷ) Rebuild the work tree engine (`cd ~/projects/gaia-work/gaia-rl && .venv/bin/maturin develop --release`,
  owner command, minutes) when bot-turn tools must run on the new engine; then manifests checked on
  `fc19671c4278` (this one) are the ones to use.
- (ㄹ) Before flag-on games feed BC/PPO: collection and policy play must use the same flag setting (flag-on
  lists are shorter than the 114 data).
Bot recommendation: (ㄱ) → (ㄴ); (ㄷ) when needed; (ㄹ) with the next collection.
