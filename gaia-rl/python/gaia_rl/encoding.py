"""Versioned flat features with explicit board positions and concrete candidate parameters."""
import numpy as np
from gymnasium import spaces
from .vocabulary import CATEGORIES
from ._native import ENGINE_BUILD_ID, ENV_SCHEMA_VERSION

ENCODING_VERSION = 3
BOARD_CAPACITY = 256
CATEGORY_IDS = {name: i + 1 for i, name in enumerate(CATEGORIES)}
ACTION_FIELDS = (
    'phase', 'type', 'to', 'to.Academy', 'track', 'id', 'tile', 'tile.pool',
    'tile.tile', 'booster_id', 'accept', 'gain_before', 'charge_first', 'kind',
    'count', 'ship', 'artifact', 'copy_federation_token_kind', 'bonus_tech_tile',
    'bonus_research_track', 'token_kind', 'token.source', 'token.kind', 'token.ship',
    'tech_tile_choice.kind', 'tech_tile_choice.tile', 'tech_tile_choice.advance_track',
    'tech_tile_choice.track', 'tech_tile_choice.covered_tile', 'choice.kind',
    'choice.tile', 'choice.advance_track', 'choice.track', 'choice.covered_tile',
)
COORD_ROLES = ('coord', 'mine_coord', 'bonus_build_coord',
               'tech_tile_choice.bonus_build_coord', 'choice.bonus_build_coord',
               'hexes', 'satellite_hexes')
PLAYER_SCALARS = ('faction', 'vp', 'passed', 'booster', 'exploration_shuttles_available',
    'gaiaformers_total', 'gaiaformers_deployed', 'gaiaformers_in_gaia_area',
    'pi_ability_used', 'first_colonization_bonus_used', 'academy_qic_action_used_this_round',
    'gleens_special_action_used_this_round', 'space_giants_special_action_used_this_round',
    'round_booster_special_action_used_this_round', 'faction_special_action_used_this_round',
    'tinkeroids_selected_tile')
PLAYER_LISTS = ('artifacts', 'federation_tokens', 'gray_federation_tokens', 'alliance_tiles',
    'tech_tiles', 'advanced_tech_tiles', 'covered_tech_tiles', 'tinkeroids_tiles_used',
    'tech_tile_special_actions_used_this_round', 'advanced_tech_tile_special_actions_used_this_round')
PLANETS = ('Terra','Swamp','Desert','Oxide','Titanium','Volcanic','Ice','Transdim',
           'Gaia','LostPlanet','Asteroid','ProtoPlanet')
SHIPS = ('Twilight','Rebellion','TFMars','Eclipse')
TRACKS = ('Terraforming','Navigation','ArtificialIntelligence','GaiaProject','Economy','Science')


class EncodingError(ValueError):
    pass


def scalar(value):
    if value is None:
        return 0.0
    if isinstance(value, str):
        if value not in CATEGORY_IDS:
            raise EncodingError(f'Unknown categorical value: {value}')
        return CATEGORY_IDS[value] / len(CATEGORIES)
    if isinstance(value, (int, float, bool)):
        return float(value) / 100.0
    raise EncodingError(f'Expected scalar: {value!r}')


def histogram(values, capacity=32):
    result = [0.0] * capacity
    for value in values:
        if not isinstance(value, int) or not 0 <= value < capacity:
            raise EncodingError(f'Tile ID outside encoding: {value}')
        result[value] += 0.1
    return result


def fixed(values, capacity):
    if len(values) > capacity:
        raise EncodingError(f'{len(values)} values exceed {capacity} slots')
    return list(values) + [0.0] * (capacity - len(values))


def coordinate(value):
    return tuple(map(int, value.split(',')))


def structure(kind):
    return scalar(kind if isinstance(kind, str) else next(iter(kind.values())))


