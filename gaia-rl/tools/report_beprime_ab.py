"""Replay completed paired games and report observable A/B actions, without new games."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import statistics

from gaia_rl import Environment


POWER_ACTIONS = {4: '7돈', 3: '2광석', 5: '2지식', 6: '1테라'}
RESOURCE_KEYS = ('ore', 'credits', 'knowledge', 'qic')


def structures(player):
    return {row['hex']: row['kind'] for row in player['structures']}


def combo(player):
    counts = Counter(structures(player).values())
    labels = [('Academy', 'AC'), ('PlanetaryInstitute', 'PI'),
              ('ResearchLab', 'RL'), ('TradingStation', 'TS'), ('Mine', 'M')]
    return '+'.join(f'{counts[kind]}{name}' for kind, name in labels if counts[kind]) or '없음'


def action_label(action):
    kind = action['type']
    if kind == 'Build':
        return f'광산 {action["coord"]}'
    if kind == 'Upgrade':
        return f'{action["to"]} {action["coord"]}'
    if kind == 'PowerAction':
        return f'공용 {action["id"]} {action.get("coord") or ""}'.strip()
    if kind == 'FreeAction':
        return f'프리 {action["kind"]}×{action.get("count", 1)}'
    if kind == 'ResearchAdvance':
        return f'연구 {action["track"]}'
    if kind == 'Pass':
        return '패스'
    return kind


def replay(path):
    result = json.loads((path/'result.json').read_text())
    if not result['complete']:
        return None
    environment = Environment(result['seed'])
    seats = {seat: {'faction': faction, 'arm': 'A' if seat in result['a_seats'] else 'B',
                    'r1_actions': [], 'r1_combo': None, 'mines': Counter(),
                    'terraform': Counter(), 'labs': Counter(), 'tech': Counter(),
                    'free': Counter(), 'public': Counter(), 'passes': defaultdict(list),
                    'federations': 0}
             for seat, faction in enumerate(result['factions'])}
    last_round = 0
    with gzip.open(path/'decisions.jsonl.gz', 'rt') as trace:
        for line in trace:
            row = json.loads(line)
            before = json.loads(environment.snapshot_json())
            if row['decision_id'] != before['decision_id'] or row['seat'] != before['player']:
                raise ValueError(f'Trace diverged: {path}, step {row["step"]}')
            seat, rnd = row['seat'], before['state']['round']
            action = before['candidates'][row['index']]['action']
            actor_before = before['state']['players'][seat]
            entry = seats[seat]
            if rnd == 1:
                entry['r1_actions'].append(f'{row["step"]}:{action_label(action)}')
            if action['type'] == 'Pass' and rnd in range(1, 7):
                resources = actor_before['resources']
                entry['passes'][rnd].append({key: resources[key] for key in RESOURCE_KEYS} |
                                             {key: resources['power'][key] for key in ('bowl1','bowl2','bowl3')})
            environment.step(row['decision_id'], row['index'])
            after = json.loads(environment.snapshot_json())
            actor_after = after['state']['players'][seat]
            if rnd in range(1, 7):
                prior, later = structures(actor_before), structures(actor_after)
                entry['mines'][rnd] += sum(kind == 'Mine' and prior.get(coord) != 'Mine'
                                           for coord,kind in later.items())
                entry['labs'][rnd] += sum(kind == 'ResearchLab' and prior.get(coord) != kind
                                          for coord,kind in later.items())
                for tile in set(actor_after['tech_tiles'])-set(actor_before['tech_tiles']):
                    entry['tech'][f'{rnd}:std-{tile:02d}'] += 1
                for tile in set(actor_after['advanced_tech_tiles'])-set(actor_before['advanced_tech_tiles']):
                    entry['tech'][f'{rnd}:adv-{tile:02d}'] += 1
                if action['type'] == 'PowerAction':
                    identifier = action['id']
                    entry['public'][POWER_ACTIONS.get(identifier, f'id{identifier}')] += 1
                    if identifier == 6:
                        entry['terraform'][rnd] += 1
                if action['type'] == 'FreeAction':
                    free_kind = action['kind']
                    mapped = {'QicToOre':'QIC→광석', 'KnowledgeToCredit':'지식→크레딧',
                              'OreToCredit':'광석→크레딧'}
                    if free_kind in mapped:
                        entry['free'][mapped[free_kind]] += action.get('count', 1)
                    elif free_kind.startswith('PowerTo'):
                        entry['free']['파워→자원'] += action.get('count', 1)
                if action['type'] == 'FormFederation':
                    entry['federations'] += 1
            if last_round == 1 and after['state']['round'] != 1:
                for current in after['state']['players']:
                    seats[current['player_id']]['r1_combo'] = combo(current)
            last_round = after['state']['round']
    terminal = json.loads(environment.snapshot_json())['state']
    for seat,entry in seats.items():
        player = terminal['players'][seat]
        entry['tracks'] = player['research_tracks']
        entry['buildings'] = len(player['structures'])
        entry['federations_final'] = len(player['federation_tokens'])+len(player['gray_federation_tokens'])
        if entry['r1_combo'] is None:
            raise ValueError(f'Missing round-one boundary: {path}')
        for key in ('mines','terraform','labs','tech','free','public'):
            entry[key] = dict(entry[key])
        entry['passes'] = dict(entry['passes'])
    return {'path': str(path), 'seed': result['seed'], 'pair': int(path.parent.name.split('-')[1]),
            'game': int(path.name.split('-')[1]), 'seats': seats}


def aggregate(games):
    groups = defaultdict(list)
    for game in games:
        for entry in game['seats'].values():
            groups[(entry['faction'],entry['arm'])].append(entry)
    result = {}
    for (faction,arm),entries in sorted(groups.items()):
        counts = {key: Counter() for key in ('r1_combo','mines','terraform','labs','tech','free','public')}
        tracks = defaultdict(list)
        passes = defaultdict(lambda: defaultdict(list))
        for entry in entries:
            counts['r1_combo'][entry['r1_combo']] += 1
            for key in ('mines','terraform','labs','tech','free','public'):
                counts[key].update(entry[key])
            for track,level in entry['tracks'].items():
                tracks[track].append(level)
            for rnd,observations in entry['passes'].items():
                for observation in observations:
                    for key,value in observation.items():
                        passes[rnd][key].append(value)
        result[f'{faction}:{arm}'] = {
            'games':len(entries),
            **{key:dict(value) for key,value in counts.items()},
            'tracks':{key:statistics.mean(values) for key,values in tracks.items()},
            'federations_mean':statistics.mean(e['federations_final'] for e in entries),
            'buildings_mean':statistics.mean(e['buildings'] for e in entries),
            'passes':{str(rnd):{key:statistics.mean(values) for key,values in data.items()}
                      for rnd,data in passes.items()}}
    return result


def sequence_distance(left, right):
    a,b = [part.split(':',1)[1] for part in left],[part.split(':',1)[1] for part in right]
    previous = list(range(len(b)+1))
    for index,item in enumerate(a,1):
        current = [index]
        for column,other in enumerate(b,1):
            current.append(min(previous[column]+1,current[column-1]+1,
                               previous[column-1]+(item != other)))
        previous=current
    return previous[-1]


def representative_pairs(games):
    by_pair=defaultdict(dict)
    for game in games:
        by_pair[game['pair']][game['game']]=game
    rows=[]
    for pair,record in by_pair.items():
        if set(record)!={0,1}:
            continue
        first,second=record[0],record[1]
        for seat in range(4):
            one,two=first['seats'][seat],second['seats'][seat]
            a,b=(one,two) if one['arm']=='A' else (two,one)
            rows.append({'pair':pair,'seed':first['seed'],'seat':seat,'faction':a['faction'],
                         'distance':sequence_distance(a['r1_actions'],b['r1_actions']),
                         'A':a['r1_actions'],'B':b['r1_actions'],
                         'A_combo':a['r1_combo'],'B_combo':b['r1_combo']})
    rows.sort(key=lambda row:(-row['distance'],row['pair'],row['seat']))
    selected=[]
    for row in rows:
        if row['pair'] not in {found['pair'] for found in selected}:
            selected.append(row)
        if len(selected)==2:
            break
    return selected


def run(root, output):
    paths=sorted((root/'off').glob('pair-*/game-*'))
    games=[replay(path) for path in paths if (path/'result.json').exists()]
    games=[game for game in games if game is not None]
    record={'games_replayed':len(games),'metrics':aggregate(games),
            'representative':representative_pairs(games)}
    output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print({'games_replayed':len(games),'groups':len(record['metrics'])})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.root,args.output)
