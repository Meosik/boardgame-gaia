# Cycle 061 — all rules + setup_one_near, same teacher in all four seats (stopped)

A = B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-fix-setup-cap20.json` —
when_all_tech_fix (059 B) plus setup_one_near: once one of the faction's structures lies within 2 hexes of an
opponent, later starting places are no longer held to the opponent's side (user, 2026-10-16: "교역소 올릴 건물만
인접해있으면 되는건데").
Purpose (user, 2026-10-16 "점수 좀 낮더라도 규칙을 다 넣어보고 … A 섯인 종족 없이 … 한 두겜만 끝까지"): watch
replays of the full rule stack playing itself, not an A/B. 2 seeds (geo-quartet-683063, 683209) × 2 games, all 6 rounds.

Stopped by the user after 48 minutes (2026-10-16 16:41 → 17:29, "일단 지금 실험 멈추고"); `teacher_ab` ended with
exit code −15 (SIGTERM). No result; the four game folders under `runs/lab-061-all-rules-selfplay-full/` hold partial
games. The queue entry was switched to kind `external` so the lab does not rerun it.

Nothing was measured. The teacher ran without import or startup errors for 48 minutes, so the setup_one_near factory
loads and plays. Base stack decision unchanged (proposal from 060: back to vm_lf_ts_ships). Next: lab 062
(vm_lf_ts_ships 20 s vs 40 s cap).
