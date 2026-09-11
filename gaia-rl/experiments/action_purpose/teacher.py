"""Bounded action-purpose ablations, not new game rules or learned PPO weights."""
import json
from action_purpose.costs import CorrectedContextTeacher, construction_cost
from research_context.teacher import advance

PASSIVE = {'FreeAction', 'Pass', 'ChargePower', 'ChooseIncomeOrder', 'PlaceStartingStructure', 'SelectStartingBooster'}
CHAINS = {
    'QicToOre': {'OreToCredit'},
    'BurnPower': {'BurnPower', 'PowerToOre', 'PowerToCredit', 'PowerToKnowledge', 'PowerToQic'},
}


def key(action):
    return json.dumps(action, sort_keys=True, separators=(',', ':'))


def productive(action):
    return action['type'] not in PASSIVE


def conversion_loss(before, after, actions, rnd):
    """Net resource sacrifice plus circulation/opportunity cost, never game-VP shaping."""
    b, a = before['resources'], after['resources']
    loss = max(0, sum(price*(b[k]-a[k]) for k, price in
                      (('ore', 2.5), ('knowledge', 3), ('qic', 3), ('credits', 1))))
    old_tokens = sum(b['power'][k] for k in ('bowl1', 'bowl2', 'bowl3'))
    new_tokens = sum(a['power'][k] for k in ('bowl1', 'bowl2', 'bowl3'))
    loss += 2*max(0, old_tokens-new_tokens)
    if rnd < 6:
        loss += 4*(max(0, 4-new_tokens)-max(0, 4-old_tokens))
        if b['knowledge'] >= 4 > a['knowledge']:
            loss += 4
    loss += .5*max(0, b['power']['bowl3']-a['power']['bowl3'])
    loss += sum(3 if a['kind'] == 'KnowledgeToCredit' else 1 if a['kind'] == 'OreToCredit' else 0 for a in actions)
    return max(0, loss)+len(actions)


class PurposeTeacher(CorrectedContextTeacher):
    """Stages: 1 conversion/burn, 2 pass, 3 research order, 4 ship follow-ups."""
    def __init__(self, stage=1):
        if stage not in range(1, 5):
            raise ValueError('stage must be 1..4')
        self.stage = stage
        self.env = None
        self.last_scores = None
        self.preview_count = 0

    def bind(self, env):
        self.env = env
        return self

    def base_rank(self, snapshot):
        return CorrectedContextTeacher.rank(self, snapshot)

    def rank(self, snapshot):
        scores = self.base_rank(snapshot)
        self.preview_count = 0
        state, player, _ = self.context(snapshot)
        if not isinstance(state['phase'], dict) or 'ActionPhase' not in state['phase']:
            self.last_scores = scores
            return scores
        before_main = {key(c['action']) for c in snapshot['candidates'] if productive(c['action'])}
        if any(c['action']['type'] == 'FreeAction' for c in snapshot['candidates']) and self.env is None:
            raise ValueError('PurposeTeacher requires its current native environment for previews')
        for i, candidate in enumerate(snapshot['candidates']):
            action = candidate['action']
            if action['type'] != 'FreeAction':
                continue
            # Preserve Xenos' established low-token recovery exception.
            if action['kind'] == 'OreToPowerBowl3':
                continue
            scores[i] = (-12.0, 'purpose: no verified productive follow-up')
            if action.get('count', 1) != 1 or (self.stage >= 4 and self.preview_count >= 18):
                continue
            branch, after = self.preview(self.env, snapshot, i)
            if after is None or after['player'] != snapshot['player']:
                continue
            best, target = self.route_value(snapshot, after, before_main, [action])
            for j, next_candidate in enumerate(after['candidates']):
                second = next_candidate['action']
                if second['type'] != 'FreeAction' or second.get('count', 1) != 1 or second['kind'] not in CHAINS.get(action['kind'], set()):
                    continue
                _, last = self.preview(branch, after, j)
                if last is None or last['player'] != snapshot['player']:
                    continue
                value, followup = self.route_value(snapshot, last, before_main, [action, second])
                if value > best:
                    best, target = value, followup
            if target:
                scores[i] = (best, f'purpose: native-legal follow-up {key(target)}; net={best:.3f}')
        if self.stage >= 2:
            self.adjust_pass(snapshot, scores)
        if self.stage >= 3:
            self.adjust_research_order(snapshot, scores)
        if self.stage >= 4:
            self.adjust_ship_entry(snapshot, scores)
        self.last_scores = scores
        return scores

    def preview(self, env, snapshot, index):
        # Bounded deterministic lookahead. No hypothetical opponent turns or free resources.
        if self.preview_count >= 24:
            return None, None
        self.preview_count += 1
        branch = env.fork(snapshot['decision_id'], index)
        return branch, json.loads(branch.snapshot_json())

    def route_value(self, before, after, already_legal, actions):
        values = self.base_rank(after)
        options = [(value, c['action']) for c, (value, _) in zip(after['candidates'], values)
                   if productive(c['action']) and key(c['action']) not in already_legal]
        if not options:
            return -12.0, None
        value, action = max(options, key=lambda item: item[0])
        p = before['player']
        penalty = conversion_loss(before['state']['players'][p], after['state']['players'][p], actions, before['state']['round'])
        score = .9*value-penalty
        return (score, action) if score > 0 else (-12.0, None)

    def adjust_pass(self, snapshot, scores):
        # Compare available positive-valued actions, not resource stock itself. Keeping
        # resources when no worthwhile move is available is never penalized here.
        productive_scores = [s[0] for c, s in zip(snapshot['candidates'], scores) if productive(c['action'])]
        best = max(productive_scores, default=0)
        for i, candidate in enumerate(snapshot['candidates']):
            if candidate['action']['type'] == 'Pass' and best > 3:
                value, reason = scores[i]
                scores[i] = (value-min(6, (best-3)*.1), reason+'; pass: available productive action opportunity')

    def adjust_research_order(self, snapshot, scores):
        state, player, r = self.context(snapshot)
        for i, c in enumerate(snapshot['candidates']):
            a = c['action']
            if a['type'] != 'ResearchAdvance' or a['track'] not in ('Terraforming', 'Navigation'):
                continue
            after = advance(player, a['track'])
            best = 0.0
            for coord, cell in state['board']['hexes'].items():
                planet = cell['planet']
                if not planet or planet['owner'] is not None or planet['planet_type'] == 'Transdim':
                    continue
                if sum(s['kind'] == 'Mine' for s in player['structures']) >= 8:
                    continue
                build = {'type': 'Build', 'coord': coord}
                old, new = construction_cost(state, player, build), construction_cost(state, after, build)
                if not old or not new or any(getattr(new, k) > r[k] for k in ('ore', 'credits', 'qic')):
                    continue
                if planet['planet_type'] == 'Asteroid' and player['gaiaformers_total']-player['gaiaformers_deployed']-player['gaiaformers_in_gaia_area']-r['spent_gaia_formers'] < 1:
                    continue
                best = max(best, (old.ore-new.ore)*2.5+(old.qic-new.qic)*4)
            if best > 0:
                value, reason = scores[i]
                scores[i] = (value+min(12, best), reason+f'; research first: fundable next-build saving={best:.2f}; opponents may intervene')

    def adjust_ship_entry(self, snapshot, scores):
        for i, c in enumerate(snapshot['candidates']):
            a = c['action']
            if not a['type'].endswith('ExploreSpaceship'):
                continue
            # Entry is a main action. Assess remaining resources, not pre-entry stock;
            # do not pretend we control the next player's turn.
            _, after = self.preview(self.env, snapshot, i)
            if after is None:
                continue
            state = after['state']
            player = state['players'][snapshot['player']]
            value, target = ship_followup(state, player, a['ship'])
            scores[i] = (20+value-4*max(0, len(player['explored_ships'])-1),
                         f'ship: post-entry funded opportunity={target}; value={value:.2f}; no reservation guarantee')


