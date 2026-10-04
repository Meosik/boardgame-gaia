# Cycle 026 — Booster look-ahead

A: `teacher-a-search2-h1-geodens.json` (normal teacher, 2 comparisons, no cap).
B: `teacher-a-search2-h1-booster.json` (`teacher_patches.booster_lookahead`: when the current
choice is a booster pick, up to 3 other boosters are compared through the next round's income).
Seeds geo-quartet-126275 … 147743 (12) × 2 seat-swapped games; run by hand on the laptop.

| Faction | Pairs | B−A VP | 95% CI |
|---|---:|---:|---|
| Geodens | 12 | +2.2 | [−5.5, +9.8] |
| Taklons | 12 | +2.3 | [−5.9, +10.6] |
| Terrans | 12 | −1.8 | [−9.0, +5.5] |
| Xenos | 12 | −6.3 | [−20.4, +7.7] |
| **Seat mean** | 12 | **−0.9** | **[−6.4, +4.6]** |

Decision time: A mean 4.26 s (median 1.06, p90 10.72, max 332.1); B mean 4.54 s (median 1.52,
p90 12.50, max 198.6). No error, timeout or fallback games.

Rejected: no measurable gain for +7% decision time. Booster choice already gets its ordinary
comparisons; looking one round further does not change outcomes measurably at this sample.
The patch stays opt-in and unused; the rare parallel+booster divergence is moot while unused.
