"""Explicit one-game teacher recording; never starts BC/PPO or promotes a model."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from gaia_rl import Environment
from gaia_rl.versions import runtime_versions
from faction_learning.models import write_json
from faction_learning.records import NativeRecorder
from four_factions.provenance import hashes, verify
from .profiles import profiles
from .teacher import SharedTeacher
from .clock import AdaptiveClock
from .diagnostics import summarize_candidate_limits
from .continuation import load_continuation, restore_continuation, save_checkpoint
from four_factions.timed import atomic_json


def collect(destination, seed, *, adaptive=False, resume_checkpoint=None):
    destination = Path(destination)
    continuation = load_continuation(resume_checkpoint, seed) if resume_checkpoint is not None else None
    saved_clock = continuation['saved']['memory'].get('_clock') if continuation else None
    if saved_clock is not None and not adaptive:
        raise ValueError('An adaptive-clock game cannot silently reset to a legacy clock')
    clock = AdaptiveClock(state=saved_clock) if adaptive else None
    env = Environment(seed, 2000)
    before = json.loads(env.snapshot_json())
    unsupported = {p['faction'] for p in before['state']['players']} - profiles().keys()
    if unsupported:
        raise ValueError(f'Seed contains factions without an approved teacher: {sorted(unsupported)}')
    manifest = {'versions': runtime_versions(), 'source_hashes': hashes()}
    verify(manifest)
    spec = {'name': 'shared-native-bgg-r1-adaptive-v2' if adaptive else 'shared-native-bgg-r1-v1',
            **manifest, 'bgg_openings': True,
            'quality': 'unreviewed; native replay does not prove expert quality',
            'profiles': {p['faction']: {k: v for k, v in asdict(profiles()[p['faction']]).items()
                                       if k != 'openings'} for p in before['state']['players']}}
    spec['time_control'] = ({'mode': 'adaptive', 'target_seconds': 10, 'long_seconds': 120,
                             'long_uses_per_seat': 6, 'artificial_delays': False,
                             'timeout_fallback': 'bounded-native-one-step-reserve'} if adaptive else
                            {'mode': 'legacy', 'target_seconds': 60, 'maximum_seconds': 300})
    if continuation:
        spec['continuation'] = continuation['provenance']
    recorder = NativeRecorder(destination, seed, teacher_seats=range(4), teacher_spec=spec)
    policy = SharedTeacher(seed, adaptive_clock=clock).bind(env)
    try:
        if recorder.current != before:
            raise ValueError('Recorder and teacher native initial states differ')
        with (destination/'teacher-audit.jsonl').open('x') as audit:
            if continuation:
                before = restore_continuation(continuation, env, recorder, policy, audit)
                write_json(destination/'continuation-verified.json', {
                    **continuation['provenance'], 'native_replayed': True, 'strategic_memory_restored': True})
            save_checkpoint(recorder, policy, manifest)
            while not env.is_terminal():
                decision, index = policy.choose(before)
                env.step(decision, index)
                after = json.loads(env.snapshot_json())
                recorded = recorder.step(decision, index, controller='teacher')
                if recorded != after:
                    raise ValueError('Recorder diverged from teacher execution')
                policy.observe(before, index, after)
                audit.write(json.dumps({'decision_id': decision, 'index': index,
                                        'audit': policy.last_audit}, allow_nan=False)+'\n')
                audit.flush()
                before = after
                save_checkpoint(recorder, policy, manifest)
        verify(manifest)
        recorder.finish()
        with (destination/'teacher-audit.jsonl').open() as audits:
            limits = summarize_candidate_limits(json.loads(line) for line in audits)
        write_json(destination/'search-limits.json', limits)
        atomic_json(destination/'progress.json', {'complete': True, 'steps': before['steps'],
                    'scores': env.final_scores(), 'phase': before['state']['phase']})
        return {'complete': True, 'path': str(destination), 'steps': before['steps'],
                'factions': [p['faction'] for p in before['state']['players']],
                'training_performed': False, 'quality': spec['quality'], 'search_limits': limits}
    except BaseException as error:
        recorder.close()
        write_json(destination/'failure.json', {'complete': False, 'error': repr(error)})
        atomic_json(destination/'progress.json', {'complete': False, 'failed': True, 'error': repr(error)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('profiles', help='Show supported factions and source coverage')
    game = commands.add_parser('record', help='One complete four-teacher game, potentially slow')
    game.add_argument('--seed', required=True)
    game.add_argument('--output', type=Path, required=True)
    game.add_argument('--adaptive-clock', action='store_true', help='10 s target; up to six 120 s thoughts per teacher')
    game.add_argument('--resume-checkpoint', type=Path, help='Verified exact prefix and teacher memory; new output required')
    args = parser.parse_args()
    if args.command == 'profiles':
        result = {f: {k: v for k, v in asdict(p).items() if k != 'openings'}
                  for f, p in profiles().items()}
    else:
        result = collect(args.output, args.seed, adaptive=args.adaptive_clock, resume_checkpoint=args.resume_checkpoint)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
