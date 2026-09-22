"""Bdoubleprime/(c)/(b)/(b+c) state diagnostics. No games and no tuning."""
import argparse
from collections import Counter
import copy
from dataclasses import dataclass
import difflib
import json
from pathlib import Path

from validate_bprime import ROOT, EPSILON, CONVERSIONS, fixtures, compare
from validate_bdoubleprime import representative, successor, bdoubleprime, expected_sign, write_json
import state_evaluation_btripleprime as variant


@dataclass(frozen=True)
class Configured:
    b: bool = False
    c: bool = False

    def evaluate_state(self, state, actor, **kwargs):
        return variant.evaluate_state(state, actor, secured_planets=False,
            token_shortfall=self.b, remaining_income=self.c, **kwargs)


MODELS = {'B″': bdoubleprime, 'B″+c': Configured(c=True),
          'B″+b': Configured(b=True), 'B″+b+c': Configured(b=True, c=True)}


def structure(state, actor, coord, kind):
    p = state['players'][actor]
    existing = next((s for s in p['structures'] if s['hex'] == coord), None)
    if existing is None:
        p['structures'].append({'hex': coord, 'kind': kind})
    else:
        existing['kind'] = kind
    cell = state['board']['hexes'][coord]
    cell['planet']['owner'] = actor
    cell['structures'] = [{'owner': actor, 'kind': kind}]


def cap_state(round_number, count, *, stress=False):
    state, actor = representative(round_number)
    p = state['players'][actor]
    p['research_tracks']['economy'] = 3
    p['tech_tiles'] = [2]  # Native +1 charge income; economy adds 3 => four before booster.
    p['resources']['power'].update(bowl1=0, bowl2=0, bowl3=count, brainstone=None)
    if stress:
        structure(state, actor, '0,0', 'PlanetaryInstitute')
        p['booster'] = 4
    return state, actor


def invariants():
    for scenario, state, actor in fixtures():
        yield 'existing', scenario, state, actor, CONVERSIONS
    for round_number in (1, 3, 6):
        state, actor = cap_state(round_number, 4, stress=True)
        # Four normal III tokens make every resource conversion legal; no II tokens to burn.
        yield 'cap-boundary', 'cap-boundary', state, actor, CONVERSIONS[:-1]


