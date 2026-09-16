from pathlib import Path
import unittest

from import_uiqoo_setup import convert

URL = ('https://uiqoo.kr/boardgames/gaiaproject/randomizer.html?'
       'player=4&seed=145526867337&centerbalance=true&expan=lostfleet')
HTML = (Path(__file__).parent / 'fixtures/uiqoo-145526867337.html').read_text()


class ObservedSetupTest(unittest.TestCase):
    def test_reference_tiles_and_no_invented_actions(self):
        s = convert(HTML, URL)
        self.assertEqual(s['factions_in_source_order'],
                         ['Geodens', 'Tinkeroids', 'HadschHallas', 'Moweyds'])
        self.assertEqual(s['round_tile_ids'], [1, 3, 6, 7, 2, 12])
        self.assertEqual(s['tech_tile_slot_ids'], [3, 2, 9, 8, 5, 10, 6, 7, 4])
        self.assertEqual(s['advanced_tech_tile_ids'], [7, 9, 13, 3, 8, 5, 19])
        self.assertEqual(s['booster_ids'], [7, 11, 5, 13, 6, 4, 9])
        self.assertEqual(s['final_scoring_ids'], [10, 9])
        self.assertEqual(s['spaceship_federation_ids'], [11, 12, 8, 14])
        self.assertEqual(s['spaceship_tech_ids'], [13, 12, 11])
        self.assertEqual(s['artifact_ids'], [12, 6, 8, 3])
        self.assertEqual(s['terraforming_color_order'],
                         ['Terra', 'Swamp', 'Titanium', 'Oxide', 'Ice', 'Desert', 'Volcanic'])
        self.assertEqual(s['terraforming_level_5_token'], 2)
        self.assertEqual(s['economy_research_tile_side'], 'vp')
        self.assertEqual(s['lost_fleet_advanced_tech_requirement'], 'vp')
        self.assertIsNone(s['player_assignments'])
        self.assertIsNone(s['bids'])
        self.assertEqual(s['actions'], [])

    def test_reference_lattice_and_sides(self):
        s = convert(HTML, URL)
        self.assertEqual(len(s['sectors']), 18)
        self.assertEqual(len(s['interspaces']), 10)
        self.assertLess(s['geometry_max_rounding_residual_hex'], .06)
        by_id = {p['sector_id']: p for p in s['sectors']}
        for id, side, origin, rotation in [(1, None, '0,0', 0), (5, 'A', '9,-6', 3),
                                            (12, 'B', '8,-8', 2), (15, 'A', '2,-7', 0)]:
            p = by_id[id]
            self.assertEqual((p['side'], p['origin'], p['rotation']), (side, origin, rotation))
        self.assertEqual(next(t['coord'] for t in s['interspaces'] if t['kind'] == 'twilight'), '4,2')

    def test_reject_unsupported_source_and_missing_seed(self):
        for url in [URL.replace('player=4', 'player=2'), URL.replace('uiqoo.kr', 'example.com'),
                    URL.replace('seed=145526867337&', '')]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                convert(HTML, url)

    def test_unknown_assets_and_faces_are_not_guessed(self):
        for old, new in [('tech_4c.png', 'tech_unknown.png'), ('econ_vp.png', 'econ_unknown.png'),
                         ('advcond_vp.png', 'advcond_unknown.png'),
                         ('map_tile_05a.png', 'map_tile_05b.png'),
                         ('map_deep_17b.png', 'map_deep_17.png')]:
            with self.subTest(asset=old), self.assertRaises(ValueError):
                convert(HTML.replace(old, new), URL)

    def test_missing_duplicate_and_invalid_geometry_fail(self):
        for content in [HTML.replace('id="map0"', 'id="absent"'),
                        HTML + '<img id="map0" src="map_tile_05a.png">',
                        HTML.replace('rotate(300deg)', 'rotate(301deg)'),
                        HTML.replace('width: 6.4%', 'width: 6.5%')]:
            with self.subTest(content=content[-60:]), self.assertRaises((ValueError, KeyError)):
                convert(content, URL)


if __name__ == '__main__':
    unittest.main()
