"""Incremental exact decision traces; exceptions are failures, never partial wins."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import random
import time

from gaia_rl._native import Environment
from four_factions import FACTIONS
from four_factions.teacher import QuartetTeacher, brainstone_committed


def dump(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def progress(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False)+'\n')
    temporary.replace(path)


def play(spec, output, *, factory=QuartetTeacher, focal=None):
    """All four teachers for demonstrations, one focal policy vs random for eval."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    env = Environment(spec['seed'], 2000)
    snapshot = json.loads(env.snapshot_json())
    factions = [p['faction'] for p in snapshot['state']['players']]
    if factions != spec['factions'] or set(factions) != set(FACTIONS):
        raise ValueError('Full native setup does not match the approved quartet')
    seat = None if focal is None else factions.index(focal)
    policy = factory()
    if hasattr(policy, 'bind'):
        policy.bind(env)
    streams = [random.Random(f"{spec['seed']}:{focal}:opponent:{p}") for p in range(4)]
    counts = {f: Counter() for f in factions}
    violations = {f: Counter() for f in factions}
    started = time.monotonic()
    maximum = 0.0
    try:
        with gzip.open(output/'decisions.jsonl.gz', 'wt') as trace:
            while not env.is_terminal():
                actor = snapshot['player']
                faction = factions[actor]
                chosen_by_policy = seat is None or seat == actor
                before = env.snapshot_json()
                tick = time.monotonic()
                if chosen_by_policy:
                    decision, index = policy.choose(snapshot)
                    ranks = getattr(policy, 'last_scores', None)
                    reason = ranks[index][1] if ranks else 'student inference; native mask only'
                    if env.snapshot_json() != before:
                        raise ValueError('Policy ranking mutated its parent environment')
                else:
                    decision, index = snapshot['decision_id'], streams[actor].randrange(len(snapshot['candidates']))
                    reason = 'uniform random opponent'
                if decision != snapshot['decision_id'] or not 0 <= index < len(snapshot['candidates']):
                    raise ValueError('Invalid policy decision identity/index')
                elapsed = time.monotonic()-tick
                maximum = max(maximum, elapsed)
                action = snapshot['candidates'][index]['action']
                env.step(decision, index)
                after = json.loads(env.snapshot_json())
                if hasattr(policy, 'observe'):
                    policy.observe(snapshot, index, after)
                if chosen_by_policy:
                    counts[faction][action['type']] += 1
                    if action['type'] == 'FreeAction' and action['kind'] in ('OreToCredit', 'KnowledgeToCredit'):
                        violations[faction][action['kind']] += action.get('count', 1)
                    if brainstone_committed(snapshot, after, actor):
                        violations[faction]['BrainstoneGaia'] += 1
                    if isinstance(policy, QuartetTeacher) and violations[faction]:
                        raise ValueError('Teacher bypassed standing conservation policy')
                record = {'snapshot': snapshot, 'index': index, 'policy': chosen_by_policy,
                          'reason': reason, 'seconds': elapsed}
                if chosen_by_policy and isinstance(policy, QuartetTeacher):
                    record['teacher_audit'] = policy.last_audit
                trace.write(json.dumps(record, allow_nan=False)+'\n')
                trace.flush()
                progress(output/'progress.json', {'state': 'running', 'step': after['steps'],
                         'round': after['state']['round'], 'last_faction': faction,
                         'action': action, 'seconds': time.monotonic()-started})
                if after['steps'] % 10 == 0:
                    print(output.name, 'step', after['steps'], 'round', after['state']['round'],
                          faction, action['type'], f'{elapsed:.2f}s', flush=True)
                snapshot = after
        scores = dict(env.final_scores())
        best = max(scores.values())
        rows = [{'faction': f, 'seat': i, 'vp': scores[i], 'actions': dict(counts[f]),
                 'policy_violations': dict(violations[f]),
                 'win_share': (1/sum(v == best for v in scores.values())) if scores[i] == best else 0,
                 'final_tracks': snapshot['state']['players'][i]['research_tracks'],
                 'advanced_tiles': len(snapshot['state']['players'][i]['advanced_tech_tiles'])}
                for i, f in enumerate(factions) if seat is None or i == seat]
        result = {'complete': True, **spec, 'focal': focal, 'rows': rows, 'scores': scores,
                  'steps': snapshot['steps'], 'seconds': time.monotonic()-started,
                  'max_decision_seconds': maximum}
        dump(output/'terminal.json', snapshot)
        dump(output/'result.json', result)
        progress(output/'progress.json', {'state': 'complete', **result})
        return result
    except BaseException as error:
        dump(output/'failure.json', {'complete': False, 'error': repr(error), 'snapshot': snapshot,
             'last_chosen_index': locals().get('index'), 'actual_native_snapshot': json.loads(env.snapshot_json())})
        progress(output/'progress.json', {'state': 'failed', 'error': repr(error), 'step': snapshot['steps']})
        raise


def audit(output):
    """Independently re-execute every saved native candidate and terminal result."""
    output = Path(output)
    result = json.loads((output/'result.json').read_text())
    if not result['complete']:
        raise ValueError('Cannot certify an incomplete game')
    env = Environment(result['seed'], 2000)
    count = 0
    with gzip.open(output/'decisions.jsonl.gz', 'rt') as trace:
        for line in trace:
            row = json.loads(line)
            snapshot = json.loads(env.snapshot_json())
            if snapshot != row['snapshot']:
                raise ValueError(f'Native trace mismatch at {count}')
            env.step(snapshot['decision_id'], row['index'])
            count += 1
    terminal = json.loads(env.snapshot_json())
    if not env.is_terminal() or terminal != json.loads((output/'terminal.json').read_text()):
        raise ValueError('Native terminal snapshot mismatch')
    if count != result['steps'] or dict(env.final_scores()) != {int(k): v for k, v in result['scores'].items()}:
        raise ValueError('Native score/step mismatch')
    receipt = {'native_complete': True, 'verified_decisions': count, 'scores': result['scores'],
               'trace_sha256': hashlib.sha256((output/'decisions.jsonl.gz').read_bytes()).hexdigest()}
    dump(output/'native-audit.json', receipt)
    return receipt
