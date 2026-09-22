"""Isolated teacher revision: burn for useful shared actions, not generic liquidation."""
from action_purpose.teacher import PurposeTeacher, conversion_loss, key
from action_purpose.costs import construction_cost

POWER_COST = {1: 7, 2: 5, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3}


def tokens(player):
    return sum(player['resources']['power'][k] for k in ('bowl1', 'bowl2', 'bowl3'))


def contested(state, player, action):
    """Readiness, not a prediction that an opponent will actually take this slot."""
    cost = POWER_COST.get(action.get('id'), 255)
    return any(p['player_id'] != player['player_id'] and not p.get('passed', False)
               and p['resources']['power']['bowl3'] >= cost for p in state['players'])


def useful_power(state, player, action):
    if action['type'] != 'PowerAction' or action['id'] in state.get('used_power_actions', []):
        return False
    r = player['resources']
    if action.get('coord') is not None:
        normal = construction_cost(state, player, {'type': 'Build', 'coord': action['coord']})
        discounted = construction_cost(state, player, action)
        return bool(normal and discounted and normal.terraform_ore > discounted.terraform_ore)
    return {1: r['knowledge'] < 4, 3: r['ore'] < 4, 4: r['credits'] < 8,
            5: r['knowledge'] < 4, 7: tokens(player) < 6}.get(action['id'], False)


class PowerPurposeTeacher(PurposeTeacher):
    """Keeps the frozen v1 teacher intact; no PPO weights or game rewards are changed."""
    def __init__(self):
        super().__init__(stage=3)

    def base_rank(self, snapshot):
        scores = super().base_rank(snapshot)
        state, player, _ = self.context(snapshot)
        for i, candidate in enumerate(snapshot['candidates']):
            action = candidate['action']
            value, reason = scores[i]
            cost = construction_cost(state, player, action)
            # Expensive construction is an exception, not a ban. Exceptional scoring,
            # income, or a federation can still outweigh these opportunity costs.
            if cost and cost.terraform_steps and cost.terraform_ore == 3*cost.terraform_steps:
                value -= 24*cost.terraform_steps
                reason += '; expensive: 3 ore per paid terraform step'
            if action['type'] == 'Upgrade' and action.get('to') == 'TradingStation' and cost and cost.credits == 6:
                value -= 18
                reason += '; expensive: isolated 6-credit trading station'
            if useful_power(state, player, action) and contested(state, player, action):
                value += 10
                reason += '; power: useful shared slot, opponent can afford printed cost'
            scores[i] = value, reason
        return scores

    def route_value(self, before, after, already_legal, actions):
        if not any(action['kind'] == 'BurnPower' for action in actions):
            return super().route_value(before, after, already_legal, actions)
        # Do not burn merely to turn the resulting power into loose resources.
        if any(action['kind'] != 'BurnPower' for action in actions):
            return -12.0, None
        actor = before['player']
        state, player = before['state'], before['state']['players'][actor]
        remaining = after['state']['players'][actor]
        if state['round'] < 6 and tokens(remaining) < 4:
            return -12.0, None
        bowl = player['resources']['power']
        congested = (state['round'] < 6 and tokens(player) > 8
                     and bowl['bowl2'] >= 4 and bowl['bowl2'] >= bowl['bowl1'])
        options = []
        for candidate, (value, _) in zip(after['candidates'], self.base_rank(after)):
            action = candidate['action']
            if key(action) in already_legal or not useful_power(state, player, action):
                continue
            race = contested(state, player, action)
            loss = conversion_loss(player, remaining, actions, state['round'])
            # Native preview proves that the entire action (including a mine's other
            # costs) is legal after burning. Congestion needs an immediate spend too.
            bonus = 12 if race else 8 if congested else 0
            score = min(value-.5, .9*value-loss+bonus)
            options.append((score, action))
        return max(options, key=lambda item: item[0]) if options else (-12.0, None)
