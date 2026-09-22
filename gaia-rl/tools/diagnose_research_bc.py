"""Read-only native-successor diagnostics for uncapped Bdoubleprime+(b)+(c).

No teacher selection, simulation games, evaluator edits or weight tuning.
"""
import argparse
import ast
import copy
from dataclasses import asdict
import hashlib
from pathlib import Path

from validate_bc import (Configured, MODELS, cap_state, compare, representative,
                         structure, successor, variant, write_json)
from validate_bprime import opportunity_fixture

MODEL = Configured(b=True, c=True)


def diagnose(before, actor, action):
    after = successor(before, actor, action)
    row = compare(before, after, actor, action['type'], 'research-diagnostic', True, model=MODEL)
    row = {k: v for k, v in row.items() if k not in ('passed', 'status', 'exception')}
    old, new = before['players'][actor], after['players'][actor]
    row.update(action=action, before_state=before, after_state=after,
               tracks_before=old['research_tracks'], tracks_after=new['research_tracks'],
               income_before=variant.engine_facts(before, old)['income'],
               income_after=variant.engine_facts(after, new)['income'],
               resources_before=old['resources'], resources_after=new['resources'],
               formers_before=old['gaiaformers_total'], formers_after=new['gaiaformers_total'])
    row['options_before'] = [asdict(o) for o in MODEL.evaluate_state(before, actor).opportunities]
    row['options_after'] = [asdict(o) for o in MODEL.evaluate_state(after, actor).opportunities]
    return row


def delta(row, key):
    return row['changed_breakdown'].get(key, {}).get('delta', 0.0)


def research_rows():
    rows = []
    for r in (1, 3):
        state, actor = representative(r)
        state['players'][actor]['resources']['knowledge'] = 4
        for key, track in variant.TRACK_IDS.items():
            row = diagnose(state, actor, {'type': 'ResearchAdvance', 'track': track})
            row['track'] = key
            cost = variant.engine_facts(state, state['players'][actor])['research_knowledge_cost']
            assert row['resources_after']['knowledge'] == row['resources_before']['knowledge']-cost
            row['knowledge_spend_vp'] = -cost*variant.PRICES['knowledge']
            # Resource stock gain beyond the native paid research cost (not round VP).
            row['instant_reward_vp'] = sum(delta(row, k+'_stock') for k in variant.PRICES)-row['knowledge_spend_vp']
            rows.append(row)
    return rows


