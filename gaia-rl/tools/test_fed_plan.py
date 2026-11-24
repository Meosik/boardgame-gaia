import unittest

import fed_plan


def board(cells, radius=None):
    """cells: coord -> None (free space), 'planet' (unowned planet) or (owner, kind). Only the listed hexes exist
    unless `radius` adds free spaces around 0,0."""
    hexes = {}
    if radius is not None:
        for q in range(-radius, radius + 1):
            for r in range(-radius, radius + 1):
                if abs(q + r) <= radius:
                    hexes[f'{q},{r}'] = {'structures': [], 'planet': None, 'satellites': []}
    for coord, what in cells.items():
        cell = {'structures': [], 'planet': None, 'satellites': []}
        if what == 'planet':
            cell['planet'] = {'planet_type': 'Desert', 'owner': None, 'is_gaia_formed': False}
        elif what is not None:
            owner, kind = what
            cell['planet'] = {'planet_type': 'Desert', 'owner': owner, 'is_gaia_formed': False}
            cell['structures'] = [{'owner': owner, 'kind': kind}]
        hexes[coord] = cell
    return hexes


def state_of(hexes, faction='Terrans', tokens=3, federated=(), supply=(1,), tiles=(), qic=0, owned_tokens=()):
    structures = [{'hex': c, 'kind': s['kind']} for c, cell in hexes.items() for s in cell['structures'] if s['owner'] == 0]
    player = {'player_id': 0, 'faction': faction, 'structures': structures, 'federated_hexes': list(federated),
              'tech_tiles': list(tiles), 'covered_tech_tiles': [], 'moweyds_power_ring_hexes': [],
              'federation_tokens': list(owned_tokens), 'gray_federation_tokens': [],
              'research_tracks': {'terraforming': 0},
              'resources': {'qic': qic, 'power': {'bowl1': tokens, 'bowl2': 0, 'bowl3': 0}}}
    return {'players': [player], 'board': {'hexes': hexes, 'spaceship_tiles': {}, 'lost_planet': None},
            'research_board': {'federation_tokens': list(supply)}}


PI, TS, MINE = 'PlanetaryInstitute', 'TradingStation', 'Mine'


def tile(number, bonus=None):
    return {'kind': 'Standard', 'tile': number, 'advance_track': None, 'bonus_build_coord': bonus}


def lab(coord, choice):
    return {'action': {'type': 'Upgrade', 'coord': coord, 'to': 'ResearchLab', 'tech_tile_choice': choice}}


class Ready(unittest.TestCase):
    def test_adjacent_buildings_with_seven_power_need_no_satellite(self):
        state = state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, TS)}), tokens=0)
        p = fed_plan.plan(state, 0)
        self.assertTrue(p['ready'])
        self.assertEqual(p['target'], {'hexes': ['0,0', '1,0', '2,0'], 'power': 7, 'short': 0, 'sats': 0})

    def test_a_gap_takes_one_satellite_and_one_power_token(self):
        cells = {'0,0': (0, PI), '1,0': (0, TS), '2,0': None, '3,0': (0, TS)}
        self.assertEqual(fed_plan.plan(state_of(board(cells), tokens=1), 0)['target']['sats'], 1)
        self.assertTrue(fed_plan.plan(state_of(board(cells), tokens=1), 0)['ready'])
        short = fed_plan.plan(state_of(board(cells), tokens=0), 0)
        self.assertFalse(short['ready'])
        self.assertEqual(short['reason'], 'satellites')
        self.assertEqual(short['blocked']['sats'], 1)

    def test_a_planet_in_the_only_gap_is_no_route(self):
        cells = {'0,0': (0, PI), '1,0': (0, TS), '2,0': 'planet', '3,0': (0, TS)}
        p = fed_plan.plan(state_of(board(cells), tokens=9), 0)
        self.assertFalse(p['ready'])
        self.assertEqual(p['reason'], 'route')
        self.assertEqual(p['target']['short'], 2)                 # the reachable group: institute + station = 5

    def test_the_route_goes_around_a_blocked_gap_when_the_board_allows(self):
        cells = {'0,0': (0, PI), '1,0': (0, TS), '2,0': 'planet', '3,0': (0, TS)}
        p = fed_plan.plan(state_of(board(cells, radius=4), tokens=9), 0)
        self.assertTrue(p['ready'])
        self.assertEqual(p['target']['sats'], 2)

    def test_an_empty_token_supply_is_not_ready(self):
        state = state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, TS)}), supply=())
        p = fed_plan.plan(state, 0)
        self.assertFalse(p['ready'])
        self.assertEqual(p['reason'], 'token')

    def test_six_power_is_short_by_one(self):
        p = fed_plan.plan(state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE)})), 0)
        self.assertEqual((p['ready'], p['reason'], p['target']['short']), (False, 'power', 1))

    def test_xenos_with_the_institute_need_six(self):
        p = fed_plan.plan(state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE)}), faction='Xenos'), 0)
        self.assertEqual((p['need'], p['ready']), (6, True))

    def test_the_large_building_tile_adds_one(self):
        p = fed_plan.plan(state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE)}), tiles=(6,)), 0)
        self.assertEqual((p['target']['power'], p['ready']), (7, True))


