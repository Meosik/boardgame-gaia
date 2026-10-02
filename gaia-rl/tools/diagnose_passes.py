"""Record every Pass decision of a teacher self-play game, to diagnose early passing.

For each Pass the teacher chose: round, resources, power bowls, the Pass score and the
best-ranked non-pass alternatives (score, reason, action). At game end: final VP,
structures, colonized planet types and leftover resources per seat. Read-only: the
teacher tree is chosen by PYTHONPATH and is not edited.

Run from gaia-rl/ (see the module docstring of tools/ai_worker.py for PYTHONPATH):
  .venv/bin/python tools/diagnose_passes.py --seed geo-quartet-24 --level easy --output runs/x.json
"""
import argparse
import json
import time
from collections import Counter

LEVELS = {'easy': (0, 2), 'normal': (2, 1)}   # (comparisons, horizon incomes), as in ai_worker


def action_label(decision):
    action = decision.get('action', {})
    kind = action.get('type', '?') if isinstance(action, dict) else str(action)
    detail = {k: v for k, v in action.items() if k != 'type'} if isinstance(action, dict) else {}
    return f"{decision.get('phase')}:{kind} {json.dumps(detail, sort_keys=True)[:160]}"


def kind_of(decision):
    action = decision.get('action', {})
    return action.get('type', '?') if isinstance(action, dict) else str(action)


def player_summary(state, index):
    player = state['players'][index]
    hexes = state['board']['hexes']
    types = Counter(hexes[s['hex']]['planet']['planet_type'] for s in player['structures']
                    if hexes.get(s['hex'], {}).get('planet'))
    kinds = Counter(s['kind'] if isinstance(s['kind'], str) else next(iter(s['kind']))
                    for s in player['structures'])
    resources = {k: player['resources'][k] for k in ('ore', 'credits', 'knowledge', 'qic')}
    power = {k: player['resources']['power'][k] for k in ('bowl1', 'bowl2', 'bowl3', 'gaia_bowl')}
    return {'faction': player['faction'], 'vp': player['vp'], 'resources': resources, 'power': power,
            'structures': dict(kinds), 'planet_types': dict(types),
            'research': player['research_tracks'], 'federations': len(player['federation_tokens'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', required=True)
    parser.add_argument('--level', choices=sorted(LEVELS), default='easy')
    parser.add_argument('--output', required=True)
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--symmetric-pass', action='store_true',
                        help='Apply tools/teacher_patches.py symmetric_pass')
    parser.add_argument('--calibrated', action='store_true',
                        help='Apply tools/teacher_patches.py calibrated_value (GAIA_VALUE_WEIGHTS)')
    parser.add_argument('--geodens-guide', action='store_true',
                        help='Apply tools/teacher_patches.py geodens_guide (includes symmetric_pass)')
    args = parser.parse_args()

    import fast_teacher
    fast_teacher.install()
    import budget_teacher
    from gaia_rl import Environment
    from four_factions.timed import TimedPreparationTeacher

    comparisons, horizon = LEVELS[args.level]
    budget_teacher.install(comparisons)
    budget_teacher.set_horizon(horizon)
    env = Environment(args.seed, 2000)
    if args.calibrated:
        from teacher_patches import calibrated_value as factory
    elif args.geodens_guide:
        from teacher_patches import geodens_guide as factory
    elif args.symmetric_pass:
        from teacher_patches import symmetric_pass as factory
    else:
        factory = TimedPreparationTeacher
    teacher = factory(args.seed, bgg_openings=True, shared_factions=True)
    teacher.bind(env)
    snapshot = json.loads(env.snapshot_json())
    passes, choices, started = [], Counter(), time.monotonic()
    from collections import defaultdict
    thinking = defaultdict(list)
    while not env.is_terminal():
        tick = time.monotonic()
        decision_id, index = teacher.choose(snapshot)
        thinking[snapshot['state']['players'][snapshot['player']]['faction']].append(time.monotonic()-tick)
        chosen = snapshot['candidates'][index]
        seat = snapshot['player']
        faction = snapshot['state']['players'][seat]['faction']
        action = chosen.get('action', {})
        kind = action.get('type') if isinstance(action, dict) else str(action)
        choices[(faction, kind)] += 1
        if kind == 'Pass':
            scores = teacher.last_scores
            ranked = sorted(range(len(scores)), key=lambda i: scores[i][0], reverse=True)
            alternatives = [i for i in ranked
                            if snapshot['candidates'][i].get('action', {}).get('type') != 'Pass']
            pass_scores = [scores[i][0] for i in range(len(scores))
                           if snapshot['candidates'][i].get('action', {}).get('type') == 'Pass']
            passes.append({
                'step': snapshot['steps'], 'round': snapshot['state']['round'], 'seat': seat,
                'faction': faction, 'player': player_summary(snapshot['state'], seat),
                'candidates': len(scores),
                'candidate_types': dict(Counter(c.get('action', {}).get('type', c.get('phase'))
                                                for c in snapshot['candidates'])),
                'pass_score_max': max(pass_scores) if pass_scores else None,
                'selected': (teacher.last_audit or {}).get('selected'),
                'alternatives': [{'score': scores[i][0], 'reason': str(scores[i][1])[:200],
                                  'action': action_label(snapshot['candidates'][i])}
                                 for i in alternatives[:args.top]],
                # The best candidate of every action type, so an absent type is visible.
                'best_by_type': {kind_of(snapshot['candidates'][i]): {
                    'score': scores[i][0], 'reason': str(scores[i][1])[:300],
                    'action': action_label(snapshot['candidates'][i])}
                    for i in reversed(ranked)}})
        before = snapshot
        env.step(decision_id, index)
        snapshot = json.loads(env.snapshot_json())
        teacher.observe(before, index, snapshot)
    state = snapshot['state']
    phase = state['phase']
    final = dict(phase['Ended']['final_scores']) if isinstance(phase, dict) and 'Ended' in phase else {}
    result = {'seed': args.seed, 'level': args.level, 'seconds': round(time.monotonic()-started, 1),
              'final_scores': {state['players'][i]['faction']: final.get(i) for i in range(4)},
              'end': [player_summary(state, i) for i in range(4)],
              'thinking': {f: {'decisions': len(v), 'mean': round(sum(v)/len(v), 2), 'max': round(max(v), 1)}
                           for f, v in thinking.items()},
              'choices': {f'{f}:{k}': n for (f, k), n in sorted(choices.items())},
              'passes': passes}
    with open(args.output, 'w') as out:
        json.dump(result, out, indent=1, ensure_ascii=False)
    print(json.dumps({'seed': args.seed, 'level': args.level, 'seconds': result['seconds'],
                      'final_scores': result['final_scores']}))


if __name__ == '__main__':
    main()
