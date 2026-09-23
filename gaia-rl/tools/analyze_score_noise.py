"""Summarize paired four-seed score noise and observed search determinism."""
import argparse
import gzip
import json
import math
from pathlib import Path
import statistics

from scipy.stats import t


def _score(result: dict) -> int:
    return sum(faction['score'] for faction in result['factions'].values())


def _interval(values: list[float]) -> dict:
    if len(values) < 2:
        raise ValueError('at least two values required')
    average = statistics.mean(values)
    deviation = statistics.stdev(values)
    half_width = t.ppf(.975, len(values) - 1) * deviation / math.sqrt(len(values))
    return {
        'n': len(values),
        'mean': average,
        'sample_standard_deviation': deviation,
        'ci95': [average - half_width, average + half_width],
        'ci95_half_width': half_width,
    }


def _metrics(result: dict) -> dict:
    factions = result['factions'].values()
    return {
        'buildings': sum(row['buildings'] for row in factions),
        'federations': sum(row['federations'] for row in factions),
        'score': _score(result),
        'conversions': result['free_action_conversion_count'],
        'decisions': result['decisions'],
        'fallback_ratio': result['fallback_ratio'],
        'navigation': sum(row['research_tracks']['navigation'] for row in factions),
    }


def _mean_metrics(results: list[dict]) -> dict:
    rows = [_metrics(result) for result in results]
    return {key: statistics.mean(row[key] for row in rows) for key in rows[0]}


def _trace(path: Path) -> tuple[list[dict], list[str]]:
    rows = [json.loads(line) for line in gzip.open(path, 'rt')]
    return ([row['action'] for row in rows], [row['path'] for row in rows])


def _outcome_signature(result: dict) -> dict:
    return {
        'decisions': result['decisions'],
        'fallback_timeouts': result['fallback_timeouts'],
        'free_action_conversions': result['free_action_conversions'],
        'factions': result['factions'],
    }


def _determinism(first_result: dict, repeat_result: dict,
                 first_trace: Path, repeat_trace: Path) -> dict:
    first_actions, first_paths = _trace(first_trace)
    repeat_actions, repeat_paths = _trace(repeat_trace)
    return {
        'seed': first_result['seed'],
        'same_seed': first_result['seed'] == repeat_result['seed'],
        'same_action_sequence': first_actions == repeat_actions,
        'same_search_path_sequence': first_paths == repeat_paths,
        'same_final_outcome': _outcome_signature(first_result) == _outcome_signature(repeat_result),
        'first': _metrics(first_result),
        'repeat': _metrics(repeat_result),
    }


def _load(paths: list[Path]) -> list[dict]:
    return [json.loads(path.read_text()) for path in paths]


def run(args) -> dict:
    baseline = _load(args.a_result)
    current = _load(args.current_result)
    if len(baseline) != 4 or len(current) != 4:
        raise ValueError('exactly four A and four current results required')
    by_a = {row['seed']: row for row in baseline}
    by_current = {row['seed']: row for row in current}
    if set(by_a) != set(by_current) or len(by_a) != 4:
        raise ValueError('arms must contain the same four unique seeds')
    seeds = sorted(by_a)
    paired = [_score(by_current[seed]) - _score(by_a[seed]) for seed in seeds]
    paired_rows = [{'seed': seed, 'A': _score(by_a[seed]),
                    'current': _score(by_current[seed]),
                    'current_minus_A': _score(by_current[seed]) - _score(by_a[seed])}
                   for seed in seeds]
    difference = _interval(paired)
    result = {
        'score_unit': 'sum of four faction final scores per game',
        'A': {'metrics_mean': _mean_metrics(baseline),
              'score_sampling': _interval([_score(row) for row in baseline])},
        'current': {'metrics_mean': _mean_metrics(current),
                    'score_sampling': _interval([_score(row) for row in current])},
        'paired_current_minus_A': {**difference, 'rows': paired_rows,
            'minimum_distinguishable_absolute_mean_difference_four_seeds':
                difference['ci95_half_width'],
            'definition': 'observed paired-noise 95% CI half-width; zero-exclusion threshold, not an 80% power MDE'},
        'determinism': {
            'A': _determinism(
                json.loads(args.a_determinism_result[0].read_text()),
                json.loads(args.a_determinism_result[1].read_text()),
                args.a_determinism_trace[0], args.a_determinism_trace[1]),
            'current': _determinism(
                json.loads(args.current_determinism_result[0].read_text()),
                json.loads(args.current_determinism_result[1].read_text()),
                args.current_determinism_trace[0], args.current_determinism_trace[1]),
        },
    }
    result['deterministic_in_observed_repeats'] = all(
        row['same_action_sequence'] and row['same_search_path_sequence']
        and row['same_final_outcome'] for row in result['determinism'].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a-result', type=Path, action='append', required=True)
    parser.add_argument('--current-result', type=Path, action='append', required=True)
    parser.add_argument('--a-determinism-result', type=Path, action='append', required=True)
    parser.add_argument('--a-determinism-trace', type=Path, action='append', required=True)
    parser.add_argument('--current-determinism-result', type=Path, action='append', required=True)
    parser.add_argument('--current-determinism-trace', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parsed = parser.parse_args()
    for name in ('a_determinism_result', 'a_determinism_trace',
                 'current_determinism_result', 'current_determinism_trace'):
        if len(getattr(parsed, name)) != 2:
            parser.error(f'--{name.replace("_", "-")} must be given twice')
    run(parsed)