class ExistingFederation(unittest.TestCase):
    def test_buildings_and_spaces_next_to_a_federation_are_out(self):
        # federation on -1,0; 0,0 touches it (out), 1,0 is free but its only link to 3,0 (2,0) is fine
        cells = {'-1,0': (0, PI), '0,0': (0, TS), '1,0': (0, TS), '2,0': None, '3,0': (0, TS)}
        p = fed_plan.plan(state_of(board(cells), federated=('-1,0',)), 0)
        self.assertEqual(sorted(p['buildings']), ['1,0', '3,0'])
        self.assertEqual(p['target'], {'hexes': ['1,0', '3,0'], 'power': 4, 'short': 3, 'sats': 1})

    def test_ivits_grow_their_federation_and_count_all_of_it(self):
        cells = {'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, TS), '3,0': None, '4,0': (0, PI), '5,0': (0, TS), '6,0': (0, TS)}
        state = state_of(board(cells), faction='Ivits', federated=('0,0', '1,0', '2,0'), owned_tokens=(1,), qic=1)
        p = fed_plan.plan(state, 0)
        self.assertEqual((p['need'], p['inside']), (14, 7))
        self.assertTrue(p['ready'])
        self.assertEqual(p['target']['sats'], 1)
        self.assertFalse(fed_plan.plan(state_of(board(cells), faction='Ivits', federated=('0,0', '1,0', '2,0'),
                                                owned_tokens=(1,), qic=0), 0)['ready'])


class MovesAndSites(unittest.TestCase):
    def setUp(self):
        self.cells = {'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE), '3,0': 'planet', '2,1': None, '2,2': 'planet'}
        self.candidates = [{'action': {'type': 'Pass'}},
                           {'action': {'type': 'Upgrade', 'coord': '2,0', 'to': TS, 'tech_tile_choice': None}},
                           {'action': {'type': 'Upgrade', 'coord': '1,0', 'to': 'ResearchLab', 'tech_tile_choice': tile(1)}},
                           {'action': {'type': 'Upgrade', 'coord': '1,0', 'to': 'ResearchLab', 'tech_tile_choice': tile(2)}},
                           {'action': {'type': 'Build', 'coord': '3,0'}}]

    def test_moves_that_fill_the_shortfall_come_first_and_a_lab_is_no_gain(self):
        p = fed_plan.plan(state_of(board(self.cells)), 0, self.candidates)
        self.assertEqual([(m['index'], m['to'], m['ready_after'], m['short_after']) for m in p['moves']],
                         [(1, TS, True, 0), (4, MINE, True, 0)])

    def test_a_mine_next_to_an_existing_federation_is_no_move(self):
        cells = {'-1,0': (0, PI), '0,0': 'planet', '2,0': (0, TS), '3,0': 'planet'}
        candidates = [{'action': {'type': 'Build', 'coord': '0,0'}}, {'action': {'type': 'Build', 'coord': '3,0'}}]
        p = fed_plan.plan(state_of(board(cells), federated=('-1,0',)), 0, candidates)
        self.assertEqual([m['coord'] for m in p['moves']], ['3,0'])

    def test_bescods_institute_lifts_the_other_home_planet_buildings(self):
        hexes = board({'0,0': (0, TS), '1,0': (0, MINE), '2,0': (0, MINE)})
        for coord in ('1,0', '2,0'):
            hexes[coord]['planet']['planet_type'] = 'Titanium'
        candidates = [{'action': {'type': 'Upgrade', 'coord': '0,0', 'to': PI, 'tech_tile_choice': None}}]
        p = fed_plan.plan(state_of(hexes, faction='Bescods'), 0, candidates)
        self.assertEqual(p['target']['power'], 4)
        self.assertEqual((p['moves'][0]['short_after'], p['moves'][0]['ready_after']), (0, True))   # 3 + 2 + 2

    def test_a_lab_that_takes_the_large_building_tile_opens_the_federation(self):
        # institute 3 + station 2 + mine 1 = 6; station -> lab keeps 2, tile 6 makes the institute 4 -> 7
        state = state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE)}))
        p = fed_plan.plan(state, 0, [lab('1,0', tile(1)), lab('1,0', tile(6)), lab('1,0', tile(2))])
        self.assertEqual([(m['index'], m['large_tile_after'], m['ready_after']) for m in p['moves']], [(1, True, True)])
        every = fed_plan.plan(state, 0, [lab('1,0', tile(1)), lab('1,0', tile(6)), lab('1,0', tile(2))], every=True)
        self.assertEqual([(m['index'], m['ready_after']) for m in every['moves']], [(1, True), (0, False)])
        raw = fed_plan.plan(state, 0, [lab('1,0', tile(1)), lab('1,0', tile(6)), lab('1,0', tile(2))], every=True, merge=False)
        self.assertEqual([(m['index'], m['ready_after']) for m in raw['moves']], [(1, True), (0, False), (2, False)])

    def test_covering_the_large_building_tile_takes_its_power_away(self):
        state = state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE)}), tiles=(6,))
        cover = {'kind': 'Advanced', 'track': 'Economy', 'covered_tile': 6, 'advance_track': None}
        p = fed_plan.plan(state, 0, [lab('1,0', cover)], every=True)
        self.assertTrue(p['ready'])
        self.assertEqual((p['moves'][0]['large_tile_after'], p['moves'][0]['short_after']), (False, 1))

    def test_a_tile_that_comes_with_a_mine_adds_the_mine(self):
        state = state_of(board({'0,0': (0, PI), '1,0': (0, TS), '2,0': (0, MINE), '3,0': 'planet'}))
        p = fed_plan.plan(state, 0, [lab('1,0', tile(3, bonus='3,0'))])
        self.assertEqual((p['moves'][0]['bonus_mine'], p['moves'][0]['ready_after']), ('3,0', True))

    def test_a_verdict_that_hangs_on_funds_is_marked_for_a_move_with_a_tile(self):
        # after the tile the power is there, but the gap needs a satellite the seat cannot pay now
        cells = {'0,0': (0, PI), '1,0': (0, TS), '2,0': None, '3,0': (0, MINE)}
        p = fed_plan.plan(state_of(board(cells), tokens=0), 0, [lab('1,0', tile(6))], every=True)
        self.assertEqual((p['moves'][0]['ready_after'], p['moves'][0]['funds_unknown']), (False, True))

    def test_sites_next_to_the_target_and_one_space_away(self):
        p = fed_plan.plan(state_of(board(self.cells)), 0, self.candidates)
        self.assertEqual([(s['coord'], s['gap'], s['legal_now']) for s in p['sites']],
                         [('2,2', 1, False), ('3,0', 0, True)])


if __name__ == '__main__':
    unittest.main()
