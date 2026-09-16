"""Replay-only publication to the approved mini-PC origin; never restart services."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

from evaluation_replays import ROOT, validate_batch
from publish_replays import publish, read_catalog, write_json

HOST = 'agentmaco'
PROJECT = Path('/home/sohegi/projects/gaia')
CONTAINER = 'gaia-gaia-server-1'
STATIC = '/app/gaia-frontend/dist'
PUBLIC = 'https://shgaia.com/ai-replays/'


def command(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, capture_output=True, **kwargs).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def remote_publish(stage, expected_index_hash, published_at):
    """Runs on the origin host with a staged, validated batch and preserved backups."""
    with Path('/tmp/gaia-auto-replay-deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        incoming = stage/'incoming'
        validate_batch(incoming)
        destination = PROJECT/'gaia-frontend/public/ai-replays'
        before = json.loads(command(['docker', 'inspect', CONTAINER,
                                     '--format', '{{json .State}}']))
        container_id = command(['docker', 'inspect', CONTAINER, '--format', '{{.Id}}']).strip()
        image = command(['docker', 'inspect', CONTAINER, '--format', '{{.Image}}']).decode().strip()
        configured = command(['docker', 'inspect', CONTAINER, '--format', '{{.Config.Image}}']).decode().strip()
        if '@' in configured or configured.startswith('sha256:'):
            raise ValueError('Immutable image reference needs an explicit deployment decision')
        live_index = command(['docker', 'exec', CONTAINER, 'cat', STATIC+'/ai-replays/index.json'])
        if digest(live_index) != expected_index_hash or (destination/'index.json').read_bytes() != live_index:
            raise ValueError('Origin catalog changed or differs from source; nothing published')
        history = read_catalog(destination/'archive-index.json')
        for game in history:
            live_hash = command(['docker', 'exec', CONTAINER, 'sha256sum', STATIC+'/ai-replays/'+game['file']]).decode().split()[0]
            if digest((destination/game['file']).read_bytes()) != live_hash:
                raise ValueError('Origin replay payload differs from durable source')
        shutil.copytree(destination, stage/'backup')
        merged = stage/'merged'
        shutil.copytree(destination, merged)
        visible, retained = publish(incoming, merged, now=published_at)
        kept = {g['file'] for g in read_catalog(merged/'archive-index.json')}
        removed = [g['file'] for g in history if g['file'] not in kept]
        # Preserve the actual live static assets, even if an earlier hot deployment
        # differs from its base image. Only the replay subtree changes in the new image.
        command(['docker', 'cp', CONTAINER+':'+STATIC, stage/'runtime-dist'])
        shutil.rmtree(stage/'runtime-dist/ai-replays')
        shutil.copytree(merged, stage/'runtime-dist/ai-replays')
        command(['docker', 'cp', CONTAINER+':/app/gaia-server', stage/'gaia-server'])
        base_tag = 'gaia-replay-base:' + stage.name.lower()
        command(['docker', 'tag', image, base_tag])
        (stage/'Dockerfile').write_text(
            f'FROM {base_tag}\nRUN rm -rf {STATIC}/ai-replays\n'
            f'COPY runtime-dist/ {STATIC}/\nCOPY gaia-server /app/gaia-server\n')
        (stage/'.dockerignore').write_text('*\n!Dockerfile\n!runtime-dist/\n!runtime-dist/**\n!gaia-server\n')
        release = 'gaia-replays:' + stage.name.lower()
        build = subprocess.run(['docker', 'build', '-t', release, str(stage)], capture_output=True)
        (stage/'image-build.log').write_bytes(build.stdout + build.stderr)
        build.check_returncode()
        # Detect concurrent deployment before touching the live catalog or source.
        if (command(['docker', 'inspect', CONTAINER, '--format', '{{.Id}}']).strip() != container_id
                or command(['docker', 'exec', CONTAINER, 'cat', STATIC+'/ai-replays/index.json']) != live_index):
            raise ValueError('Concurrent deployment detected; staged release not applied')
        transfer = '/tmp/' + stage.name
        command(['docker', 'exec', CONTAINER, 'mkdir', '-p', transfer])
        command(['docker', 'cp', str(merged)+ '/.', CONTAINER+':'+transfer])
        # Payloads first, atomic catalog moves second, authorized expiration last.
        target = STATIC+'/ai-replays'
        script = f'set -eu; cd {shlex.quote(transfer)}; '
        script += f'for f in *.json.gz; do if [ ! -f {target}/"$f" ]; then cp "$f" {target}/"$f".tmp; mv {target}/"$f".tmp {target}/"$f"; fi; done; '
        for name in ('archive-index.json', 'index.json', 'publication-times.json'):
            script += f'mv {shlex.quote(name)} {target}/{name}; '
        for filename in removed:
            script += f'rm {target}/{shlex.quote(filename)}; '
        command(['docker', 'exec', CONTAINER, 'sh', '-c', script])
        publish(incoming, destination, now=published_at)
        # Recreating the service from either existing tag keeps the new replay data.
        for tag in {configured, 'gaia-gaia-server:latest'}:
            command(['docker', 'tag', release, tag])
        after = json.loads(command(['docker', 'inspect', CONTAINER, '--format', '{{json .State}}']))
        if after['StartedAt'] != before['StartedAt']:
            raise ValueError('Unexpected service restart during replay publication')
        for name in ('index.json', 'archive-index.json', 'publication-times.json'):
            if command(['docker', 'exec', CONTAINER, 'cat', target+'/'+name]) != (destination/name).read_bytes():
                raise ValueError('Published catalog verification failed')
        result = {'visible': visible, 'retained': retained, 'removed_viewing_files': removed,
                  'backup': str(stage/'backup'), 'release_image': release,
                  'previous_image': image, 'service_restarted': False,
                  'published_at': published_at, 'index_sha256': digest((destination/'index.json').read_bytes())}
        write_json(stage/'result.json', result)
        return result


def deploy(source, evidence):
    games = validate_batch(source)
    evidence.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix='attempt-', dir=evidence))
    expected = digest(command(['curl', '-fsS', '--max-time', '30', PUBLIC+'index.json']))
    stage = command(['ssh', '-o', 'BatchMode=yes', HOST, 'mktemp -d /tmp/gaia-auto-replays.XXXXXXXX']).decode().strip()
    write_json(evidence/'remote-stage.json', {'host': HOST, 'stage': stage})
    write_json(attempt/'remote-stage.json', {'host': HOST, 'stage': stage})
    command(['scp', '-q', '-r', source, HOST+':'+stage+'/incoming'])
    for name in ('deploy_replays.py', 'evaluation_replays.py', 'publish_replays.py', 'replay_log.py', 'replay_income.py'):
        command(['scp', '-q', Path(__file__).parent/name, HOST+':'+stage+'/'+name])
    now = time.time()
    remote = ['python3', stage+'/deploy_replays.py', '--remote-stage', stage,
              '--expected-index', expected, '--published-at', str(now)]
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', HOST, shlex.join(remote)], capture_output=True)
    (evidence/'deploy.log').write_bytes(result.stdout + result.stderr)
    (attempt/'deploy.log').write_bytes(result.stdout + result.stderr)
    result.check_returncode()
    receipt = json.loads(command(['ssh', '-o', 'BatchMode=yes', HOST, 'cat '+shlex.quote(stage+'/result.json')]))
    # Verify the actual public origin, not just SSH/container files.
    public_index = command(['curl', '-fsS', '--max-time', '30', PUBLIC+'index.json'])
    if digest(public_index) != receipt['index_sha256']:
        raise ValueError('Public catalog differs from deployed origin')
    for game in games:
        data = command(['curl', '-fsS', '--max-time', '30', PUBLIC+game['file']])
        if data != (source/game['file']).read_bytes():
            raise ValueError('Public replay differs from verified export')
    write_json(evidence/'receipt.json', receipt)
    write_json(attempt/'receipt.json', receipt)
    # Local development/build source follows the same approved retention policy.
    for destination in (ROOT/'gaia-frontend/public/ai-replays', ROOT/'gaia-frontend/dist/ai-replays'):
        if destination.exists():
            publish(source, destination, now=now)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote-stage', type=Path, required=True)
    parser.add_argument('--expected-index', required=True)
    parser.add_argument('--published-at', type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(remote_publish(args.remote_stage, args.expected_index, args.published_at)))
