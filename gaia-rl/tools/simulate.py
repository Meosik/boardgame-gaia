"""Standard evaluation entry point: simulate, verify replays, publish automatically.

Training-internal games and frozen historical low-level runners are not published.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from deploy_replays import deploy
from evaluation_replays import ROOT, export_evaluation
from publish_replays import write_json


def finish(run):
    """Retry a saved evaluation; a missing export reconstructs it, never retrains."""
    status = run/'publication.json'
    if status.exists() and json.loads(status.read_text()).get('status') == 'published':
        # Revalidate report/export identity without republishing an old batch.
        export_evaluation(run)
        print('Already published; no simulation or promotion repeated.', flush=True)
        return
    write_json(status, {'status': 'pending', 'training': False})
    try:
        if not (run/'browser-replays').exists():
            subprocess.run(['cargo', 'build', '--locked', '-p', 'gaia-engine', '--release',
                            '--example', 'replay_income'], cwd=ROOT, check=True)
        source = export_evaluation(run)
        receipt = deploy(source, run/'replay-publication')
    except Exception as error:
        write_json(status, {'status': 'failed', 'training': False,
                            'error': str(error), 'retry': f'{sys.executable} {__file__} publish --run {run}'})
        raise
    write_json(status, {'status': 'published', 'training': False, **receipt})
    print('Published: https://shgaia.com/?aiReplay=1', flush=True)


def run_evaluation(args):
    from gaia_rl.versions import require_current_sources, require_compatible_versions, runtime_versions
    require_current_sources(ROOT)
    if args.output.exists():
        raise ValueError('New output directory required; use publish --run to retry publication')
    output = args.output.resolve()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': str(ROOT/'gaia-rl/experiments') + os.pathsep + os.environ.get('PYTHONPATH', '')}
    command = [sys.executable, '-B', '-u', '-m']
    if args.kind == 'ppo':
        if args.seeds < 1:
            raise ValueError('seeds must be positive')
        checkpoint = args.checkpoint.resolve()
        require_compatible_versions(json.loads((checkpoint/'metadata.json').read_text())['versions'])
        prefix = args.seed_prefix or datetime.now(timezone.utc).strftime('auto-eval-%Y%m%dT%H%M%SZ')
        command += ['gaia_rl.evaluation', '--checkpoint', str(checkpoint), '--seeds', str(args.seeds),
                    '--seed-prefix', prefix, '--output', str(output/'report.json')]
        if args.opponent:
            command += ['--opponent', str(args.opponent.resolve())]
        output.mkdir(parents=True)
    else:
        module = {'research': 'research_plans.evaluate', 'resources': 'resource_plans.evaluate'}.get(
            args.kind, 'current_actions.evaluate')
        command += [module, '--output', str(output), '--stages', args.stages]
        if args.specs:
            command += ['--specs', str(args.specs.resolve())]
        output.parent.mkdir(parents=True, exist_ok=True)
    versions = runtime_versions()
    # Teacher runner creates its own output; keep launch evidence in the parent until then.
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if output.exists():
        write_json(output/'auto-replay-launch.json', {
            'command': command, 'returncode': result.returncode, 'versions': versions,
            'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'training': False})
    result.check_returncode()
    require_current_sources(ROOT)
    require_compatible_versions(versions)
    finish(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='kind', required=True)
    ppo = commands.add_parser('ppo', help='Complete PPO evaluation, followed by automatic public replays')
    ppo.add_argument('--checkpoint', type=Path, required=True)
    ppo.add_argument('--opponent', type=Path)
    ppo.add_argument('--seeds', type=int, default=2)
    ppo.add_argument('--seed-prefix')
    ppo.add_argument('--output', type=Path, required=True)
    purpose = commands.add_parser('purpose', help='Current teacher comparison, then automatic public replays')
    purpose.add_argument('--output', type=Path, required=True)
    purpose.add_argument('--specs', type=Path)
    purpose.add_argument('--stages', default='0,1,2,3,4')
    research = commands.add_parser('research', help='Hadsch two-income plans versus current teacher, with automatic replays')
    research.add_argument('--output', type=Path, required=True)
    research.add_argument('--specs', type=Path, required=True)
    research.add_argument('--stages', default='0,1', help='0=current stage1, 1=research plans')
    resources = commands.add_parser('resources', help='Xenos conditional resource plans, with automatic replays')
    resources.add_argument('--output', type=Path, required=True)
    resources.add_argument('--specs', type=Path, required=True)
    resources.add_argument('--stages', default='0,1', help='0=current stage1, 1=resource plans')
    retry = commands.add_parser('publish', help='Publish an existing completed evaluation; no new games')
    retry.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    if args.kind == 'publish':
        finish(args.run.resolve())
    else:
        run_evaluation(args)


if __name__ == '__main__':
    main()