class FeatureEncoder:
    """No candidate truncation or coordinate hashing. Capacity overflow is fatal."""
    def __init__(self, candidate_capacity=2048):
        self.candidate_capacity = candidate_capacity
        self.candidate_size = len(ACTION_FIELDS) * 2 + BOARD_CAPACITY
        # Fixed upper bound for the documented flat state layout, not a truncation rule.
        self.state_size = 16384
        self.observation_space = spaces.Dict({
            'observation': spaces.Box(-np.inf, np.inf, (self.state_size,), np.float32),
            'candidates': spaces.Box(-np.inf, np.inf,
                                     (candidate_capacity, self.candidate_size), np.float32),
            'action_mask': spaces.MultiBinary(candidate_capacity),
        })

    def candidate(self, decision, indices):
        result = np.zeros(self.candidate_size, dtype=np.float32)
        data = {'phase': decision['phase'], **decision['action']}
        def visit(value, path):
            if value is None:
                return
            if path in COORD_ROLES:
                for coord in value if isinstance(value, list) else [value]:
                    if coord not in indices:
                        raise EncodingError(f'Candidate coordinate absent from board: {coord}')
                    result[len(ACTION_FIELDS)*2 + indices[coord]] += 2 ** COORD_ROLES.index(path)
            elif isinstance(value, dict):
                for key, child in value.items():
                    visit(child, f'{path}.{key}' if path else key)
            elif path in ACTION_FIELDS:
                index = ACTION_FIELDS.index(path)*2
                result[index:index+2] = [1, scalar(value)]
            else:
                raise EncodingError(f'Unencoded action field: {path}={value!r}')
        visit(data, '')
        return result

    def encode(self, snapshot, player):
        if (snapshot.get('engine_build_id') != ENGINE_BUILD_ID
                or snapshot.get('schema_version') != ENV_SCHEMA_VERSION):
            raise EncodingError('Snapshot engine/observation schema is incompatible')
        state = snapshot['state']
        hexes = state['board']['hexes']
        coords = sorted(hexes, key=coordinate)
        if len(coords) > BOARD_CAPACITY:
            raise EncodingError('Board exceeds fixed coordinate capacity')
        indices = {coord: i for i, coord in enumerate(coords)}
        def owner(value):
            return 0.0 if value is None else ((value-player)%4+1)/4
        features = [state['round']/6, owner(snapshot['player'])]
        features += fixed([owner(p) for p in state['turn_order']],4)
        features += fixed([owner(p) for p in state['pass_order']],4)
        # Phase variant names and pending amounts/owners retain their recursive order.
        phase = []
        def phase_values(value):
            if isinstance(value, dict):
                for key, child in sorted(value.items()):
                    if key in CATEGORY_IDS:
                        phase.append(scalar(key))
                    phase_values(child)
            elif isinstance(value, list):
                for child in value:
                    phase_values(child)
            elif isinstance(value,str) and ',' in value:
                phase.extend(v/20 for v in coordinate(value))
            else:
                phase.append(scalar(value))
        phase_values(state['phase'])
        features += fixed(phase,128)
        players = sorted(state['players'], key=lambda p:(p['player_id']-player)%4)
        for p in players:
            features += [scalar(p[key]) for key in PLAYER_SCALARS]
            resources = p['resources']
            features += [scalar(resources[key]) for key in ('ore','credits','knowledge','qic','spent_gaia_formers')]
            features += [scalar(resources['power'][key]) for key in
                         ('bowl1','bowl2','bowl3','gaia_bowl','gaia_forming','brainstone')]
            features += [scalar(p['research_tracks'][key]) for key in
                         ('terraforming','navigation','ai','gaia','economy','science')]
            for key in PLAYER_LISTS:
                features += histogram(p[key])
            features += [float(ship in p['explored_ships']) for ship in range(4)]
            for key in ('geodens_rewarded_planet_types','expensive_terraforming_planet_types'):
                features += [float(planet in p[key]) for planet in PLANETS]
        # One row per sorted axial coordinate: neither geometry nor occupancy is pooled away.
        board = []
        for coord in coords:
            cell = hexes[coord]; planet = cell['planet']
            row = [1, *(v/20 for v in coordinate(coord)), scalar(cell['space_tile_kind'])]
            row += [scalar(planet['planet_type']), float(planet['is_gaia_formed']), owner(planet['owner'])] if planet else [0]*3
            row += [float(state['board']['spaceship_tiles'].get(ship)==coord) for ship in SHIPS]
            for p in players:
                pid = p['player_id']
                buildings = [s for s in cell['structures'] if s['owner']==pid]
                if len(buildings)>1:
                    raise EncodingError('Multiple structures for one owner on one hex')
                row += [structure(buildings[0]['kind']) if buildings else 0,
                        float(pid in cell['satellites'])]
                row += [float(coord in p[key]) for key in
                        ('federated_hexes','moweyds_power_ring_hexes','artifact_mines')]
            board += row
        features += fixed(board,BOARD_CAPACITY*31)
        for sector in state['board']['sectors']:
            features += [sector['id']/20, sector['rotation']/6, *(v/20 for v in coordinate(sector['origin']))]
        features = fixed(features,12000)
        features += histogram(state['boosters'])
        features += fixed([scalar(t['id']) for t in state['round_tiles']],6)
        features += fixed([scalar(t['id']) for t in state['final_scoring_tiles']],2)
        features += [scalar(v) for v in state['terraforming_color_order']]
        research = state['research_board']
        features += histogram(research['tech_tiles']) + histogram(research['federation_tokens'])
        features += fixed([scalar(v) for v in research['tech_tile_slots']],9)
        features += [scalar(v) for v in research['advanced_tech_tiles']]
        features += [scalar(research[key]) for key in ('terraforming_level_5_token',
            'lost_fleet_advanced_tech_tile','lost_fleet_advanced_tech_requirement','economy_research_tile_side')]
        for track in TRACKS:
            features += [owner(v) for v in research['tracks'][track]['alliance_taken']]
        for ship in sorted(state['spaceship_boards'],key=lambda s: SHIPS.index(s['id'])):
            features += fixed([owner(v) for v in ship['explorers']],4)
            features += histogram(ship['artifact_pool']) + histogram(ship['tech_tiles'])
            features += [scalar(ship['federation_token'])]
        features += histogram(state['used_power_actions'])
        features += histogram(state['used_spaceship_actions'])
        actions = snapshot['candidates']
        if len(actions)>self.candidate_capacity:
            raise EncodingError('Candidate capacity exceeded')
        candidates = np.zeros((self.candidate_capacity,self.candidate_size),np.float32)
        for i, action in enumerate(actions):
            candidates[i] = self.candidate(action,indices)
        return {'observation':np.asarray(fixed(features,self.state_size),np.float32),
                'candidates':candidates,
                'action_mask':np.arange(self.candidate_capacity)<len(actions)}
