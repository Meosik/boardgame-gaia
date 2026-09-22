# 연방 후보 평가-선택 불일치 진단 — 2026-09-18

k+n 단독판의 153개 원본 행동을 같은 시드로 재생하여 플래너 선택 153/153을 재현했다. 원본 행동 로그에는 선택 사유가 없어 재현 실행의 `last_audit`를 사용했다. 다음 표의 직접 순위는 모든 합법 후보를 네이티브 `env.fork`로 평가한 최고 연방 후보의 전체 순위다.

| 결정 | 종족 | 연방 ΔVP·순위 | 최종 선택 | 평가 후보/연방 | 선택 사유 | 계획 충돌 |
|---:|---|---:|---|---:|---|---|
| 106 | Xenos | +5.031 · 2/118 | ResearchAdvance | 10/0 | quick-native-fallback | 없음 |
| 113 | Xenos | +4.071 · 3/128 | Upgrade | 9/0 | quick-native-fallback | 없음 |
| 118 | Terrans | +5.301 · 1/151 | Upgrade | 10/0 | quick-native-fallback | 없음 |
| 124 | Xenos | +3.945 · 22/264 | Build | 9/0 | quick-native-fallback | 없음 |
| 127 | Terrans | +4.218 · 1/191 | FormFederation | 9/3 | quick-native-fallback | 없음 |
| 128 | HadschHallas | +3.833 · 1/42 | Pass | 1/0 | quick-native-fallback | 없음 |
| 129 | Xenos | +3.439 · 4/352 | ResearchAdvance | 6/0 | quick-native-fallback | 없음 |
| 130 | Taklons | +5.822 · 1/61 | FormFederation | 11/10 | quick-native-fallback | 없음 |
| 136 | Xenos | +3.439 · 1/342 | PowerAction | 8/0 | quick-native-fallback | 없음 |
| 144 | Xenos | +5.359 · 24/367 | Upgrade | 8/0 | quick-native-fallback | 없음 |
| 146 | Xenos | +5.359 · 1/326 | Upgrade | 7/0 | quick-native-fallback | 없음 |
| 148 | Xenos | +6.512 · 1/447 | ExploreSpaceship | 2/0 | quick-native-fallback | 없음 |
| 149 | Xenos | +6.512 · 1/517 | ExploreSpaceship | 2/0 | quick-native-fallback | 없음 |
| 150 | Xenos | +6.512 · 1/589 | ExploreSpaceship | 2/0 | quick-native-fallback | 없음 |
| 151 | Xenos | +6.512 · 1/665 | ExamineArtifact | 8/3 | quick-native-fallback | 없음 |

15건 모두 fallback이었다. 정상 탐색의 완료 비교(`plans`)는 0건이고 저장 계획(`memory_plans`)도 없었다. 따라서 계획 잠금 또는 계획 목표 충돌이 아니라, 시간 제한으로 정상 탐색이 완료되지 않아 한 단계 fallback으로 전환된 것. 이 fallback은 `Pass→Build→Upgrade→GaiaFormation→ResearchAdvance→PowerAction`을 먼저 놓고 연방 선언은 기본 우선순위 6으로 뒤에 둔다. 제노스의 직접 1위 연방 6건(136·146·148·149·150·151) 중 앞의 5건은 연방 후보를 하나도 평가하지 않았고, 마지막은 657개 중 3개만 평가해 직접 최고 후보(인덱스 655)를 보지 못했다. 원인은 **fallback 후보 평가 서순 + 짧은 탐색 시간**이다. 연방 후보가 금지·제외된 것은 아니므로 엄밀한 후보 필터 문제는 아니다.

## 참고 측정

위성 없는 최대 인접 건물군의 파워(필요 파워는 네 종족 모두 7):

| 라운드 | Terrans | HadschHallas | Taklons | Xenos |
|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 1 | 1 |
| 2 | 1 | 1 | 1 | 1 |
| 3 | 2 | 2 | 2 | 1 |
| 4 | 3 | 2 | 2 | 2 |
| 5 | 3 | 3 | 2 | 2 |
| 6 | 3 | 4 | 3 | 4 |

평가기가 선택한 확장 기회 좌표의 기존 자기 건물과 거리 1 인접률: 모든 순위 59/93 (63.4%); 각 결정의 최상위 기회 37/59 (62.7%). 실제 건설 행동의 인접률이 아니라 평가 기회 좌표의 비율이다.

## (o) 적용 전 확인

현행 준비도는 이미 `최대 토큰 보상 VP × 0.5 × min(1, 건물 파워/필요 파워)^2 × min(1, 토큰/링크 수)`다. 따라서 지시한 `완성 확률 × 보상 × 0.5`를 그대로 중복 적용하지 않고, 확률을 무엇으로 정의할지 결정해야 한다. Terrans R3 통제 상태의 네이티브 +12 대비 평가 −1.416에서 위성 토큰 부족 벌점 −6.39만 제거하면 +4.974로 50% 목표 +6에 아직 못 미친다. 준비도 확률을 추가로 낮출 기준이 필요하다. 생산 평가 코드와 플래너 정책은 이 진단에서 변경하지 않았다.
