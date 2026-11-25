# 137-teacher-early-upgrades — 완료

코덱스 이상 없음(사용자 2026-11-13 상시 지시), HANDOFF E339: 사용자 「점수 비교 유지에서 초반에 업그레이드를 잘 안하진 않나?」 → 현재 교사 6R 완주 141판(114 · 119 · 123, 엔진 fc19671c) 재생(읽기 전용, lab/scratch_e339_upgrades.py). 1–2라운드 주 차례 결정(후보에 패스)을 selected(업그레이드 둠) · lost_compare(업그레이드 합법, 업그레이드 계획이 비교됐는데 다른 계획이 이김) · menu_only(메뉴 · 메뉴 풀에만 있고 비교 못 감) · not_in_menu(합법인데 메뉴에 없음) · not_legal로 나눠 종족별 · 합법 대상 건물별로 셈; 좌석-판마다 1–2R 업그레이드 대상별 수, 첫 업그레이드 라운드, 무료 업그레이드(광석 · 돈 안 줄어듦), lost_compare의 값 차이(최고 계획 − 최고 업그레이드 계획) 분위. 판정 없음(교사 · 엔진 변경 없음, 새 판 없음). 볼 것(정리 턴): ① logged.has_compared_field / main_decisions — 비교 기록이 없는 결정 비율(없으면 lost_compare/menu_only를 나눌 수 없다고 적음) ② 종족별 분류 · 첫 업그레이드 라운드(전문가 기록 observed-uiqoo-20260916-log.md는 1판 4종족이라 같은 종족끼리만 참고, 아이비츠 시작 의회 · 무료 교역소는 따로) ③ lost_compare 값 차이와 예시 ④ engine이 fc19671c인지 ⑤ error_count. 규칙 변경(초반 업그레이드 우선 · 수입 평가)은 결과를 보고 사용자에게 묻는다. 예상 ≈ 15분(141판 전체 재생), 제한 1시간.

종료 코드 0

```
{"engine": "49318fefc9954a00afe6e36c1b3c5dd246e06a5bba974a767964c90cb20f65e9", "games": 18, "logged": {"has_compared_field": 5349, "main_decisions": 5349}, "error_count": 123}
ALL {'selected': 1143, 'lost_compare': 14, 'menu_only': 457, 'not_in_menu': 993, 'not_legal': 2742} first: None
Ambas {'selected': 75, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 135, 'not_legal': 183} first: {1: 9}
BalTaks {'selected': 14, 'lost_compare': 0, 'menu_only': 1, 'not_in_menu': 36, 'not_legal': 2} first: None
Bescods {'selected': 20, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 22, 'not_legal': 0} first: None
Darkanians {'selected': 70, 'lost_compare': 0, 'menu_only': 1, 'not_in_menu': 58, 'not_legal': 181} first: {1: 4}
Firaks {'selected': 101, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 51, 'not_legal': 210} first: {1: 1}
Geodens {'selected': 28, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 37, 'not_legal': 66} first: {1: 4}
Gleens {'selected': 31, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 23, 'not_legal': 4} first: None
HadschHallas {'selected': 101, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 68, 'not_legal': 243} first: {1: 9}
Itars {'selected': 28, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 24, 'not_legal': 1} first: None
Ivits {'selected': 45, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 130, 'not_legal': 230} first: {2: 1}
Lantids {'selected': 82, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 98, 'not_legal': 189} first: {1: 1}
Moweyds {'selected': 11, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 22, 'not_legal': 27} first: {1: 1}
Nevlas {'selected': 86, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 184, 'not_legal': 175} first: {1: 1}
SpaceGiants {'selected': 71, 'lost_compare': 0, 'menu_only': 2, 'not_in_menu': 41, 'not_legal': 193} first: {1: 4}
Taklons {'selected': 29, 'lost_compare': 0, 'menu_only': 24, 'not_in_menu': 6, 'not_legal': 85} first: {1: 4}
Terrans {'selected': 167, 'lost_compare': 7, 'menu_only': 209, 'not_in_menu': 24, 'not_legal': 320} first: {1: 16}
Tinkeroids {'selected': 6, 'lost_compare': 0, 'menu_only': 0, 'not_in_menu': 18, 'not_legal': 32} first: {1: 1}
Xenos {'selected': 178, 'lost_compare': 7, 'menu_only': 220, 'not_in_menu': 16, 'not_legal': 601} first: {1: 16}
```

