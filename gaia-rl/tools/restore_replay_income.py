"""Prepare income-corrected copies of a replay catalog; never overwrite or publish originals."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from publish_replays import read_catalog
from replay_log import add_decision_log


def restore(source, output):
    games = read_catalog(source/'index.json')
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for game in games:
        data = (source/game['file']).read_bytes()
        replay = json.loads(gzip.decompress(data))
        updated = add_decision_log(replay)
        updated['metadata']['income_reconstruction'] = {
            'source_sha256': hashlib.sha256(data).hexdigest(),
            'method': 'current engine transition; complete resulting game state equality required',
            'historical_actions_and_scores_unchanged': True,
        }
        payload = json.dumps(updated, separators=(',', ':'), ensure_ascii=False).encode()
        with (output/game['file']).open('xb') as f:
            f.write(gzip.compress(payload, mtime=0))
        count = sum('IncomeReceived' in e for e in updated['events'])
        reports.append({'file': game['file'], 'income_events': count,
                        'source_sha256': hashlib.sha256(data).hexdigest()})
        print(game['file'], count, 'income events; original unchanged', flush=True)
    # No selectable catalog until every game has been verified and written.
    (output/'report.json').write_text(json.dumps(reports, indent=2))
    (output/'index.json').write_text(json.dumps({'schema_version': 1, 'games': games}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    restore(args.source, args.output)
