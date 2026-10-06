"""uiqoo (어잌후) resource prices for the teacher's state value, in the guides' own unit.

User decision (2026-10-05): the uiqoo guides' common (non-faction) material is applied,
numbers included. Sources and the full tables are in research/strategy/:
lf01-lf02-value-table.md, lf03-lf04-goals-round1.md, b01-b02-strategy-power-buildings.md,
b03-tech-boosters-claims.md.

Unit: one charge ("충전") = one power token moved one bowl up; spending a bowl-III token is
two charges (LF01 free-action table: 3 power -> 1 ore is written "6충전").

Rounds: LF01 prices 1 VP = 1.5 charges, stated for rounds 4-5; the guides give a direction
for other rounds (charges better in 1-4R, VP better in 5-6R, LF1-04, B01 §1) but no number,
so every round uses the one stated rate (user: no numbers of our own). A finished game uses
the engine's final scores.
"""

# LF01 / LF02 §1 (확장판 자원 가치).
CHARGE = {'credits': 1.2, 'ore': 4.0, 'knowledge': 4.0, 'qic': 7.0}
TOKEN = 3.2          # one power token while tokens are still needed (LF01; B02: 0 above need)
PLANET = 6.0         # one more planet (structure) held (LF01)
CHARGES_PER_VP = {r: 1.5 for r in range(7)}

# B02 §1: about 5 tokens run the power actions; a Gaia-forming player needs 10-11 at
# Gaia 1-2 and 8-9 from Gaia 3. Tokens beyond that are worth 0.
TOKENS_NEEDED = 5
TOKENS_NEEDED_GAIA = {1: 11, 2: 11, 3: 9, 4: 9, 5: 9}

# LF02 §3 round boosters, whole-round value in charges (engine ids, engine.rs
# apply_round_booster_income). Score boosters carry their income here; their pass VP is
# the rule fact added by teacher_patches.booster_pass_vp.
BOOSTER = {9: 9.4, 12: 8.4, 8: 9.0, 5: 8.0, 13: 8.0, 2: 10.2, 4: 4.0, 3: 4.0, 7: 4.0,
           11: 4.8, 1: 4.0, 14: 3.6, 6: 4.0, 10: 4.0}

# LF03 §2: a fleet power/knowledge/credit action gains "usually about 2 charges" of
# resources, one action per round for the ship's explorers.
SHIP_ACTION_GAIN = 2.0

# LF01 §2.4: a tech tile is worth about 30 charges "including 16 charges for the research
# advance" (4 knowledge). One research level = 16 charges.
RESEARCH_STEP = 16.0

# LF02 §1: the 4-charge tech tile (engine standard tile 10, an action) is 4 charges a round.
CHARGE_TILE = 10
CHARGE_TILE_PER_ROUND = 4.0


def charges_per_vp(state):
    return CHARGES_PER_VP[min(max(state['round'], 0), 6)]


def to_vp(state, charges):
    return charges/charges_per_vp(state)


def materials(state, resources):
    """Stock of ore/credits/knowledge/QIC in VP at the current round's rate."""
    return to_vp(state, sum(CHARGE[k]*resources.get(k, 0) for k in CHARGE))


def tokens_needed(player):
    level = player['research_tracks']['gaia']
    return TOKENS_NEEDED_GAIA.get(level, TOKENS_NEEDED)


def power_value(state, player):
    """Normal tokens' charges held (bowl II = 1, bowl III = 2, B02) plus tokens up to the
    need, in VP. Tokens in the Gaia area and the Brainstone keep the frozen teacher's own
    terms in the caller (they differ by faction; no faction-specific change here)."""
    power = player['resources']['power']
    charges = power['bowl2'] + 2*power['bowl3']
    tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
    return to_vp(state, charges + TOKEN*min(tokens, tokens_needed(player)))


def research_value(state, player):
    """Research levels held, 16 charges each (LF01). Final scoring's 4 VP per level beyond 2
    is part of what an advance is worth, so it is not added again before the game ends."""
    return to_vp(state, RESEARCH_STEP*sum(player['research_tracks'].values()))


