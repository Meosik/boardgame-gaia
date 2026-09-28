"""One saved-branch decision with the inherited clock; never starts a new game."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from gaia_rl import Environment
from faction_teachers.teacher import SharedTeacher
from four_factions.provenance import hashes
from diagnose_plan_completion import digest, inherited_clock


WORKER_TRACE = '''import json, sys, time
from four_factions import preparation as prep
from four_factions.timed import worker
original = prep.rollout
def emit(event, **data):
    with open(sys.argv[2], 'a') as stream:
        stream.write(json.dumps(dict(event=event, time=time.monotonic(), **data)) + '\\n')
def rollout(*args, **kwargs):
    context = dict(goal=args[3].name, depth=kwargs.get('decision_depth'))
    emit('comparison_started', **context)
    result = original(*args, **kwargs)
    emit('comparison_finished', complete=result['complete'], value=result['value'], **context)
    return result
prep.rollout = rollout
worker(sys.argv[1])
'''


def probe(fixture, checkpoint):
    sources = hashes()
    env = Environment(fixture['seed'], 2000)
    for index in fixture['prefix']:
        snapshot = json.loads(env.snapshot_json())
        env.step(snapshot['decision_id'], index)
    root = json.loads(env.snapshot_json())
    if digest(root) != fixture['snapshot_sha256']:
        raise ValueError('Fixture root changed')
    clock = inherited_clock(checkpoint, 67)
    remaining = clock.remaining(root['player'])
    teacher = SharedTeacher(fixture['seed'], prefix=fixture['prefix'],
                            adaptive_clock=clock, faction_tech_plans=True).bind(env)
    teacher.memory = {'_clock': clock.state()}
    popen = subprocess.Popen
    with tempfile.TemporaryDirectory(prefix='gaia-progressive-probe-') as directory:
        trace = Path(directory)/'trace.jsonl'
        def launch(command, **kwargs):
            return popen([sys.executable, '-c', WORKER_TRACE, command[-1], str(trace)], **kwargs)
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            _, index = teacher.choose(root)
        events = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    if hashes() != sources or json.loads(env.snapshot_json()) != root:
        raise ValueError('Sources or native root changed during probe')
    audit = teacher.last_audit
    depth = audit.get('comparison_depth')
    if depth is not None and any(row['comparison_depth'] != depth for row in audit['plans']):
        raise AssertionError('Mixed-depth published result')
    return dict(scope='One saved hypothetical branch decision, not a game or strength benchmark',
                root_sha256=fixture['snapshot_sha256'], source_hashes=sources,
                clock_inherited_through_decision=67, long_remaining_before=remaining,
                long_remaining_after=clock.remaining(root['player']),
                memory='No saved plan/conversion commitments; same isolated controller setup as cycle012',
                observation='Native worker instrumentation overhead counts within unchanged time budget',
                chosen_action=root['candidates'][index]['action'], worker_events=events,
                audit=audit, root_unchanged=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('checkpoint', type=Path)
    args = parser.parse_args()
    result = probe(json.loads(args.fixture.read_text())['fixture'], json.loads(args.checkpoint.read_text()))
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
