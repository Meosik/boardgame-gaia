# 135-fed-plan-check-all-candidates — 완료

코덱스 이상 없음(사용자 2026-11-13 상시 지시), HANDOFF E308 ⏩ → E309: 연방 계산 함수(tools/fed_plan.py, 계산만) 대 엔진의 전 결정 대조 — 133-fixed-seed-ladder-baseline-12의 12판에서 연방이 불가능한 결정 전부(E307 기준 2,759개)에 대해 엔진이 낸 합법 건설 · 업그레이드 후보를 하나씩(merge=False, 커밋 68965ed) 둬 보고 '이 수를 두면 연방이 열린다 / 안 열린다'가 엔진과 같은지 센다. E308은 다섯 결정마다 하나(552결정)만 돌려 7,033개 전부 일치(열림 430 · 안 열림 6,603, 재원에 달려 뺀 것 705)였음 — 이번은 stride 1(전부). 판정 없음(교사 · 엔진 · 배포 변경 없음, 읽기 전용; 새 시드 없음 — 133의 저장된 판을 재생). 볼 것(정리 턴): ① 'C MISMATCH' 줄의 합이 0인지(0이 아니면 metrics의 examples로 fed_plan을 고침 — 봇 턴) ② A(엔진 합법인데 계산은 준비 안 됨) · B(계산은 준비됐는데 엔진 불법) · E(필요 값 미만으로 만든 연방)가 0인지(E307: A 0/79 · B 0/2,759 · 실제 연방 66/66) ③ 대조한 후보 수와 재원에 달려 뺀 수(C funds unknown) — E307의 대표 후보 대조는 18,689개 중 1,051개를 뺌 ④ engine 값이 133과 같은 49318fef인지(다르면 결과를 빌드 차이로 적음) ⑤ 걸린 시간. 한계: 맵 하나 · 12판, 건설 · 업그레이드가 아닌 수와 가격 · sites는 대조하지 않음. 예상 ≈ 8분(표본 552결정에서 환산), 제한 1시간. 리플레이 게시 없음.

종료 코드 0

```
engine 49318fef | seconds 309
  C decisions with every build / upgrade forked: 2759
  C funds unknown, not forked: 3408
  C plan: leaves it closed — engine agrees: 30911
  C plan: opens the federation — engine agrees: 1726
  decisions: 2838
  engine legal: 79
  engine not legal: 2759
  engine not legal, plan reason power: 2490
  engine not legal, plan reason route: 17
  engine not legal, plan reason satellites: 252
  exact: 2838
  federations formed: 66
```

지표

```json
{
 "engine": "49318fefc9954a00afe6e36c1b3c5dd246e06a5bba974a767964c90cb20f65e9",
 "stride": 1,
 "counts": {
  "decisions": 2838,
  "exact": 2838,
  "engine not legal, plan reason power": 2490,
  "engine not legal": 2759,
  "C decisions with every build / upgrade forked": 2759,
  "C plan: leaves it closed — engine agrees": 30911,
  "C funds unknown, not forked": 3408,
  "engine not legal, plan reason satellites": 252,
  "engine legal": 79,
  "federations formed": 66,
  "C plan: opens the federation — engine agrees": 1726,
  "engine not legal, plan reason route": 17
 },
 "examples": []
}
```

<sub>agentmaco · 커밋 a0d6286 · 2026-11-25T01:37:20+09:00 → 2026-11-25T01:42:30+09:00</sub>
