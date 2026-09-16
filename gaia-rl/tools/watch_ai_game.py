"""Read-only live observer for a four_factions game's flushed native trace.

No model inference, training edits, server commands, or public deployment. Replays
recorded candidate choices on an independent compatible native engine; verifies
every before-state, so unknown/mismatched rules cannot silently produce a stream.
"""
import argparse
import json
from pathlib import Path
import time
import zlib

from evaluation_replays import frame
from live_replays import LiveReplayWriter


class GrowingTrace:
    """gzip.flush() writes readable data before the final gzip trailer exists."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('rb')
        self.inode = self.path.stat().st_ino
        self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.pending = b''

    def rows(self):
        stat = self.path.stat()
        if stat.st_ino != self.inode or stat.st_size < self.stream.tell():
            raise ValueError('Live source was replaced or truncated')
        while chunk := self.stream.read(65536):
            self.pending += self.decoder.decompress(chunk)
            while b'\n' in self.pending:
                line, self.pending = self.pending.split(b'\n', 1)
                yield json.loads(line)
            if len(self.pending) > 64 * 1024 * 1024:
                raise ValueError('Unterminated trace row exceeds the observer limit')

    def close(self):
        self.stream.close()


class GameObserver:
    def __init__(self, source, manifest, output, seed, environment_factory=None, focal=None,
                 policy='live_observer'):
        self.source = Path(source)
        self.versions = manifest['versions']
        self.seed = seed
        self.focal = focal
        self.policy = policy
        if environment_factory is None:
            from gaia_rl._native import Environment
            from gaia_rl.versions import require_compatible_versions
            require_compatible_versions(self.versions)
            environment_factory = Environment
        self.factory = environment_factory
        self.trace = GrowingTrace(self.source / 'decisions.jsonl.gz')
        self.writer = LiveReplayWriter(output, str(self.source.resolve()))
        self.env = None
        self.replay = None
        self.published_steps = -1

    def accept(self, row):
        snapshot, index = row['snapshot'], row['index']
        if self.env is None:
            self.env = self.factory(self.seed, 2000)
        actual = json.loads(self.env.snapshot_json())
        if snapshot != actual:
            raise ValueError(f'Native trace mismatch at decision {snapshot["decision_id"]}')
        if type(index) is not int or not 0 <= index < len(snapshot['candidates']):
            raise ValueError('Invalid recorded candidate index')
        if self.replay is None:
            players = snapshot['state']['players']
            focus = next((i for i, player in enumerate(players) if player['faction'] == self.focal), 0)
            if self.focal is not None and players[focus]['faction'] != self.focal:
                raise ValueError('Focal faction is missing from the recorded game')
            self.replay = {'schema_version': 1, 'metadata': {
                'seed': self.seed, 'policy': self.policy,
                'faction': players[focus]['faction'], 'focus_player': focus,
                'versions': self.versions, 'steps': 0}, 'events': [], 'frames': [frame(snapshot)]}
        self.env.step(snapshot['decision_id'], index)
        after = json.loads(self.env.snapshot_json())
        self.replay['frames'].append(frame(after, snapshot['player'],
            snapshot['candidates'][index]['action'], snapshot['candidates']))

    def poll(self):
        for row in self.trace.rows():
            self.accept(row)
        if self.replay is None:
            return 'waiting'
        status = 'running'
        if (self.source / 'failure.json').exists():
            status = 'failed'
        elif self.env.is_terminal():
            # Native final action may arrive before the producer finishes its result files.
            terminal, result = self.source / 'terminal.json', self.source / 'result.json'
            if not terminal.exists() or not result.exists():
                return 'waiting'
            result = json.loads(result.read_text())
            scores = dict(self.env.final_scores())
            if (json.loads(terminal.read_text()) != json.loads(self.env.snapshot_json())
                    or result.get('complete') is not True
                    or {int(k): v for k, v in result['scores'].items()} != scores
                    or result['steps'] != len(self.replay['frames']) - 1):
                raise ValueError('Producer/native terminal result mismatch')
            self.replay['metadata']['scores'] = scores
            status = 'complete'
        steps = len(self.replay['frames']) - 1
        if steps != self.published_steps or status != 'running':
            self.writer.write(self.replay, status)
            self.published_steps = steps
            print(f'{status}: {steps} recorded actions', flush=True)
        return status

    def close(self):
        self.trace.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True, help='Directory containing decisions.jsonl.gz')
    parser.add_argument('--manifest', type=Path, required=True, help='The original training manifest.json')
    parser.add_argument('--seed', required=True, help='Exact seed from that manifest/setup; never regenerated')
    parser.add_argument('--output', type=Path, required=True, help='New local frontend public/ai-live directory')
    parser.add_argument('--once', action='store_true', help='Publish only the current prefix; do not claim completion')
    args = parser.parse_args()
    observer = GameObserver(args.game.resolve(), json.loads(args.manifest.read_text()), args.output.resolve(), args.seed)
    try:
        while True:
            status = observer.poll()
            if args.once or status in ('failed', 'complete'):
                break
            time.sleep(2)
    finally:
        observer.close()


if __name__ == '__main__':
    main()
