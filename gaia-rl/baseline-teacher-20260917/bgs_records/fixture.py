"""A hand-written two-seat game, small enough to check by eye and shaped like a real one.

Written rather than downloaded so the tests state what the code must do, instead of
restating what one recorded game happens to contain. The VP deltas are chosen to land
on the recorded final scores, which is exactly the invariant `timeline.build` enforces.
"""
import copy

MOVES = [
    'init 2 Test-game-0001',
    'p1 faction terrans',
    'p2 faction xenos',
    'terrans build m 3A1',
    'xenos build m 3A0',
    'xenos build m 6A0',
    'terrans build m 6B5',
    'xenos booster booster4',
    'terrans booster booster6',
    'terrans build ts 3A1.',
    'xenos charge 1pw (2/4/0/0 ⇒ 1/5/0/0)',
    'terrans build lab 3A1. tech nav. up nav (0 ⇒ 1).',
    'terrans federation 3A1,6B5 fed2 using area1: 2.',
    'terrans pass booster5 returning booster6',
    'xenos pass returning booster4',
]

LOG = [
    {'player': 0, 'move': 1},
    {'player': 1, 'move': 2},
    {'player': 0, 'changes': {'beginGame': {'t': 8, 'pw': 4, 'k': 3, 'o': 4, 'c': 15}}},
    {'player': 1, 'changes': {'beginGame': {'t': 6, 'pw': 4, 'k': 1, 'o': 4, 'c': 15}}},
    {'player': 0, 'move': 3},
    {'player': 1, 'move': 4},
    {'player': 1, 'move': 5},
    {'player': 0, 'move': 6},
    {'player': 1, 'move': 7},
    {'player': 0, 'move': 8},
    {'round': 1},
    {'phase': 'roundIncome'},
    {'player': 0, 'changes': {'income': {'o': 3, 'k': 1}}},
    {'phase': 'roundGaia'},
    {'phase': 'roundMove'},
    {'player': 0, 'move': 9, 'changes': {'build': {'c': -6, 'o': -2}}},
    {'player': 1, 'move': 10, 'changes': {'charge': {'pw': 1, 'vp': -1}}},
    {'player': 0, 'move': 11, 'changes': {'build': {'c': -5, 'o': -3}, 'nav': {'vp': 2}}},
    {'player': 0, 'move': 12, 'changes': {'federation': {'vp': 7}}},
    {'player': 0, 'move': 13},
    {'player': 1, 'move': 14},
    {'round': 2},
    {'round': 3},
    {'round': 4},
    {'round': 5},
    {'round': 6},
    {'phase': 'endGame'},
    {'player': 0, 'changes': {'final1': {'vp': 5}}},
    {'player': 1, 'changes': {'final1': {'vp': 3}}},
]

DATA = {
    'ended': True,
    'version': '4.8.51',
    'expansions': 0,
    'moveHistory': MOVES,
    'advancedLog': LOG,
    'options': {'layout': 'standard', 'factionVariant': 'standard',
                'factionVariantVersion': 0},
    'tiles': {'scorings': {'round': ['score3', 'score10', 'score8', 'score7',
                                     'score1', 'score5'],
                           'final': ['gaia', 'satellite']}},
    'players': [
        {'player': 0, 'faction': 'terrans', 'name': 'first',
         'data': {'victoryPoints': 24,
                  'buildings': {'m': 1, 'ts': 0, 'lab': 1, 'PI': 0, 'ac1': 0, 'ac2': 0,
                                'gf': 0, 'sp': 0},
                  'research': {'terra': 0, 'nav': 1, 'int': 0, 'gaia': 0, 'eco': 0,
                               'sci': 0}}},
        {'player': 1, 'faction': 'xenos', 'name': 'second',
         'data': {'victoryPoints': 12,
                  'buildings': {'m': 2, 'ts': 0, 'lab': 0, 'PI': 0, 'ac1': 0, 'ac2': 0,
                                'gf': 0, 'sp': 0},
                  'research': {'terra': 0, 'nav': 0, 'int': 0, 'gaia': 0, 'eco': 0,
                               'sci': 0}}},
    ],
}

SUMMARY = {
    '_id': 'Test-game-0001',
    'status': 'ended',
    'cancelled': False,
    'game': {'name': 'gaia-project', 'expansions': []},
    'players': [
        {'name': 'first', 'ranking': 1, 'elo': {'initial': 200, 'delta': 8}},
        {'name': 'second', 'ranking': 2, 'elo': {'initial': 180, 'delta': -8}},
    ],
}


def data(**overrides) -> dict:
    """A fresh copy, so a test that mutates it cannot affect the next one."""
    record = copy.deepcopy(DATA)
    record.update(copy.deepcopy(overrides))
    return record


def summary() -> dict:
    return copy.deepcopy(SUMMARY)
