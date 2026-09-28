"""One saved-state timed-worker decision, with independent native forecast replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from gaia_rl import Environment, ENGINE_BUILD_ID
from gaia_rl.versions import require_current_sources
from faction_teachers.clock import AdaptiveClock
from four_factions.timed import TimedPreparationTeacher
from four_factions.preparation import leaf_value
from four_factions.value import ROOT, INCOME_PATH
import gzip

from build_a02_source import verify_baseline


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(trace, step):
    if os.environ.get('GAIA_ENGINE_FIXES_2', '1') != '1':
        raise ValueError('A02 probes use the corrected engine ON; historical OFF results stay separate')
    require_current_sources(ROOT)
    verify_baseline()
    source = Path(__import__('four_factions.timed', fromlist=['worker']).__file__).resolve().parents[1]
    derivation = json.loads((source/'A02_DERIVATION.json').read_text())
    def verify_source():
        for name, expected in derivation['python_files'].items():
            if sha(source/name) != expected:
                raise ValueError(f'A02 derivative changed: {name}')
    verify_source()
    trace_hash, income_hash = sha(trace), sha(INCOME_PATH)
    recorded = [json.loads(line) for line in gzip.open(trace, 'rt')]
    seed = json.loads(trace.with_name('result.json').read_text())['seed']
    if not 0 <= step < len(recorded):
        raise ValueError('Requested saved decision is absent')
    env = Environment(seed, 2000)
    prefix = []
    for record in recorded[:step]:
        snapshot = json.loads(env.snapshot_json())
        faction = snapshot['state']['players'][snapshot['player']]['faction']
        if (snapshot['steps'], snapshot['player'], faction) != (record['step'], record['seat'], record['faction']):
            raise ValueError(f'Historical prefix differs under corrected engine at {record["step"]}')
        matches = [i for i, c in enumerate(snapshot['candidates']) if c['action'] == record['action']]
        if len(matches) != 1:
            raise ValueError(f'Historical action not uniquely legal at {record["step"]}')
        prefix.append(matches[0])
        env.step(snapshot['decision_id'], matches[0])
    root = json.loads(env.snapshot_json())
    actor = root['player']
    target = recorded[step]
    if (root['steps'], actor, root['state']['round']) != (step, target['seat'], target['round']):
        raise ValueError('Historical target decision changed')
    clock = AdaptiveClock(target_seconds=10, long_seconds=20, uses=0)
    teacher = TimedPreparationTeacher(seed, prefix=prefix, target_seconds=10,
        maximum_seconds=20, adaptive_clock=clock, bgg_openings=True, shared_factions=True).bind(env)
    started = time.monotonic()
    decision, index = teacher.choose(root)
    seconds = time.monotonic()-started
    audit = teacher.last_audit
    replayed = []
    if audit.get('a02'):
        for row in audit['plans']:
            if not row['complete']:
                continue
            branch = None
            before = root
            for action_row in row['actions']:
                if (before['player'], before['state']['round']) != (action_row['actor'], action_row['round']):
                    raise AssertionError('Forecast replay actor/round mismatch')
                indices = [i for i, c in enumerate(before['candidates']) if c['action'] == action_row['action']]
                if len(indices) != 1:
                    raise AssertionError('Forecast replay action is not uniquely legal')
                if branch is None:
                    if indices[0] != row['first']:
                        raise AssertionError('Forecast first action differs from published choice')
                    branch = env.fork(before['decision_id'], indices[0])
                else:
                    branch.step(before['decision_id'], indices[0])
                before = json.loads(branch.snapshot_json())
            from a02_round_investment import endpoint, _outcome, Node
            if not endpoint(before, root['state']['round']):
                raise AssertionError('Forecast did not reach common boundary')
            value = leaf_value(before, actor, root['state']['players'][actor])
            if abs(value-row['value']) > 1e-8:
                raise AssertionError('Replayed leaf differs from published value')
            if _outcome(Node(branch, before, None, [], [], None), actor) != row['outcome']:
                raise AssertionError('Replayed resources/income/availability differ')
            replayed.append(row['goal'])
    if json.loads(env.snapshot_json()) != root or sha(trace) != trace_hash or sha(INCOME_PATH) != income_hash:
        raise AssertionError('Original state, trace or income data changed')
    verify_source()
    verify_baseline()
    return dict(scope='Saved-state functional probe; not a full game or strength evaluation',
                seed=seed, step=step, flag=os.environ.get('GAIA_A02_ROUND_INVESTMENT', '0'),
                engine_fixes_2=True, engine_build_id=ENGINE_BUILD_ID,
                trace_sha256=trace_hash, income_sha256=income_hash,
                derivation_sha256=sha(source/'A02_DERIVATION.json'), tool_sha256=sha(Path(__file__)),
                root_sha256=hashlib.sha256(json.dumps(root, sort_keys=True).encode()).hexdigest(),
                memory='Fresh isolated controller; no claim of historical full-memory reproduction',
                root_player=root['state']['players'][actor],
                historical_action=target['action'], chosen_action=root['candidates'][index]['action'],
                decision_id=decision, seconds=seconds, clock=clock.state(), audit=audit,
                replayed_complete_paths=replayed, original_unchanged=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--step', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    value = probe(args.trace, args.step)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(args.output), chosen=value['chosen_action'], seconds=value['seconds'],
                         complete_paths=len(value['replayed_complete_paths']),
                         a02=value['audit'].get('a02', False)), ensure_ascii=False))