지표

```json
{
 "engine": "49318fefc9954a00afe6e36c1b3c5dd246e06a5bba974a767964c90cb20f65e9",
 "games": 18,
 "rounds": "1-2",
 "logged": {
  "has_compared_field": 5349,
  "main_decisions": 5349
 },
 "classes_by_faction": {
  "ALL": {
   "selected": 1143,
   "lost_compare": 14,
   "menu_only": 457,
   "not_in_menu": 993,
   "not_legal": 2742
  },
  "Ambas": {
   "selected": 75,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 135,
   "not_legal": 183
  },
  "BalTaks": {
   "selected": 14,
   "lost_compare": 0,
   "menu_only": 1,
   "not_in_menu": 36,
   "not_legal": 2
  },
  "Bescods": {
   "selected": 20,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 22,
   "not_legal": 0
  },
  "Darkanians": {
   "selected": 70,
   "lost_compare": 0,
   "menu_only": 1,
   "not_in_menu": 58,
   "not_legal": 181
  },
  "Firaks": {
   "selected": 101,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 51,
   "not_legal": 210
  },
  "Geodens": {
   "selected": 28,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 37,
   "not_legal": 66
  },
  "Gleens": {
   "selected": 31,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 23,
   "not_legal": 4
  },
  "HadschHallas": {
   "selected": 101,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 68,
   "not_legal": 243
  },
  "Itars": {
   "selected": 28,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 24,
   "not_legal": 1
  },
  "Ivits": {
   "selected": 45,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 130,
   "not_legal": 230
  },
  "Lantids": {
   "selected": 82,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 98,
   "not_legal": 189
  },
  "Moweyds": {
   "selected": 11,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 22,
   "not_legal": 27
  },
  "Nevlas": {
   "selected": 86,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 184,
   "not_legal": 175
  },
  "SpaceGiants": {
   "selected": 71,
   "lost_compare": 0,
   "menu_only": 2,
   "not_in_menu": 41,
   "not_legal": 193
  },
  "Taklons": {
   "selected": 29,
   "lost_compare": 0,
   "menu_only": 24,
   "not_in_menu": 6,
   "not_legal": 85
  },
  "Terrans": {
   "selected": 167,
   "lost_compare": 7,
   "menu_only": 209,
   "not_in_menu": 24,
   "not_legal": 320
  },
  "Tinkeroids": {
   "selected": 6,
   "lost_compare": 0,
   "menu_only": 0,
   "not_in_menu": 18,
   "not_legal": 32
  },
  "Xenos": {
   "selected": 178,
   "lost_compare": 7,
   "menu_only": 220,
   "not_in_menu": 16,
   "not_legal": 601
  }
 },
 "classes_by_legal_target": {
  "Academy": {
   "selected": 133,
   "lost_compare": 0,
   "menu_only": 4,
   "not_in_menu": 8,
   "not_legal": 0
  },
  "PlanetaryInstitute": {
   "selected": 396,
   "lost_compare": 0,
   "menu_only": 42,
   "not_in_menu": 60,
   "not_legal": 0
  },
  "ResearchLab": {
   "selected": 484,
   "lost_compare": 1,
   "menu_only": 57,
   "not_in_menu": 85,
   "not_legal": 0
  },
  "TradingStation": {
   "selected": 1043,
   "lost_com
```

<sub>agentmaco · 커밋 73a4997 · 2026-11-26T01:47:31+09:00 → 2026-11-26T01:47:57+09:00</sub>
