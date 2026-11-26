# 140a-prune-probe — 완료

사용자(2026-11-26 「일단 딱 한판 돌려볼래? 무작위 시드에서 젤 잘 풀릴거 같은 종족 4개 골라서」, 토론 1/1 수정 2건 뒤 코덱스 이상 없음, HANDOFF E362 — 이 한 판에 한해 실험 보류 예외): 6R 한 판(140) 앞의 점검. 봇 턴에서 파이썬을 못 돌려 lab에서 한다. ① 후보 줄이기 필터(teacher_patches.prune_indices, E362)를 쉬운 교사 3라운드(geo-quartet-24)에 걸어 결정마다 후보 수 전 · 후와 줄인 종류(기술 타일 · 광산 · 연방)를 센다 ② 무작위 맵 시드 하나를 뽑아 기본 14종족의 맞음 점수(모행성 종류 칸 3칸 안 테라포밍 0–1단계 행성 수 + 가이아 트랙 종족은 가이아 1 · 차원 변형 0.5, 글린은 0단계 · 가이아만)로 같은 보드 짝을 피해 4종족을 고른다. 건강 기준: 종료 코드 0, PROBE · PICK 줄이 모두 찍힘, 예외 없음. 판정 없음. 정리 턴: 줄어든 비율을 적고 PICK seedarg로 140(새 스펙 prune, 4좌석 같은 교사, 6R 1판) 큐. 예상 ≈ 5–15분(실측 없음), 제한 1시간.

종료 코드 0

```
PICK seed e362-20388
PICK scores [('Firaks', 7.0), ('Itars', 6.0), ('BalTaks', 6.0), ('Xenos', 5.5), ('Bescods', 5.0), ('Terrans', 4.0), ('Nevlas', 4.0), ('Ivits', 4.0), ('HadschHallas', 4.0), ('Taklons', 3.0), ('Geodens', 3.0), ('Ambas', 3.0), ('Gleens', 2.5), ('Lantids', 2.0)]
PICK factions Firaks,Itars,BalTaks,Xenos
PICK seedarg e362-20388@factions=Firaks,Itars,BalTaks,Xenos
PROBE decisions 38 {"before": 1784, "after": 1509, "cut_mine": 30, "cut_tile": 245}
PROBE largest (before, after, round, faction) [(138, 121, 1, 'Xenos'), (113, 83, 3, 'Taklons'), (108, 77, 3, 'Terrans'), (102, 90, 1, 'Xenos'), (88, 58, 2, 'Geodens'), (86, 66, 1, 'Xenos'), (75, 55, 3, 'Xenos'), (70, 51, 1, 'Geodens'), (70, 50, 2, 'Xenos'), (67, 47, 3, 'Xenos')]
```

<sub>agentmaco · 커밋 cc7886b · 2026-11-26T19:50:10+09:00 → 2026-11-26T19:50:13+09:00</sub>
