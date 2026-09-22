"""Explicit matched evaluation entry point; never trains or promotes weights."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
from action_purpose.evaluate import run_game, dump, source_hash, historical_hashes
from action_purpose.teacher import PurposeTeacher
from power_purpose.teacher import PowerPurposeTeacher
from gaia_rl.versions import runtime_versions, require_current_sources, require_compatible_versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--specs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():parser.error('New output directory required')
    specs = json.loads(args.specs.read_text())
    versions = runtime_versions()
    sources = [*Path(__file__).parent.glob('*.py'), ROOT/'gaia-rl/tools/replay_log.py',
               ROOT/'gaia-rl/tools/replay_income.py', ROOT/'gaia-engine/examples/replay_income.rs',
               ROOT/'target/release/examples/replay_income']
    def hashes():return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    own, base, historical = hashes(), source_hash(), historical_hashes()
    def guard():
        require_current_sources(ROOT);require_compatible_versions(versions)
        assert hashes() == own and source_hash() == base and historical_hashes() == historical
    guard();args.output.mkdir(parents=True)
    dump(args.output/'manifest.json', {'versions': versions, 'sources': own, 'base_hash': base,
         'historical_hashes': historical, 'specs': specs, 'training_steps': 0, 'promotion': False,
         'opponents': 'three deterministic random players; only focal player uses teacher'})
    for p in sources:
        dest = args.output/'sources'/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(p, dest)
    rows = []
    for i, spec in enumerate(specs):
        for label, policy in (('control', PurposeTeacher(3)), ('power-purpose', PowerPurposeTeacher())):
            guard()
            result, replay = run_game(spec, policy, versions)
            guard()
            with gzip.open(args.output/f'{label}-{i}.json.gz', 'xt') as f:json.dump(replay, f, separators=(',', ':'))
            dump(args.output/f'{label}-{i}.json', result)
            rows.append({'policy': label, 'game': i, 'faction': spec['faction'], 'vp': result['vp'], 'metrics': result['metrics']})
            print(json.dumps(rows[-1]), flush=True)
    dump(args.output/'report.json', {'games': rows, 'all_complete': True, 'promotion': False})


if __name__ == '__main__':main()