def action_cases():
    for r in (1, 3, 6):
        s, a = representative(r)
        home = copy.deepcopy(s)
        home['board']['hexes']['1,0']['planet']['planet_type'] = 'Desert'
        yield '모행성 광산', 'positive' if r < 6 else None, home, a, {'type': 'Build', 'coord': '1,0'}, None
        yield '공용 1테라+광산', 'positive' if r == 1 else None, s, a, {'type': 'PowerAction', 'id': 6, 'coord': '1,0'}, None
        for tile in ((4, 3, 10) if r < 6 else ()):
            lab = copy.deepcopy(s)
            structure(lab, a, '0,0', 'TradingStation')
            label = f'교역소→연구소+std-{tile:02d}+진보'
            yield label, 'positive', lab, a, {
                'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                'tech_tile_choice': {'kind': 'Standard', 'tile': tile,
                    'advance_track': 'Terraforming' if tile == 3 else None}}, None
        for count in (3, 7):
            low = copy.deepcopy(s)
            low['players'][a]['resources']['power'].update(bowl1=0, bowl2=0, bowl3=count)
            yield f'가용{count}개: 공용 2토큰', 'positive' if count == 3 else 'negative', low, a, {
                'type': 'PowerAction', 'id': 7, 'coord': None}, None
        for count in (2, 3, 4):
            low = copy.deepcopy(s)
            low['players'][a]['resources']['power'].update(bowl1=count-2, bowl2=2, bowl3=0)
            yield f'가용{count}개: 일반 소각', 'negative', low, a, {
                'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1}, None
        third = copy.deepcopy(home)
        third['board']['hexes']['0,1']['planet']['planet_type'] = 'Desert'
        structure(third, a, '0,1', 'Mine')
        yield '세 번째 광산', None, third, a, {'type': 'Build', 'coord': '1,0'}, None
        economy = copy.deepcopy(s)
        economy['players'][a]['resources']['knowledge'] = 4
        yield '경제1→2(지식4 지불)', None, economy, a, {'type': 'ResearchAdvance', 'track': 'Economy'}, None
        # Controlled state difference isolates the +4 income, not a fabricated tech tile.
        for count in (3, 7):
            before, actor = cap_state(r, count)
            after = copy.deepcopy(before)
            after['players'][actor]['booster'] = 4
            yield f'가용{count}개: 충전 수입4→8(부스터4 보유차)', None, before, actor, None, after


def evaluate_actions():
    rows = []
    for label, expectation, before, actor, action, explicit_after in action_cases():
        after = explicit_after if explicit_after is not None else successor(before, actor, action)
        values = {}
        for name, model in MODELS.items():
            row = compare(before, after, actor, label, 'representative', True, model=model)
            for key in ('passed', 'status', 'exception'):
                row.pop(key)
            row['sign_ok'] = expected_sign(row['delta'], expectation)
            values[name] = row
        rows.append({'label': label, 'round': before['round'], 'expected': expectation,
                     'action': action, 'state_difference_only': action is None,
                     'before_state': before, 'after_state': after, 'values': values})
    return rows


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    results = {name: [] for name in MODELS}
    states = []
    for suite, scenario, before, actor, conversions in invariants():
        states.append({'suite': suite, 'scenario': scenario, 'state': before, 'actor': actor})
        operations = [(f'add:{resource}', None) for resource in variant.PRICES]
        operations += [(kind, {'type': 'FreeAction', 'kind': kind, 'count': 1}) for kind in conversions]
        for conserve in (True, False):
            for label, action in operations:
                if action is None:
                    after = copy.deepcopy(before)
                    after['players'][actor]['resources'][label[4:]] += 1
                else:
                    after = successor(before, actor, action)
                for name, model in MODELS.items():
                    row = compare(before, after, actor, label, scenario, conserve, model=model)
                    row['suite'] = suite
                    results[name].append(row)
    actions = evaluate_actions()
    counts = {name: dict(Counter(r['status'] for r in rows)) for name, rows in results.items()}
    record = {'invariants': results, 'counts': counts, 'actions': actions, 'invariant_states': states,
              'a_enabled': False, 'games_run': 0,
              'income': {'discount': .7, 'charge_vp': .6, 'cap': None,
                         'phases': {'1': 5, '3': 3, '6': 0}},
              'notes': ['Synthetic native-paid actions, not a game or universal proof.',
                        'Tile10 is a four-charge special action, NOT automatic income.',
                        'Tile3 lower-row choice explicitly advances Terraforming; tile4/10 use native aligned tracks.',
                        'The income+4 rows isolate booster4 ownership; no booster-selection cost or turn claimed.',
                        'The earlier broad Taklons burn exception remains counted separately.']}
    write_json(output/'comparison.json', record)
    lines = ['| 불변식: 통과/승인예외/실패 | '+' | '.join(MODELS)+' |', '|---|'+'---:|'*4]
    for suite in ('existing', 'cap-boundary'):
        for rnd in (1, 3, 6):
            cells = []
            for name, rows in results.items():
                c = Counter(r['status'] for r in rows if r['suite'] == suite and r['round'] == rnd)
                cells.append(f'{c["pass"]}/{c["exception"]}/{c["fail"]}')
            lines.append(f'| {suite} R{rnd} | '+' | '.join(cells)+' |')
    lines += ['', '| 행동 ΔVP | R | '+' | '.join(MODELS)+' |', '|---|---:|'+'---:|'*4]
    for row in actions:
        cells = [f'{r["delta"]:+.6f}'+(' ❌' if r['sign_ok'] is False else '') for r in row['values'].values()]
        lines.append(f'| {row["label"]} | {row["round"]} | '+' | '.join(cells)+' |')
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    failures = ['| 검증 | 구성 | R | 전→후 VP | 변화 breakdown |', '|---|---|---:|---|---|']
    for name, rows in results.items():
        for row in rows:
            if not row['passed']:
                parts = '; '.join(f'{k} {v["delta"]:+.6f}' for k, v in row['changed_breakdown'].items())
                failures.append(f'| {row["action"]}·{row["scenario"]}·{row["conservation"]} | {name} | {row["round"]} | '
                    f'{row["before"]:.6f}→{row["after"]:.6f} | {parts} |')
    sign_failures = 0
    for action in actions:
        for name, row in action['values'].items():
            if row['sign_ok'] is False:
                sign_failures += 1
                parts = '; '.join(f'{k} {v["delta"]:+.6f}' for k, v in row['changed_breakdown'].items())
                failures.append(f'| {action["label"]} | {name} | {action["round"]} | '
                    f'{row["before"]:.6f}→{row["after"]:.6f} | {parts} |')
    (output/'failures.md').write_text('\n'.join(failures)+'\n')
    before = Path(bdoubleprime.__file__).read_text()
    after = Path(variant.__file__).read_text()
    (output/'variant.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='Bdoubleprime/state_evaluation.py', tofile='Btripleprime/state_evaluation.py')))
    print(json.dumps({'counts': counts, 'sign_failures': sign_failures, 'games_run': 0}, ensure_ascii=False))
    return any(c.get('fail', 0) for c in counts.values()) or sign_failures > 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(int(run(parser.parse_args().output)))
