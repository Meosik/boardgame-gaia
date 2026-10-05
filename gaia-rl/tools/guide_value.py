"""uiqoo (어잌후) resource prices for the teacher's state value, in the guides' own unit.

User decision (2026-10-05): the uiqoo guides' common (non-faction) material is applied,
numbers included. Sources and the full tables are in research/strategy/:
lf01-lf02-value-table.md, lf03-lf04-goals-round1.md, b01-b02-strategy-power-buildings.md,
b03-tech-boosters-claims.md.

Unit: one charge ("충전") = one power token moved one bowl up; spending a bowl-III token is
two charges (LF01 free-action table: 3 power -> 1 ore is written "6충전").

Rounds: LF01 prices 1 VP = 1.5 charges "at rounds 4-5", charges worth more before
(1-4R charge better than VP) and VP worth more after (5-6R VP better, LF1-04, B01 §1).
CHARGES_PER_VP interpolates those anchors; the end of the game is the rule's own
conversion (3 credits/ore/knowledge = 1 VP), which `potential` already uses once the
game has ended. The interpolated rounds (1-3, 6) are the only numbers here that are not
read directly from a guide; they keep the guide's ordering and its 1.5 anchor.
"""

# LF01 / LF02 §1 (확장판 자원 가치).
CHARGE = {'credits': 1.2, 'ore': 4.0, 'knowledge': 4.0, 'qic': 7.0}
TOKEN = 3.2          # one power token while tokens are still needed (LF01; B02: 0 above need)
PLANET = 6.0         # one more planet (structure) held (LF01)
CHARGES_PER_VP = {0: 1.2, 1: 1.2, 2: 1.3, 3: 1.4, 4: 1.5, 5: 1.5, 6: 3.0}

# B02 §1: about 5 tokens run the power actions; a Gaia-forming player needs 10-11 at
# Gaia 1-2 and 8-9 from Gaia 3. Tokens beyond that are worth 0.
TOKENS_NEEDED = 5
TOKENS_NEEDED_GAIA = {1: 11, 2: 11, 3: 9, 4: 9, 5: 9}

# LF02 §3 round boosters, whole-round value in charges (engine ids, engine.rs
# apply_round_booster_income). Score boosters carry their income here; their pass VP is
# the rule fact added by teacher_patches.booster_pass_vp.
BOOSTER = {9: 9.4, 12: 8.4, 8: 9.0, 5: 8.0, 13: 8.0, 2: 10.2, 4: 4.0, 3: 4.0, 7: 4.0,
           11: 4.8, 1: 4.0, 14: 3.6, 6: 4.0, 10: 4.0}

# LF03 §2 / LF04: a fleet action is worth about 2 charges over a public one, and each of the
# four ships gives one power/credit/knowledge action per round to its explorers only;
# the 5 VP entry "is repaid after two or three uses". LF01 §2.3 gains: 1.4 to 5.2, 10.
SHIP_ACTION_GAIN = 3.0


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
    """Charges held (bowl II = 1, bowl III = 2) plus tokens up to the need, in VP.

    Tokens in the Gaia area come back next round (bowl I; bowl II for Terrans, one charge).
    The Brainstone is spent as three power: three times a token's charges."""
    power = player['resources']['power']
    charges = power['bowl2'] + 2*power['bowl3']
    stone = power.get('brainstone')
    charges += {'Area2': 3, 'Area3': 6}.get(stone, 0)
    returning = power.get('gaia_forming', 0)
    if player['faction'] == 'Terrans':
        charges += returning
    tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3')) + returning
    return to_vp(state, charges + TOKEN*min(tokens, tokens_needed(player)))


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


def planet_value(state):
    return to_vp(state, PLANET) if state['round'] < 6 else 0.0
