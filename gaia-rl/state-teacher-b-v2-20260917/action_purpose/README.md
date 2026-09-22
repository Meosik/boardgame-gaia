# Action-purpose pilot (2026-09-11)

Approved scope: correct natural Gaia / TF Mars credit costs, then compare purposeful
conversion/burn, pass opportunity, research-before-build and funded ship entry against
the existing ContextResearch baseline. This is an isolated teacher experiment, NOT
PPO learning, a rules ban, a VP penalty, or production model promotion.

## Rules and frozen evidence

- Natural Gaia entry cost is additive to range QIC; own reserved former-converted
  Transdim exemption and faction costs remain. Engine regression tests cover this.
- TF Mars 3-credit action validates its mine against the POST-activation balance.
  Ordinary mines need 5 combined credits; asteroid mining still costs only activation.
- Both control and candidate use the same rebuilt native engine. `costs.py` adapts
  direct natural-Gaia and research forecast costs without editing pinned historical
  strategy files. All old weights/replays/results are retained; no version-check bypass.
- Native `Environment.fork` takes a real legal candidate and runs the ordinary step
  on a clone, with stale-id/step-limit checks. It does not mutate the real episode.

## Preregistered cumulative ablations

0. CorrectedContextTeacher: existing control + mandatory Gaia cost adaptation.
1. Replace threshold-only conversion/burn priority with one/two free actions followed
   by an actual newly legal productive action, using native branch candidates.
   Prefer a good already-funded main action to paying conversion overhead. Preserve
   Xenos' existing low-token 1 ore -> bowlIII token recovery exception.
2. Lower Pass relative to positive available main actions, never resource stock itself.
   This may yield IDENTICAL decisions to stage1: the control's main-action score offset
   already usually beats Pass. Treat it as an invariant/diagnostic, not claimed learning.
3. Bounded bonus for legal Terraforming/Navigation research that reduces the cost of
   a currently fundable next mine. Research is still a main turn; rivals may intervene.
   Not full multi-turn search; no hard track priorities or inefficient-build ban.
4. Ship-entry value uses resources AFTER paying actual native entry cost. Check shared
   slot availability and a concrete funded Rebellion tech, Twilight lab, TF Mars mine
   or Eclipse asteroid. Delayed income, other ship actions/artifacts and rivals' moves
   remain unmodeled; no claim of complete fleet strategy.

Internal coefficients are hypotheses, not observed learned values: prerequisite score
0.9*follow-up score minus net sacrifices; ore2.5/knowledge3/QIC3/credit1; lost token2;
extra4 per new deficit below4tokens before R6; crossing4knowledge down adds4;
spent bowlIII0.5; credit liquidation extra3 knowledge/1ore;1 per conversion step.
Default unsupported conversion -12, except preserved Xenos recovery. Max24 native
previews per decision; reserve6 for ship previews at stage4. Chain support restricted
to QIC->ore->credit and burn->burn/power conversion. Count>1 conversion candidates
not favored; one-at-a-time execution remains legal. Branch score does not include
recursive lookahead, and a different best follow-up may be chosen on the next step.
Research bonus capped12 based ore2.5/QIC4 saved. Ship base20 + funded followup42..48
minus4 per previously explored ship; zero funding is not a hard prohibition.

## Evaluation / learning gate

First batch fixed BEFORE outcomes: prior2 maps x Xenos/HH x stages0..4 =20 games,
identical setup/opponent RNG scheme under corrected rules. No retuning on these
outcomes; no historical-score equivalence. Save all actions, top3 alternatives,
resources, preview counts, exact debit audits, stage metrics and snapshots/hashes.

Compare stage increments, completion, focal scores by faction, conversion/burn counts,
terraform ore, passes with legal research and ship entry. Fewer actions alone is NOT
an improvement if scores fall. Positive candidates need separate maps before any BC
labels are selected. If nothing improves, retain control and do NOT train worse labels.
No unattended long training, historical checkpoint overwrite or deployment in this pilot.

## Remaining limitations

Only Xenos/HH receive strategy evaluation; other players are explicitly random.
Small reused-map trials cannot establish general playing strength. Known historical
PPO liquidation loops are not repaired just by changing this teacher: updated model
training is a separate gated phase. Shared power action scoring and round forecasting
remain inherited approximations. No resource-stock penalty encourages dumping assets.
