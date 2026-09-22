"""Validate the preserved state evaluator against the opt-in density bonus."""
import argparse
from collections import Counter
import copy
from dataclasses import dataclass
from pathlib import Path

from diagnose_research_bc import token_rows
from validate_bc import cap_state, compare, invariants, successor, write_json
from validate_bprime import CONVERSIONS, fixtures
import state_evaluation_bef as variant


@dataclass(frozen=True)
class Configured:
    density_bonus: bool = False

    def evaluate_state(self, state, actor, **kwargs):
        return variant.evaluate_state(
            state, actor,
            token_shortfall=True,
            remaining_income=True,
            distributed_research=True,
            round_resource_prices=True,
            booster_one_income=True,
            gaia_token_return=True,
            fixed_income_and_planets=True,
            direct_stock_prices=True,
            federation_satellite_tokens=True,
            density_bonus=self.density_bonus,
            **kwargs,
        )


MODELS = {
    'B-lite+k+n+f-prime+g+h+o+p': Configured(),
    'B-lite+k+n+f-prime+g+h+o+p+q': Configured(density_bonus=True),
}


def _cases():
    yield from invariants()
    for scenario, state, actor in fixtures():
        if state['round'] == 3:
            state = copy.deepcopy(state)
            state['round'] = 5
            yield 'existing', scenario, state, actor, CONVERSIONS
    state, actor = cap_state(5, 4, stress=True)
    yield 'cap-boundary', 'cap-boundary', state, actor, CONVERSIONS[:-1]


def run(output: Path) -> bool:
    output.mkdir(parents=True, exist_ok=True)
    results = {name: [] for name in MODELS}
    for suite, scenario, before, actor, conversions in _cases():
        operations = [(f'add:{key}', None) for key in variant.base.base.PRICES]
        operations.extend((kind, {'type': 'FreeAction', 'kind': kind, 'count': 1})
                          for kind in conversions)
        for conserve in (True, False):
            for label, action in operations:
                if action is None:
                    after = copy.deepcopy(before)
                    after['players'][actor]['resources'][label[4:]] += 1
                else:
                    after = successor(before, actor, action)
                for name, model in MODELS.items():
                    row = compare(before, after, actor, label, scenario,
                                  conserve, model=model)
                    row['suite'] = suite
                    results[name].append(row)

    for token in token_rows():
        before, after = token['before_state'], token['after_state']
        actor = next(p['player_id'] for p in before['players'] if p['faction'] == 'Xenos')
        for name, model in MODELS.items():
            row = compare(before, after, actor, 'OreToPower',
                          f'tokens:{token["active_tokens"]}', token['conservation'], model=model)
            row['suite'] = 'token-shortfall'
            results[name].append(row)

    for count in (3, 7):
        before, actor = cap_state(5, count, stress=True)
        after = successor(before, actor, {'type': 'FreeAction', 'kind': 'OreToPower', 'count': 1})
        for conserve in (True, False):
            for name, model in MODELS.items():
                row = compare(before, after, actor, 'OreToPower', f'tokens:{count}',
                              conserve, model=model)
                row['suite'] = 'token-shortfall'
                results[name].append(row)

    counts = {name: dict(Counter(row['status'] for row in rows))
              for name, rows in results.items()}
    failures = [(name, row) for name, rows in results.items()
                for row in rows if not row['passed']]
    write_json(output/'comparison.json', {
        'models': results,
        'counts': counts,
        'rounds_validated': [1, 3, 5, 6],
        'flags': {
            'GAIA_EXPANSION_MODE': 'lite',
            'GAIA_PASS_TIMING': '1',
            'GAIA_FIXED_INCOME_PLANETS': '1',
            'GAIA_DIRECT_STOCK_PRICES': '1',
            'GAIA_FEDERATION_VALUE': '1',
            'GAIA_FEDERATION_TOP_FIVE': '1',
            'GAIA_DENSITY_BONUS': '0/1',
        },
        'games_run': 0,
    })
    lines = ['| 구성 | 행동 | R | 상태·보존 | ΔVP | breakdown |',
             '|---|---|---:|---|---:|---|']
    for name, row in failures:
        parts = '; '.join(f'{key} {part["delta"]:+.6f}'
                          for key, part in row['changed_breakdown'].items())
        lines.append(f'| {name} | {row["action"]} | {row["round"]} | '
                     f'{row["scenario"]} {row["conservation"]} | {row["delta"]:+.6f} | {parts} |')
    (output/'failures.md').write_text('\n'.join(lines)+'\n')
    summary = {'counts': counts, 'unapproved_failures': len(failures),
               'approved_exception': None, 'games_run': 0}
    write_json(output/'summary.json', summary)
    print(summary)
    return bool(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(int(run(parser.parse_args().output)))
