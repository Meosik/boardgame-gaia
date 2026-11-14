"""115e review: stage timing in the decision log (pre-registered reading of the queue note).
Per game: instrumentation coverage, decision-time distribution, slow decisions (>= 100 s, or >= 30 s with 0
completed comparisons), stage split of the >= 60 s decisions, and how long the line equals 115d's."""
import glob
import gzip
import json
import statistics
from collections import Counter

RUNS = '/home/sohegi/projects/gaia-lab/gaia-rl/runs/'
RUN = RUNS + 'lab-115e-stage-timing-crash-seeds-4r'
OLD = RUNS + 'lab-115d-fed-on-crash-seeds-full'


def load(game):
    return [json.loads(line) for line in gzip.open(game + '/decisions.jsonl.gz', 'rt')]


def split(row):
    timing = row.get('timing') or {}
    stages = dict(timing.get('stages') or {})
    choose, search = timing.get('choose'), timing.get('search')
    parts = {'runner_ipc': None if choose is None else round(row['seconds'] - choose, 2),
             'choose_wrap': None if None in (choose, search) else round(choose - search, 2)}
    if 'parallel_search' in stages:
        stages['frozen_search'] = round(stages['parallel_search'] - stages.get('prefetch', 0)
                                        - stages.get('drop_unfinished', 0) - stages.get('root_rank', 0)
                                        - stages.get('planned_tasks', 0), 2)
    return parts, stages


def show(row, factions):
    parts, stages = split(row)
    timing = row.get('timing') or {}
    print('   step', row['step'], 'round', row.get('round'), 'seat', row['seat'], factions[row['seat']],
          'seconds', row['seconds'], 'completed', row['completed_comparisons'], 'unsearched',
          row['unsearched_comparisons'], 'selected', row['selected'], 'fallback', row['fallback_timeout'],
          'digest', (row.get('digest') or '')[:12])
    print('     ', parts, 'published_at', (timing.get('published_at') or [])[:3], 'n_published',
          len(timing.get('published_at') or []), 'time_capped', timing.get('time_capped'), 'budget_stopped',
          timing.get('budget_stopped'), 'expired', timing.get('expired_before_search'))
    print('      stages', stages)


for game in sorted(glob.glob(RUN + '/pair-*/game-*')):
    result = json.load(open(game + '/result.json'))
    factions = result['factions']
    rows = load(game)
    name = '/'.join(game.split('/')[-2:])
    print(name, result['seed'], 'rows', len(rows), 'rounds', Counter(row.get('round') for row in rows))
    missing = [row['step'] for row in rows if row.get('round') is None or not row.get('digest')
               or not isinstance(row.get('timing'), dict)]
    fresh = [row for row in rows if (row.get('timing') or {}).get('audit_fresh')]
    no_stages = [row['step'] for row in fresh if not row['timing'].get('stages')]
    print('  rows missing round/digest/timing', len(missing), '| audit_fresh', len(fresh), 'of', len(rows),
          '| fresh without stages', len(no_stages), '| not fresh steps', [row['step'] for row in rows
                                                                        if row not in fresh][:12])
    seconds = sorted(row['seconds'] for row in rows)
    print('  seconds mean %.1f median %.1f p90 %.1f max %.2f' % (
        statistics.mean(seconds), statistics.median(seconds), seconds[int(len(seconds) * 0.9)], seconds[-1]),
        '| >=60:', sum(s >= 60 for s in seconds), '| >=100:', sum(s >= 100 for s in seconds),
        '| fallback_timeout', sum(bool(row['fallback_timeout']) for row in rows),
        '| federation_limit_hits', sum(row['federation_limit_hits'] for row in rows),
        '| expired_before_search', sum(bool((row.get('timing') or {}).get('expired_before_search')) for row in rows))
    slow = [row for row in rows if row['seconds'] >= 100
            or (row['seconds'] >= 30 and row['completed_comparisons'] == 0)]
    print('  slow decisions (>=100 s, or >=30 s with 0 completed):', len(slow))
    for row in slow:
        show(row, factions)
    capped = [row for row in rows if row['seconds'] >= 60]
    longest = Counter()
    for row in capped:
        parts, stages = split(row)
        pool = {k: v for k, v in {**parts, **stages}.items()
                if v is not None and k not in ('parallel_search', 'search_call')}
        longest[max(pool, key=pool.get)] += 1
    print('  >=60 s decisions, longest stage:', dict(longest), '| completed comparisons',
          sorted(row['completed_comparisons'] for row in capped))
    print('  largest runner_ipc %.2f, largest choose_wrap %.2f, largest root_rank %.2f, largest prefetch %.2f,'
          ' largest first publish %.2f' % (
              max(split(row)[0]['runner_ipc'] or 0 for row in rows),
              max(split(row)[0]['choose_wrap'] or 0 for row in rows),
              max(split(row)[1].get('root_rank', 0) for row in rows),
              max(split(row)[1].get('prefetch', 0) for row in rows),
              max(((row.get('timing') or {}).get('published_at') or [0])[0] for row in rows)))
    print('  three slowest:')
    for row in sorted(rows, key=lambda r: -r['seconds'])[:3]:
        show(row, factions)
    if len(rows) > 111:
        print('  step 111:')
        show(rows[111], factions)
    old = load(game.replace(RUN, OLD))
    same = 0
    for a, b in zip(rows, old):
        if a['chosen'] != b['chosen'] or a['seat'] != b['seat']:
            break
        same += 1
    print('  same line as 115d for the first', same, 'decisions (115d rows', len(old), ')')
