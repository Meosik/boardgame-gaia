"""Read saved replays; compare risky recorded actions under legacy/corrected rules."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path

from evaluation_replays import ROOT, validate_replay
from gaia_rl._native import evaluation_successor_json
from gaia_rl.versions import require_current_sources, runtime_versions


def successor(state, actor, action, flag):
    previous = os.environ.get('GAIA_ENGINE_FIXES_2')
    try:
        os.environ['GAIA_ENGINE_FIXES_2'] = flag
        # Exporters omit event_log; it is output history, not rule state.
        state = dict(state, event_log=state.get('event_log', []))
        result = evaluation_successor_json(json.dumps(state), actor, json.dumps(action))
        return {'state': json.loads(result)}
    except RuntimeError as error:
        return {'error': str(error)}
    finally:
        if previous is None:
            os.environ.pop('GAIA_ENGINE_FIXES_2', None)
        else:
            os.environ['GAIA_ENGINE_FIXES_2'] = previous


def audit(directory):
    require_current_sources(ROOT)
    files, cases, failures = [], [], []
    frame_count = 0
    for path in sorted(directory.glob('*.json.gz')):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        replay = json.loads(gzip.decompress(raw))
        validate_replay(replay)
        frames = replay['frames']
        frame_count += len(frames)
        for before, after in zip(frames, frames[1:]):
            actor, action = after['player'], after['action']
            old_player = before['state']['players'][actor]
            new_player = after['state']['players'][actor]
            flipped_base = (new_player.get('gray_federation_tokens', []).count(1)
                            > old_player.get('gray_federation_tokens', []).count(1))
            bonus_build = (action['type'] == 'Upgrade'
                           and (action.get('tech_tile_choice') or {}).get('bonus_build_coord') is not None)
            if not (flipped_base or bonus_build):
                continue
            legacy = successor(before['state'], actor, action, '0')
            corrected = successor(before['state'], actor, action, '1')
            cases.append({
                'file': path.name, 'decision': after['decision_id'],
                'reason': 'base_12vp_flip' if flipped_base else 'upgrade_bonus_build',
                'legacy_error': legacy.get('error'), 'corrected_error': corrected.get('error'),
                'legacy_phase': legacy.get('state', {}).get('phase'),
                'corrected_phase': corrected.get('state', {}).get('phase'),
                'changed': legacy != corrected,
            })
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append(path.name)
        files.append({'file': path.name, 'sha256': digest, 'frames': len(frames)})
    return {
        'scope': 'Saved-frame validation and selected one-action replay only; not full-game resimulation.',
        'runtime': runtime_versions(), 'replays': len(files), 'frames': frame_count,
        'file_mutations': failures, 'selected_actions': len(cases),
        'changed_actions': sum(row['changed'] for row in cases),
        'legacy_rejected_actions': sum(row['legacy_error'] is not None for row in cases),
        'corrected_rejected_actions': sum(row['corrected_error'] is not None for row in cases),
        'selected_reason_counts': dict(Counter(row['reason'] for row in cases)),
        'files': files, 'cases': cases,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT/'gaia-frontend/public/ai-replays')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('files', 'cases')}, indent=2))
