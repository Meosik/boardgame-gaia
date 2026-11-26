import json
import tempfile
import unittest
from pathlib import Path

import setup_report as sr


def planet(kind, owner=None):
    return {'planet': {'planet_type': kind, 'owner': owner}, 'structures': []}


def player(seat, faction, hexes):
    return {'player_id': seat, 'faction': faction, 'structures': [{'hex': h} for h in hexes],
            'research_tracks': {'navigation': 0}, 'tech_tiles': [], 'covered_tech_tiles': [],
            'resources': {'qic': 1}}


def synthetic_state():
    cells = {'0,0': planet('Terra', 0), '3,0': planet('Terra', 0), '5,1': planet('Desert', 1)}
    cells['0,0']['structures'] = [{'owner': 0}]
    cells['3,0']['structures'] = [{'owner': 0}]
    cells['5,1']['structures'] = [{'owner': 1}]
    cells.update({'1,0': planet('Oxide'), '0,1': planet('Volcanic'), '-1,0': planet('Gaia'),
                  '4,0': planet('Desert'), '3,1': planet('Ice'), '0,-2': planet('Swamp')})
    cells['2,5'] = {'planet': None, 'structures': []}
    return {'board': {'hexes': cells},
            'players': [player(0, 'Terrans', ['0,0', '3,0']), player(1, 'Xenos', ['5,1'])]}


class SetupReportTest(unittest.TestCase):
    def test_added_planets(self):
        seat = sr.seat_report(synthetic_state(), 0)
        self.assertEqual(seat['reach'], 1)
        self.assertEqual(seat['pairwise_distance'], [3])
        self.assertEqual(seat['added_planets'], {'second_adds': 2, 'first_adds': 3})
        self.assertEqual(seat['min_distance_to_opponent'], {'0,0': 6, '3,0': 3})

    def test_site_ranking(self):
        seat = sr.seat_report(synthetic_state(), 0)
        order = [s['coord'] for s in seat['top_sites']]
        # steps 1 (near-opponent Ice before Oxide), Volcanic 2, Desert 3, Gaia off the ring; QIC site last
        self.assertEqual(order, ['3,1', '1,0', '0,1', '4,0', '-1,0'])
        sites = {s['coord']: s for s in seat['sites']}
        self.assertEqual(sites['3,1']['steps'], 1)
        self.assertTrue(sites['3,1']['near_opponent'])
        self.assertEqual(sites['4,0']['steps'], 3)
        self.assertIsNone(sites['-1,0']['steps'])
        self.assertTrue(sites['0,-2']['qic'])
        self.assertFalse(sites['1,0']['qic'])
        self.assertEqual(seat['sites'][-1]['coord'], '0,-2')

    def test_single_structure_has_no_added(self):
        seat = sr.seat_report(synthetic_state(), 1)
        self.assertIsNone(seat['added_planets'])
        self.assertEqual(seat['faction'], 'Xenos')

    def test_main_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)/'pair-000'/'game-0'
            game.mkdir(parents=True)
            (game/'setup_state.json').write_text(json.dumps(synthetic_state()))
            (game/'result.json').write_text(json.dumps({'seed': '42'}))
            sr.main([tmp])
            report = json.loads((Path(tmp)/'setup_report.json').read_text())
            self.assertEqual(report['games'][0]['seed'], '42')
            self.assertIn('Terrans', (Path(tmp)/'setup_report.md').read_text())


if __name__ == '__main__':
    unittest.main()