def tech_rows():
    rows = []
    for r in (1, 3):
        state, actor = representative(r)
        structure(state, actor, '0,0', 'TradingStation')
        for tile in (4, 3, 10):
            # The lower-row tile3 can select any track; report ALL six, not only the best.
            tracks = list(variant.TRACK_IDS.values()) if tile == 3 else [None]
            for track in tracks:
                row = diagnose(state, actor, {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': track}})
                row['tile'] = tile
                changed = [(k, row['tracks_before'][k], v) for k, v in row['tracks_after'].items()
                           if v != row['tracks_before'][k]]
                assert len(changed) == 1 and changed[0][2]-changed[0][1] == 1
                row['advance'] = changed[0]
                row['main_case'] = tile != 3 or track == 'Terraforming'
                rows.append(row)
    return rows


def access_rows():
    rows = []
    for r in (1, 3):
        for track, start, target, distance in (
                ('navigation', 1, 'Desert', 2), ('terraforming', 1, 'Terra', 1),
                ('terraforming', 3, 'Terra', 1)):
            state, actor = opportunity_fixture(target=target, distance=distance, count=1)
            state.update(round=r)
            state['board']['spaceship_tiles'] = {}
            p = state['players'][actor]
            p['booster'] = None
            p['resources'].update(ore=15, credits=30, knowledge=4, qic=0)
            p['research_tracks'][track] = start
            row = diagnose(state, actor, {'type': 'ResearchAdvance', 'track': variant.TRACK_IDS[track]})
            facts = variant.engine_facts(state, p)
            table = facts['navigation_range' if track == 'navigation' else 'terraform_ore_per_step']
            row.update(track=track, rule_effect_before=table[start], rule_effect_after=table[start+1],
                       target=target, distance=distance)
            rows.append(row)
    return rows


def token_rows():
    rows = []
    for r in (1, 3, 6):
        for count in (3, 7):
            state, actor = cap_state(r, count, stress=True)
            action = {'type': 'FreeAction', 'kind': 'OreToPower', 'count': 1}
            after = successor(state, actor, action)
            for conserve in (True, False):
                values = {name: compare(state, after, actor, 'OreToPower', 'token-shortfall', conserve, model=model)
                          for name, model in MODELS.items()}
                rows.append({'round': r, 'active_tokens': count, 'conservation': conserve, 'values': values,
                             'before_state': state, 'after_state': after})
    return rows


def function_digest():
    tree = ast.parse(Path(variant.__file__).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'research_progress')
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    digest = function_digest()
    research, tech, access, tokens = research_rows(), tech_rows(), access_rows(), token_rows()
    assert digest == function_digest()
    state = research[0]['before_state']
    player = next(p for p in state['players'] if p['faction'] == 'Xenos')
    facts = variant.engine_facts(state, player)
    record = {'model': 'B″+b+c (uncapped)', 'conservation': 'ON', 'secured_planets': False,
              'research': research, 'technology': tech, 'access': access, 'ore_to_token': tokens,
              'research_function_sha256': digest, 'rules': facts, 'games_run': 0,
              'notes': ['Synthetic Xenos representative; K4 for paid research, K3 for lab acquisition.',
                        'std04 is aligned to Navigation, std10 to Science in this fixed board.',
                        'std03 lower-row options include every track; Terraforming is the main regression case.',
                        'Access fixtures isolate distance2 with QIC0 or three terraform steps with sufficient ore.',
                        'Raw states, actual successor tracks, income and full breakdown are retained.']}
    write_json(output/'research-diagnostic.json', record)
    lines = ['# B″+(b)+(c), 상한 없음, (a) OFF, 보존 ON; 합성 제노스 상태', '',
             '| 연구 | R | ΔVP | 지식 지출 | 연구 진행 | 확정 트랙 VP | 즉시 자원 | 확장 | 미래 수입 | 기타 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for row in research:
        key = row['track']
        keys = {'knowledge_stock', 'ore_stock', 'credits_stock', 'qic_stock', 'research_progress',
                'research_final_vp', 'expansion_opportunity', 'future_income'}
        other = '; '.join(f'{k} {v["delta"]:+.6f}' for k, v in row['changed_breakdown'].items() if k not in keys) or '0'
        cells = [row['delta'], row['knowledge_spend_vp'], delta(row, 'research_progress'),
                 delta(row, 'research_final_vp'), row['instant_reward_vp'],
                 delta(row, 'expansion_opportunity'), delta(row, 'future_income')]
        lines.append(f'| {key} {row["tracks_before"][key]}→{row["tracks_after"][key]} | {row["round"]} | '+
                     ' | '.join(f'{v:+.6f}' for v in cells)+f' | {other} |')
    lines += ['', '| 기술+무료 진보 | R | ΔVP | 광석 | 돈 | 지식 | QIC | 연구 진행 | 미래 수입 | 기타 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for row in tech:
        keys = ['ore_stock', 'credits_stock', 'knowledge_stock', 'qic_stock', 'research_progress', 'future_income']
        other = '; '.join(f'{k} {v["delta"]:+.6f}' for k, v in row['changed_breakdown'].items() if k not in keys) or '0'
        track, old, new = row['advance']
        lines.append(f'| std-{row["tile"]:02d} + {track}{old}→{new} | {row["round"]} | '+
                     ' | '.join(f'{v:+.6f}' for v in [row['delta']]+[delta(row,k) for k in keys])+f' | {other} |')
    lines += ['', '| 접근 확인 | R | 규칙 전→후 | 선택 기회 전→후 | 확장 ΔVP | 전체 ΔVP |', '|---|---:|---|---|---:|---:|']
    for row in access:
        lines.append(f'| {row["track"]} {row["tracks_before"][row["track"]]}→{row["tracks_after"][row["track"]]} | '
                     f'{row["round"]} | {row["rule_effect_before"]}→{row["rule_effect_after"]} | '
                     f'{len(row["options_before"])}→{len(row["options_after"])} | '
                     f'{delta(row,"expansion_opportunity"):+.6f} | {row["delta"]:+.6f} |')
    (output/'research-diagnostic.md').write_text('\n'.join(lines)+'\n')
    print(f'Research {len(research)}, tech {len(tech)}, access {len(access)}, token {len(tokens)}; games 0')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
