"""146 (E373, debate 1/1): why federation-plan-* goals fell to the budget check (teacher_patches.plan_affordable).

Replays the 146 game with the lab checkout's modules (the lab engine build; the work tree build diverges), installs the
fedplan factory so _guide matches the run, and at every decision whose log lists a dropped federation-plan goal
rebuilds fed_plan_goals and prints, per plan: budget (held + next income), cost (_plan_cost), shortfall and the power
tokens the conversion rule may use. Read only; nothing is written under gaia-lab.

  scratch_146_budget.py <game dir>
"""
import gzip
import json
import os
import sys
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python'), str(LAB/'baseline-teacher-20260917'), str(LAB/'tools')]


def main():
    game = Path(sys.argv[1])
    result = json.loads((game/'result.json').read_text())
    import teacher_patches as tp
    from gaia_rl import Environment
    tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier_prune_fedplan(result['seed'])
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows:
        dropped = [str(g) for g in row.get('menu_dropped') or [] if 'federation-plan' in str(g)]
        if dropped:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            player = state['players'][snapshot['player']]
            power = player['resources']['power']
            tokens = power['bowl3'] + power['bowl2']//2 + (3 if power.get('brainstone') == 'Area3' else 0)
            budget = tp._plan_budget(state, player)
            print(f"step {row['step']} seat {row['seat']} {player['faction']} R{state['round']} dropped {dropped}"
                  f" budget {budget} tokens {tokens}")
            for goal in tp.fed_plan_goals(snapshot):
                cost = tp._plan_cost(snapshot, goal)
                short = {k: n - budget.get(k, 0) for k, n in cost.items() if n > budget.get(k, 0)}
                print(f"   {goal.name}: ok={tp.plan_affordable(snapshot, goal)} multi={tp._menu_multi_step(snapshot, goal)}"
                      f" cost {cost} short {short}")
        env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