def charge_tile_value(state, player):
    """The 4-charge action tile, once per round from now to round 6 (LF02 §1)."""
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
    if CHARGE_TILE not in active:
        return 0.0
    rounds = 7-max(state['round'], 1)
    return to_vp(state, CHARGE_TILE_PER_ROUND*rounds)


def income_value(state, income):
    """One round of income (engine income vector) in VP at the next round's rate."""
    nxt = dict(state, round=min(state['round']+1, 6))
    ore, credits, knowledge, qic, charge, tokens, vp = income[:7]
    charges = (CHARGE['ore']*ore + CHARGE['credits']*credits + CHARGE['knowledge']*knowledge
               + CHARGE['qic']*qic + charge + TOKEN*tokens)
    return to_vp(nxt, charges) + vp


def incomes_value(state, income):
    """Every remaining income of a recurring vector, each at its own round's rate."""
    total = 0.0
    for r in range(state['round']+1, 7):
        total += income_value(dict(state, round=r-1), income)
    return total


def booster_value(state, booster):
    """A booster's whole next round (LF02 §3), in VP at the next round's rate."""
    nxt = dict(state, round=min(state['round']+1, 6))
    return to_vp(nxt, BOOSTER.get(booster, 0.0))


def ship_value(state):
    """An explored ship: its action for every round left including this one."""
    total = 0.0
    for r in range(max(state['round'], 1), 7):
        total += to_vp(dict(state, round=r), SHIP_ACTION_GAIN)
    return total


# LF01 §2 fleet actions, net gain per use in charges (cost already deducted: e.g. Rebellion
# 2 knowledge -> 2 credits + 1 QIC = 9.4 - 8 = +1.4). Engine ship ids (engine.rs
# spaceship_id_to_ship_id). User (2026-10-07): assume a ship is used a lot -> its best listed
# action once every round left. Situational figures left out: Twilight +10 only when exactly
# 3 range is needed, Rebellion 3-QIC tech (stated as a 21-charge price, not a gain).
SHIP_ACTION_NET = {0: 4.0,   # Twilight: research lab +4 (1 knowledge +3 range: +3 at 2 range)
                   1: 5.2,   # Rebellion: expensive trading station +5.2 (cheap +1.6)
                   2: 2.4,   # TF Mars: 3 credits 1 terraform +2.4 (instant Gaia-forming +2)
                   3: 5.2}   # Eclipse: 6-credit asteroid mine +5.2 (advance +2)

# User (2026-10-07): a green (flippable) federation token is worth the difference between the
# open and the closed 12 VP token, taken as LF01's fleet tokens (21-22 charges) minus the base
# tokens (18-19): 3 charges. Token 1 is the closed (gray) 12 VP token (engine.rs
# flip_a_federation_token).
GREEN_TOKEN = 3.0


# LF02 §2 advanced special action tiles, resources per use in charges (no cost): "1정보 5돈이면
# 자원 가치는 14충전", "3광석이나 3지식이면 자원 가치는 12충전". Engine advanced tile ids.
SPECIAL_ACTION = {20: 12.0, 21: 12.0, 22: 14.0}

# Our own numbers (user 2026-10-07: "없는 건 하면서 만들어야제"), not from the guides:
EVENT_USES_PER_ROUND = 1.5   # advanced "VP when you do X" tiles: one or two triggers a round
FEDERATION_TOKEN = 18.0      # LF01 lower bound of a base federation token (18-19 charges)
FEDERATION_POWER = 7         # rulebook: a federation needs buildings of total power value 7
LEECH_PER_NEIGHBOR = 2.0     # charges a round from each opponent with buildings within 2 hexes
LEECH_NEIGHBORS_MAX = 3


def ships_value(state, player):
    """Each explored ship's best net action once for every round left including this one."""
    rounds = 7-max(state['round'], 1)
    return to_vp(state, rounds*sum(SHIP_ACTION_NET.get(ship, SHIP_ACTION_GAIN)
                                   for ship in player['explored_ships']))


def green_tokens_value(state, player):
    green = [t for t in player['federation_tokens'] if t != 1]
    return to_vp(state, GREEN_TOKEN*len(green)) if state['round'] < 6 else 0.0


def planet_value(state):
    return to_vp(state, PLANET) if state['round'] < 6 else 0.0
