# Cycle 116 — `expand+o` vs `expand+o2` on the 114 BC samples — structure-kind, planet-type and satellite outcome features, 5 game-level folds, command, no teacher verdict

A = `expand+o`: the flattened candidate encoding of `lab/scratch_bc114_variants.py` plus the 53 outcome columns of
E148 (`lab/scratch_bc114_outcome.py`: state right after the candidate minus the state before, the acting player's
numeric fields). B = `expand+o2`: A + 19 columns from the same `preview_state_json` pair — the mover's structure
count by kind (6: Mine, TradingStation, ResearchLab, PlanetaryInstitute, Academy, SpaceStation), the count of planets
the mover owns by planet type (12), the mover's satellite hexes (1) — 53 → 72 outcome columns
(`lab/scratch_bc114_o2.py`, extraction version 2, sorted key order). Queued 2026-11-14 by the user 「(a) 진행해」
(HANDOFF E149 (ㄴ) ②, E150). No games, not a teacher verdict: a feature-selection test for encoding v4.
Pre-registered report (queue note): per-game accuracy difference (o2 − o) mean, game-level t interval, games o2
better n/46, validation loss per fold, difference per quartet. Reading: interval includes 0 → "effect not confirmed";
above 0 → o2 becomes an encoding v4 candidate; below 0 → dropped. Checks: the `expand+o` arm must match E149's 34.6%
(otherwise a reproducibility problem, reported separately); a candidate count that differs from `outcome.npz` ends
the script with an error.
114 samples: 46 games, 13,841 decisions, quartet-stratified 5 folds by game (validation 11·11·10·8·6 games), width
64, lr 0.001, fixed 9 epochs (no epoch selection on the validation fold), same torch seed and batch order in both
arms, one torch seed. Host agentmaco, run in the bot work tree with the work tree venv (lab venv has no torch;
shards and `outcome.npz` exist only under the work tree `runs/`, engine 36d2e007), commit dcc4089 (script b073972),
2026-11-14 20:59:53 → 21:08:22 (8 min 29 s; extraction 269 s, training to 504 s). Result:
lab/results/116-bc114-o2-features-cv.md, metrics `runs/bc-114-o2/metrics.json` (work tree, outside git).

**Health: clean.** Exit code 0; no candidate-count mismatch against `outcome.npz` (the script would have stopped).
Reproducibility check passed: `expand+o` per game 0.3466 (E149 0.346), decision-weighted 0.3472 (E149 0.347);
validation loss per fold 2.234·2.186·2.207·2.257·2.190 against E149's 2.234·2.186·2.207·2.258·2.190 (fold 3 differs
by 0.001 in the third decimal, the other four are identical). The result page has no second-model review section
(command job).

## Accuracy per game (the pre-registered measure; no charge table — no games)

| Measure | `expand+o` (A) | `expand+o2` (B) | B−A | 95% CI | Games B > A |
|---|---:|---:|---:|---|---:|
| Per game (n = 46) | 34.7% | 35.1% | **+0.47 pt** | **[−0.05, +0.99]** | 25/46 (equal 4, worse 17) |
| Decision-weighted (13,841) | 34.7% | 35.2% | +0.44 pt | — | — |

| Fold | Val games | Val decisions | Loss A | Loss B | Acc A | Acc B | Acc B−A |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 11 | 3,242 | 2.234 | 2.234 | 36.0% | 36.9% | +0.9 |
| 1 | 11 | 3,409 | 2.186 | 2.188 | 35.1% | 35.8% | +0.7 |
| 2 | 10 | 3,137 | 2.207 | 2.234 | 33.5% | 33.3% | −0.2 |
| 3 | 8 | 2,302 | 2.257 | 2.261 | 33.1% | 33.3% | +0.2 |
| 4 | 6 | 1,751 | 2.190 | 2.171 | 35.7% | 36.3% | +0.6 |
| mean | | | 2.215 | 2.218 | | | |

| Quartet | Games | B−A | Games B > A |
|---|---:|---:|---:|
| geo | 2 | +1.7 pt | 2/2 |
| a | 10 | −0.7 pt | 2/10 |
| b | 9 | +1.2 pt | 6/9 |
| c | 9 | +0.1 pt | 4/9 |
| d | 8 | +0.9 pt | 5/8 |
| e | 8 | +0.8 pt | 6/8 |

Largest per-game gains +3.2·+3.4·+5.1 pt, largest losses −2.7·−2.6·−1.9 pt.

