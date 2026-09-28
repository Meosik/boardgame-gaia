"""Create a new, isolated A02 derivative; never edits the frozen or current teacher."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'gaia-rl/baseline-teacher-20260917'
MODULE = Path(__file__).with_name('a02_round_investment.py')


def verify_baseline():
    manifest = json.loads((BASELINE / 'FROZEN.json').read_text())
    for name, expected in manifest['files'].items():
        if hashlib.sha256((BASELINE / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen source changed: {name}')
    return manifest


def build(output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    if not output.is_relative_to(ROOT / 'gaia-rl/runs'):
        raise ValueError('Disposable A02 sources must live under gaia-rl/runs')
    frozen = verify_baseline()
    shutil.copytree(BASELINE, output, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    output.chmod(output.stat().st_mode | 0o200)
    pattern = re.compile(r'Path\(__file__\)\.resolve\(\)\.parents\[([23])\]')
    relocated = []
    for path in output.rglob('*.py'):
        original = BASELINE / path.relative_to(output)
        text = path.read_text()
        updated = pattern.sub(lambda m: f'Path({str(original.parents[int(m[1])])!r})', text)
        if text != updated:
            path.chmod(path.stat().st_mode | 0o200)
            path.write_text(updated)
            relocated.append(path.relative_to(output).as_posix())
    timed = output / 'four_factions/timed.py'
    anchor = '    from four_factions.preparation import search, check_time\n'
    replacement = ('    from four_factions.preparation import search as original_search, check_time\n'
                   '    from a02_round_investment import dispatch\n'
                   '    from functools import partial\n'
                   '    search = partial(dispatch, original_search)\n')
    text = timed.read_text()
    if text.count(anchor) != 1:
        raise ValueError('Frozen timed-worker import anchor changed')
    timed.chmod(timed.stat().st_mode | 0o200)
    timed.write_text(text.replace(anchor, replacement))
    shutil.copyfile(MODULE, output / MODULE.name)
    files = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob('*.py'))}
    record = dict(baseline=str(BASELINE), frozen_files=len(frozen['files']),
                  default_off_flag='GAIA_A02_ROUND_INVESTMENT',
                  scope='Terrans/Taklons local-pass decisions; next-round investment comparison',
                  relocated_root_lookups=relocated, python_files=files,
                  builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output / 'A02_DERIVATION.json').write_text(json.dumps(record, indent=2) + '\n')
    verify_baseline()
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
