"""Tables from gaia-rl/runs/vp-sources-93/seats.json (scratch_vp_sources.py): where the points come from, and inside
each (quartet, faction) cell the upper half of the seats by final score against the lower half."""
import json
import statistics
from collections import Counter, defaultdict

rows = json.load(open('gaia-rl/runs/vp-sources-93/seats.json'))
GROUPS = {
    '광산 건설': ['Build', 'GleensBuildMine', 'SpaceGiantsBuildMine', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild',
              'TwilightRangeBuild', 'EclipseAsteroidMine', 'PlaceLostPlanet', 'SpaceshipCreditTerraform'],
    '업그레이드·기술타일': ['Upgrade', 'RebellionFreeTradingStation', 'TwilightFreeResearchLab', 'FiraksDowngradeResearchLab',
                    'RebellionGainTechTile', 'TFMarsTechBonus'],
    '연구 전진': ['ResearchAdvance', 'BescodsLowestResearchAdvance', 'EclipseResearchBoost'],
    '연방': ['FormFederation', 'TwilightReplayFederationToken'],
    '패스(부스터·타일)': ['Pass', 'other seat: Pass'],
    '함선 입장': ['ExploreSpaceship', 'GleensExploreSpaceship', 'RoundBoosterRangeExploreSpaceship',
              'TwilightRangeExploreSpaceship'],
    '함선·기타 행동': ['EclipsePlanetTypeBonus', 'ExamineArtifact', 'PowerAction', 'TinkeroidsUseTile'],
    '충전 비용': ['ChargePower'],
}
kind_group = {kind: group for group, kinds in GROUPS.items() for kind in kinds}
assert all(kind in kind_group for row in rows for kind in row['booked']), 'ungrouped action type'
COLUMNS = ['시작'] + list(GROUPS) + ['종료: 트랙', '종료: 목표+자원']
EXTRA = ['r1-3', 'r4-6', 'federations', 'green_left', 'advanced', 'level5', 'turn', 'ships']
for row in rows:
    parts = Counter({'시작': row['start'], '종료: 트랙': row['end_tracks'], '종료: 목표+자원': row['end_rest']})
    for kind, value in row['booked'].items():
        parts[kind_group[kind]] += value
    assert sum(parts.values()) == row['final'], row
    row['parts'] = parts
    row['r1-3'] = sum(value for key, value in row['by_round'].items() if key in '123')
    row['r4-6'] = sum(value for key, value in row['by_round'].items() if key in '456')
    row['ships'] = sum(row['actions'].get(kind, 0) for kind in GROUPS['함선 입장'])


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def line(label, seats):
    return (f"{label:<14}{len(seats):>4}{mean(row['final'] for row in seats):>7.1f} | "
            + ' '.join(f"{mean(row['parts'][column] for row in seats):>6.1f}" for column in COLUMNS) + ' | '
            + ' '.join(f"{mean(row[key] for row in seats):>5.2f}" for key in EXTRA))


print('columns:', 'seats final |', ' / '.join(COLUMNS), '|', ' / '.join(EXTRA))
print(line('전체', rows))
for source in ('114', '119'):
    print(line(source, [row for row in rows if row['source'] == source]))
finals = sorted(row['final'] for row in rows)
print('final score: median', statistics.median(finals), '| seats >= 150:', sum(f >= 150 for f in finals),
      '| >= 130:', sum(f >= 130 for f in finals), '| >= 120:', sum(f >= 120 for f in finals), '| < 80:', sum(f < 80 for f in finals))
print(line('승자(판 1위)', [row for row in rows if row['rank'] == 1]))
print(line('2-4위', [row for row in rows if row['rank'] > 1]))
print(line('150점 이상', [row for row in rows if row['final'] >= 150]))
print('150점 이상 좌석:', Counter(row['faction'] for row in rows if row['final'] >= 150).most_common())

# inside (quartet, faction) cells: upper half by final score against the lower half (middle seat dropped when odd)
cells = defaultdict(list)
for row in rows:
    cells[(row['quartet'], row['faction'])].append(row)
high, low, small, per_cell = [], [], [], []
for key, seats in sorted(cells.items()):
    if len(seats) < 6:
        small.append((key, len(seats)))
        continue
    seats = sorted(seats, key=lambda row: row['final'])
    half = len(seats)//2
    bottom, top = seats[:half], seats[-half:]
    high += top
    low += bottom
    per_cell.append((key, half, {column: mean(row['parts'][column] for row in top)-mean(row['parts'][column] for row in bottom)
                                 for column in COLUMNS},
                     mean(row['final'] for row in top)-mean(row['final'] for row in bottom)))
print('cells used', len(per_cell), 'seats per half', len(high), '| cells below 6 seats (left out):', small)
print(line('상위 절반', high))
print(line('하위 절반', low))
print(f"{'차이(상위-하위)':<14}{'':>4}{mean(r['final'] for r in high)-mean(r['final'] for r in low):>7.1f} | "
      + ' '.join(f"{mean(r['parts'][c] for r in high)-mean(r['parts'][c] for r in low):>6.1f}" for c in COLUMNS) + ' | '
      + ' '.join(f"{mean(r[k] for r in high)-mean(r[k] for r in low):>5.2f}" for k in EXTRA))
print('cells where the upper half is ahead on the column (of %d):' % len(per_cell),
      {column: sum(diff[column] > 0 for _, _, diff, _ in per_cell) for column in COLUMNS})
print('per faction (all quartets): seats, mean final, federations, 연방 점수, 종료 목표+자원')
by_faction = defaultdict(list)
for row in rows:
    by_faction[row['faction']].append(row)
for faction, seats in sorted(by_faction.items(), key=lambda item: -mean(row['final'] for row in item[1])):
    print(f"  {faction:<14}{len(seats):>3}{mean(r['final'] for r in seats):>7.1f}{mean(r['federations'] for r in seats):>6.2f}"
          f"{mean(r['parts']['연방'] for r in seats):>7.1f}{mean(r['parts']['종료: 목표+자원'] for r in seats):>7.1f}")