**Pre-registered reading: effect not confirmed** — the interval [−0.05, +0.99] includes 0. Exact two-sided sign test
on 25 better vs 17 worse (4 ties left out): p = 0.28 (bot computation, binomial). Validation loss does not go down:
lower in 1 fold of 5, equal in 1, higher in 3 (mean 2.215 → 2.218), where the E149 step `expand` → `expand+o` lowered
it in all 5 folds (by 0.08–0.15). The upper end of this run's 95% interval is about +1.0 pt — a bound of one
estimate from a single training seed, not a limit on the effect (debate 1/1 correction). For reference the 53 outcome
columns measured +2.3 pt [+1.6, +3.1] in E149; the two effects were not compared directly, so no ratio is claimed.

## Activation

- o2 columns present: 19 (smoke saw 18; `structure.SpaceStation` appeared in the full run). Candidate rows with any
  non-zero o2 column: 53.1% of 536,858 candidates (`candidate rows with an o2 change`, script output) — the features
  fire on about half of all candidates, so the flat result is not an empty input.
- The A arm reproduces E149 to the third decimal (above), so the comparison ran under the E149 conditions.

## Reading (HANDOFF 1 order)

- ① noise: the difference is at the edge (lower bound −0.05 pt), 25/17 by sign with p = 0.28, one torch seed, and
  the quartets disagree (a −0.7 pt with 2/10, the other five positive). Not a result in either direction; the upper
  bound of this run's interval is about +1 pt (single training seed, not an absolute limit).
- ② activation: fired (53.1% of candidate rows).
- ③ scope: part of o2 repeats what the candidate input already holds. The candidate encoding carries the action
  type and the upgrade target (`ACTION_FIELDS` `type`, `to`, `to.Academy`, `gaia_rl/encoding.py:10–12`; flattened to
  embedding ids in `expand`), and o already has the structure list length. So the structure-kind columns are
  mostly a restatement; the planet-type and satellite columns are the new information, and they did not move the
  loss. Not separated in this run (no per-group ablation).
- ④ interaction: 19 more input columns at fixed width 64, 9 epochs and 35–40 training games per fold; fold 2
  loss rises by 0.027 with o2. Whether network size or data amount limits what an extra feature can add is exactly
  the open (ㄷ) test of E149 — until that is read, "o2 does not help" is a statement about this setting only.
- ⑤ ⑥ ⑦: not applicable (no games, no source claim).
- Health and timing: clean, 8.5 minutes (extraction 269 s — o2 reads `players[].structures` and `board.hexes` from
  each preview JSON; E148's numeric-field extraction took 229 s).

No code or deployment change (scratch script only). Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Encoding v4 without o2: flattened candidate fields + the 53 outcome columns (module, `bc_train`,
  `OfflinePolicy`, export, PPO input; bot turns 2–3). o2 stays out because its effect is not confirmed; it can be
  retested later on the v4 code.
- (ㄴ) Network size and data amount on the same 5 folds first (E149 (ㄷ)): `expand+o` at width 64 vs 256 × all
  training games vs half, plus one `expand+o2` arm at width 256 to answer reading ④; fixed 9 epochs as the main
  comparison, per-epoch validation loss recorded for every arm (no selection). Debate 1/1 correction: half the
  games at 9 epochs also halves the optimizer updates (one step per 256-decision batch, `scratch_bc114_o2.py:159–178`),
  so each width also gets an update-matched arm: half the games, trained until exactly the optimizer step count of
  the all-games arm of the same fold, 9 × ceil(N_all/256), stopping mid-epoch (debate 2/2 correction: a fixed 18
  epochs does not match the count — games differ in decisions and the last partial batch also steps, so the real
  count is epochs × ceil(decisions/256)). The data-amount reading is all games (9 epochs) vs half (same step
  count), with half (9 epochs) reported beside it; the step count of every arm is recorded. About 7 arms × 5 folds ≈ 20–30 minutes → lab queue `kind: command` in the work tree venv, as 116.
- (ㄷ) More self-play collection (user: on hold), (ㄹ) BC vs teacher A/B (needs torch in the lab venv and a seed
  count), (ㅁ) PPO as is (Seraph, user).
Bot recommendation: (ㄴ) → (ㄱ). (ㄴ) is cheap and tells whether v4 should also change the network width, and
whether o2 deserves a second look, before the encoding is moved into real code.
