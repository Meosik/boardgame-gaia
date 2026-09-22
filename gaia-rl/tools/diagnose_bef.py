"""Native paid research/build comparisons after the four-model invariant gate."""
import argparse
import copy
from pathlib import Path

from validate_bef import MODELS
from validate_bc import representative, structure, successor, write_json
from validate_bprime import compare, opportunity_fixture


def evaluate(before: dict, actor: int, action: dict, label: str, kind: str) -> dict:
    after = successor(before, actor, action)
    values = {}
    for name, model in MODELS.items():
        row = compare(before, after, actor, label, kind, True, model=model)
        assert abs(row['delta']-sum(v['delta'] for v in row['changed_breakdown'].values())) < 1e-8
        values[name] = {key: row[key] for key in ('before', 'after', 'delta', 'changed_breakdown',
                                                 'before_breakdown', 'after_breakdown')}
    return {'label': label, 'kind': kind, 'round': before['round'], 'action': action,
            'before_state': before, 'after_state': after, 'values': values}


def generic_research() -> list[dict]:
    rows = []
    for round_number in (1, 3):
        before, actor = representative(round_number)
        before['players'][actor]['resources']['knowledge'] = 4
        for track in ('Terraforming', 'Navigation', 'ArtificialIntelligence', 'GaiaProject',
                      'Economy', 'Science'):
            action = {'type': 'ResearchAdvance', 'track': track}
            rows.append(evaluate(before, actor, action, track, 'generic research'))
    return rows


def special_state(round_number: int, kind: str) -> tuple[dict, int]:
    target, distance = {'navigation': ('Desert', 2), 'terraforming': ('Terra', 1),
                        'gaia': ('Transdim', 1)}[kind]
    state, actor = opportunity_fixture(target=target, distance=distance, count=1)
    state['round'] = round_number
    state['board']['spaceship_tiles'] = {}
    player = state['players'][actor]
    player['booster'] = None
    player['resources'].update(ore=15, credits=30, knowledge=4, qic=0)
    return state, actor


def special_research() -> tuple[list[dict], list[dict]]:
    cases, differences = [], []
    for round_number in (1, 3):
        for kind, track in (('navigation', 'Navigation'), ('terraforming', 'Terraforming'),
                            ('gaia', 'GaiaProject')):
            before, actor = special_state(round_number, kind)
            action = {'type': 'ResearchAdvance', 'track': track}
            row = evaluate(before, actor, action, kind, 'special research')
            row['planet'] = {'navigation': 'distance-2 home / QIC0',
                             'terraforming': 'only 3-step Terra',
                             'gaia': 'one Transdim; reference only'}[kind]
            cases.append(row)
            economy = evaluate(before, actor, {'type':'ResearchAdvance', 'track':'Economy'},
                               'economy on '+kind+' state', 'economy control')
            differences.append({'round':round_number, 'track':kind,
                'economy':economy, 'track_case':row,
                'track_minus_economy':{name:row['values'][name]['delta']-economy['values'][name]['delta']
                                       for name in MODELS}})
    return cases, differences


def buildings() -> list[dict]:
    rows = []
    for round_number in (1, 3, 5):
        before, actor = representative(round_number)
        home = copy.deepcopy(before)
        home['board']['hexes']['1,0']['planet']['planet_type'] = 'Desert'
        rows.append(evaluate(home, actor, {'type':'Build','coord':'1,0'}, 'home mine', 'building'))
        rows.append(evaluate(before, actor, {'type':'PowerAction','id':6,'coord':'1,0'},
                             'one-terraform + mine', 'building'))
        lab = copy.deepcopy(before)
        structure(lab, actor, '0,0', 'TradingStation')
        rows.append(evaluate(lab, actor, {'type':'Upgrade','coord':'0,0','to':'ResearchLab',
            'tech_tile_choice': {'kind':'Standard','tile':3,'advance_track':'Terraforming'}},
            'station-to-lab + std-03 + Terraforming', 'building'))
    return rows


def run(output: Path, gate: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    from json import loads
    summary = loads(gate.read_text())
    if any(count.get('fail', 0) for count in summary['counts'].values()) or summary['token_sign_failures']:
        raise ValueError('Invariant gate failed; paid follow-up comparisons are not authorized')
    research = generic_research()
    special, differences = special_research()
    build = buildings()
    record = {'generic_research':research, 'special_research':special, 'buildings':build,
              'economy_differences':differences, 'invariant_gate':str(gate), 'games_run':0,
              'notes':['All actions use the native successor and pay their real costs.',
                       'Special controls use exactly the same pre-action state.',
                       'Transdim Gaia 0->1 is reference only: no sign expectation.',
                       'No A/B, teacher selection or new game execution.']}
    write_json(output/'downstream.json', record)
    names = list(MODELS)
    lines = ['| 행동 ΔVP | R | '+' | '.join(names)+' |', '|---|---:|'+'---:|'*len(names)]
    for section, rows in (('유료 진보', research), ('기회 상태 유료 진보', special),
                          ('건설', build)):
        lines += ['', '| '+section+' | | '+' | '.join('' for _ in names)+' |']
        for row in rows:
            lines.append('| '+row['label']+' | '+str(row['round'])+' | '+
                         ' | '.join(f'{row["values"][name]["delta"]:+.6f}' for name in names)+' |')
    lines += ['', '| 경제1→2 대비 트랙 ΔVP 차이 | R | '+' | '.join(names)+' |']
    for row in differences:
        lines.append('| '+row['track']+' − Economy | '+str(row['round'])+' | '+
                     ' | '.join(f'{row["track_minus_economy"][name]:+.6f}' for name in names)+' |')
    (output/'downstream.md').write_text('\n'.join(lines)+'\n')
    print({'paid':len(research),'special':len(special),'buildings':len(build),
           'economy_differences':len(differences),'games_run':0})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--gate',type=Path,required=True)
    args=parser.parse_args()
    run(args.output,args.gate)
