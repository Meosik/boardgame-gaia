# Cycle 025 — The live hard level against normal

A: `teacher-a-search2-h1-geodens-cap5.json` (live normal: 2 comparisons, 5 s cap).
B: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, 20 s cap).
12 fresh geo-quartet seeds (148191 … 166856) × 2 seat-swapped games, laptop, `--jobs 4`.

| Faction | Pairs | B−A VP | 95% CI |
|---|---:|---:|---|
| Geodens | 12 | +22.5 | [+13.5, +31.5] |
| Taklons | 12 | +26.1 | [+17.2, +34.9] |
| Terrans | 12 | +23.2 | [+11.6, +34.9] |
| Xenos | 12 | +12.6 | [−1.8, +27.0] |
| **Seat mean** | 12 | **+21.1** | **[+14.9, +27.3]** |

No error, timeout or fallback games. Decision time per move:

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A normal | 2625 | 1.88 s | 0.70 s | 5.11 s | 16.2 s |
| B hard | 2621 | 4.87 s | 1.74 s | 16.94 s | 33.1 s |

Hard is clearly stronger: more than cycle 023's uncapped 4 comparisons (+13.1) because here it
plays against the 5 s-capped normal, which loses comparisons on big decisions. It costs 2.6×
the mean time and a p90 of 17 s (laptop, 4 games at once; the server also runs comparisons in
parallel).

The 20 s cap is checked between comparisons, so a comparison already running finishes: the
max was 33.1 s, above the server's 30 s hung-worker guard, which would have restarted the
worker and played a fallback move. `gaia-server/src/ai.rs` `guard_timeout` now gives hard at
least 60 s.

Normal stays as agreed (mean 2–3 s, 5 s cap); hard remains the opt-in per room. Whether the
default should move closer to hard is a time-versus-strength choice for the user.
