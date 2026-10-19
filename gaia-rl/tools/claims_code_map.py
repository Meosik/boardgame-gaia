"""Fill the '코드반영(Codex기입)' column of research/strategy/gaia-strategy-claims.csv for faction claims.

User 2026-10-20 "종족 자료 묶음 중에 부족한 부분이 보이나?" → "자료에 있는거 반영 시작하고": the column was empty,
so nothing said which guide claims the teacher already follows. Each faction row gets one of:
  Y(기준) <part>   — in the base stack (the live ships teacher)
  Y(실험) <part>   — only in an opt-in / experiment factory (byfaction, byfaction_guide, ...)
  N                — not reflected
Rows of '공통' factions are left as they are. The mapping is by faction, topic and a few claim ids; edit
RULES / BY_ID when a part lands, then rerun. Prints a per-faction summary.

  .venv/bin/python tools/claims_code_map.py [--dry-run]

It also writes research/strategy/faction-claims-status.md: per faction the counts and every claim with its
status, the guide condition and the first words of the advice, so a reader sees what is still missing.
"""
import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

CSV = Path(__file__).resolve().parents[1]/'research/strategy/gaia-strategy-claims.csv'
COLUMN = '코드반영(Codex기입)'

NEW_ID = re.compile(r'^PG\d\d-S\d+$')
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
    'B15-02': 'Y(실험) 가이아 특화 종족 없으면 1–3R 가이아 2까지(niche_tracks, byfaction_guide); 파워 운용 N',
    'B19-03': 'Y(실험) 경제2·항해2 뒤 남들이 덜 간 가이아·테라·AI(niche_tracks, byfaction_guide); 라운드 보너스 N',
    'B17-01': 'Y(실험) 4돈 기술 피함(tile_prefs, byfaction_guide); 교역소·의회 운용 N',
    'H01': 'Y(실험) 4돈 기술 피함(tile_prefs, byfaction_guide)',
    'LF2-01': 'Y(실험) 하드쉬 할라 1광석1충전 기술 선호(tile_prefs); 함선별 자원 밸런스 N',
    'IR01-03': 'Y(실험) 하드쉬 할라·매드 안드로이드 4돈 기술 피함(tile_prefs); 교역소 운용 N',
    'B13-04': 'Y(실험) 큰 건물 4티어 기술 선호(tile_prefs); 4연방 계획 N',
    'B6-01': 'Y(실험) 1광석1충전 기술 피함(tile_prefs); 의회 이동·고급 기술 N',
    'B7-01': 'Y(실험) 의회 기술 선호(tile_prefs); 파워 운용 N',
    'B12-01': 'Y(실험) 4충전 → 1광석1정보·행성종류당 지식 기술(tile_prefs); 파워 운용 N',
    'B16-01': 'Y(실험) 4돈 기술 선호·4충전 기술 피함(tile_prefs); 기생 시점 N',
    'B14-01': 'Y(실험) 초반 4충전, 4R부터 행성종류당 지식 기술(tile_prefs); 파워 액션 순서 N',
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
    if NEW_ID.match(rid):
        return 'N'   # transcript claims (claims-new/) are detailed: reflected only by explicit id
    faction, topic = row['종족'].strip(), row['주제']
    for factions, keyword, value in RULES:
        if faction in factions and keyword in topic:
            return value
    return 'N'


# Claims read in full from the podcast transcripts (2026-10-20, one file per episode, kept apart for
# provenance; same columns as the main list).
NEW_DIR = CSV.parent/'claims-new'


