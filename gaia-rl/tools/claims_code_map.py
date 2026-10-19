"""Fill the '코드반영(Codex기입)' column of research/strategy/gaia-strategy-claims.csv for faction claims.

User 2026-10-20 "종족 자료 묶음 중에 부족한 부분이 보이나?" → "자료에 있는거 반영 시작하고": the column was empty,
so nothing said which guide claims the teacher already follows. Each faction row gets one of:
  Y(기준) <part>   — in the base stack (the live ships teacher)
  Y(실험) <part>   — only in an opt-in / experiment factory (byfaction, byfaction_guide, ...)
  N                — not reflected
Rows of '공통' factions are left as they are. The mapping is by faction, topic and a few claim ids; edit
RULES / BY_ID when a part lands, then rerun. Prints a per-faction summary.

  .venv/bin/python tools/claims_code_map.py [--dry-run]
"""
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

CSV = Path(__file__).resolve().parents[1]/'research/strategy/gaia-strategy-claims.csv'
COLUMN = '코드반영(Codex기입)'

GEO = {'제노스', '타클론', '테란', '기오덴', '지오덴'}
TRACK_SET_10 = {'글린', '앰바스', '아이타', '아이타(이타르)', '네블라', '네뷸라', '파이락', '발타크', '하이브(아이비츠)', '이비츠',
                '매드안드로이드(베스코드)', '란티다', '란티드', '하드쉬할라', '하쉬할라'}
LOST_FLEET = {'모웨이드', '스페이스자이언트', '팅커로이드', '다카니안'}
OPENING = 'Y(기준) 1R 오프닝 후보 순서(UIQOO_OPENINGS·bgg_openings, LOST_FLEET_OPENINGS) — 순서만'

# Explicit claims (id -> value), checked first.
BY_ID = {
    'B11-03': 'Y(실험) 발타크 아카데미 스타트(opening_only·fixed_academy, byfaction_guide)',
    'B11-02': 'Y(실험) 가이아 1R 4단계·AI 4 상한·항해/과학 안 올림(TRACK_STEPS·TRACK_CAPS·track_set, byfaction_guide)',
    'B11-01': 'Y(실험) 의회 6R 전 안 지음(building_limits, byfaction_guide); 파워·포머 운용 N',
    'B17-03': 'Y(실험) 아카데미 뒤 경제 2(academy_economy opt-in); 점수 방법 N',
    'B17-02': 'Y(실험) 경제 2·4(TRACK_STEPS·TRACK_CAPS·track_set, byfaction_guide); 트랙 방어 N',
    'B10-01': 'Y(기준) 브레인스톤 함선 시점(brainstone_ships); 토큰 적정량 N',
    'B04-01': 'Y(기준) 테란 가이아 연구 1–3R 최하위(terrans_gaia_late)',
    'B4-01': 'Y(기준) 테란 가이아 연구 1–3R 최하위(terrans_gaia_late)',
    'B15-02': 'N (가이아 특화 종족 없을 때 가이아 — 미반영)',
    'B19-03': 'N (남들이 안 가는 테크 — 미반영)',
}
# (faction set, topic keyword) -> value; first match wins.
RULES = [
    (GEO | TRACK_SET_10 | LOST_FLEET | {'기타 종족'}, '오프닝', OPENING),
    ({'기오덴', '지오덴'}, '연구', 'Y(기준) 기오덴 1R 경제·과학 먼저, 테라3·항해2는 식민지 뒤(geodens_r1_research·geodens_guide)'),
    ({'테란'}, '연구', 'Y(기준) 가이아 후순위·track_income(terrans_gaia_late, track_income)'),
    (TRACK_SET_10, '연구', 'Y(실험) 트랙 순서·단계·상한(track_set·TRACK_STEPS·TRACK_CAPS, byfaction/byfaction_guide)'),
    (LOST_FLEET, '연구', 'Y(실험) 트랙 순서(track_set, byfaction_guide)'),
    ({'파이락'}, '건물', 'Y(실험) 아카데미 안 지음(building_limits, byfaction_guide)'),
]


def value_for(row):
    rid = (row.get('id') or '').strip()
    if rid in BY_ID:
        return BY_ID[rid]
    faction, topic = row['종족'].strip(), row['주제']
    for factions, keyword, value in RULES:
        if faction in factions and keyword in topic:
            return value
    return 'N'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    with CSV.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    summary = defaultdict(Counter)
    for row in rows:
        if row['종족'].strip().startswith('공통'):
            continue
        row[COLUMN] = value_for(row)
        summary[row['종족'].strip()][row[COLUMN].split(' ')[0]] += 1
    if not args.dry_run:
        with CSV.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')   # the file is LF
            writer.writeheader()
            writer.writerows(rows)
    total = Counter()
    for faction, counts in sorted(summary.items(), key=lambda kv: -sum(kv[1].values())):
        total.update(counts)
        print(f"{faction:16s} " + '  '.join(f'{k} {v}' for k, v in sorted(counts.items())))
    print('total            ' + '  '.join(f'{k} {v}' for k, v in sorted(total.items())))


if __name__ == '__main__':
    main()