def ship_followup(state, player, ship):
    """Funded one-step opportunities only; no promise competitors leave spaces open."""
    r = player['resources']
    used = set(state['used_spaceship_actions'])
    board = next(b for b in state['spaceship_boards'] if b['id'] == ship)
    tiles = state['research_board']['tech_tiles']+board['tech_tiles']
    has_tech = any(tile not in player['tech_tiles'] for tile in tiles)
    if ship == 'Rebellion' and r['qic'] >= 3 and has_tech and 12 not in used:
        return 48, '3QIC technology/research'
    if ship == 'Twilight' and 2 not in used and r['ore'] >= 2 and r['power']['bowl3'] >= 3 and has_tech:
        if any(s['kind'] == 'TradingStation' for s in player['structures']) and sum(s['kind'] == 'ResearchLab' for s in player['structures']) < 3:
            return 45, 'research lab and technology'
    if ship in ('Eclipse', 'TFMars') and sum(s['kind'] == 'Mine' for s in player['structures']) < 8:
        action_type, action_id = ('EclipseAsteroidMine', 9) if ship == 'Eclipse' else ('SpaceshipCreditTerraform', 1)
        if action_id not in used:
            for coord, cell in state['board']['hexes'].items():
                planet = cell['planet']
                if not planet or planet['owner'] is not None or planet['planet_type'] == 'Transdim':
                    continue
                if ship == 'Eclipse' and planet['planet_type'] != 'Asteroid':
                    continue
                cost = construction_cost(state, player, {'type': action_type, 'coord': coord})
                if cost and all(getattr(cost, k) <= r[k] for k in ('ore', 'credits', 'qic')):
                    if ship == 'TFMars' and planet['planet_type'] == 'Asteroid' and player['gaiaformers_total']-player['gaiaformers_deployed']-player['gaiaformers_in_gaia_area']-r['spent_gaia_formers'] < 1:
                        continue
                    return 42, action_type
    return 0, 'none verified'
