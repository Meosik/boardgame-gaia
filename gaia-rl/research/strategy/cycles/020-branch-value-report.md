# Branch value — 1000 training / 368 validation positions (10 of 37 seeds held out)

| Evaluator | Pair accuracy | Best branch | Regret (VP margin) | Pairs |
|---|---:|---:|---:|---:|
| potential (hand weights) | 0.533 | 0.361 | 7.81 | 1883 |
| branch weights (this fit) | 0.514 | 0.348 | 7.95 | 1883 |
| outcome weights (cycle 019) | 0.526 | 0.367 | 8.02 | 1883 |
| always the recorded move | — | 0.367 | 7.69 | — |
| always the rank1 move | — | 0.315 | 7.90 | — |

| Branch kind | Mean loss vs best branch | Positions |
|---|---:|---:|
| random | 8.51 | 323 |
| rank1 | 7.90 | 89 |
| rank2 | 8.92 | 351 |
| rank3 | 8.35 | 284 |
| rank4 | 10.23 | 51 |
| recorded | 7.69 | 368 |

## Branch-fitted weights (teacher uses 1.0)

| Term | 1-5 | 6 |
|---|---:|---:|
| advanced | 2.90 | 0.07 |
| expansion | 0.02 | 0.00 |
| forming | 0.48 | 0.00 |
| gaia | 0.27 | 0.00 |
| income | 0.24 | 0.00 |
| materials | 0.11 | 0.00 |
| passed_booster | -0.78 | 0.00 |
| pending_booster | -0.27 | 0.00 |
| pending_pass_vp | 0.25 | 0.09 |
| power | 0.17 | 0.00 |
| research_options | -0.22 | 0.00 |
| research_vp | 0.03 | 0.62 |
| ships | 0.45 | 0.00 |
| standings | 0.27 | 0.29 |
| structures | -0.10 | 0.00 |
| taklons_neighbours | 0.19 | 0.00 |
| terminal_power | 0.87 | -0.06 |
| terminal_resources | 0.31 | 0.44 |
| tile_options | 1.30 | 0.00 |
| vp | 0.31 | 0.17 |

Saved weights refitted on all 1368 positions to datasets/branch-weights.json