def _read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = [name.lstrip('﻿') for name in reader.fieldnames]
        rows = [{k.lstrip('﻿'): v for k, v in row.items()} for row in reader]
    return fields, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    fields, rows = _read(CSV)
    files = [(CSV, fields, rows)]
    seen = {row['id'] for row in rows}
    for path in sorted(NEW_DIR.glob('*.csv')) if NEW_DIR.exists() else []:
        new_fields, new_rows = _read(path)
        problems = []
        if new_fields != fields:
            problems.append('header differs')
        problems += [f"row {row.get('id')}: extra or missing cells" for row in new_rows
                     if None in row or any(v is None for v in row.values())]
        problems += [f"duplicate id {row['id']}" for row in new_rows if row['id'] in seen]
        seen |= {row['id'] for row in new_rows}
        print(f'{path.name}: {len(new_rows)} rows' + (f" — PROBLEMS: {'; '.join(problems[:5])}" if problems else ''))
        if not problems:
            files.append((path, new_fields, new_rows))
    summary = defaultdict(Counter)
    every = []
    for _, _, file_rows in files:
        for row in file_rows:
            every.append(row)
            if row['종족'].strip().startswith('공통'):
                continue
            row[COLUMN] = value_for(row)
            summary[row['종족'].strip()][row[COLUMN].split(' ')[0]] += 1
    if not args.dry_run:
        for path, file_fields, file_rows in files:
            with path.open('w', encoding='utf-8-sig' if path == CSV else 'utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=file_fields, lineterminator='\n')   # LF files
                writer.writeheader()
                writer.writerows(file_rows)
    rows = every
    total = Counter()
    for faction, counts in sorted(summary.items(), key=lambda kv: -sum(kv[1].values())):
        total.update(counts)
        print(f"{faction:16s} " + '  '.join(f'{k} {v}' for k, v in sorted(counts.items())))
    print('total            ' + '  '.join(f'{k} {v}' for k, v in sorted(total.items())))
    if not args.dry_run:
        write_status(rows, summary, total)


STATUS_MD = CSV.parent/'faction-claims-status.md'
ORDER = {'N': 0, 'Y(실험)': 1, 'Y(기준)': 2}


def write_status(rows, summary, total):
    """Readable per-faction table of the column (generated; edit the CSV / this tool, not the md)."""
    def cell(text, width):
        text = ' '.join(str(text).split()).replace('|', '/')
        return text if len(text) <= width else text[:width-1]+'…'
    lines = ['# 종족 자료 현황표 (생성 파일 — `tools/claims_code_map.py`가 씀)', '',
             '출처: `gaia-strategy-claims.csv`의 종족 행 + `claims-new/PGxx.csv`(팟캐스트 회차 자막 정독, 2026-10-20). '
             '상태 Y(기준) = 배포 교사, Y(실험) = 실험 교사에만, N = 미반영.',
             '사용: 교사 코드는 이 표를 읽지 않는다. 다음에 넣을 자료를 고르는 작업 목록이고, 부품을 넣으면 도구의 규칙을 고쳐 다시 만든다.',
             '', f"전체: Y(기준) {total.get('Y(기준)', 0)} · Y(실험) {total.get('Y(실험)', 0)} · N {total.get('N', 0)}", '']
    by_faction = {}
    for row in rows:
        faction = row['종족'].strip()
        if faction.startswith('공통'):
            continue
        by_faction.setdefault(faction, []).append(row)
    for faction, items in sorted(by_faction.items(), key=lambda kv: -len(kv[1])):
        counts = summary[faction]
        lines += [f'## {faction} — Y(기준) {counts.get("Y(기준)", 0)} · Y(실험) {counts.get("Y(실험)", 0)} · N {counts.get("N", 0)}',
                  '', '| 상태 | id | 주제 | 조건 | 자료 내용(앞부분) | 반영 부품 |', '|---|---|---|---|---|---|']
        for row in sorted(items, key=lambda r: (ORDER.get(r[COLUMN].split(' ')[0], 0), r['id'])):
            status, _, part = row[COLUMN].partition(' ')
            lines.append(f"| {status} | {row['id']} | {cell(row['주제'], 14)} | {cell(row['조건'], 24)} | "
                         f"{cell(row['추천_판단'], 70)} | {cell(part, 60)} |")
        lines.append('')
    STATUS_MD.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'status table -> {STATUS_MD}')


if __name__ == '__main__':
    main()
