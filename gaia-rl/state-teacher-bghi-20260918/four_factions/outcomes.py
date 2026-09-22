"""Post-game observations kept separate from forecasts and causal explanations."""
import gzip
import json

from four_factions.preparation import achieved, advance_goal, goal_from_dict
from research_plans.teacher import reached_horizon


def summarize(path, initial, terminal):
    pending, observed = [], []
    first_academies, federations = {}, {}

    def settle(snapshot):
        for item in tuple(pending):
            if reached_horizon(snapshot['state'], item['target_round']):
                observed.append({k: v for k, v in item.items() if k != 'goal_spec'} | {
                    'observed_goal_acquired': achieved(snapshot, item['player'], goal_from_dict(item['goal_spec'])),
                    'observed_round': snapshot['state']['round']})
                pending.remove(item)

    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            snapshot = row['snapshot']
            settle(snapshot)
            actor = snapshot['player']
            faction = snapshot['state']['players'][actor]['faction']
            action = snapshot['candidates'][row['index']]['action']
            # Only the recorded actor's paid action can fulfil a ship-use step.
            # Resource/structure milestones settle against subsequent snapshots.
            from dataclasses import asdict
            for item in pending:
                if item['player'] == actor:
                    item['goal_spec'] = asdict(advance_goal(snapshot, actor,
                                                          goal_from_dict(item['goal_spec']), action))
            if action['type'] == 'Upgrade' and isinstance(action.get('to'), dict) and 'Academy' in action['to']:
                first_academies.setdefault(faction, {'decision_id': snapshot['decision_id'],
                                                   'round': snapshot['state']['round'], 'kind': action['to']['Academy']})
            if action['type'] == 'FormFederation':
                federations.setdefault(faction, []).append(snapshot['state']['round'])
            audit = row.get('teacher_audit') or {}
            selected = next((p for p in audit.get('plans', []) if p['goal'] == audit.get('selected')), None)
            if selected and selected.get('goal_spec', {}).get('family') in (
                    'upgrade', 'research', 'colony', 'advanced', 'federations', 'sequence',
                    'expansion', 'explore', 'ship', 'lost-fleet', 'federation-race'):
                pending.append({'decision_id': snapshot['decision_id'], 'player': actor, 'faction': faction,
                                'goal': selected['goal'], 'goal_spec': asdict(advance_goal(
                                    snapshot, actor, goal_from_dict(selected['goal_spec']), action)),
                                'target_round': snapshot['state']['round']+2,
                                'predicted_goal_acquired': selected.get('goal_acquired')})
    settle(terminal)
    board, end = initial['state']['board']['hexes'], terminal['state']['board']['hexes']
    planets = {}
    for name in ('Gaia', 'Transdim'):
        coords = [c for c, cell in board.items() if cell['planet'] and cell['planet']['planet_type'] == name]
        planets[name] = {'original': len(coords), 'colonized': sum(bool(end[c]['structures']) for c in coords),
                         'formed': sum(end[c]['planet']['is_gaia_formed'] for c in coords)}
    return {'first_academies': first_academies, 'federation_rounds': federations,
            'original_planets': planets, 'selected_goal_outcomes': observed,
            'unresolved_goal_outcomes': len(pending),
            'qualification': 'Observed milestone agreement, not proof of causation or optimality'}
