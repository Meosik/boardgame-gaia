"""Evaluation-only callbacks for the frozen planner; no candidate/search policy."""
from functools import lru_cache
import json
import os

from gaia_rl._native import evaluation_successor_json, evaluation_pass_next_round_json
from state_evaluation_bef import evaluate_state


def active():
    return os.environ.get('GAIA_STATE_EVALUATION') == '1'


def conservation_off():
    return active() and os.environ.get('GAIA_CONSERVATION_OFF') == '1'


@lru_cache(maxsize=256)
def _evaluation(state_json, actor, conserve, expansion_mode, pass_timing, fixed_income_and_planets,
                direct_stock_prices, federation_satellite_tokens, density_bonus, token_ore_price,
                reachable_planets):
    state = json.loads(state_json)
    if pass_timing and 1 <= state['round'] <= 6 and next(
            p for p in state['players'] if p['player_id'] == actor)['passed']:
        state = json.loads(evaluation_pass_next_round_json(state_json, actor))
    return evaluate_state(state, actor, conserve_resources=conserve,
                          token_shortfall=True, remaining_income=True,
                          distributed_research=True, round_resource_prices=True,
                          discounted_expansion=expansion_mode != 'lite',
                          booster_one_income=True, gaia_token_return=True,
                          cached_expansion=expansion_mode == 'i_prime',
                          fixed_income_and_planets=fixed_income_and_planets,
                          direct_stock_prices=direct_stock_prices,
                          federation_satellite_tokens=federation_satellite_tokens,
                          density_bonus=density_bonus,
                          token_ore_price=token_ore_price,
                          reachable_planets=reachable_planets)


def evaluation(state, actor):
    return _evaluation(json.dumps(state, sort_keys=True), actor, not conservation_off(),
                       os.environ.get('GAIA_EXPANSION_MODE', 'i_prime'),
                       os.environ.get('GAIA_PASS_TIMING') == '1',
                       os.environ.get('GAIA_FIXED_INCOME_PLANETS') == '1',
                       os.environ.get('GAIA_DIRECT_STOCK_PRICES') == '1',
                       os.environ.get('GAIA_FEDERATION_VALUE') == '1',
                       os.environ.get('GAIA_DENSITY_BONUS') == '1',
                       os.environ.get('GAIA_TOKEN_ORE_PRICE') == '1',
                       os.environ.get('GAIA_REACHABLE_PLANETS') == '1')


def value(state, actor):
    return evaluation(state, actor).total_vp


def potential(state, actor, **kwargs):
    if active():
        return value(state, actor)
    from four_factions.value import potential as original
    return original(state, actor, **kwargs)


def score(snapshot, action):
    actor = snapshot['player']
    after = json.loads(evaluation_successor_json(json.dumps(snapshot['state']), actor, json.dumps(action)))
    result = evaluation(after, actor)
    baseline = value(snapshot['state'], actor)
    return result.total_vp-baseline, 'state VP delta: '+json.dumps(result.breakdown, sort_keys=True)


def route_value(teacher, before, after, already_legal, actions):
    from action_purpose.teacher import productive, key
    values = teacher.base_rank(after)
    options = [(v, c['action']) for c, (v, _) in zip(after['candidates'], values)
               if productive(c['action']) and key(c['action']) not in already_legal]
    if not options:
        return 0.0, None
    continuation, action = max(options, key=lambda item: item[0])
    actor = before['player']
    # Include conversion's actual state cost, not per-action overhead or a bonus.
    net = continuation + value(after['state'], actor)-value(before['state'], actor)
    return (net, action) if net > 0 else (0.0, None)


class PolicyBans(set):
    def __contains__(self, item):
        return False if conservation_off() else super().__contains__(item)
