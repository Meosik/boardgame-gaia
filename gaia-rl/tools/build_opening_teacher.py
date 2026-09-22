"""Build A-open without editing frozen A: filter only its BGG candidate catalog."""
import argparse
import difflib
import json
from pathlib import Path
import shutil

import teacher_ab as ab

ALLOWED = {
    'Terrans': ('1AC+1M', '1RL+2M', '1RL+4M'),
    'HadschHallas': ('1RL+4M', '1RL+1TS+2M'),
    'Xenos': ('1RL+5M', '1RL+4M', '1RL+1TS+2M'),
    'Taklons': ('1RL+5M', '1RL+4M'),
}
CATALOG = 'bgg_openings/catalog.py'
RETURN = '    return {f: tuple(rows) for f, rows in catalog.items()}\n'


def build(destination):
    baseline = ab.resolve_teacher('baseline')
    if ab.frozen_problems(baseline):
        raise ValueError('Frozen A changed')
    source = Path(baseline['source'])
    destination = Path(destination)
    if destination.exists() or destination.parent.resolve() != (ab.ROOT/'gaia-rl').resolve():
        raise ValueError('Use a fresh direct gaia-rl child; never overwrite a teacher')
    before = (source/CATALOG).read_text()
    if before.count(RETURN) != 1:
        raise ValueError('Catalog patch no longer matches frozen A')
    replacement = ('    # User-approved A-open candidates; preserve source order and provenance.\n'
                   f'    allowed = {ALLOWED!r}\n'
                   '    return {f: tuple(row for row in rows\n'
                   '                     if f not in allowed or row.label in allowed[f])\n'
                   '            for f, rows in catalog.items()}\n')
    after = before.replace(RETURN, replacement)
    for path in source.rglob('*'):
        if not path.is_file() or path.name == 'FROZEN.json' or '__pycache__' in path.parts:
            continue
        target = destination/path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (destination/CATALOG).write_text(after)
    (destination/'opening-only.diff').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='A/'+CATALOG,
        tofile='A-open/'+CATALOG)))
    changed = [str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()
               and p.name != 'FROZEN.json' and '__pycache__' not in p.parts
               and p.read_bytes() != (destination/p.relative_to(source)).read_bytes()]
    if changed != [CATALOG]:
        raise ValueError(f'Unexpected diff: {changed}')
    spec = {key: baseline[key] for key in ('factory', 'kwargs')}
    spec['source'] = str(destination.resolve().relative_to(ab.ROOT))
    spec['description'] = 'A-open: frozen A with only BGG R1 catalog filtered; original fallback.'
    ab.write_json(destination/'teacher.json', spec)
    manifest = {'baseline_fingerprint': ab.fingerprint(baseline), 'changed': changed,
                'allowed': ALLOWED, 'kwargs': baseline['kwargs'], 'fixed_openings': False,
                'fallback': 'unchanged four_factions/preparation.py::publish_current',
                'games_run': 0}
    ab.write_json(destination/'opening-manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    print(json.dumps(build(parser.parse_args().destination), indent=2))
