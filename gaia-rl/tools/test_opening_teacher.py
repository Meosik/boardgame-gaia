"""The A-open treatment is a catalog filter, not new scoring or fallback logic."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from build_opening_teacher import ALLOWED, CATALOG
import teacher_ab as ab

VARIANT = ab.ROOT/'gaia-rl/a-open-20260917'


def query(source, code):
    result = subprocess.run([sys.executable, '-c',
        f'import sys; sys.path.insert(0, {str(source)!r});\n'+code],
        check=True, capture_output=True, text=True)
    return result.stdout


class OpeningVariantTests(unittest.TestCase):
    def test_only_catalog_file_differs_and_baseline_is_frozen(self):
        baseline = ab.resolve_teacher('baseline')
        self.assertEqual(ab.frozen_problems(baseline), [])
        source = Path(baseline['source'])
        changed = [str(p.relative_to(source)) for p in source.rglob('*.py')
                   if p.read_bytes() != (VARIANT/p.relative_to(source)).read_bytes()]
        self.assertEqual(changed, [CATALOG])
        spec = ab.resolve_teacher(str(VARIANT/'teacher.json'))
        for key in ('factory', 'kwargs'):
            self.assertEqual(spec[key], baseline[key])
        self.assertFalse(spec['kwargs'].get('fixed_openings', False))

    def test_exact_whitelist_preserves_all_source_observations_and_order(self):
        code = ('import json; from dataclasses import asdict\n'
                'from bgg_openings.catalog import load_catalog\n'
                'print(json.dumps({f:[asdict(r) for r in rows] for f,rows in load_catalog().items()}))')
        baseline = ab.resolve_teacher('baseline')
        a = json.loads(query(baseline['source'], code))
        b = json.loads(query(VARIANT, code))
        self.assertEqual(set(a), set(b))
        for faction, rows in a.items():
            expected = [r for r in rows if faction not in ALLOWED or r['label'] in ALLOWED[faction]]
            self.assertEqual(b[faction], expected)
        for faction, allowed in ALLOWED.items():
            self.assertEqual({r['label'] for r in b[faction]}, set(allowed))

    def test_original_fallback_and_round_two_controller(self):
        query(VARIANT, '''
from bgg_openings.test_controller import ControllerTests
test = ControllerTests()
test.test_fallback_is_original_teacher_not_an_invented_pass()
test.test_round_two_disables_guidance_and_clears_target()
''')

    def test_unproven_allowed_forecasts_cannot_override_fallback(self):
        query(VARIANT, '''
from dataclasses import asdict
from bgg_openings.catalog import load_catalog
from bgg_openings.planning import select_forecast
for rows in load_catalog().values():
    forecasts = [dict(complete=False, value=9999, first=0, r1_buildings=asdict(row.buildings)) for row in rows]
    assert select_forecast(rows, None, forecasts) is None
''')


if __name__ == '__main__':
    unittest.main()
