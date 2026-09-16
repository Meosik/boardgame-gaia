"""Read-only quartet run spectator: follow new games, retain immutable old records."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from live_replays import atomic_json
from watch_ai_game import GameObserver


def recorded_games(run, manifest):
    """Only original preregistered games; never regenerate a seed or start a game."""
    games = []
    for split in ('training', 'validation'):
        for index, spec in enumerate(manifest['setups'][split]):
            games.append((run / split / str(index), spec['seed'], None))
    for arm in ('bc_only', 'baseline_ppo', 'bc_ppo', 'teacher'):
        for index, spec in enumerate(manifest['setups']['evaluation']):
            for faction in manifest['factions']:
                games.append((run / 'evaluation' / arm / f'{index}-{faction}', spec['seed'], faction))
    return [game for game in games if (game[0] / 'decisions.jsonl.gz').exists()]


class RunObserver:
    def __init__(self, run, output, observer_factory=GameObserver, previous=None):
        self.run, self.output = Path(run).resolve(), Path(output).resolve()
        self.manifest = json.loads((self.run / 'manifest.json').read_text())
        self.output.mkdir(parents=True, exist_ok=False)
        self.factory = observer_factory
        self.source = None
        self.observer = None
        self.entries = {}
        self.last_catalog = None
        if previous is not None:
            previous = Path(previous).resolve()
            for entry in json.loads((previous / 'index.json').read_text())['games']:
                if entry['status'] not in ('complete', 'failed'):
                    raise ValueError('Previous observer must finish before transfer')
                if not re.fullmatch(r'live-[a-f0-9]{16}-[0-9]+\.json\.gz', entry['file']):
                    raise ValueError('Invalid previous recording filename')
                (self.output / entry['file']).symlink_to(previous / entry['file'])
                self.entries[entry['id']] = entry

    def publish(self):
        if self.observer is None:
            return
        directory = self.observer.writer.directory
        index = directory / 'index.json'
        if not index.exists():
            return
        entry = json.loads(index.read_text())['games'][0]
        source = directory / entry['file']
        destination = self.output / entry['file']
        if not destination.exists():
            destination.symlink_to(source)
        self.entries[entry['id']] = entry
        catalog = {'schema_version': 1, 'games': sorted(self.entries.values(),
                   key=lambda item: item['updated_at'], reverse=True)}
        if catalog != self.last_catalog:
            atomic_json(self.output / 'index.json', catalog)
            self.last_catalog = catalog

    def poll(self):
        games = recorded_games(self.run, self.manifest)
        if not games:
            return 'waiting'
        source, seed, focal = max(games, key=lambda game: (game[0] / 'decisions.jsonl.gz').stat().st_mtime_ns)
        if source != self.source:
            if self.observer is not None:
                if self.observer.writer.status == 'running':
                    self.observer.poll()
                self.publish()
                self.observer.close()
            identity = hashlib.sha256(str(source).encode()).hexdigest()[:16]
            self.observer = self.factory(source, self.manifest,
                self.output / 'recordings' / identity, seed, focal=focal,
                policy='quartet_teacher' if self.manifest.get('mode') == 'competitive_teacher' else 'live_observer')
            self.source = source
            print(f'Following {source.relative_to(self.run)}', flush=True)
        if self.observer.writer.status == 'running':
            self.observer.poll()
        self.publish()
        status_path = self.run / 'progress.json'
        stage = json.loads(status_path.read_text()).get('stage') if status_path.exists() else None
        if stage in ('complete', 'failed', 'failed_evaluations'):
            if self.observer.writer.status == 'running' and self.observer.replay:
                self.observer.writer.write(self.observer.replay, 'failed')
                self.publish()
            return stage
        return 'running'

    def producer_stopped(self):
        if self.observer is not None and self.observer.writer.status == 'running':
            self.observer.poll()
            if self.observer.writer.status == 'running' and self.observer.replay:
                self.observer.writer.write(self.observer.replay, 'failed')
            self.publish()

    def close(self):
        if self.observer is not None:
            self.observer.close()


def process_identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New local ai-live directory')
    parser.add_argument('--pid', type=int, required=True, help='Existing producer; never started or signaled here')
    parser.add_argument('--previous', type=Path, help='Finished local observer catalog to retain for paused viewers')
    args = parser.parse_args()
    identity = process_identity(args.pid)
    if identity is None:
        parser.error('Producer is not running')
    observer = RunObserver(args.run, args.output, previous=args.previous)
    try:
        while True:
            status = observer.poll()
            if status in ('complete', 'failed', 'failed_evaluations'):
                break
            if process_identity(args.pid) != identity:
                observer.producer_stopped()
                break
            time.sleep(2)
    except Exception as error:
        # Keep the last validated catalog; never manufacture successful completion.
        atomic_json(observer.output / 'observer-error.json', {'error': repr(error), 'time': time.time()})
        current = observer.observer
        if current is not None and current.writer.status == 'running' and current.replay:
            current.writer.write(current.replay, 'failed')
            observer.publish()
        raise
    finally:
        observer.close()


if __name__ == '__main__':
    main()
