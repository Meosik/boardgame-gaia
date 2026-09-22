"""Resumable paired quartet comparison: frozen A versus state B conservation ON/OFF.

Smoke is the first ON game, not an additional sample. Completed results are reused
only with unchanged seeds, teachers and native build. Increasing --games appends
new fixed seeds; it never reinterprets earlier pair assignments.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time

import teacher_ab as ab

FACTIONS = {'Xenos','HadschHallas','Terrans','Taklons'}


def teacher_b(conserve, source):
    return {'name':f'state-B-{"on" if conserve else "off"}',
            'source':str(Path(source).resolve()),'factory':'state_teacher:StateTeacher',
            'kwargs':{'conserve_resources':conserve},'frozen':False}


def fixed_schedule(seeds, games):
    if games < 2 or games % 2 or len(seeds) < games//2 or len(set(seeds)) != len(seeds):
        raise ValueError('Distinct fixed seeds and an even N; one seed per pair required')
    return ab.schedule(seeds[:games//2],games)


def win_rates(games, faction=None):
    wins, totals = dict.fromkeys('AB',0.0), dict.fromkeys('AB',0)
    for game in games:
        if not game['complete']:
            continue
        best = max(game['scores'].values())
        winners = [seat for seat,score in game['scores'].items() if score == best]
        for seat,name in enumerate(game['factions']):
            if faction is not None and name != faction:
                continue
            arm = 'A' if seat in game['a_seats'] else 'B'
            totals[arm] += 1
            if str(seat) in winners:
                wins[arm] += 1/len(winners)
    # Seat win rate: probability that one policy-controlled seat wins; ties shared.
    return {arm:wins[arm]/totals[arm] if totals[arm] else None for arm in 'AB'}


def results(root, schedule, modes=('on','off')):
    output = {}
    for mode in modes:
        games, pairs = [], []
        for pair in schedule:
            found = []
            for index in range(2):
                path = root/mode/f'pair-{pair["pair"]:03d}'/f'game-{index}'/'result.json'
                if path.exists():
                    game = json.loads(path.read_text())
                    games.append(game)
                    found.append(game)
            if len(found) == 2 and all(g['complete'] for g in found):
                pairs.append(ab.pair_differences(*found))
        summary = ab.summarize(pairs,games)
        for faction,row in summary['factions'].items():
            row['win_rate'] = win_rates(games,None if faction == 'ALL' else faction)
        output[mode] = summary
    return output


def table(summaries):
    lines = ['| 비교 | 종족 | 완료 쌍 | 평균 점수 차이 B−A | 95% 신뢰구간 | 승률 A / B¹ | 오류 / 타임아웃 판 |',
             '|---|---|---:|---:|---|---|---:|']
    for mode,summary in summaries.items():
        for faction,row in sorted(summary['factions'].items(),key=lambda item:(item[0]!='ALL',item[0])):
            mean = '—' if row['mean_B_minus_A'] is None else f'{row["mean_B_minus_A"]:+.2f}'
            rates = ['—' if row['win_rate'][arm] is None else f'{row["win_rate"][arm]:.1%}' for arm in 'AB']
            name = '전체' if faction == 'ALL' else f'{faction} (참고용)'
            lines.append(f'| A vs B 보존 {mode.upper()} | {name} | {row["pairs"]} | {mean} | '
                         f'{ab.format_ci(row["ci95"])} | {" / ".join(rates)} | '
                         f'{row["error_games"]} / {row["timeout_games"]} |')
    lines.append('| ¹승률 정의 | 담당 좌석별 단독 1위 1, 공동 1위는 인원수로 분할 | | | | | |')
    return '\n'.join(lines)+'\n'


def run(args):
    from gaia_rl import Environment
    from gaia_rl.versions import runtime_versions, require_current_sources
    require_current_sources(ab.ROOT)
    seeds_path = Path(args.seeds)
    seed_record = json.loads(seeds_path.read_text())
    seeds = [row['seed'] for row in seed_record['setups']]
    plan = fixed_schedule(seeds,args.games)
    baseline = ab.resolve_teacher('baseline')
    if ab.frozen_problems(baseline):
        raise ValueError('Frozen A changed; cannot compare')
    b_source = Path(args.b_source).resolve()
    if not (b_source/'adapter-manifest.json').exists():
        raise ValueError('Build the auditable frozen-A adapter before running B')
    teachers = {'A':baseline,'on':teacher_b(True,b_source),'off':teacher_b(False,b_source)}
    modes = ('on','off') if args.mode == 'both' else (args.mode,)
    signature = {'teachers':{k:{**v,'fingerprint':ab.fingerprint(v)} for k,v in teachers.items()},
                 'versions':runtime_versions(),'clock':ab.CLOCKS['data']}
    root = Path(args.output)
    root.mkdir(parents=True,exist_ok=True)
    manifest_path = root/'manifest.json'
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old['signature'] != signature or old['schedule'] != plan[:len(old['schedule'])]:
            raise ValueError('Source/build/seed schedule changed; use a new experiment directory')
    for pair in plan:
        snapshot = json.loads(Environment(pair['seed']).snapshot_json())
        if {p['faction'] for p in snapshot['state']['players']} != FACTIONS:
            raise ValueError('Seed does not have the approved quartet')
    ab.write_json(manifest_path,{'signature':signature,'games_per_comparison':args.games,
                  'schedule':plan,'seed_file':str(seeds_path),'training':False,
                  'inference':'paired t interval over distinct map/seat-swapped pairs; per-faction exploratory'})
    if args.jobs > 1 and not args.smoke:
        def game_task(mode, pair, index, game):
            path = root/mode/f'pair-{pair["pair"]:03d}'/f'game-{index}'
            if (path/'result.json').exists():
                return mode, pair['pair'], index, json.loads((path/'result.json').read_text())
            if path.exists():
                raise ValueError(f'Interrupted game evidence at {path}; preserve it and resolve before resuming')
            if ab.frozen_problems(baseline):
                raise ValueError('Frozen A changed during experiment')
            started = time.monotonic()
            result = ab.play(path,pair['seed'],{'A':baseline,'B':teachers[mode]},
                             set(game['a_seats']),ab.CLOCKS['data'])
            result['wall_seconds'] = time.monotonic()-started
            ab.write_json(path/'result.json',result)
            return mode, pair['pair'], index, result

        tasks = [(mode,pair,index,game) for mode in modes for pair in plan
                 for index,game in enumerate(pair['games'])]
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = [executor.submit(game_task,*task) for task in tasks]
            for future in as_completed(futures):
                mode,pair,index,result = future.result()
                print(json.dumps({'mode':mode,'pair':pair,'game':index,
                    'complete':result['complete'],'wall_seconds':result.get('wall_seconds'),
                    'failure':result.get('failure_kind')},ensure_ascii=False),flush=True)
        summary = results(root,plan,modes)
        ab.write_json(root/'results.json',summary)
        (root/'report.md').write_text(table(summary))
        print(table(summary),flush=True)
        return
    for mode in modes:
        for pair in plan:
            for index,game in enumerate(pair['games']):
                path = root/mode/f'pair-{pair["pair"]:03d}'/f'game-{index}'
                if not (path/'result.json').exists():
                    if path.exists():
                        raise ValueError(f'Interrupted game evidence at {path}; preserve it and resolve before resuming')
                    if ab.frozen_problems(baseline):
                        raise ValueError('Frozen A changed during experiment')
                    started = time.monotonic()
                    result = ab.play(path,pair['seed'],{'A':baseline,'B':teachers[mode]},
                                     set(game['a_seats']),ab.CLOCKS['data'])
                    result['wall_seconds'] = time.monotonic()-started
                    ab.write_json(path/'result.json',result)
                    print(json.dumps({'mode':mode,'pair':pair['pair'],'game':index,
                          'complete':result['complete'],'wall_seconds':result['wall_seconds'],
                          'failure':result.get('failure_kind')},ensure_ascii=False),flush=True)
                else:
                    result = json.loads((path/'result.json').read_text())
                if mode == modes[0] and pair['pair'] == 0 and index == 0:
                    ab.write_json(root/'smoke.json',{
                        'complete':result['complete'],'wall_seconds':result.get('wall_seconds'),
                        'errors':int(result.get('failure_kind')=='error'),
                        'timeouts':int(result.get('failure_kind')=='timeout'),
                        'reused_in_full_experiment':True,
                    })
                    if args.smoke or not result['complete']:
                        return
                summary = results(root,plan,modes)
                ab.write_json(root/'results.json',summary)
                (root/'report.md').write_text(table(summary))
    print(table(results(root,plan,modes)),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds',required=True)
    parser.add_argument('--games',type=int,default=20)
    parser.add_argument('--output',required=True)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--mode',choices=('both','on','off'),default='both')
    parser.add_argument('--jobs',type=int,default=1)
    parser.add_argument('--b-source',required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
