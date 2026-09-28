"""Owned subprocess supervision: native search cannot block the game indefinitely."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from current_actions.conservation import blocked, identity
from four_factions.teacher import QuartetTeacher


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False))
    temporary.replace(path)


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=.15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=.15)


class TimedPreparationTeacher(QuartetTeacher):
    def __init__(self, seed, *, target_seconds=60.0, maximum_seconds=300.0, prefix=(), bgg_openings=False,
                 shared_factions=False, adaptive_clock=None, delta_factions=(), fixed_openings=False,
                 observed_factions=(), faction_tech_plans=False):
        super().__init__()
        if not (0 < target_seconds <= maximum_seconds and math.isfinite(maximum_seconds)):
            raise ValueError('Positive finite target <= maximum required')
        self.seed = seed
        self.target_seconds = target_seconds
        self.maximum_seconds = maximum_seconds
        self.prefix = list(prefix)
        self.bgg_openings = bgg_openings
        self.fixed_openings = fixed_openings
        self.shared_factions = shared_factions
        self.faction_tech_plans = bool(shared_factions and faction_tech_plans)
        self.adaptive_clock = adaptive_clock
        from four_factions.preparation import Policies
        self.delta_factions = Policies(delta_factions=delta_factions).delta_factions
        self.observed_factions = tuple(sorted(set(observed_factions)))
        self.memory = {}
        self.times = {str(i): [] for i in range(4)}

    def observe(self, before, index, after):
        if before['steps'] != len(self.prefix) or after['steps'] != len(self.prefix)+1:
            raise ValueError('Timed teacher requires the exact append-only native action prefix')
        self.prefix.append(index)
        from dataclasses import asdict
        from four_factions.preparation import achieved, advance_goal, goal_from_dict, viable
        actor = str(before['player'])
        plans = self.memory.get('_plans', {})
        if actor in plans:
            goal = advance_goal(after, before['player'], goal_from_dict(plans[actor]),
                                before['candidates'][index]['action'], before=before)
            if achieved(after, before['player'], goal) or not viable(after, before['player'], goal):
                del plans[actor]
            else:
                plans[actor] = asdict(goal)
        if self.bgg_openings and before['state']['round'] == 1 and after['state']['round'] == 2:
            from bgg_openings.inventory import building_counts, round_one_result
            observed = {}
            for player in before['state']['players']:
                pid = player['player_id']
                target = self.memory.get('_bgg_targets', {}).get(str(pid))
                matching = [o.label for o in round_one_result(before, after, pid)]
                observed[player['faction']] = {'target': target, 'matching_openings': matching,
                    'actual_buildings': asdict(building_counts(player)),
                    'target_met': target in matching if target is not None else None}
            if self.last_audit is not None:
                self.last_audit['bgg_r1_observed'] = observed
            self.memory.pop('_bgg_targets', None)
        if self.fixed_openings and before['state']['round'] == 1 and after['state']['round'] == 2:
            from bgg_openings.fixed import TARGETS, completed, MISSED_TARGET_COST
            observed = {p['faction']: {'target': TARGETS[p['faction']], 'minimum_mines': 2,
                'target_met': completed(p), 'utility_loss': 0 if completed(p) else MISSED_TARGET_COST}
                for p in before['state']['players'] if p['faction'] in TARGETS}
            if self.last_audit is not None:
                self.last_audit['fixed_r1_observed'] = observed

    def choose(self, snapshot):
        started = time.monotonic()
        if self.env is None or json.loads(self.env.snapshot_json()) != snapshot:
            raise ValueError('Timed teacher must be bound to the current native snapshot')
        if snapshot['steps'] != len(self.prefix):
            raise ValueError('Missing native actions; cannot reconstruct a search process')
        actor = str(snapshot['player'])
        # The approved mean is a target, not a debt bank. A long placement must
        # not give the following investment decisions zero comparison time.
        # Easy responses finish early; every decision retains its soft target.
        clock = self.adaptive_clock
        soft = clock.base_seconds(snapshot, self.memory) if clock is not None else self.target_seconds
        deadline = started+self.maximum_seconds
        # Reserve a small portion of the SAME budget for process cleanup.
        hard_deadline = deadline-min(.4, self.maximum_seconds/10)
        search_deadline = (started+soft-min(.1, soft/10)) if clock is not None else hard_deadline
        long_reason = None
        latest = None
        reserve = None
        reserve_started = time.monotonic()
        if clock is not None:
            from four_factions.quick import fallback
            # Reserve a real evaluated move before a large root ranking can
            # consume the entire deadline. This uses the SAME decision budget.
            reserve = fallback(self.env, snapshot, self.memory,
                               deadline=started+min(.5, soft/10), fixed_openings=self.fixed_openings)
        reserve_seconds = time.monotonic()-reserve_started
        process = None
        with tempfile.TemporaryDirectory(prefix='gaia-preparation-') as directory:
            root = Path(directory)
            request = {'seed': self.seed, 'prefix': self.prefix, 'memory': self.memory,
                       'bgg_openings': self.bgg_openings,
                       'fixed_openings': self.fixed_openings,
                       'shared_factions': self.shared_factions,
                       'faction_tech_plans': self.faction_tech_plans,
                       'delta_factions': self.delta_factions,
                       'observed_factions': self.observed_factions,
                       'adaptive': clock is not None,
                       'snapshot_sha256': sha256(identity(snapshot).encode()).hexdigest(),
                       'soft_deadline': started+soft, 'hard_deadline': hard_deadline}
            atomic_json(root/'request.json', request)
            try:
                with (root/'stderr.log').open('w') as errors:
                    process = subprocess.Popen([sys.executable, '-m', 'four_factions.timed',
                                                '--request', str(root/'request.json')],
                                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                               stderr=errors)
                    modified = None
                    while True:
                        candidate = root/'candidate.json'
                        if candidate.exists() and candidate.stat().st_mtime_ns != modified:
                            modified = candidate.stat().st_mtime_ns
                            value = json.loads(candidate.read_text())
                            if value['published_at'] <= search_deadline:
                                latest = value
                        if (root/'error.json').exists():
                            raise RuntimeError(json.loads((root/'error.json').read_text())['error'])
                        if process.poll() is not None:
                            if process.returncode:
                                raise RuntimeError(f'Search process failed: {(root/"stderr.log").read_text()[-2000:]}')
                            # A final atomic update may have arrived after the poll.
                            if candidate.exists():
                                value = json.loads(candidate.read_text())
                                if value['published_at'] <= search_deadline:
                                    latest = value
                            break
                        if time.monotonic() >= search_deadline:
                            if clock is not None and long_reason is None:
                                reason = clock.extension_reason(snapshot, self.memory, latest)
                                if reason and clock.spend(snapshot):
                                    long_reason = reason
                                    search_deadline = hard_deadline
                                    atomic_json(root/'allocation.json', {'soft_deadline': hard_deadline})
                                    continue
                            break
                        time.sleep(min(.025, max(0, search_deadline-time.monotonic())))
            finally:
                if process is not None:
                    stop(process)
            # An error can be published between the final poll and termination.
            # Do not turn a known failed search into a successful stale fallback.
            if (root/'error.json').exists():
                raise RuntimeError(json.loads((root/'error.json').read_text())['error'])
            candidate = root/'candidate.json'
            if candidate.exists():
                value = json.loads(candidate.read_text())
                if value['published_at'] <= search_deadline:
                    latest = value
            if latest is None:
                if reserve is None:
                    raise TimeoutError('No eligible evaluated action before deadline; no automatic pass')
                latest = reserve
        used_reserve = latest is reserve
        index = latest['index']
        if (latest['decision_id'] != snapshot['decision_id'] or type(index) is not int
                or not 0 <= index < len(snapshot['candidates'])
                or len(latest['scores']) != len(snapshot['candidates'])
                or not all(math.isfinite(v) for v, _ in latest['scores'])
                or blocked(latest['scores'][index])):
            raise ValueError('Search result does not belong to the current native decision')
        if json.loads(self.env.snapshot_json()) != snapshot:
            raise ValueError('Parent native state changed during isolated search')
        self.memory = latest['memory']
        if clock is not None:
            self.memory['_clock'] = clock.state()
        self.last_scores = [tuple(score) for score in latest['scores']]
        elapsed = time.monotonic()-started
        self.times[actor].append(elapsed)
        selected_value = math.nextafter(max(v for v, _ in self.last_scores), math.inf)
        self.last_scores[index] = (selected_value, f'preparation path={latest["selected"]}; '
                                   'paid native forecast, not observed future or guaranteed optimum')
        self.last_audit = {**{k: v for k, v in latest.items() if k != 'memory'}, 'selected_index': index,
                           'faction_tech_plans': self.faction_tech_plans,
                           'delta_factions': list(self.delta_factions),
                           'value_model': ('shared-quick-fallback' if used_reserve else
                               'B19-expansion-v1' if snapshot['state']['players'][snapshot['player']]['faction']
                               in self.delta_factions and 'Setup' not in snapshot['state']['phase']
                               else 'control'),
                           'ranking_mode': ('shared-quick-fallback' if used_reserve else
                               'state-delta' if snapshot['state']['players'][snapshot['player']]['faction']
                               in self.delta_factions and 'Setup' not in snapshot['state']['phase']
                               else 'control'),
                           'candidate_generation': snapshot.get('candidate_generation'),
                           'predictions_are_not_observed_outcomes': True,
                           'timing': {'seconds': elapsed, 'target_mean_seconds': self.target_seconds,
                                      'maximum_seconds': self.maximum_seconds,
                                      'own_mean_seconds': sum(self.times[actor])/len(self.times[actor]),
                                      'own_max_seconds': max(self.times[actor]),
                                      'deadline_reached': time.monotonic() >= search_deadline,
                                      **({'base_seconds': soft, 'long_think_used': long_reason is not None,
                                          'long_think_reason': long_reason,
                                          'long_thinks_remaining': clock.remaining(actor),
                                          'long_thinks_per_seat': clock.uses,
                                          'total_decision_cap_seconds': self.maximum_seconds if long_reason else soft,
                                          'quick_fallback_used': used_reserve,
                                          'quick_reserve_seconds': reserve_seconds}
                                         if clock is not None else {})}}
        return snapshot['decision_id'], index


def worker(request_path):
    from gaia_rl import Environment
    from four_factions.preparation import search, check_time
    path = Path(request_path)
    request = json.loads(path.read_text())
    root = path.parent
    try:
        env = Environment(request['seed'], 2000)
        for index in request['prefix']:
            check_time(request['hard_deadline'])
            snapshot = json.loads(env.snapshot_json())
            env.step(snapshot['decision_id'], index)
        snapshot = json.loads(env.snapshot_json())
        if sha256(identity(snapshot).encode()).hexdigest() != request['snapshot_sha256']:
            raise ValueError('Reconstructed native state/source differs from parent')

        def publish(result):
            check_time(request['hard_deadline'])
            atomic_json(root/'candidate.json', {**result, 'published_at': time.monotonic()})

        def allocation():
            path = root/'allocation.json'
            return json.loads(path.read_text())['soft_deadline'] if path.exists() else request['soft_deadline']

        search(env, snapshot, request['memory'], publish,
               soft_deadline=request['soft_deadline'], hard_deadline=request['hard_deadline'],
               bgg_openings=request.get('bgg_openings', False),
               fixed_openings=request.get('fixed_openings', False),
               shared_factions=request.get('shared_factions', False),
               faction_tech_plans=request.get('faction_tech_plans', False),
               delta_factions=request.get('delta_factions', ()),
               observed_factions=tuple(request.get('observed_factions', ())),
               adaptive=request.get('adaptive', False),
               allocation=allocation if request.get('adaptive') else None)
    except Exception as error:
        from four_factions.preparation import SearchExpired
        if isinstance(error, SearchExpired):
            return  # Parent uses the last completed incumbent or explicit failure.
        atomic_json(root/'error.json', {'error': repr(error)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    worker(parser.parse_args().request)
