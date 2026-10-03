# Cycle 024 — Parallel comparisons and a hard level

## Hard level (opt-in per AI game)
Cycle 023's 4 comparisons (+13.1 VP/seat) cost ~1.9× decision time, beyond the agreed normal
target (mean 2–3 s, 5 s cap). `tools/ai_worker.py` gains `hard` (4 comparisons, one-income
horizon, 20 s cap, below the server's 30 s guard). Rooms store the level chosen at creation;
the create-room view offers "AI 3명과 대전 (어려움)". Normal stays as agreed.

## Parallel comparisons (`tools/parallel_search.py`, `GAIA_AI_PARALLEL=N`)
Each comparison of a decision clones the search's policies and changes no parent state, so
the first `budget` comparisons are computed in N forked processes before the unchanged
sequential search runs and takes the finished results. A result is used only for the same
position, goal, first move and policy memory; otherwise the ordinary call runs.

Equivalence (`tools/test_parallel_search.py`, geo-quartet-9840, 4 comparisons, 90 decisions of
which 74 searched, including a second factory install as for a second AI room): decisions,
selected plans and plan values identical. Wall time 264.5 s → 170.2 s with 3 processes on this
4-core container (1.55×); the root ranking and plan bookkeeping stay sequential.

Pending: the capped A/B (normal: 2 vs 4 comparisons under the 5 s cap) decides whether normal
can move to 4 comparisons with parallel processes.
